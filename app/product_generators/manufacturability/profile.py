from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ManufacturingProfile:
    nozzle_diameter: float = 0.4
    layer_height: float = 0.20

    # Structural
    min_wall_thickness: float = 0.8
    min_feature_size: float = 0.45

    # Text
    min_text_stroke: float = 0.45
    min_text_depth: float = 0.40
    min_text_region_volume: float = 1.0

    # Decoration
    min_decoration_feature_size: float = 0.80
    min_decoration_region_volume: float = 1.0

    # Color
    min_color_region_volume: float = 1.0

    # Final-product geometric rules
    min_clearance: float = 0.25
    max_overhang_angle: float = 50.0
    min_bed_contact_area: float = 25.0
    min_stability_margin: float = 3.0

    # Production limits
    max_size_x: float = 300.0
    max_size_y: float = 300.0
    max_size_z: float = 300.0
    bed_z_tolerance: float = 0.05

    def validate(self) -> None:
        positive = (
            self.nozzle_diameter,
            self.layer_height,
            self.min_wall_thickness,
            self.min_feature_size,
            self.min_text_stroke,
            self.min_text_depth,
            self.min_text_region_volume,
            self.min_decoration_feature_size,
            self.min_decoration_region_volume,
            self.min_color_region_volume,
            self.min_clearance,
            self.max_overhang_angle,
            self.min_bed_contact_area,
            self.min_stability_margin,
            self.max_size_x,
            self.max_size_y,
            self.max_size_z,
            self.bed_z_tolerance,
        )

        if any(value <= 0.0 for value in positive):
            raise ValueError(
                "Manufacturing profile values must be positive."
            )
