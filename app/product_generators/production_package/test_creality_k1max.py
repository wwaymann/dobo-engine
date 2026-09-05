from __future__ import annotations

import json

import pytest

from app.product_generators.production_package.creality_k1max import (
    CREALITY_K1MAX_END_GCODE,
    CREALITY_K1MAX_START_GCODE,
    PrintIntent,
    build_k1max_profile,
    write_k1max_profile_bundle,
)


def test_fast_profile_is_flow_limited_instead_of_blind_600mm_s():
    profile = build_k1max_profile(
        intent=PrintIntent.FAST,
        nozzle_diameter_mm=0.4,
        wall_thickness_mm=2.4,
        material_max_flow_mm3_s=24.0,
    )

    overrides = profile.to_creality_overrides()

    assert profile.layer_height_mm == pytest.approx(0.28)
    assert profile.wall_loops >= 3
    assert float(overrides["outer_wall_speed"]) <= profile.max_speed_for_flow(
        profile.outer_line_width_mm
    )
    assert float(overrides["inner_wall_speed"]) <= profile.max_speed_for_flow(
        profile.inner_line_width_mm
    )
    assert float(overrides["inner_wall_speed"]) < 280.0
    assert float(overrides["travel_speed"]) == 500.0


def test_text_profile_preserves_detail_with_lower_outer_acceleration():
    fast = build_k1max_profile(intent=PrintIntent.FAST)
    text = build_k1max_profile(intent=PrintIntent.TEXT)

    assert text.layer_height_mm < fast.layer_height_mm
    assert text.outer_wall_speed_mm_s < fast.outer_wall_speed_mm_s
    assert text.outer_wall_accel_mm_s2 < fast.outer_wall_accel_mm_s2
    assert text.inner_wall_speed_mm_s > text.outer_wall_speed_mm_s


def test_profile_rejects_flow_above_k1max_hotend_limit():
    with pytest.raises(ValueError, match="hotend limit"):
        build_k1max_profile(material_max_flow_mm3_s=32.1)


def test_official_k1max_macro_boundary_is_kept():
    assert CREALITY_K1MAX_START_GCODE.startswith(
        "START_PRINT EXTRUDER_TEMP=[nozzle_temperature_initial_layer]"
    )
    assert "BED_TEMP=[bed_temperature_initial_layer_single]" in CREALITY_K1MAX_START_GCODE
    assert CREALITY_K1MAX_END_GCODE == "END_PRINT\n"


def test_profile_bundle_writes_profile_and_gcode(tmp_path):
    artifacts = write_k1max_profile_bundle(
        tmp_path,
        intent=PrintIntent.FAST,
        wall_thickness_mm=2.4,
        material_max_flow_mm3_s=24.0,
    )

    profile_payload = json.loads((tmp_path / "dobo_k1max_fast_profile.json").read_text())

    assert set(artifacts) == {"profile", "start_gcode", "end_gcode"}
    assert profile_payload["intent"] == "fast"
    assert profile_payload["creality_overrides"]["sparse_infill_density"] == "0%"
    assert (tmp_path / "dobo_k1max_start.gcode").read_text().startswith("START_PRINT")
    assert (tmp_path / "dobo_k1max_end.gcode").read_text() == "END_PRINT\n"
