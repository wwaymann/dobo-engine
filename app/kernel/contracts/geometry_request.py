"""
DOBO CAD Kernel

Geometry Request

Universal backend-independent request consumed by
geometry operation executors.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from .geometry_definition_set import (
    GeometryDefinitionSet,
)
from .geometry_operation_type import (
    GeometryOperationType,
)


Vector3 = tuple[
    float,
    float,
    float,
]


@dataclass(frozen=True, slots=True)
class GeometryRequest:
    """
    Immutable intermediate representation for one
    geometric construction request.

    Feature builders create GeometryRequest objects.

    The request does not contain CadQuery or
    OpenCascade objects.
    """

    geometry: GeometryDefinitionSet

    operation: GeometryOperationType

    parameters: dict[str, Any]

    id: str = field(
        default_factory=lambda: str(
            uuid4()
        )
    )

    output_id: str = ""

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates the complete geometry request.
        """

        if not isinstance(
            self.id,
            str,
        ) or not self.id.strip():
            raise ValueError(
                "GeometryRequest id cannot be empty."
            )

        if not isinstance(
            self.geometry,
            GeometryDefinitionSet,
        ):
            raise TypeError(
                "GeometryRequest geometry must be "
                "GeometryDefinitionSet."
            )

        self.geometry.validate()

        if not isinstance(
            self.operation,
            GeometryOperationType,
        ):
            raise TypeError(
                "GeometryRequest operation must be "
                "GeometryOperationType."
            )

        if not isinstance(
            self.parameters,
            dict,
        ):
            raise TypeError(
                "GeometryRequest parameters must be "
                "a dictionary."
            )

        if not isinstance(
            self.output_id,
            str,
        ) or not self.output_id.strip():
            raise ValueError(
                "GeometryRequest output_id cannot "
                "be empty."
            )

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "GeometryRequest metadata must be "
                "a dictionary."
            )

        self._validate_operation_parameters()

    def _validate_operation_parameters(self) -> None:
        """
        Validates parameters required by the selected
        operation.
        """

        if self.operation is GeometryOperationType.EXTRUDE:
            self._validate_extrude_parameters()
            return

        if self.operation is GeometryOperationType.REVOLVE:
            self._validate_revolve_parameters()
            return

        if self.operation is GeometryOperationType.LOFT:
            self._validate_loft_parameters()
            return

        if self.operation is GeometryOperationType.SWEEP:
            self._validate_sweep_parameters()
            return

        raise ValueError(
            "Unsupported GeometryOperationType "
            f"'{self.operation}'."
        )

    def _validate_extrude_parameters(self) -> None:
        """
        Validates extrusion parameters.
        """

        distance = self.get_parameter(
            "distance"
        )

        if distance is None:
            raise ValueError(
                "Extrude GeometryRequest requires "
                "'distance'."
            )

        distance_value = self._numeric_parameter(
            "distance",
            distance,
        )

        if distance_value <= 0:
            raise ValueError(
                "Extrude distance must be greater "
                "than zero."
            )

        direction = self.get_parameter(
            "direction",
            (
                0.0,
                0.0,
                1.0,
            ),
        )

        self._validate_vector3(
            name="direction",
            value=direction,
            allow_zero=False,
        )

        symmetric = self.get_parameter(
            "symmetric",
            False,
        )

        if not isinstance(
            symmetric,
            bool,
        ):
            raise TypeError(
                "Extrude symmetric must be boolean."
            )

        draft_angle = self.get_parameter(
            "draft_angle",
            0.0,
        )

        draft_value = self._numeric_parameter(
            "draft_angle",
            draft_angle,
        )

        if not (
            -89.0
            < draft_value
            < 89.0
        ):
            raise ValueError(
                "Extrude draft_angle must be "
                "between -89 and 89 degrees."
            )

    def _validate_revolve_parameters(self) -> None:
        """
        Validates revolve parameters.
        """

        angle = self.get_parameter(
            "angle"
        )

        if angle is None:
            raise ValueError(
                "Revolve GeometryRequest requires "
                "'angle'."
            )

        angle_value = self._numeric_parameter(
            "angle",
            angle,
        )

        if not (
            0.0
            < angle_value
            <= 360.0
        ):
            raise ValueError(
                "Revolve angle must be greater than "
                "zero and at most 360 degrees."
            )

        axis_origin = self.get_parameter(
            "axis_origin"
        )

        axis_direction = self.get_parameter(
            "axis_direction"
        )

        if axis_origin is None:
            raise ValueError(
                "Revolve GeometryRequest requires "
                "'axis_origin'."
            )

        if axis_direction is None:
            raise ValueError(
                "Revolve GeometryRequest requires "
                "'axis_direction'."
            )

        self._validate_vector3(
            name="axis_origin",
            value=axis_origin,
            allow_zero=True,
        )

        self._validate_vector3(
            name="axis_direction",
            value=axis_direction,
            allow_zero=False,
        )

    def _validate_loft_parameters(self) -> None:
        """
        Validates loft parameters.
        """

        if self.geometry.count < 2:
            raise ValueError(
                "Loft GeometryRequest requires at "
                "least two GeometryDefinitions."
            )

        solid = self.get_parameter(
            "solid",
            True,
        )

        if not isinstance(
            solid,
            bool,
        ):
            raise TypeError(
                "Loft solid must be boolean."
            )

    def _validate_sweep_parameters(self) -> None:
        """
        Validates sweep parameters.
        """

        path = self.get_parameter(
            "path"
        )

        if path is None:
            raise ValueError(
                "Sweep GeometryRequest requires "
                "'path'."
            )

        if not isinstance(
            path,
            tuple,
        ) or len(
            path
        ) < 2:
            raise ValueError(
                "Sweep path must contain at least "
                "two points."
            )

        for index, point in enumerate(
            path
        ):
            self._validate_vector3(
                name=f"path[{index}]",
                value=point,
                allow_zero=True,
            )

    def get_parameter(
        self,
        name: str,
        default: Any = None,
    ) -> Any:
        """
        Returns one request parameter.
        """

        if not isinstance(
            name,
            str,
        ) or not name.strip():
            raise ValueError(
                "GeometryRequest parameter name "
                "cannot be empty."
            )

        return self.parameters.get(
            name,
            default,
        )

    @property
    def geometry_count(self) -> int:
        return self.geometry.count

    @property
    def is_extrude(self) -> bool:
        return (
            self.operation
            is GeometryOperationType.EXTRUDE
        )

    @property
    def is_revolve(self) -> bool:
        return (
            self.operation
            is GeometryOperationType.REVOLVE
        )

    @property
    def is_loft(self) -> bool:
        return (
            self.operation
            is GeometryOperationType.LOFT
        )

    @property
    def is_sweep(self) -> bool:
        return (
            self.operation
            is GeometryOperationType.SWEEP
        )

    @staticmethod
    def _numeric_parameter(
        name: str,
        value: Any,
    ) -> float:
        """
        Converts and validates one numeric parameter.
        """

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
                f"GeometryRequest parameter "
                f"'{name}' must be numeric."
            )

        numeric = float(
            value
        )

        if not math.isfinite(
            numeric
        ):
            raise ValueError(
                f"GeometryRequest parameter "
                f"'{name}' must be finite."
            )

        return numeric

    @classmethod
    def _validate_vector3(
        cls,
        *,
        name: str,
        value: Any,
        allow_zero: bool,
    ) -> Vector3:
        """
        Validates one three-dimensional vector.
        """

        if not isinstance(
            value,
            tuple,
        ) or len(
            value
        ) != 3:
            raise TypeError(
                f"GeometryRequest parameter "
                f"'{name}' must be a 3-value tuple."
            )

        normalized: Vector3 = (
    cls._numeric_parameter(
        f"{name}[0]",
        value[0],
    ),
    cls._numeric_parameter(
        f"{name}[1]",
        value[1],
    ),
    cls._numeric_parameter(
        f"{name}[2]",
        value[2],
    ),
)

        length = math.sqrt(
            sum(
                coordinate * coordinate
                for coordinate in normalized
            )
        )

        if (
            not allow_zero
            and length <= 1e-12
        ):
            raise ValueError(
                f"GeometryRequest parameter "
                f"'{name}' cannot be zero."
            )

        return normalized