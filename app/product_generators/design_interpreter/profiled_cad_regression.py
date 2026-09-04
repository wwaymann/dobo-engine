from __future__ import annotations

"""Physical matrix for the first reusable revolved-profile catalog."""

import json
from pathlib import Path

from .native_profiled_cad_adapter import PROFILE_CATALOG, PROFILE_DEFAULT_DIMENSIONS, PROFILE_LABELS
from .phase_5_design_matrix import _program
from .structural_pipeline import DoboStructuralPipeline


OUTPUT = Path("outputs-ci/profiled-cad")


def _semantic(variant: str):
    height, width = PROFILE_DEFAULT_DIMENSIONS[variant]
    return _program(
        f"profiled_{variant}",
        f"Crea una maceta de perfil {PROFILE_LABELS[variant]}, hueca, abierta y con drenaje.",
        family="tapered", height=height, width=width, depth=width,
        opening_shape="circular", opening_width=0.58, opening_depth=0.58,
        style_tags=[variant], features=[], relations=[],
    )


def run() -> dict:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    pipeline = DoboStructuralPipeline()
    records: list[dict] = []

    for variant in PROFILE_CATALOG:
        result = pipeline.generate_from_semantic(
            _semantic(variant),
            output_root=OUTPUT / variant,
            generation_budget_seconds=120.0,
        )
        result.validate()
        motor = json.loads(Path(result.motor_path).read_text(encoding="utf-8"))
        route = motor.get("_profiled_revolution", {})
        checks = dict(result.mesh_result.semantic_checks or {})
        saucer = motor.get("_profiled_saucer", {})
        text_zone = route.get("text_zone", {})
        assertions = {
            "route": motor.get("_capability_route") == "analytic_cad_profiled_revolution",
            "morphology": motor.get("morphogenesis", {}).get("profile") == "profiled_revolution",
            "variant": route.get("variant") == variant,
            "profile_contract": len(route.get("control_profile", [])) >= 4,
            "dense_profile": len(route.get("normalized_profile", [])) >= 31,
            "profile_resolution": int(route.get("profile_samples_per_span", 0)) >= 10,
            "watertight": bool(result.mesh_result.watertight),
            "winding_consistent": bool(result.mesh_result.winding_consistent),
            "one_component": int(result.mesh_result.component_count) == 1,
            "cavity": bool(checks.get("cavity_is_empty")),
            "opening": bool(checks.get("opening_is_clear")),
            "drain": bool(checks.get("drain_is_clear")),
            "wall": bool(checks.get("wall_is_solid")),
            "base": bool(checks.get("base_is_solid")),
            "known_profile": bool(checks.get("profile_variant_known")),
            "text_zone": isinstance(text_zone, dict) and text_zone.get("id") == "front_primary" and bool(text_zone.get("emboss_allowed")) and bool(text_zone.get("deboss_allowed")),
            "surface_regions": len(route.get("surface_regions", [])) >= 4,
            "color_regions": len(route.get("color_regions", [])) >= 4,
            "saucer_file": isinstance(saucer, dict) and Path(str(saucer.get("stl_path", ""))).is_file(),
            "saucer_watertight": bool(saucer.get("watertight")),
            "saucer_winding": bool(saucer.get("winding_consistent")),
            "saucer_one_component": int(saucer.get("component_count", 0)) == 1,
            "saucer_clearance": float(saucer.get("drain_clearance_mm", 0.0)) >= 1.0,
            "native_mesh": 0 < int(result.mesh_result.vertex_count) < 150_000,
        }
        record = {
            "variant": variant,
            "status": "PASS" if all(assertions.values()) else "FAIL",
            "route": motor.get("_capability_route"),
            "vertices": result.mesh_result.vertex_count,
            "faces": result.mesh_result.face_count,
            "volume_mm3": result.mesh_result.volume_mm3,
            "assertions": assertions,
            "stl": result.stl_path,
            "three_mf": result.three_mf_path,
            "text_zone": text_zone,
            "saucer": saucer.get("stl_path"),
        }
        records.append(record)
        if record["status"] != "PASS":
            failed = [name for name, value in assertions.items() if not value]
            raise RuntimeError(f"{variant} profiled CAD regression failed: {failed}")

    distinct_volumes = len({
        round(float(record["volume_mm3"]), 1)
        for record in records
    })
    summary = {
        "schema": "dobo.profiled_cad_regression.2",
        "case_count": len(records),
        "pass": sum(record["status"] == "PASS" for record in records),
        "fail": sum(record["status"] != "PASS" for record in records),
        "distinct_volumes": distinct_volumes,
        "profiles": records,
    }
    minimum_distinct = max(8, int(0.75 * len(PROFILE_CATALOG)))
    if distinct_volumes < minimum_distinct:
        raise RuntimeError(f"Profile catalog did not produce enough physically distinct bodies: {distinct_volumes} < {minimum_distinct}.")
    target = OUTPUT / "PROFILED_CAD_REGRESSION.json"
    target.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    run()
