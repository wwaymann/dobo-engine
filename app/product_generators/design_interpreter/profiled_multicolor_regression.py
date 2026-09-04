from __future__ import annotations

"""Creality compound-multicolor regression for every promoted profiled planter."""

import json
from pathlib import Path

from .intelligent_surfaces import SurfaceLayerIntent
from .native_profiled_cad_adapter import PROFILE_CATALOG
from .profiled_native_text_regression import _with_text
from .structural_pipeline import DoboStructuralPipeline


OUTPUT = Path("outputs-ci/profiled-multicolor")
BASE_COLOR = "#EAEAEA"
TEXT_COLOR = "#6D3BFF"
ACCENT_COLOR = "#19A974"


def _surface_intents(*, effect: str, multiline: bool) -> tuple[SurfaceLayerIntent, ...]:
    payload = "PLANTA\\nUNA\\nIDEA" if multiline else "WALTER"
    text_effect = "recessed" if effect == "recessed" else "raised"
    return (
        SurfaceLayerIntent(
            id="profiled_text_material",
            kind="text",
            payload=payload,
            region="front",
            u_center=0.5,
            v_center=0.52,
            width_fraction=0.55,
            height_fraction=0.12 if multiline else 0.14,
            effect=text_effect,
            depth_mm=1.2,
            color=TEXT_COLOR,
            filament_slot=2,
        ),
        SurfaceLayerIntent(
            id="profiled_upper_accent",
            kind="procedural_relief",
            payload="solid upper accent band",
            region="upper",
            u_center=0.5,
            v_center=0.96,
            width_fraction=1.0,
            height_fraction=0.08,
            effect="color_only",
            depth_mm=0.0,
            color=ACCENT_COLOR,
            filament_slot=3,
        ),
    )


def run() -> dict:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    pipeline = DoboStructuralPipeline()
    records: list[dict] = []

    cases = [
        (variant, "raised", False)
        for variant in PROFILE_CATALOG
    ]
    cases.extend(
        (variant, "recessed", False)
        for variant in PROFILE_CATALOG
    )
    cases.extend(
        (variant, "raised" if index % 2 == 0 else "recessed", True)
        for index, variant in enumerate(PROFILE_CATALOG)
    )

    for variant, effect, multiline in cases:
        name = (
            f"{variant}_{effect}_{'multiline' if multiline else 'single'}_three_color"
        )
        try:
            result = pipeline.generate_from_semantic(
                _with_text(variant, effect=effect, multiline=multiline),
                output_root=OUTPUT / name,
                surface_intents=_surface_intents(
                    effect=effect, multiline=multiline
                ),
                base_color=BASE_COLOR,
                generation_budget_seconds=180.0,
            )
            motor = json.loads(Path(result.motor_path).read_text(encoding="utf-8"))
            multicolor = motor.get("_profiled_multicolor", {})
            expected_mode = "deboss" if effect == "recessed" else "emboss"
            expected_lines = 3 if multiline else 1
            assertions = {
                "route": motor.get("_capability_route") == "analytic_cad_profiled_text",
                "compound_contract": bool(multicolor.get("compound_object")),
                "compound_method": (
                    multicolor.get("method")
                    == "cad_volume_partition_creality_compound"
                ),
                "relief_mode": multicolor.get("text_relief_mode") == expected_mode,
                "line_count": int(multicolor.get("text_lines", 0)) == expected_lines,
                "three_regions": result.three_mf.material_count == 3,
                "three_color_zones": result.surface_report.color_zones == 3,
                "filament_slots": tuple(result.three_mf.filament_slots) == (1, 2, 3),
                "region_names": tuple(result.three_mf.region_names)
                == ("Body", "Text", "Accent"),
                "colors": tuple(result.three_mf.colors)
                == (BASE_COLOR, TEXT_COLOR, ACCENT_COLOR),
                "one_build_item": int(multicolor.get("build_items", 0)) == 1,
                "volume_conserved": float(multicolor.get("volume_error_mm3", 1e9))
                <= max(
                    1.0,
                    float(multicolor.get("volume_final_mm3", 0.0)) * 2.0e-4,
                ),
                "physical_text_material": result.three_mf.painted_triangle_count > 0,
                "visible_deboss": (
                    float(multicolor.get("visible_recess_depth_mm", 0.0)) > 0.0
                    and float(multicolor.get("open_recess_volume_mm3", 0.0)) > 0.0
                    if expected_mode == "deboss"
                    else float(multicolor.get("visible_recess_depth_mm", 0.0)) == 0.0
                ),
                "watertight": bool(result.mesh_result.watertight),
                "one_component": int(result.mesh_result.component_count) == 1,
            }
            failed = [key for key, value in assertions.items() if not value]
            records.append(
                {
                    "name": name,
                    "variant": variant,
                    "effect": effect,
                    "multiline": multiline,
                    "status": "PASS" if not failed else "FAIL",
                    "failed_assertions": failed,
                    "three_mf": result.three_mf_path,
                    "materials": result.three_mf.material_count,
                    "filament_slots": list(result.three_mf.filament_slots),
                    "colors": list(result.three_mf.colors),
                    "triangle_count": result.three_mf.triangle_count,
                    "non_body_material_triangles": (
                        result.three_mf.painted_triangle_count
                    ),
                    "relief_mode": multicolor.get("text_relief_mode"),
                    "text_lines": multicolor.get("text_lines"),
                    "visible_recess_depth_mm": multicolor.get("visible_recess_depth_mm"),
                    "open_recess_volume_mm3": multicolor.get("open_recess_volume_mm3"),
                    "volume_error_mm3": result.three_mf.volume_error_mm3,
                    "assertions": assertions,
                }
            )
        except Exception as error:
            records.append(
                {
                    "name": name,
                    "variant": variant,
                    "effect": effect,
                    "multiline": multiline,
                    "status": "ERROR",
                    "error_type": type(error).__name__,
                    "error": str(error),
                }
            )
    summary = {
        "schema": "dobo.profiled_multicolor_regression.2",
        "case_count": len(records),
        "pass": sum(record["status"] == "PASS" for record in records),
        "fail": sum(record["status"] != "PASS" for record in records),
        "colors": [BASE_COLOR, TEXT_COLOR, ACCENT_COLOR],
        "records": records,
    }
    target = OUTPUT / "PROFILED_MULTICOLOR_REGRESSION.json"
    target.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if summary["fail"]:
        failed_names = [
            record["name"]
            for record in records
            if record["status"] != "PASS"
        ]
        raise RuntimeError(
            "Profiled compound multicolor matrix failed after full sweep: "
            + ", ".join(failed_names)
        )
    return summary


if __name__ == "__main__":
    run()
