"""
DOBO CAD Kernel

Extrude Request Executor

Executes GeometryRequest objects whose operation type
is EXTRUDE.
"""

from __future__ import annotations

from typing import Any

import cadquery as cq

from kernel.contracts.contour_definition import (
    ContourDefinition,
)
from kernel.contracts.geometry_definition import (
    GeometryDefinition,
)
from kernel.contracts.geometry_operation_type import (
    GeometryOperationType,
)
from kernel.contracts.geometry_request import (
    GeometryRequest,
    Vector3,
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


class ExtrudeRequestExecutor(
    GeometryRequestExecutor,
):
    """
    Executes planar extrusion requests.

    Supports:

    - exterior contours;
    - inner contours as holes;
    - multiple independent regions;
    - symmetric extrusion;
    - arbitrary extrusion directions.

    Non-zero draft angles are not yet supported.
    """

    @property
    def operation_type(
        self,
    ) -> GeometryOperationType:
        """
        Returns the supported operation type.
        """

        return GeometryOperationType.EXTRUDE

    def execute(
        self,
        request: GeometryRequest,
    ) -> GeometryResult:
        """
        Executes one EXTRUDE GeometryRequest.
        """

        if not isinstance(
            request,
            GeometryRequest,
        ):
            raise TypeError(
                "ExtrudeRequestExecutor requires "
                "a GeometryRequest."
            )

        request.validate()

        if not self.supports(
            request.operation
        ):
            raise ValueError(
                "ExtrudeRequestExecutor cannot execute "
                f"'{request.operation.value}'."
            )

        distance = float(
            request.get_parameter(
                "distance"
            )
        )

        direction = self._normalize_vector(
            request.get_parameter(
                "direction",
                (
                    0.0,
                    0.0,
                    1.0,
                ),
            )
        )

        symmetric = request.get_parameter(
            "symmetric",
            False,
        )

        draft_angle = float(
            request.get_parameter(
                "draft_angle",
                0.0,
            )
        )

        if abs(
            draft_angle
        ) > 1e-12:
            raise NotImplementedError(
                "ExtrudeRequestExecutor does not yet "
                "support non-zero draft_angle."
            )

        extrusion_vector = cq.Vector(
            direction[0]
            * distance,
            direction[1]
            * distance,
            direction[2]
            * distance,
        )

        generated_geometry = tuple(
            self._extrude_definition(
                definition=definition,
                vector=extrusion_vector,
                symmetric=symmetric,
            )
            for definition
            in request.geometry.definitions
        )

        if not generated_geometry:
            raise RuntimeError(
                "ExtrudeRequestExecutor generated "
                "no geometry."
            )

        combined_geometry = self._combine_shapes(
            generated_geometry
        )

        solid = SolidFactory.from_shape(
            geometry=combined_geometry,
            source="extrude_request_executor",
            metadata={
                "request_id": request.id,
                "output_id": request.output_id,
                "operation": request.operation.value,
                "geometry_definition_count": (
                    request.geometry.count
                ),
                "generated_geometry_count": len(
                    generated_geometry
                ),
                "distance": distance,
                "direction": direction,
                "symmetric": symmetric,
                "draft_angle": draft_angle,
                **request.metadata,
            },
        )

        result = GeometryResult(
            request=request,
            solid=solid,
            generated_geometry=generated_geometry,
            metadata={
                "executor": (
                    "extrude_request_executor"
                ),
                "operation": (
                    request.operation.value
                ),
                "distance": distance,
                "direction": direction,
                "symmetric": symmetric,
                "draft_angle": draft_angle,
                "geometry_count": (
                    request.geometry.count
                ),
                "generated_geometry_count": len(
                    generated_geometry
                ),
                **request.metadata,
            },
        )

        result.validate()

        return result

    def _extrude_definition(
        self,
        *,
        definition: GeometryDefinition,
        vector: cq.Vector,
        symmetric: bool,
    ) -> cq.Shape:
        """
        Extrudes one planar GeometryDefinition.
        """

        definition.validate()

        outer_wire = self._build_wire(
            definition.outer_contour
        )

        inner_wires = tuple(
            self._build_wire(
                contour
            )
            for contour
            in definition.inner_contours
        )

        if symmetric:
            translation = cq.Vector(
                -vector.x / 2.0,
                -vector.y / 2.0,
                -vector.z / 2.0,
            )

            outer_wire = self._translate_wire(
                outer_wire,
                translation,
            )

            inner_wires = tuple(
                self._translate_wire(
                    wire,
                    translation,
                )
                for wire in inner_wires
            )

        try:
            geometry = cq.Solid.extrudeLinear(
                outer_wire,
                list(
                    inner_wires
                ),
                vector,
            ).clean()

        except Exception as error:
            raise RuntimeError(
                "ExtrudeRequestExecutor could not "
                "extrude the GeometryDefinition."
            ) from error

        if not isinstance(
            geometry,
            cq.Shape,
        ):
            raise RuntimeError(
                "ExtrudeRequestExecutor did not "
                "produce a CadQuery Shape."
            )

        if not geometry.isValid():
            raise RuntimeError(
                "ExtrudeRequestExecutor generated "
                "invalid geometry."
            )

        return geometry

    @staticmethod
    def _build_wire(
        contour: ContourDefinition,
    ) -> cq.Wire:
        """
        Converts one contour into a planar wire.
        """

        contour.validate()

        if not contour.closed:
            raise ValueError(
                "ExtrudeRequestExecutor requires "
                "closed contours."
            )

        points = [
            cq.Vector(
                float(
                    point[0]
                ),
                float(
                    point[1]
                ),
                0.0,
            )
            for point in contour.points
        ]

        try:
            wire = cq.Wire.makePolygon(
                points,
                close=True,
            )

        except Exception as error:
            raise RuntimeError(
                "ExtrudeRequestExecutor could not "
                "build a contour wire."
            ) from error

        if not isinstance(
            wire,
            cq.Wire,
        ):
            raise RuntimeError(
                "ExtrudeRequestExecutor did not "
                "produce a CadQuery Wire."
            )

        if not wire.isValid():
            raise RuntimeError(
                "ExtrudeRequestExecutor generated "
                "an invalid wire."
            )

        return wire

    @staticmethod
    def _translate_wire(
        wire: cq.Wire,
        translation: cq.Vector,
    ) -> cq.Wire:
        """
        Translates one CadQuery wire.
        """

        translated = wire.translate(
            translation
        )

        if not isinstance(
            translated,
            cq.Wire,
        ):
            raise RuntimeError(
                "ExtrudeRequestExecutor could not "
                "translate a wire."
            )

        if not translated.isValid():
            raise RuntimeError(
                "ExtrudeRequestExecutor translated "
                "an invalid wire."
            )

        return translated

    @staticmethod
    def _combine_shapes(
        geometries: tuple[
            cq.Shape,
            ...,
        ],
    ) -> cq.Shape:
        """
        Combines generated shapes.

        Intersecting shapes are fused. Separate shapes
        are preserved inside a compound.
        """

        if not geometries:
            raise ValueError(
                "Cannot combine empty geometry."
            )

        if len(
            geometries
        ) == 1:
            return geometries[0]

        combined = geometries[0]

        for geometry in geometries[1:]:
            try:
                fused = combined.fuse(
                    geometry
                ).clean()

                if not fused.isValid():
                    raise RuntimeError(
                        "Invalid fused geometry."
                    )

                combined = fused

            except Exception:
                compound = cq.Compound.makeCompound(
                    [
                        combined,
                        geometry,
                    ]
                )

                if not compound.isValid():
                    raise RuntimeError(
                        "ExtrudeRequestExecutor could "
                        "not combine generated geometry."
                    )

                combined = compound

        if not combined.isValid():
            raise RuntimeError(
                "ExtrudeRequestExecutor produced an "
                "invalid combined shape."
            )

        return combined

    @staticmethod
    def _normalize_vector(
        value: Any,
    ) -> Vector3:
        """
        Validates and normalizes one Vector3.
        """

        if not isinstance(
            value,
            tuple,
        ) or len(
            value
        ) != 3:
            raise TypeError(
                "Extrusion direction must be "
                "a 3-value tuple."
            )

        coordinates: list[float] = []

        for index, coordinate in enumerate(
            value
        ):
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
                    "Extrusion direction coordinate "
                    f"{index} must be numeric."
                )

            coordinates.append(
                float(
                    coordinate
                )
            )

        x = coordinates[0]
        y = coordinates[1]
        z = coordinates[2]

        length = (
            x * x
            + y * y
            + z * z
        ) ** 0.5

        if length <= 1e-12:
            raise ValueError(
                "Extrusion direction cannot be zero."
            )

        normalized: Vector3 = (
            x / length,
            y / length,
            z / length,
        )

        return normalized