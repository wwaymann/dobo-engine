from __future__ import annotations

from dataclasses import dataclass
import re

from .semantic_contract import DesignSemanticProgram
from .semantic_parser import SemanticProgramParser


@dataclass(frozen=True, slots=True)
class DesignMatrixCase:
    id: str
    label: str
    expected_body_profile: str
    expected_style_profile: str
    expected_component: str
    program: DesignSemanticProgram


def _feature(
    feature_id: str,
    concept: str,
    form_hint: str,
    surface_effect: str,
    *,
    region: str,
    horizontal: float,
    vertical: float,
    width: float,
    height: float,
    depth: float,
    roll: float = 0.0,
) -> dict:
    return {
        "id": feature_id,
        "concept": concept,
        "form_hint": form_hint,
        "surface_effect": surface_effect,
        "anchor": {
            "region": region,
            "horizontal": horizontal,
            "vertical": vertical,
            "roll_degrees": roll,
        },
        "size": {
            "width_ratio": width,
            "height_ratio": height,
            "depth_mm": depth,
        },
        "priority": "required",
        "can_omit": False,
        "confidence": 0.98,
    }


def _relation(kind: str, subject: str, target: str) -> dict:
    return {
        "kind": kind,
        "subject_id": subject,
        "object_id": target,
        "confidence": 0.98,
    }


def _normalized_program_id(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9_]+", "_", value.strip().lower())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    if len(normalized) < 2:
        normalized = f"dobo_{normalized or 'design'}"
    return normalized[:64].rstrip("_")


def _program(
    case_id: str,
    prompt: str,
    *,
    family: str,
    height: float,
    width: float,
    depth: float,
    opening_shape: str,
    opening_width: float,
    opening_depth: float,
    style_tags: list[str],
    features: list[dict],
    relations: list[dict],
) -> DesignSemanticProgram:
    data = {
        "schema_version": "3A.1",
        "id": _normalized_program_id(case_id),
        "product_kind": "planter",
        "source": {
            "kind": "prompt",
            "prompt": prompt,
            "image_reference": None,
        },
        "body": {
            "family": family,
            "height_mm": height,
            "width_mm": width,
            "depth_mm": depth,
            "opening_shape": opening_shape,
            "opening_width_ratio": opening_width,
            "opening_depth_ratio": opening_depth,
            "style_tags": style_tags,
        },
        "features": features,
        "relations": relations,
        "manufacturing": {
            "minimum_wall_mm": 4.0,
            "minimum_feature_mm": 1.2,
            "maximum_relief_depth_mm": 3.0,
            "drainage_required": True,
            "multicolor_requested": False,
        },
        "assumptions": [],
        "ambiguities": [],
    }
    return SemanticProgramParser().parse_dict(data)


def _cat() -> DesignSemanticProgram:
    features = [
        _feature("left_ear", "ear", "point", "raised", region="upper", horizontal=-0.72, vertical=0.92, width=0.20, height=0.25, depth=3.0, roll=-8.0),
        _feature("right_ear", "ear", "point", "raised", region="upper", horizontal=0.72, vertical=0.92, width=0.20, height=0.25, depth=3.0, roll=8.0),
        _feature("left_eye", "eye", "slit", "recessed", region="front", horizontal=-0.28, vertical=0.62, width=0.11, height=0.07, depth=1.6),
        _feature("right_eye", "eye", "slit", "recessed", region="front", horizontal=0.28, vertical=0.62, width=0.11, height=0.07, depth=1.6),
        _feature("muzzle", "muzzle", "oval", "raised", region="front", horizontal=0.0, vertical=0.43, width=0.34, height=0.22, depth=3.2),
        _feature("nose", "nose", "point", "raised", region="front", horizontal=0.0, vertical=0.50, width=0.12, height=0.10, depth=2.6),
    ]
    relations = [
        _relation("mirror_of", "left_ear", "right_ear"),
        _relation("mirror_of", "left_eye", "right_eye"),
        _relation("centered_on", "nose", "muzzle"),
        _relation("below", "muzzle", "left_eye"),
        _relation("below", "muzzle", "right_eye"),
    ]
    return _program(
        "matrix_cat_planter",
        "Maceta infantil de gato con orejas triangulares y rostro suave.",
        family="character",
        height=112.0,
        width=108.0,
        depth=104.0,
        opening_shape="elliptical",
        opening_width=0.58,
        opening_depth=0.54,
        style_tags=["childlike", "soft"],
        features=features,
        relations=relations,
    )


