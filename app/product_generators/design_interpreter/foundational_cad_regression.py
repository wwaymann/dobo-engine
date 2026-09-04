from __future__ import annotations

"""Focused physical regression for promoted cylinder and triangular-prism CAD."""

import json
from pathlib import Path

from .phase_5_design_matrix import _feature, _program
from .structural_pipeline import DoboStructuralPipeline


OUTPUT = Path("outputs-ci/foundational-cad")


def _text(effect: str, concept: str = "walter", depth: float = 1.2) -> dict:
    return _feature(
        "front_text",
        concept,
        "text",
        effect,
        region="front",
        horizontal=0.0,
        vertical=0.52,
        width=0.55,
        height=0.14,
        depth=depth,
    )


def _cylinder(case_id: str, prompt: str, *, effect: str | None = None, concept: str = "walter"):
    features = [] if effect is None else [_text(effect, concept)]
    return _program(
        case_id,
        prompt,
        family="cylindrical",
        height=115.0,
        width=110.0,
        depth=110.0,
        opening_shape="circular",
        opening_width=0.72,
        opening_depth=0.72,
        style_tags=["cylindrical"],
        features=features,
        relations=[],
    )


def _triangle(case_id: str, prompt: str, *, effect: str | None = None, concept: str = "walter", depth: float = 1.2):
    features = [] if effect is None else [_text(effect, concept, depth)]
    return _program(
        case_id,
        prompt,
        family="hexagonal",
        height=112.0,
        width=120.0,
        depth=120.0,
        opening_shape="polygonal",
        opening_width=0.72,
        opening_depth=0.72,
        style_tags=["triangular_prism"],
        features=features,
        relations=[],
    )


def run() -> dict:
    cases = {
        "cylinder_plain": _cylinder("cylinder_plain", "Crea una maceta cilindro"),
        "cylinder_emboss": _cylinder(
            "cylinder_emboss",
            "Crea una maceta cilindro con el texto WALTER en sobrerrelieve sobre la cara frontal.",
            effect="raised",
        ),
        "cylinder_deboss": _cylinder(
            "cylinder_deboss",
            "Crea una maceta cilindro con el texto WALTER en bajorrelieve sobre la cara frontal.",
            effect="recessed",
        ),
        "cylinder_multiline": _cylinder(
            "cylinder_multiline",
            "Crea una maceta cilindro con texto en sobrerrelieve sobre la cara frontal, centrado y distribuido exactamente en tres líneas: línea 1: PLANTA; línea 2: UNA; línea 3: IDEA.",
            effect="raised",
            concept="planta",
        ),
        "triangle_plain": _triangle("triangle_plain", "Crea una maceta prisma triangular"),
        "triangle_emboss": _triangle(
            "triangle_emboss",
            "Crea una maceta prisma triangular con el texto WALTER en sobrerrelieve sobre la cara frontal.",
            effect="raised",
        ),
        "triangle_deboss": _triangle(
            "triangle_deboss",
            "Crea una maceta prisma triangular con el texto WALTER en bajorrelieve sobre la cara frontal.",
            effect="recessed",
        ),
        "triangle_deep_deboss": _triangle(
            "triangle_deep_deboss",
            "Crea una maceta prisma triangular con el texto WALTER en bajorrelieve profundo sobre la cara frontal.",
            effect="recessed",
            depth=12.0,
        ),
        "triangle_multiline": _triangle(
            "triangle_multiline",
            "Crea una maceta prisma triangular con texto en sobrerrelieve sobre la cara frontal, centrado y distribuido exactamente en tres líneas: línea 1: PLANTA; línea 2: UNA; línea 3: IDEA.",
            effect="raised",
            concept="planta",
        ),
    }

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pipeline = DoboStructuralPipeline()
    results: dict[str, dict] = {}

    for name, program in cases.items():
        result = pipeline.generate_from_semantic(
            program,
            output_root=OUTPUT / name,
            generation_budget_seconds=120.0,
        )
        motor = json.loads(Path(result.motor_path).read_text(encoding="utf-8"))
        checks = dict(result.mesh_result.semantic_checks or {})
        is_cylinder = name.startswith("cylinder")
        expected_route = (
            "analytic_cad_cylindrical_text"
            if is_cylinder
            else "analytic_cad_triangular_primitive"
        )
        entries = (
            motor.get("_analytic_cylindrical", {}).get("text_entries", [])
            if is_cylinder
            else motor.get("_analytic_triangular", {}).get("text_entries", [])
        )
        expected_lines = 3 if "multiline" in name else (0 if "plain" in name else 1)
        assertions = {
            "route": motor.get("_capability_route") == expected_route,
            "watertight": bool(result.mesh_result.watertight),
            "winding_consistent": bool(result.mesh_result.winding_consistent),
            "one_component": int(result.mesh_result.component_count) == 1,
            "compact_cad_mesh": 0 < int(result.mesh_result.vertex_count) < 30_000,
            "cavity": bool(checks.get("cavity_is_empty")),
            "opening": bool(checks.get("opening_is_clear")),
            "drain": bool(checks.get("drain_is_clear")),
            "line_count": len(entries) == expected_lines,
            "triangle_profile": bool(checks.get("profile_is_triangular")) if not is_cylinder else True,
            "triangle_text_volume": bool(checks.get("native_text_volume_changed")) if (not is_cylinder and expected_lines) else True,
        }
        if not all(assertions.values()):
            failed = [key for key, value in assertions.items() if not value]
            raise RuntimeError(f"{name} foundational CAD regression failed: {failed}")

        results[name] = {
            "route": motor.get("_capability_route"),
            "vertices": result.mesh_result.vertex_count,
            "faces": result.mesh_result.face_count,
            "generation_seconds": result.mesh_result.generation_seconds,
            "line_count": len(entries),
            "volume_mm3": result.mesh_result.volume_mm3,
            "assertions": assertions,
            "stl": result.stl_path,
        }

    # The same exact cylinder body is used for all four cases, so the volume
    # direction independently proves that its text was physically fused/cut.
    plain_volume = float(results["cylinder_plain"]["volume_mm3"])
    emboss_volume = float(results["cylinder_emboss"]["volume_mm3"])
    deboss_volume = float(results["cylinder_deboss"]["volume_mm3"])
    multiline_volume = float(results["cylinder_multiline"]["volume_mm3"])
    cylinder_volume_assertions = {
        "emboss_adds_volume": emboss_volume > plain_volume + 1e-3,
        "deboss_removes_volume": deboss_volume < plain_volume - 1e-3,
        "multiline_adds_volume": multiline_volume > plain_volume + 1e-3,
    }
    if not all(cylinder_volume_assertions.values()):
        failed = [key for key, value in cylinder_volume_assertions.items() if not value]
        raise RuntimeError(f"cylinder native text volume regression failed: {failed}")
    results["cylinder_volume_assertions"] = cylinder_volume_assertions

    target = OUTPUT / "FOUNDATIONAL_CAD_REGRESSION.json"
    target.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return results


if __name__ == "__main__":
    run()
