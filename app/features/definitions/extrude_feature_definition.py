"""
DOBO Features

Extrude Feature Definition

Declaratively describes one extrusion request.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from features.contracts import (
    BooleanMode,
    FeatureDefinition,
)


Vector3 = tuple[
    float,
    float,
    float,
]


@dataclass(
    frozen=True,
    slots=True,
)
class ExtrudeFeatureDefinition(
    FeatureDefinition,
):
    """
    Declarative definition of one extrusion.

    This class describes intent only.
    It does not execute geometry.
    """

    region_set_id: str = ""

    region_id: str = ""

    output_id: str = ""

    distance: float = 1.0

    direction: Vector3 = (
        0.0,
        0.0,
        1.0,
    )

    mode: BooleanMode = (
        BooleanMode.NEW_BODY
    )

    target_body_id: str | None = None

    symmetric: bool = False

    draft_angle: float = 0.0

    merge: bool = True

    metadata: dict[
        str,
        Any,
    ] = field(
        default_factory=dict
    )

    @property
    def feature_type(
        self,
    ) -> str:
        """
        Returns the stable Feature identifier.
        """

        return "extrude"

    def validate(
        self,
    ) -> None:
        """
        Validates the complete Extrude definition.
        """

        FeatureDefinition.validate(
            self
        )

        self._validate_identifier(
            self.region_set_id,
            field_name="region_set_id",
        )

        self._validate_identifier(
            self.region_id,
            field_name="region_id",
        )

        self._validate_identifier(
            self.output_id,
            field_name="output_id",
        )

        if isinstance(
            self.distance,
            bool,
        ) or not isinstance(
            self.distance,
            (
                int,
                float,
            ),
        ):
            raise TypeError(
                "ExtrudeFeatureDefinition distance "
                "must be numeric."
            )

        if not math.isfinite(
            float(
                self.distance
            )
        ):
            raise ValueError(
                "ExtrudeFeatureDefinition distance "
                "must be finite."
            )

        if self.distance <= 0:
            raise ValueError(
                "ExtrudeFeatureDefinition distance "
                "must be greater than zero."
            )

        if not isinstance(
            self.direction,
            tuple,
        ) or len(
            self.direction
        ) != 3:
            raise TypeError(
                "ExtrudeFeatureDefinition direction "
                "must be a 3-value tuple."
            )

        normalized_direction: list[
            float
        ] = []

        for value in self.direction:
            if isinstance(
                value,
                bool,
            ) or not isinstance(
                value,
                (
                    int,
                    float,
                ),
            ):
                raise TypeError(
                    "ExtrudeFeatureDefinition direction "
                    "values must be numeric."
                )

            numeric = float(
                value
            )

            if not math.isfinite(
                numeric
            ):
                raise ValueError(
                    "ExtrudeFeatureDefinition direction "
                    "values must be finite."
                )

            normalized_direction.append(
                numeric
            )

        direction_length = math.sqrt(
            sum(
                value * value
                for value
                in normalized_direction
            )
        )

        if direction_length <= 1e-12:
            raise ValueError(
                "ExtrudeFeatureDefinition direction "
                "cannot be zero."
            )

        if not isinstance(
            self.mode,
            BooleanMode,
        ):
            raise TypeError(
                "ExtrudeFeatureDefinition mode "
                "must be BooleanMode."
            )

        if self.mode.requires_target_body:
            if self.target_body_id is None:
                raise ValueError(
                    "ExtrudeFeatureDefinition mode "
                    f"'{self.mode.value}' requires "
                    "target_body_id."
                )

            self._validate_identifier(
                self.target_body_id,
                field_name="target_body_id",
            )

        elif self.target_body_id is not None:
            self._validate_identifier(
                self.target_body_id,
                field_name="target_body_id",
            )

        if not isinstance(
            self.symmetric,
            bool,
        ):
            raise TypeError(
                "ExtrudeFeatureDefinition symmetric "
                "must be boolean."
            )

        if isinstance(
            self.draft_angle,
            bool,
        ) or not isinstance(
            self.draft_angle,
            (
                int,
                float,
            ),
        ):
            raise TypeError(
                "ExtrudeFeatureDefinition draft_angle "
                "must be numeric."
            )

        if not math.isfinite(
            float(
                self.draft_angle
            )
        ):
            raise ValueError(
                "ExtrudeFeatureDefinition draft_angle "
                "must be finite."
            )

        if not (
            -89.0
            < self.draft_angle
            < 89.0
        ):
            raise ValueError(
                "ExtrudeFeatureDefinition draft_angle "
                "must be between -89 and 89 degrees."
            )

        if not isinstance(
            self.merge,
            bool,
        ):
            raise TypeError(
                "ExtrudeFeatureDefinition merge "
                "must be boolean."
            )

    @property
    def normalized_direction(
        self,
    ) -> Vector3:
        """
        Returns a unit extrusion direction.
        """

        x, y, z = (
            float(
                value
            )
            for value
            in self.direction
        )

        length = math.sqrt(
            x * x
            + y * y
            + z * z
        )

        if length <= 1e-12:
            raise ValueError(
                "Cannot normalize zero direction."
            )

        return (
            x / length,
            y / length,
            z / length,
        )

    @property
    def signed_start_distance(
        self,
    ) -> float:
        """
        Returns extrusion start offset.

        Symmetric extrusion starts at half the negative
        extrusion distance.
        """

        if self.symmetric:
            return (
                -self.distance
                / 2.0
            )

        return 0.0

    @property
    def signed_end_distance(
        self,
    ) -> float:
        """
        Returns extrusion end offset.
        """

        if self.symmetric:
            return (
                self.distance
                / 2.0
            )

        return self.distance

    @staticmethod
    def _validate_identifier(
        value: str,
        *,
        field_name: str,
    ) -> None:
        """
        Validates one stable identifier.
        """

        if not isinstance(
            value,
            str,
        ) or not value.strip():
            raise ValueError(
                "ExtrudeFeatureDefinition "
                f"{field_name} cannot be empty."
            )