from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CommercialPlanterSpecification:
    id: str
    name: str
    decoration: str
    mode: str
    width: float = 120.0
    depth: float = 120.0
    height: float = 140.0
    wall_thickness: float = 4.0
    decoration_width: float = 64.0
    decoration_height: float = 28.0
    decoration_depth: float = 3.0
    decoration_center_z: float = 82.0
    export_filename: str = ""

    def validate(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("id cannot be empty.")

        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name cannot be empty.")

        if self.decoration not in {
            "plate",
            "circle",
            "diamond",
            "frame",
            "brand_mark",
        }:
            raise ValueError(
                f"Unsupported decoration '{self.decoration}'."
            )

        if self.mode not in {
            "emboss",
            "deboss",
        }:
            raise ValueError(
                "mode must be 'emboss' or 'deboss'."
            )

        for field_name, value in (
            ("width", self.width),
            ("depth", self.depth),
            ("height", self.height),
            ("wall_thickness", self.wall_thickness),
            ("decoration_width", self.decoration_width),
            ("decoration_height", self.decoration_height),
            ("decoration_depth", self.decoration_depth),
            ("decoration_center_z", self.decoration_center_z),
        ):
            if isinstance(value, bool) or not isinstance(
                value,
                (int, float),
            ):
                raise TypeError(
                    f"{field_name} must be numeric."
                )

        if (
            self.width <= 0
            or self.depth <= 0
            or self.height <= 0
            or self.wall_thickness <= 0
        ):
            raise ValueError(
                "Planter dimensions must be positive."
            )

        if (
            self.decoration_width <= 0
            or self.decoration_height <= 0
            or self.decoration_depth <= 0
        ):
            raise ValueError(
                "Decoration dimensions must be positive."
            )

        if self.decoration_width >= self.width:
            raise ValueError(
                "Decoration width must fit the planter."
            )

        if not (
            self.decoration_height / 2
            < self.decoration_center_z
            < self.height - self.decoration_height / 2
        ):
            raise ValueError(
                "Decoration must fit vertically on the planter."
            )

    @property
    def resolved_export_filename(self) -> str:
        return self.export_filename or f"{self.id}.step"
