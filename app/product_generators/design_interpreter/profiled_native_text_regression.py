from __future__ import annotations

"""Physical text matrix for every reusable profiled planter body."""

import json
from pathlib import Path

from .native_profiled_cad_adapter import PROFILE_CATALOG
from .phase_5_design_matrix import _feature, _program
from .profiled_cad_regression import _semantic
from .structural_pipeline import DoboStructuralPipeline


OUTPUT = Path("outputs-ci/profiled-native-text")


def _with_text(variant: str, *, effect: str, multiline: bool = False):
    base = _semantic(variant)
    label = str(base.source.prompt).split("perfil ", 1)[-1].split(",", 1)[0]
    concept = "planta" if multiline else "walter"
    relief = "sobrerrelieve" if effect == "raised" else "bajorrelieve"
    prompt = (
        f"Crea una maceta de perfil {label} con texto en {relief} sobre la "
        "cara frontal, centrado y distribuido exactamente en tres líneas: "
        "PLANTA / UNA / IDEA."
        if multiline else
        f"Crea una maceta de perfil {label} con el texto WALTER en {relief} "
        "sobre la cara frontal."
    )
    feature = _feature(
        "front_text",
        concept,
        "text",
        effect,
        region="front",
        horizontal=0.0,
        vertical=0.52,
        width=0.55,
        height=0.12 if multiline else 0.14,
        depth=1.2,
    )
    return _program(
        f"profiled_{variant}_{'multiline' if multiline else relief}",
        prompt,
        family="tapered",
        height=120.0,
        width=120.0,
        depth=120.0,
        opening_shape="circular",
        opening_width=0.58,
        opening_depth=0.58,
        style_tags=[variant],
        features=[feature],
        relations=[],
    )


def run() -> dict:
    cases = [
        (variant, "raised" if index % 2 == 0 else "recessed", False)
        for index, variant in enumerate(PROFILE_CATALOG)
    ]
    cases.extend([
        ("amphora_tapered", "raised", True),
        ("urn_bellied", "recessed", True),
    ])

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pipeline = DoboStructuralPipeline()
    records: list[dict] = []
    for variant, effect, multiline in cases:
        name = f"{variant}_{effect}_{'multiline' if multiline else 'single'}"
        result = pipeline.generate_from_semantic(
            _with_text(variant, effect=effect, multiline=multiline),
            output_root=OUTPUT / name,
            generation_budget_seconds=180.0,
        )
        motor = json.loads(Path(result.motor_path).read_text(encoding="utf-8"))
        text = motor.get("_native_profiled_text", {})
        checks = dict(result.mesh_result.semantic_checks or {})
        delta = float(text.get("volume_delta_mm3", 0.0))
        expected_lines = 3 if multiline else 1
        expected_glyphs = 13 if multiline else 6
        assertions = {
            "route": motor.get("_capability_route") == "analytic_cad_profiled_text",
            "base_route": motor.get("_base_capability_route") == "analytic_cad_profiled_revolution",
            "variant": text.get("variant") == variant,
            "line_count": int(text.get("line_count", 0)) == expected_lines,
            "glyph_count": int(text.get("applied_glyph_count", 0)) == expected_glyphs,
            "mapping": text.get("method") == "local_radius_slope_surface_band",
            "watertight": bool(result.mesh_result.watertight),
            "winding_consistent": bool(result.mesh_result.winding_consistent),
            "one_component": int(result.mesh_result.component_count) == 1,
            "cavity": bool(checks.get("cavity_is_empty")),
            "opening": bool(checks.get("opening_is_clear")),
            "drain": bool(checks.get("drain_is_clear")),
            "profile": bool(checks.get("profile_is_revolved")),
            "text_volume_changed": bool(checks.get("native_profiled_text_volume_changed")),
            "text_one_component": bool(checks.get("native_profiled_text_one_component")),
            "glyph_integrity": bool(checks.get("native_profiled_text_glyph_integrity")),
            "relief_direction": delta > 0.0 if effect == "raised" else delta < 0.0,
            "native_mesh": 0 < int(result.mesh_result.vertex_count) < 150_000,
        }
        if not all(assertions.values()):
            failed = [key for key, value in assertions.items() if not value]
            raise RuntimeError(f"{name} profiled native text regression failed: {failed}")
        records.append({
            "name": name,
            "variant": variant,
            "effect": effect,
            "multiline": multiline,
            "status": "PASS",
            "vertices": result.mesh_result.vertex_count,
            "faces": result.mesh_result.face_count,
            "volume_delta_mm3": delta,
            "generation_seconds": result.mesh_result.generation_seconds,
            "assertions": assertions,
            "stl": result.stl_path,
        })

    summary = {
        "schema": "dobo.profiled_native_text_regression.1",
        "case_count": len(records),
        "pass": len(records),
        "fail": 0,
        "variants": len({record["variant"] for record in records}),
        "records": records,
    }
    target = OUTPUT / "PROFILED_NATIVE_TEXT_REGRESSION.json"
    target.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    run()
