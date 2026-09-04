from __future__ import annotations

"""Physical regression for text on promoted sphere and ovoid CAD bodies."""

import json
from pathlib import Path

from .phase_5_design_matrix import _feature, _program
from .structural_pipeline import DoboStructuralPipeline


OUTPUT = Path("outputs-ci/radial-native-text")


def _case(
    case_id: str,
    prompt: str,
    *,
    profile: str,
    effect: str,
    concept: str = "walter",
    height_mm: float = 112.0,
    width_mm: float = 122.0,
    depth_mm: float = 122.0,
    opening_ratio: float = 0.58,
):
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
    if profile == "spherical":
        return _program(
            case_id,
            prompt,
            family="spherical",
            height=height_mm,
            width=width_mm,
            depth=depth_mm,
            opening_shape="circular",
            opening_width=opening_ratio,
            opening_depth=opening_ratio,
            style_tags=["spherical"],
            features=[feature],
            relations=[],
        )
    return _program(
        case_id,
        prompt,
        family="organic",
        height=125.0,
        width=112.0,
        depth=106.0,
        opening_shape="elliptical",
        opening_width=0.58,
        opening_depth=0.58,
        style_tags=["ovoid"],
        features=[feature],
        relations=[],
    )


def run() -> dict:
    sphere_walter_prompt = (
        "Crea una maceta esfera con el texto WALTER en sobrerrelieve sobre la cara frontal."
    )
    sphere_multiline_prompt = (
        "Crea una maceta esfera con texto en sobrerrelieve sobre la cara frontal, "
        "centrado y distribuido exactamente en tres líneas: PLANTA / UNA / IDEA. "
        "Mantén las tres líneas separadas."
    )
    cases = {
        "sphere_emboss": _case(
            "sphere_walter_emboss",
            sphere_walter_prompt,
            profile="spherical",
            effect="raised",
        ),
        # Mirrors the 200 mm free-prompt geometry that first exposed partial
        # glyph survival on a curved body.
        "sphere_emboss_live_scale": _case(
            "sphere_walter_emboss_live_scale",
            sphere_walter_prompt,
            profile="spherical",
            effect="raised",
            height_mm=200.0,
            width_mm=200.0,
            depth_mm=200.0,
            opening_ratio=0.72,
        ),
        # Mirrors the later 300 mm Lab result shown during visual validation.
        # The previous projected-face route produced visibly incomplete strokes
        # even while topology and glyph-count checks reported PASS.
        "sphere_emboss_300": _case(
            "sphere_walter_emboss_300",
            sphere_walter_prompt,
            profile="spherical",
            effect="raised",
            height_mm=300.0,
            width_mm=300.0,
            depth_mm=300.0,
            opening_ratio=0.72,
        ),
        "sphere_deboss": _case(
            "sphere_walter_deboss",
            "Crea una maceta esfera con el texto WALTER en bajorrelieve sobre la cara frontal.",
            profile="spherical",
            effect="recessed",
        ),
        "sphere_multiline": _case(
            "sphere_multiline_emboss",
            sphere_multiline_prompt,
            profile="spherical",
            effect="raised",
            concept="planta",
        ),
        # Specifically guards the large-body version of the former
        # `glyph 0 'P' produced no measurable relief` failure.
        "sphere_multiline_300": _case(
            "sphere_multiline_emboss_300",
            sphere_multiline_prompt,
            profile="spherical",
            effect="raised",
            concept="planta",
            height_mm=300.0,
            width_mm=300.0,
            depth_mm=300.0,
            opening_ratio=0.72,
        ),
        "ovoid_emboss": _case(
            "ovoid_walter_emboss",
            "Crea una maceta ovoide con el texto WALTER en sobrerrelieve sobre la cara frontal.",
            profile="ovoid",
            effect="raised",
        ),
        "ovoid_deboss": _case(
            "ovoid_walter_deboss",
            "Crea una maceta ovoide con el texto WALTER en bajorrelieve sobre la cara frontal.",
            profile="ovoid",
            effect="recessed",
        ),
        "ovoid_multiline": _case(
            "ovoid_multiline_emboss",
            "Crea una maceta ovoide con texto en sobrerrelieve sobre la cara frontal, centrado y distribuido exactamente en tres líneas: PLANTA / UNA / IDEA. Mantén las tres líneas separadas.",
            profile="ovoid",
            effect="raised",
            concept="planta",
        ),
    }

    OUTPUT.mkdir(parents=True, exist_ok=True)
    pipeline = DoboStructuralPipeline()
    report: dict[str, dict] = {}

    for name, program in cases.items():
        expected_profile = "spherical" if name.startswith("sphere") else "ovoid"
        base_route = (
            "analytic_cad_spherical_primitive"
            if expected_profile == "spherical"
            else "analytic_cad_ovoid_primitive"
        )
        final_route = (
            "analytic_cad_spherical_text"
            if expected_profile == "spherical"
            else "analytic_cad_ovoid_text"
        )
        result = pipeline.generate_from_semantic(
            program,
            output_root=OUTPUT / name,
            generation_budget_seconds=120.0,
        )
        motor = json.loads(Path(result.motor_path).read_text(encoding="utf-8"))
        radial = motor.get("_analytic_radial", {})
        text_route = motor.get("_native_radial_text", {})
        checks = dict(result.mesh_result.semantic_checks or {})
        delta = float(text_route.get("volume_delta_mm3", 0.0))
        expected_lines = 3 if "multiline" in name else 1
        expected_glyphs = 13 if "multiline" in name else 6
        spherical_glyph_integrity = (
            bool(checks.get("native_radial_text_glyph_integrity"))
            and int(text_route.get("expected_glyph_count", 0)) == expected_glyphs
            and int(text_route.get("applied_glyph_count", 0)) == expected_glyphs
        )

        assertions = {
            "route": motor.get("_capability_route") == final_route,
            "base_route": motor.get("_base_capability_route") == base_route,
            "profile": radial.get("profile") == expected_profile,
            "text_profile": text_route.get("profile") == expected_profile,
            "line_count": int(text_route.get("line_count", 0)) == expected_lines,
            "watertight": bool(result.mesh_result.watertight),
            "winding_consistent": bool(result.mesh_result.winding_consistent),
            "one_component": int(result.mesh_result.component_count) == 1,
            "cavity": bool(checks.get("cavity_is_empty")),
            "opening": bool(checks.get("opening_is_clear")),
            "drain": bool(checks.get("drain_is_clear")),
            "radial_profile": bool(checks.get("profile_is_radial")),
            "continuous_surface": bool(checks.get("surface_is_continuous_revolution")),
            "text_volume_changed": bool(checks.get("native_radial_text_volume_changed")),
            "text_one_component": bool(checks.get("native_radial_text_one_component")),
            "mesh_compact": bool(checks.get("native_radial_text_mesh_compact")),
            "not_legacy_dense": 0 < int(result.mesh_result.vertex_count) < 100_000,
            "relief_direction": delta < 0.0 if "deboss" in name else delta > 0.0,
            "glyph_integrity": (
                spherical_glyph_integrity if expected_profile == "spherical" else True
            ),
            "spherical_surface_band": (
                text_route.get("method") == "surface_band_clipped_tangent_glyphs"
                if expected_profile == "spherical"
                else True
            ),
        }
        if not all(assertions.values()):
            failed = [key for key, value in assertions.items() if not value]
            raise RuntimeError(f"{name} radial native text regression failed: {failed}")

        report[name] = {
            "route": motor.get("_capability_route"),
            "base_route": motor.get("_base_capability_route"),
            "profile": expected_profile,
            "vertices": result.mesh_result.vertex_count,
            "faces": result.mesh_result.face_count,
            "generation_seconds": result.mesh_result.generation_seconds,
            "volume_delta_mm3": delta,
            "line_count": text_route.get("line_count"),
            "method": text_route.get("method"),
            "expected_glyph_count": text_route.get("expected_glyph_count"),
            "applied_glyph_count": text_route.get("applied_glyph_count"),
            "assertions": assertions,
            "stl": result.stl_path,
        }

    target = OUTPUT / "RADIAL_NATIVE_TEXT_REGRESSION.json"
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return report


if __name__ == "__main__":
    run()
