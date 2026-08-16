from __future__ import annotations

from dataclasses import dataclass

from .phase_5_design_matrix import _feature, _program
from .semantic_contract import DesignSemanticProgram


@dataclass(frozen=True, slots=True)
class DVisualCase:
    id: str
    label: str
    expected_profile: str
    visual_goal: str
    program: DesignSemanticProgram


def _surface_probe(case_id: str) -> list[dict]:
    return [
        _feature(
            f"{case_id}_probe",
            "ridge",
            "slit",
            "recessed",
            region="front",
            horizontal=0.0,
            vertical=0.44,
            width=0.12,
            height=0.035,
            depth=0.8,
        )
    ]


def _case(
    case_id: str,
    label: str,
    expected_profile: str,
    visual_goal: str,
    *,
    height: float,
    width: float,
    depth: float,
    opening_shape: str,
    tags: list[str],
) -> DVisualCase:
    program = _program(
        f"d_{case_id}",
        visual_goal,
        family="hexagonal" if "origami" in tags else "organic",
        height=height,
        width=width,
        depth=depth,
        opening_shape=opening_shape,
        opening_width=0.58,
        opening_depth=0.55,
        style_tags=tags,
        features=_surface_probe(case_id),
        relations=[],
    )
    return DVisualCase(case_id, label, expected_profile, visual_goal, program)


def d_visual_matrix() -> tuple[DVisualCase, ...]:
    return (
        _case(
            "organic_asymmetric",
            "Organic asymmetric",
            "undulating_shell",
            "Maceta orgánica asimétrica de silueta ondulada, natural y claramente no cilíndrica.",
            height=112.0, width=132.0, depth=118.0, opening_shape="elliptical",
            tags=["organic", "organic_asymmetric", "undulating"],
        ),
        _case(
            "figurative_sculptural",
            "Figurative / sculptural",
            "sculptural_cluster",
            "Maceta escultórica compuesta por masas jerárquicas y una silueta frontal reconociblemente compleja.",
            height=126.0, width=116.0, depth=108.0, opening_shape="elliptical",
            tags=["sculptural_cluster", "compound_sculpture"],
        ),
        _case(
            "geometric_faceted",
            "Geometric / faceted",
            "origami_crown",
            "Maceta geométrica facetada de planos tensos y corona arquitectónica.",
            height=108.0, width=128.0, depth=128.0, opening_shape="polygonal",
            tags=["geometric", "origami", "architectural_folded"],
        ),
        _case(
            "complex_relief_body",
            "Complex relief body",
            "undulating_shell",
            "Cuerpo con jerarquía de ondas grandes y pequeñas, preparado para relieve profundo posterior.",
            height=110.0, width=130.0, depth=122.0, opening_shape="elliptical",
            tags=["biomorphic_shell", "wavy_shell"],
        ),
        _case(
            "integrated_text_body",
            "Integrated text body",
            "sculptural_cluster",
            "Cuerpo frontal escultórico con superficie dominante amplia destinada a texto conformado.",
            height=112.0, width=138.0, depth=108.0, opening_shape="elliptical",
            tags=["sculptural_cluster", "multi_volume_sculptural"],
        ),
        _case(
            "perforated_biomorphic_body",
            "Perforated / biomorphic body",
            "undulating_shell",
            "Envolvente biomórfica ondulada destinada a una segunda fase de vacíos y perforaciones orgánicas.",
            height=116.0, width=130.0, depth=126.0, opening_shape="elliptical",
            tags=["organic_asymmetric", "biomorphic_shell"],
        ),
        _case(
            "spiral_dynamic",
            "Spiral / dynamic",
            "spiral_ribbed",
            "Maceta de ascenso helicoidal con secciones facetadas en torsión continua.",
            height=120.0, width=122.0, depth=122.0, opening_shape="circular",
            tags=["spiral_ribbed", "dynamic_spiral", "helical_ribs"],
        ),
        _case(
            "origami_architectural",
            "Origami / architectural",
            "origami_crown",
            "Maceta arquitectónica plegada con ritmo poligonal, variación angular y corona marcada.",
            height=122.0, width=132.0, depth=132.0, opening_shape="polygonal",
            tags=["origami", "folded_crown", "pleated"],
        ),
    )
