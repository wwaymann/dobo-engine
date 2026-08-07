from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PatternSpecification:
    id: str
    pattern: str
    width: float
    height: float
    element_width: float
    element_height: float
    spacing_x: float
    spacing_y: float
    rows: int
    columns: int

    def validate(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("id cannot be empty.")

        if self.pattern not in {
            "grid",
            "brick",
            "diamond",
            "chevron",
            "hex",
            "wave_band",
        }:
            raise ValueError(
                f"Unsupported pattern '{self.pattern}'."
            )

        for name, value in (
            ("width", self.width),
            ("height", self.height),
            ("element_width", self.element_width),
            ("element_height", self.element_height),
            ("spacing_x", self.spacing_x),
            ("spacing_y", self.spacing_y),
        ):
            if isinstance(value, bool) or not isinstance(
                value,
                (int, float),
            ):
                raise TypeError(f"{name} must be numeric.")

            if float(value) <= 0.0:
                raise ValueError(
                    f"{name} must be greater than zero."
                )

        for name, value in (
            ("rows", self.rows),
            ("columns", self.columns),
        ):
            if isinstance(value, bool) or not isinstance(
                value,
                int,
            ):
                raise TypeError(f"{name} must be an integer.")

            if value < 1:
                raise ValueError(
                    f"{name} must be at least one."
                )
