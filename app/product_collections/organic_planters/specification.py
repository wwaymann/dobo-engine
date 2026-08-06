from __future__ import annotations

from dataclasses import dataclass


SectionSpec = tuple[
    float,  # z ratio
    float,  # width scale
    float,  # depth scale
    float,  # x offset ratio
    float,  # y offset ratio
]


@dataclass(frozen=True, slots=True)
class OrganicPlanterSpecification:
    id: str
    name: str
    width: float
    depth: float
    height: float
    wall_thickness: float
    profile: str
    sections: tuple[SectionSpec, ...]
    ruled: bool = False
    export_filename: str = ""

    def validate(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("id cannot be empty.")

        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name cannot be empty.")

        if self.profile not in {
            "circle",
            "ellipse",
            "rounded_square",
        }:
            raise ValueError(
                f"Unsupported organic profile '{self.profile}'."
            )

        for name, value in (
            ("width", self.width),
            ("depth", self.depth),
            ("height", self.height),
            ("wall_thickness", self.wall_thickness),
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

        if not isinstance(self.sections, tuple):
            raise TypeError("sections must be a tuple.")

        if len(self.sections) < 3:
            raise ValueError(
                "Organic planters require at least three sections."
            )

        previous_z = -1.0

        for index, section in enumerate(self.sections):
            if not isinstance(section, tuple) or len(section) != 5:
                raise TypeError(
                    f"sections[{index}] must be a 5-value tuple."
                )

            z_ratio, sx, sy, ox, oy = section

            for value in section:
                if isinstance(value, bool) or not isinstance(
                    value,
                    (int, float),
                ):
                    raise TypeError(
                        "Organic section values must be numeric."
                    )

            if not 0.0 <= float(z_ratio) <= 1.0:
                raise ValueError(
                    "Section z ratios must be between 0 and 1."
                )

            if float(z_ratio) <= previous_z:
                raise ValueError(
                    "Section z ratios must be strictly increasing."
                )

            if float(sx) <= 0.0 or float(sy) <= 0.0:
                raise ValueError(
                    "Section scales must be greater than zero."
                )

            previous_z = float(z_ratio)

        if abs(float(self.sections[0][0])) > 1e-12:
            raise ValueError("First section must start at z ratio 0.")

        if abs(float(self.sections[-1][0]) - 1.0) > 1e-12:
            raise ValueError("Last section must end at z ratio 1.")

        if not isinstance(self.ruled, bool):
            raise TypeError("ruled must be boolean.")

    @property
    def resolved_export_filename(self) -> str:
        return self.export_filename or f"{self.id}.step"
