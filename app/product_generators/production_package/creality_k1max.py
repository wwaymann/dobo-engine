from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import json
from math import floor
from pathlib import Path


class PrintIntent(str, Enum):
    FAST = "fast"
    TEXT = "text"


@dataclass(frozen=True, slots=True)
class K1MaxMachineLimits:
    max_xy_speed_mm_s: float = 800.0
    max_accel_mm_s2: float = 20000.0
    hotend_max_flow_mm3_s: float = 32.0


@dataclass(frozen=True, slots=True)
class CrealityK1MaxProfile:
    intent: PrintIntent
    nozzle_diameter_mm: float
    layer_height_mm: float
    outer_line_width_mm: float
    inner_line_width_mm: float
    material_max_flow_mm3_s: float
    wall_loops: int
    initial_layer_speed_mm_s: float
    outer_wall_speed_mm_s: float
    inner_wall_speed_mm_s: float
    top_surface_speed_mm_s: float
    internal_solid_speed_mm_s: float
    gap_infill_speed_mm_s: float
    travel_speed_mm_s: float
    outer_wall_accel_mm_s2: float
    inner_wall_accel_mm_s2: float
    travel_accel_mm_s2: float
    initial_layer_accel_mm_s2: float

    def validate(self, machine: K1MaxMachineLimits | None = None) -> None:
        machine = machine or K1MaxMachineLimits()
        if self.nozzle_diameter_mm <= 0:
            raise ValueError("nozzle_diameter_mm must be > 0")
        if not 0 < self.layer_height_mm <= self.nozzle_diameter_mm * 0.75:
            raise ValueError("layer_height_mm must be > 0 and <= 75% of nozzle diameter")
        if self.material_max_flow_mm3_s <= 0:
            raise ValueError("material_max_flow_mm3_s must be > 0")
        if self.material_max_flow_mm3_s > machine.hotend_max_flow_mm3_s:
            raise ValueError("material flow exceeds K1 Max hotend limit")
        if self.wall_loops < 2:
            raise ValueError("wall_loops must be >= 2")
        for value in (
            self.initial_layer_speed_mm_s,
            self.outer_wall_speed_mm_s,
            self.inner_wall_speed_mm_s,
            self.top_surface_speed_mm_s,
            self.internal_solid_speed_mm_s,
            self.gap_infill_speed_mm_s,
            self.travel_speed_mm_s,
        ):
            if value <= 0:
                raise ValueError("all speeds must be > 0")
        if self.travel_speed_mm_s > machine.max_xy_speed_mm_s:
            raise ValueError("travel speed exceeds K1 Max XY limit")
        for value in (
            self.outer_wall_accel_mm_s2,
            self.inner_wall_accel_mm_s2,
            self.travel_accel_mm_s2,
            self.initial_layer_accel_mm_s2,
        ):
            if value <= 0 or value > machine.max_accel_mm_s2:
                raise ValueError("acceleration outside K1 Max limit")

    def max_speed_for_flow(self, line_width_mm: float | None = None) -> float:
        width = line_width_mm or self.outer_line_width_mm
        return self.material_max_flow_mm3_s / (width * self.layer_height_mm)

    @staticmethod
    def _round_speed(value: float) -> float:
        return round(value, 1)

    def to_creality_overrides(self) -> dict[str, str]:
        """Creality Print process-profile overrides.

        These are intended to layer on top of the stock
        'Creality K1 Max 0.4 nozzle' machine profile, not replace it.
        """
        self.validate()

        outer_cap = self.max_speed_for_flow(self.outer_line_width_mm)
        inner_cap = self.max_speed_for_flow(self.inner_line_width_mm)

        outer = min(self.outer_wall_speed_mm_s, outer_cap)
        inner = min(self.inner_wall_speed_mm_s, inner_cap)
        top = min(self.top_surface_speed_mm_s, outer_cap)
        internal = min(self.internal_solid_speed_mm_s, inner_cap)
        gap = min(self.gap_infill_speed_mm_s, inner_cap)

        return {
            "layer_height": f"{self.layer_height_mm:g}",
            "outer_wall_line_width": f"{self.outer_line_width_mm:g}",
            "inner_wall_line_width": f"{self.inner_line_width_mm:g}",
            "wall_loops": str(self.wall_loops),
            "initial_layer_speed": f"{self.initial_layer_speed_mm_s:g}",
            "outer_wall_speed": f"{self._round_speed(outer):g}",
            "inner_wall_speed": f"{self._round_speed(inner):g}",
            "top_surface_speed": f"{self._round_speed(top):g}",
            "internal_solid_infill_speed": f"{self._round_speed(internal):g}",
            "gap_infill_speed": f"{self._round_speed(gap):g}",
            "travel_speed": f"{self.travel_speed_mm_s:g}",
            "initial_layer_acceleration": f"{self.initial_layer_accel_mm_s2:g}",
            "outer_wall_acceleration": f"{self.outer_wall_accel_mm_s2:g}",
            "inner_wall_acceleration": f"{self.inner_wall_accel_mm_s2:g}",
            "travel_acceleration": f"{self.travel_accel_mm_s2:g}",
            "sparse_infill_density": "0%",
            "enable_support": "0",
            "ironing_type": "no ironing",
            "reduce_infill_retraction": "1",
            "detect_overhang_wall": "1",
            "seam_position": "aligned",
        }

    def to_json_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["intent"] = self.intent.value
        payload["creality_overrides"] = self.to_creality_overrides()
        payload["max_outer_speed_by_flow_mm_s"] = self._round_speed(
            self.max_speed_for_flow(self.outer_line_width_mm)
        )
        payload["max_inner_speed_by_flow_mm_s"] = self._round_speed(
            self.max_speed_for_flow(self.inner_line_width_mm)
        )
        return payload


