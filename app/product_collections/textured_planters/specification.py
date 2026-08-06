from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TexturedPlanterSpecification:
    id: str
    name: str
    width: float = 120.0
    depth: float = 120.0
    height: float = 140.0
    wall_thickness: float = 4.0
    texture: str = "vertical_ribs"
    texture_count: int = 8
    texture_depth: float = 3.0
    texture_width: float = 5.0
    export_filename: str = ""

    def validate(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("id cannot be empty.")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name cannot be empty.")

        allowed = {
            "vertical_ribs",
            "wide_ribs",
            "fine_fluting",
            "corner_ribs",
            "front_panels",
            "alternating_ribs",
        }
        if self.texture not in allowed:
            raise ValueError(f"Unsupported texture '{self.texture}'.")

        for name, value in (
            ("width", self.width),
            ("depth", self.depth),
            ("height", self.height),
            ("wall_thickness", self.wall_thickness),
            ("texture_depth", self.texture_depth),
            ("texture_width", self.texture_width),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be numeric.")
            if float(value) <= 0.0:
                raise ValueError(f"{name} must be greater than zero.")

        if isinstance(self.texture_count, bool) or not isinstance(
            self.texture_count, int
        ):
            raise TypeError("texture_count must be an integer.")
        if self.texture_count < 1:
            raise ValueError("texture_count must be at least one.")

    @property
    def resolved_export_filename(self) -> str:
        return self.export_filename or f"{self.id}.step"
