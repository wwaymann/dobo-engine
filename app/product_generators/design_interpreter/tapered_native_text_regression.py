from __future__ import annotations

"""Physical regression for text on the promoted analytic cone route."""

import json
from pathlib import Path

from .phase_5_design_matrix import _feature, _program
from .structural_pipeline import DoboStructuralPipeline


OUTPUT = Path("outputs-ci/tapered-native-text")


def _case(case_id: str, prompt: str, *, effect: str, concept: str = "WALTER"):
    feature = _feature(
        "front_text",
        concept,
        "text",
        effect,
        region="front",
        horizontal=0.0,
        vertical=0.52,
        width=0.55,
        height=0.14,
        depth=1.2,
    )
    return _program(
        case_id,
        prompt,
        family="tapered",
        height=120.0,
        width=120.0,
        depth=120.0,
        opening_shape="circular",
        opening_width=0.58,
        opening_depth=0.58,
        style_tags=["tapered_revolution"],
        features=[feature],
        relations=[],
    )


def run() -> dict:
    cases = {
        "emboss": _case(
            "cone_walter_emboss",
            "Crea una maceta cono con el texto WALTER en sobrerrelieve sobre la cara frontal.",
            effect="raised",
        ),
        "deboss": _case(
            "cone_walter_deboss",
            "Crea una maceta cono con el texto WALTER en bajorrelieve sobre la cara frontal.",
            effect="recessed",
        ),
        "multiline": _case(
            "cone_multiline_emboss",
            "Crea una maceta cono con texto frontal en tres líneas: línea 1: PLANTA; línea 2: UNA; línea 3: IDEA.",
            effect="raised",
            concept="PLANTA",
        ),
    }

    OUTPUT.mkdir(parents=True, exist_ok=True)
    report: dict[str, dict] = {}
    pipeline = DoboStructuralPipeline()
    for name, program in cases.items():
        result = pipeline.generate_from_semantic(
            program,
            output_root=OUTPUT / name,
            generation_budget_seconds=120.0,
        )
        motor = json.loads(Path(result.motor_path).read_text(encoding="utf-8"))
        route = motor.get("_capability_route")
        text_route = motor.get("_native_tapered_text", {})
        tapered = motor.get("_analytic_tapered", {})
        checks = dict(result.mesh_result.semantic_checks or {})

        expected_lines = 3 if name == "multiline" else 1
        assertions = {
            "route_is_native_tapered_text": route == "analytic_cad_tapered_text",
            "base_route_preserved": motor.get("_base_capability_route") == "analytic_cad_tapered_primitive",
            "line_count": int(text_route.get("line_count", 0)) == expected_lines,
            "watertight": bool(result.mesh_result.watertight),
            "winding_consistent": bool(result.mesh_result.winding_consistent),
            "one_component": int(result.mesh_result.component_count) == 1,
            "cavity": bool(checks.get("cavity_is_empty")),
            "opening": bool(checks.get("opening_is_clear")),
            "drain": bool(checks.get("drain_is_clear")),
            "taper": bool(checks.get("profile_is_tapered")) and bool(checks.get("taper_is_monotonic")),
            "text_volume_changed": bool(checks.get("native_tapered_text_volume_changed")),
            "text_one_component": bool(checks.get("native_tapered_text_one_component")),
            "mesh_not_legacy_dense": 0 < int(result.mesh_result.vertex_count) < 100_000,
            "dimensions_preserved": (
                float(tapered.get("bottom_diameter_mm", 0.0)) == 74.4
                and float(tapered.get("top_diameter_mm", 0.0)) == 108.0
                and float(tapered.get("height_mm", 0.0)) == 120.0
            ),
        }
        delta = float(text_route.get("volume_delta_mm3", 0.0))
        assertions["relief_direction"] = delta < 0.0 if name == "deboss" else delta > 0.0
        if not all(assertions.values()):
            failed = [key for key, value in assertions.items() if not value]
            raise RuntimeError(f"{name} tapered native text regression failed: {failed}")

        report[name] = {
            "route": route,
            "vertices": result.mesh_result.vertex_count,
            "faces": result.mesh_result.face_count,
            "generation_seconds": result.mesh_result.generation_seconds,
            "volume_delta_mm3": delta,
            "line_count": text_route.get("line_count"),
            "assertions": assertions,
            "stl": result.stl_path,
        }

    target = OUTPUT / "TAPERED_NATIVE_TEXT_REGRESSION.json"
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return report


if __name__ == "__main__":
    run()