CREALITY_K1MAX_START_GCODE = """START_PRINT EXTRUDER_TEMP=[nozzle_temperature_initial_layer] BED_TEMP=[bed_temperature_initial_layer_single]
T[initial_no_support_extruder]
M204 S2000
M104 S[nozzle_temperature_initial_layer]
G1 Z3 F600
M83
G92 E0
G1 Z1 F600
"""

CREALITY_K1MAX_END_GCODE = """END_PRINT
"""


def _wall_loops_for_thickness(wall_thickness_mm: float, line_width_mm: float) -> int:
    if wall_thickness_mm <= 0:
        raise ValueError("wall_thickness_mm must be > 0")
    # Keep at least three fused perimeters for a planter wall while avoiding
    # needless perimeter count inflation. Any small remainder is handled by
    # the slicer's gap fill / internal solid strategy.
    return max(3, floor(wall_thickness_mm / line_width_mm))


def build_k1max_profile(
    *,
    intent: PrintIntent | str = PrintIntent.FAST,
    nozzle_diameter_mm: float = 0.4,
    wall_thickness_mm: float = 2.4,
    material_max_flow_mm3_s: float = 24.0,
) -> CrealityK1MaxProfile:
    intent = PrintIntent(intent)
    if nozzle_diameter_mm <= 0:
        raise ValueError("nozzle_diameter_mm must be > 0")

    line_width = round(nozzle_diameter_mm * 1.12, 3)

    if intent is PrintIntent.TEXT:
        layer_height = min(round(nozzle_diameter_mm * 0.50, 3), 0.20)
        outer_speed = 120.0
        inner_speed = 220.0
        top_speed = 90.0
        internal_speed = 180.0
        gap_speed = 140.0
        outer_accel = 3000.0
        inner_accel = 7000.0
        travel_accel = 12000.0
    else:
        layer_height = min(round(nozzle_diameter_mm * 0.70, 3), 0.30)
        outer_speed = 180.0
        inner_speed = 280.0
        top_speed = 120.0
        internal_speed = 240.0
        gap_speed = 180.0
        outer_accel = 5000.0
        inner_accel = 10000.0
        travel_accel = 15000.0

    profile = CrealityK1MaxProfile(
        intent=intent,
        nozzle_diameter_mm=nozzle_diameter_mm,
        layer_height_mm=layer_height,
        outer_line_width_mm=line_width,
        inner_line_width_mm=line_width,
        material_max_flow_mm3_s=material_max_flow_mm3_s,
        wall_loops=_wall_loops_for_thickness(wall_thickness_mm, line_width),
        initial_layer_speed_mm_s=45.0,
        outer_wall_speed_mm_s=outer_speed,
        inner_wall_speed_mm_s=inner_speed,
        top_surface_speed_mm_s=top_speed,
        internal_solid_speed_mm_s=internal_speed,
        gap_infill_speed_mm_s=gap_speed,
        travel_speed_mm_s=500.0,
        outer_wall_accel_mm_s2=outer_accel,
        inner_wall_accel_mm_s2=inner_accel,
        travel_accel_mm_s2=travel_accel,
        initial_layer_accel_mm_s2=1000.0,
    )
    profile.validate()
    return profile


def write_k1max_profile_bundle(
    output_dir: str | Path,
    *,
    intent: PrintIntent | str = PrintIntent.FAST,
    nozzle_diameter_mm: float = 0.4,
    wall_thickness_mm: float = 2.4,
    material_max_flow_mm3_s: float = 24.0,
) -> dict[str, str]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    profile = build_k1max_profile(
        intent=intent,
        nozzle_diameter_mm=nozzle_diameter_mm,
        wall_thickness_mm=wall_thickness_mm,
        material_max_flow_mm3_s=material_max_flow_mm3_s,
    )

    profile_path = output / f"dobo_k1max_{profile.intent.value}_profile.json"
    start_path = output / "dobo_k1max_start.gcode"
    end_path = output / "dobo_k1max_end.gcode"

    profile_path.write_text(
        json.dumps(profile.to_json_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    start_path.write_text(CREALITY_K1MAX_START_GCODE, encoding="utf-8")
    end_path.write_text(CREALITY_K1MAX_END_GCODE, encoding="utf-8")

    return {
        "profile": str(profile_path),
        "start_gcode": str(start_path),
        "end_gcode": str(end_path),
    }
