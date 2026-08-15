from __future__ import annotations

from dataclasses import dataclass

from .phase_5_design_matrix import _feature, _program
from .phase_6_morphogenesis_matrix import morphogenesis_matrix
from .semantic_contract import DesignSemanticProgram


@dataclass(frozen=True, slots=True)
class B28CapabilityCase:
    id: str
    label: str
    expected_profile: str
    base_family: str
    program: DesignSemanticProgram


def _surface_probe(name: str) -> list[dict]:
    return [
        _feature(
            f"{name}_surface_probe",
            "ridge",
            "slit",
            "recessed",
            region="front",
            horizontal=0.0,
            vertical=0.48,
            width=0.18,
            height=0.045,
            depth=1.0,
        )
    ]


def _base_program(
    case_id: str,
    prompt: str,
    *,
    height: float,
    width: float,
    depth: float,
    opening_shape: str,
    opening_width: float,
    opening_depth: float,
    tags: list[str],
) -> DesignSemanticProgram:
    return _program(
        case_id,
        prompt,
        family="organic" if opening_shape != "polygonal" else "hexagonal",
        height=height,
        width=width,
        depth=depth,
        opening_shape=opening_shape,
        opening_width=opening_width,
        opening_depth=opening_depth,
        style_tags=tags,
        features=_surface_probe(case_id),
        relations=[],
    )


def b28_capability_matrix() -> tuple[B28CapabilityCase, ...]:
    legacy = {case.id: case.program for case in morphogenesis_matrix()}
    return (
        B28CapabilityCase(
            "organic_asymmetric",
            "Organic asymmetric",
            "helical_chain",
            "freeform_organic",
            legacy["helical"],
        ),
        B28CapabilityCase(
            "truncated_cone",
            "Truncated cone",
            "tapered_revolution",
            "tapered_revolution",
            _base_program(
                "b28_tapered_planter",
                "Maceta troncocónica funcional, base menor y boca mayor.",
                height=118.0,
                width=118.0,
                depth=118.0,
                opening_shape="circular",
                opening_width=0.63,
                opening_depth=0.63,
                tags=["minimal", "tapered_revolution", "conical"],
            ),
        ),
        B28CapabilityCase(
            "cubic_architectural",
            "Cubic architectural",
            "cuboid",
            "cuboid",
            _base_program(
                "b28_cuboid_planter",
                "Maceta cúbica arquitectónica con caras planas y esquinas controladas.",
                height=108.0,
                width=112.0,
                depth=112.0,
                opening_shape="polygonal",
                opening_width=0.67,
                opening_depth=0.67,
                tags=["geometric", "architectural", "cuboid"],
            ),
        ),
        B28CapabilityCase(
            "rectangular_planter",
            "Rectangular horizontal",
            "rectangular_prism",
            "rectangular_prism",
            _base_program(
                "b28_rectangular_planter",
                "Jardinera rectangular horizontal funcional, claramente no radial.",
                height=82.0,
                width=172.0,
                depth=88.0,
                opening_shape="elliptical",
                opening_width=0.72,
                opening_depth=0.62,
                tags=["geometric", "rectangular_prism", "elongated_planter"],
            ),
        ),
        B28CapabilityCase(
            "ovoid_sculptural",
            "Ovoid sculptural",
            "ovoid",
            "ovoid",
            _base_program(
                "b28_ovoid_planter",
                "Maceta ovoide escultórica de vientre amplio y boca funcional.",
                height=126.0,
                width=116.0,
                depth=110.0,
                opening_shape="elliptical",
                opening_width=0.52,
                opening_depth=0.48,
                tags=["organic", "sculptural", "ovoid", "bulbous"],
            ),
        ),
        B28CapabilityCase(
            "polygonal_faceted",
            "Polygonal faceted",
            "axial_faceted",
            "polygonal_faceted",
            legacy["faceted"],
        ),
        B28CapabilityCase(
            "freeform_dynamic",
            "Freeform dynamic",
            "helical_chain",
            "freeform_asymmetric",
            legacy["helical"],
        ),
        B28CapabilityCase(
            "compound_multivolume",
            "Compound multivolume",
            "compound_multivolume",
            "compound_multivolume",
            _base_program(
                "b28_multivolume_planter",
                "Maceta escultórica compuesta por varias masas fusionadas en un solo recipiente.",
                height=120.0,
                width=132.0,
                depth=112.0,
                opening_shape="elliptical",
                opening_width=0.55,
                opening_depth=0.50,
                tags=["organic", "compound_multivolume", "sculptural"],
            ),
        ),
    )
