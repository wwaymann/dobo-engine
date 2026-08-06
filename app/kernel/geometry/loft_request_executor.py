"""
DOBO CAD Kernel

Loft Request Executor

Generates a solid through multiple translated
GeometryDefinition sections.
"""

from __future__ import annotations

from typing import Any, cast

import cadquery as cq

from kernel.contracts.geometry_operation_type import (
    GeometryOperationType,
)
from kernel.contracts.geometry_request import (
    GeometryRequest,
)
from kernel.contracts.geometry_result import (
    GeometryResult,
)

from .geometry_request_executor import (
    GeometryRequestExecutor,
)
from .solid_factory import (
    SolidFactory,
)


Vector3 = tuple[
    float,
    float,
    float,
]


class LoftRequestExecutor(
    GeometryRequestExecutor,
):
    """
    Executes solid Loft GeometryRequest objects.

    Each GeometryDefinition represents one loft section.
    The optional section_offsets parameter positions those
    sections in three-dimensional space.

    Sections with inner contours are not yet supported.
    """

    @property
    def operation_type(
        self,
    ) -> GeometryOperationType:
        """
        Returns the supported operation type.
        """

        return GeometryOperationType.LOFT

    def execute(
        self,
        request: GeometryRequest,
    ) -> GeometryResult:
        """
        Executes one Loft GeometryRequest.
        """

        if not isinstance(
            request,
            GeometryRequest,
        ):
            raise TypeError(
                "LoftRequestExecutor requires "
                "a GeometryRequest."
            )

        request.validate()

        if not self.supports(
            request.operation
        ):
            raise ValueError(
                "LoftRequestExecutor only "
                "supports LOFT."
            )

        solid_mode = request.get_parameter(
            "solid",
            True,
        )

        ruled = request.get_parameter(
            "ruled",
            False,
        )

        if not isinstance(
            solid_mode,
            bool,
        ):
            raise TypeError(
                "Loft solid must be boolean."
            )

        if not isinstance(
            ruled,
            bool,
        ):
            raise TypeError(
                "Loft ruled must be boolean."
            )

        if not solid_mode:
            raise NotImplementedError(
                "LoftRequestExecutor currently "
                "supports solid lofts only."
            )

        definitions = (
            request.geometry.definitions
        )

        if len(
            definitions
        ) < 2:
            raise ValueError(
                "LoftRequestExecutor requires "
                "at least two GeometryDefinitions."
            )

        section_offsets = (
            self._resolve_section_offsets(
                value=request.get_parameter(
                    "section_offsets",
                    (),
                ),
                section_count=len(
                    definitions
                ),
            )
        )

        wires: list[cq.Wire] = []

        for definition, offset in zip(
            definitions,
            section_offsets,
        ):
            definition.validate()

            if definition.inner_contours:
                raise NotImplementedError(
                    "LoftRequestExecutor does not yet "
                    "support sections with holes."
                )

            wire = self._build_wire(
                definition
                .outer_contour
                .points
            )

            translated_shape = wire.translate(
                cq.Vector(
                    offset[0],
                    offset[1],
                    offset[2],
                )
            )

            if not isinstance(
                translated_shape,
                cq.Wire,
            ):
                raise RuntimeError(
                    "Translated loft section did "
                    "not remain a CadQuery Wire."
                )

            if not translated_shape.isValid():
                raise RuntimeError(
                    "Translated loft section "
                    "is invalid."
                )

            translated_wire = cast(
                cq.Wire,
                translated_shape,
            )

            wires.append(
                translated_wire
            )

        try:
            geometry = cq.Solid.makeLoft(
                wires,
                ruled=ruled,
            ).clean()

        except Exception as error:
            raise RuntimeError(
                "LoftRequestExecutor could not "
                "generate the loft."
            ) from error

        if not isinstance(
            geometry,
            cq.Shape,
        ):
            raise RuntimeError(
                "LoftRequestExecutor did not "
                "produce a CadQuery Shape."
            )

        if not geometry.isValid():
            raise RuntimeError(
                "LoftRequestExecutor generated "
                "invalid geometry."
            )

        solid = SolidFactory.from_shape(
            geometry=geometry,
            source="loft_request_executor",
            metadata={
                "request_id": request.id,
                "output_id": request.output_id,
                "operation": (
                    request.operation.value
                ),
                "section_count": len(
                    wires
                ),
                "section_offsets": (
                    section_offsets
                ),
                "ruled": ruled,
                "solid": solid_mode,
                **request.metadata,
            },
        )

        result = GeometryResult(
            request=request,
            solid=solid,
            generated_geometry=(
                geometry,
            ),
            metadata={
                "executor": (
                    "loft_request_executor"
                ),
                "operation": (
                    request.operation.value
                ),
                "section_count": len(
                    wires
                ),
                "section_offsets": (
                    section_offsets
                ),
                "ruled": ruled,
                "solid": solid_mode,
            },
        )

        result.validate()

        return result

    @staticmethod
    def _build_wire(
        points: tuple[
            tuple[
                float,
                float,
            ],
            ...,
        ],
    ) -> cq.Wire:
        """
        Builds one closed planar section wire.
        """

        if not isinstance(
            points,
            tuple,
        ) or len(
            points
        ) < 3:
            raise ValueError(
                "Loft section requires at "
                "least three points."
            )

        vectors = [
            cq.Vector(
                float(
                    point[0]
                ),
                float(
                    point[1]
                ),
                0.0,
            )
            for point in points
        ]

        try:
            wire = cq.Wire.makePolygon(
                vectors,
                close=True,
            )

        except Exception as error:
            raise RuntimeError(
                "LoftRequestExecutor could not "
                "build a section wire."
            ) from error

        if not isinstance(
            wire,
            cq.Wire,
        ):
            raise RuntimeError(
                "Loft section did not produce "
                "a CadQuery Wire."
            )

        if not wire.isValid():
            raise RuntimeError(
                "Loft section wire is invalid."
            )

        return wire

    @classmethod
    def _resolve_section_offsets(
        cls,
        *,
        value: Any,
        section_count: int,
    ) -> tuple[
        Vector3,
        ...,
    ]:
        """
        Validates or creates section positions.

        When section_offsets is omitted, the sections are
        placed one unit apart along the positive Z axis.
        """

        if not isinstance(
            section_count,
            int,
        ) or section_count < 2:
            raise ValueError(
                "Loft section_count must be "
                "at least two."
            )

        if value == ():
            return tuple(
                (
                    0.0,
                    0.0,
                    float(
                        index
                    ),
                )
                for index in range(
                    section_count
                )
            )

        if not isinstance(
            value,
            tuple,
        ):
            raise TypeError(
                "Loft section_offsets must "
                "be a tuple."
            )

        if len(
            value
        ) != section_count:
            raise ValueError(
                "Loft section_offsets count must "
                "match GeometryDefinitions."
            )

        return tuple(
            cls._validate_vector3(
                offset,
                index=index,
            )
            for index, offset in enumerate(
                value
            )
        )

    @staticmethod
    def _validate_vector3(
        value: Any,
        *,
        index: int,
    ) -> Vector3:
        """
        Validates one section position.
        """

        if not isinstance(
            value,
            tuple,
        ) or len(
            value
        ) != 3:
            raise TypeError(
                "Loft section offset "
                f"{index} must be a 3-value tuple."
            )

        coordinates: list[float] = []

        for coordinate in value:
            if isinstance(
                coordinate,
                bool,
            ) or not isinstance(
                coordinate,
                (
                    int,
                    float,
                ),
            ):
                raise TypeError(
                    "Loft section offset values "
                    "must be numeric."
                )

            coordinates.append(
                float(
                    coordinate
                )
            )

        return (
            coordinates[0],
            coordinates[1],
            coordinates[2],
        )