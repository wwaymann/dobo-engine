from __future__ import annotations

"""Physical regression for promoted spherical and ovoid planter bodies."""

import json
from pathlib import Path

from .phase_5_design_matrix import _program
from .structural_pipeline import DoboStructuralPipeline


OUTPUT = Path("outputs-ci/radial-native-body")


def _sphere():
    return _program(
        "sphere_native_body",
        "Crea una maceta esfera",
        family="spherical",
        height=112.0,
        width=122.0,
        depth=122.0,
        opening_shape="circular",
        opening_width=0.58,
        opening_depth=0.58,
        style_tags=["spherical"],
        features=[],
        relations=[],
    )


def _sphere_wide_opening():
    """Model the wider circular opening that free OpenAI prompts can select."""
    return _program(
        "sphere_native_body_wide_opening",
        "Crea una maceta esfera con una abertura superior amplia",
        family="spherical",
        height=112.0,
        width=122.0,
        depth=122.0,
        opening_shape="circular",
        opening_width=0.86,
        opening_depth=0.86,
        style_tags=["spherical"],
        features=[],
        relations=[],
    )


def _ovoid():
    return _program(
        "ovoid_native_body",
        "Crea una maceta ovoide",
        family="organic",
        height=125.0,
        width=112.0,
        depth=106.0,
        opening_shape="elliptical",
        opening_width=0.58,
        opening_depth=0.58,
        style_tags=["ovoid"],
        features=[],
        relations=[],
    )


def run() -> dict:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    cases = {
        "sphere": (
            _sphere(),
            "analytic_cad_spherical_primitive",
            "spherical",
            "revolved_circle",
        ),
        "sphere_wide_opening": (
            _sphere_wide_opening(),
            "analytic_cad_spherical_primitive",
            "spherical",
            "revolved_circle",
        ),
        "ovoid": (
            _ovoid(),
            "analytic_cad_ovoid_primitive",
            "ovoid",
            "revolved_spline",
        ),
    }
    report: dict[str, dict] = {}
    pipeline = DoboStructuralPipeline()

    for name, (program, expected_route, expected_profile, expected_surface) in cases.items():
        result = pipeline.generate_from_semantic(
            program,
            output_root=OUTPUT / name,
            generation_budget_seconds=120.0,
        )
        motor = json.loads(Path(result.motor_path).read_text(encoding="utf-8"))
        route = motor.get("_capability_route")
        radial = motor.get("_analytic_radial", {})
        checks = dict(result.mesh_result.semantic_checks or {})

        assertions = {
            "route": route == expected_route,
            "profile": radial.get("profile") == expected_profile,
            "surface_model": radial.get("surface_model") == expected_surface,
            "watertight": bool(result.mesh_result.watertight),
            "winding_consistent": bool(result.mesh_result.winding_consistent),
            "one_component": int(result.mesh_result.component_count) == 1,
            "outside": bool(checks.get("outside_is_empty")),
            "wall": bool(checks.get("wall_is_solid")),
            "cavity": bool(checks.get("cavity_is_empty")),
            "opening": bool(checks.get("opening_is_clear")),
            "base": bool(checks.get("base_is_solid")),
            "drain": bool(checks.get("drain_is_clear")),
            "below_base": bool(checks.get("below_base_is_empty")),
            "radial_profile": bool(checks.get("profile_is_radial")),
            "profile_specific": bool(checks.get(f"profile_is_{expected_profile}")),
            "continuous_surface": bool(checks.get("surface_is_continuous_revolution")),
            "printable": bool(checks.get("dimensions_are_printable")),
            "mesh_is_smooth_and_compact": 1_000 < int(result.mesh_result.vertex_count) < 15_000,
        }
        if expected_profile == "spherical":
            assertions["dimensions"] = (
                abs(float(radial.get("width_mm", 0.0)) - 122.0) < 1e-6
                and abs(float(radial.get("depth_mm", 0.0)) - 122.0) < 1e-6
                and abs(float(radial.get("height_mm", 0.0)) - 112.0) < 1e-6
            )
        else:
            assertions["dimensions"] = (
                abs(float(radial.get("width_mm", 0.0)) - 112.0) < 1e-6
                and abs(float(radial.get("depth_mm", 0.0)) - 106.0) < 1e-6
                and abs(float(radial.get("height_mm", 0.0)) - 125.0) < 1e-6
            )

        if not all(assertions.values()):
            failed = [key for key, value in assertions.items() if not value]
            raise RuntimeError(f"{name} radial native body regression failed: {failed}")

        report[name] = {
            "route": route,
            "profile": expected_profile,
            "surface_model": expected_surface,
            "vertices": result.mesh_result.vertex_count,
            "faces": result.mesh_result.face_count,
            "generation_seconds": result.mesh_result.generation_seconds,
            "radial": radial,
            "semantic_checks": checks,
            "assertions": assertions,
            "stl": result.stl_path,
        }

    target = OUTPUT / "RADIAL_NATIVE_BODY_REGRESSION.json"
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return report


if __name__ == "__main__":
    run()