def _rabbit() -> DesignSemanticProgram:
    features = [
        _feature("left_ear", "ear", "leaf", "raised", region="upper", horizontal=-0.62, vertical=0.90, width=0.15, height=0.36, depth=2.8, roll=-5.0),
        _feature("right_ear", "ear", "leaf", "raised", region="upper", horizontal=0.62, vertical=0.90, width=0.15, height=0.36, depth=2.8, roll=5.0),
        _feature("left_eye", "eye", "disc", "recessed", region="front", horizontal=-0.26, vertical=0.61, width=0.10, height=0.10, depth=1.5),
        _feature("right_eye", "eye", "disc", "recessed", region="front", horizontal=0.26, vertical=0.61, width=0.10, height=0.10, depth=1.5),
        _feature("muzzle", "muzzle", "oval", "raised", region="front", horizontal=0.0, vertical=0.42, width=0.30, height=0.19, depth=3.0),
        _feature("nose", "nose", "oval", "raised", region="front", horizontal=0.0, vertical=0.50, width=0.10, height=0.08, depth=2.3),
    ]
    relations = [
        _relation("mirror_of", "left_ear", "right_ear"),
        _relation("mirror_of", "left_eye", "right_eye"),
        _relation("centered_on", "nose", "muzzle"),
        _relation("below", "muzzle", "left_eye"),
        _relation("below", "muzzle", "right_eye"),
    ]
    return _program(
        "matrix_rabbit_planter",
        "Maceta orgánica de conejo con orejas largas y rostro mínimo.",
        family="organic",
        height=118.0,
        width=104.0,
        depth=100.0,
        opening_shape="elliptical",
        opening_width=0.56,
        opening_depth=0.52,
        style_tags=["organic", "soft"],
        features=features,
        relations=relations,
    )


def _botanical() -> DesignSemanticProgram:
    positions = (-0.82, -0.48, -0.16, 0.16, 0.48, 0.82)
    features = [
        _feature(
            f"leaf_{index + 1}",
            "leaf",
            "leaf",
            "raised",
            region="all_around",
            horizontal=horizontal,
            vertical=0.57 + (0.04 if index % 2 else -0.03),
            width=0.15,
            height=0.23,
            depth=2.5,
            roll=-18.0 + index * 7.2,
        )
        for index, horizontal in enumerate(positions)
    ]
    features.append(
        _feature("front_seed", "badge", "disc", "recessed", region="front", horizontal=0.0, vertical=0.43, width=0.13, height=0.13, depth=1.4)
    )
    relations = [
        _relation("repeated_from", f"leaf_{index}", f"leaf_{index + 1}")
        for index in range(1, 6)
    ]
    return _program(
        "matrix_botanical_planter",
        "Maceta botánica orgánica con corona radial de hojas.",
        family="organic",
        height=108.0,
        width=112.0,
        depth=112.0,
        opening_shape="circular",
        opening_width=0.60,
        opening_depth=0.60,
        style_tags=["botanical", "organic"],
        features=features,
        relations=relations,
    )


def _geometric() -> DesignSemanticProgram:
    features = [
        _feature("front_ridge", "ridge", "slit", "recessed", region="front", horizontal=0.0, vertical=0.52, width=0.28, height=0.06, depth=1.0),
        _feature("left_ridge", "ridge", "slit", "recessed", region="left", horizontal=0.0, vertical=0.52, width=0.28, height=0.06, depth=1.0),
        _feature("right_ridge", "ridge", "slit", "recessed", region="right", horizontal=0.0, vertical=0.52, width=0.28, height=0.06, depth=1.0),
        _feature("back_ridge", "ridge", "slit", "recessed", region="back", horizontal=0.0, vertical=0.52, width=0.28, height=0.06, depth=1.0),
    ]
    relations = [
        _relation("repeated_from", "front_ridge", "left_ridge"),
        _relation("repeated_from", "left_ridge", "back_ridge"),
        _relation("repeated_from", "back_ridge", "right_ridge"),
    ]
    return _program(
        "matrix_geometric_planter",
        "Maceta geométrica facetada con ranuras mínimas repetidas.",
        family="hexagonal",
        height=114.0,
        width=108.0,
        depth=108.0,
        opening_shape="polygonal",
        opening_width=0.58,
        opening_depth=0.58,
        style_tags=["geometric", "minimal"],
        features=features,
        relations=relations,
    )


def design_matrix() -> tuple[DesignMatrixCase, ...]:
    return (
        DesignMatrixCase("cat", "Cat", "character", "childlike", "pointed", _cat()),
        DesignMatrixCase("rabbit", "Rabbit", "organic", "organic", "elongated", _rabbit()),
        DesignMatrixCase("botanical", "Botanical", "organic", "organic", "leaf", _botanical()),
        DesignMatrixCase("geometric", "Geometric", "faceted_proxy", "geometric", "relief", _geometric()),
    )
