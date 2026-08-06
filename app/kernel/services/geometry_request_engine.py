"""
DOBO CAD Kernel

Geometry Request Engine

Executes universal backend-independent GeometryRequest
objects and produces validated Solid contracts.

Initial support:

- EXTRUDE
- planar GeometryDefinition objects
- inner contours as real holes
- symmetric extrusion
- arbitrary extrusion direction

Current limitation:

- non-zero draft angles are not yet supported
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
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
from kernel.contracts.solid import (
    BoundingBox,
    Solid,
    SolidValidation,
)
from kernel.contracts.geometry_result import GeometryResult

@dataclass(frozen=True, slots=True)
class GeometryRequestEngineResult:
    """
    Result produced by GeometryRequestEngine.
    """

    request: GeometryRequest

    solid: Solid

    generated_solids: tuple[
        cq.Shape,
        ...,
    ]

    metadata: dict[
        str,
        Any,
    ] = field(
        default_factory=dict
    )

    def validate(self) -> None:
        """
        Validates the complete engine result.
        """

        if not isinstance(
            self.request,
            GeometryRequest,
        ):
            raise TypeError(
                "GeometryRequestEngineResult request "
                "must be GeometryRequest."
            )

        self.request.validate()

        if not isinstance(
            self.solid,
            Solid,
        ):
            raise TypeError(
                "GeometryRequestEngineResult solid "
                "must be Solid."
            )

        self.solid.validate()

        if not isinstance(
            self.generated_solids,
            tuple,
        ):
            raise TypeError(
                "GeometryRequestEngineResult "
                "generated_solids must be a tuple."
            )

        if not self.generated_solids:
            raise ValueError(
                "GeometryRequestEngineResult cannot "
                "contain zero generated solids."
            )

        for geometry in self.generated_solids:
            if not isinstance(
                geometry,
                cq.Shape,
            ):
                raise TypeError(
                    "GeometryRequestEngineResult "
                    "contains non-CadQuery geometry."
                )

            if not geometry.isValid():
                raise ValueError(
                    "GeometryRequestEngineResult "
                    "contains invalid CAD geometry."
                )

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "GeometryRequestEngineResult metadata "
                "must be a dictionary."
            )

    @property
    def count(self) -> int:
        """
        Returns the number of generated solids.
        """

        return len(
            self.generated_solids
        )


class GeometryRequestEngineInterface(ABC):
    """
    Public GeometryRequest execution interface.
    """

    @abstractmethod
    def execute(
        self,
        request: GeometryRequest,
    ) -> GeometryRequestEngineResult:
        """
        Executes one GeometryRequest.
        """


class GeometryRequestEngine(
    GeometryRequestEngineInterface,
):
    """
    Executes universal GeometryRequest objects.

    The engine currently supports planar extrusion.
    """

    def execute(
        self,
        request: GeometryRequest,
    ) -> GeometryRequestEngineResult:
        """
        Executes one validated GeometryRequest.
        """

        if not isinstance(
            request,
            GeometryRequest,
        ):
            raise TypeError(
                "GeometryRequestEngine requires "
                "a GeometryRequest."
            )

        request.validate()

        if (
            request.operation
            is GeometryOperationType.EXTRUDE
        ):
            return self._execute_extrude(
                request
            )

        raise NotImplementedError(
            "GeometryRequestEngine does not yet "
            f"support '{request.operation.value}'."
        )

    def _execute_extrude(
        self,
        request: GeometryRequest,
    ) -> GeometryRequestEngineResult:
        """
        Executes one extrusion request.
        """

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
                "GeometryRequestEngine does not yet "
                "support non-zero extrusion draft_angle."
            )

        extrusion_vector = cq.Vector(
            direction[0]
            * distance,
            direction[1]
            * distance,
            direction[2]
            * distance,
        )

        generated_solids = tuple(
            self._extrude_definition(
                definition=definition,
                vector=extrusion_vector,
                symmetric=symmetric,
            )
            for definition
            in request.geometry.definitions
        )

        if not generated_solids:
            raise RuntimeError(
                "GeometryRequestEngine generated "
                "no solids."
            )

        combined_geometry = self._combine_solids(
            generated_solids
        )

        solid = self._build_solid_contract(
            geometry=combined_geometry,
            request=request,
            generated_count=len(
                generated_solids
            ),
        )

        result = GeometryRequestEngineResult(
            request=request,
            solid=solid,
            generated_solids=generated_solids,
            metadata={
                "engine": (
                    "geometry_request_engine"
                ),
                "operation": (
                    request.operation.value
                ),
                "geometry_count": (
                    request.geometry.count
                ),
                "generated_solid_count": len(
                    generated_solids
                ),
                "distance": distance,
                "direction": direction,
                "symmetric": symmetric,
                "draft_angle": draft_angle,
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
        Extrudes one GeometryDefinition.

        Inner contours are used as holes in the
        generated planar solid.
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

            translated_outer = (
                outer_wire.translate(
                    translation
                )
            )

            if not isinstance(
                translated_outer,
                cq.Wire,
            ):
                raise RuntimeError(
                    "GeometryRequestEngine could not "
                    "translate the outer Wire."
                )

            outer_wire = translated_outer

            translated_inner: list[
                cq.Wire
            ] = []

            for wire in inner_wires:
                translated_wire = wire.translate(
                    translation
                )

                if not isinstance(
                    translated_wire,
                    cq.Wire,
                ):
                    raise RuntimeError(
                        "GeometryRequestEngine could not "
                        "translate an inner Wire."
                    )

                translated_inner.append(
                    translated_wire
                )

            inner_wires = tuple(
                translated_inner
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
                "GeometryRequestEngine could not "
                "extrude the GeometryDefinition."
            ) from error

        if not isinstance(
            geometry,
            cq.Shape,
        ):
            raise RuntimeError(
                "GeometryRequestEngine extrusion "
                "did not produce a CadQuery Shape."
            )

        if not geometry.isValid():
            raise RuntimeError(
                "GeometryRequestEngine generated "
                "invalid extrusion geometry."
            )

        return geometry

    @staticmethod
    def _build_wire(
        contour: ContourDefinition,
    ) -> cq.Wire:
        """
        Converts one closed ContourDefinition
        into a planar CadQuery Wire.
        """

        contour.validate()

        if not contour.closed:
            raise ValueError(
                "GeometryRequestEngine requires "
                "closed contours for extrusion."
            )

        points = tuple(
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
        )

        try:
            wire = cq.Wire.makePolygon(
                list(
                    points
                ),
                close=True,
            )

        except Exception as error:
            raise RuntimeError(
                "GeometryRequestEngine could not "
                "create a Wire from a contour."
            ) from error

        if not isinstance(
            wire,
            cq.Wire,
        ):
            raise RuntimeError(
                "GeometryRequestEngine did not "
                "produce a CadQuery Wire."
            )

        if not wire.isValid():
            raise RuntimeError(
                "GeometryRequestEngine generated "
                "an invalid contour Wire."
            )

        return wire

    @staticmethod
    def _combine_solids(
        solids: tuple[
            cq.Shape,
            ...,
        ],
    ) -> cq.Shape:
        """
        Combines generated solids into one shape.

        Separate regions remain valid solids inside
        a compound when they do not intersect.
        """

        if not solids:
            raise ValueError(
                "Cannot combine an empty solid tuple."
            )

        if len(
            solids
        ) == 1:
            return solids[0]

        combined = solids[0]

        for geometry in solids[1:]:
            try:
                fused = combined.fuse(
                    geometry
                ).clean()

                if not fused.isValid():
                    raise RuntimeError(
                        "Fused geometry is invalid."
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
                        "GeometryRequestEngine could not "
                        "combine generated solids."
                    )

                combined = compound

        if not combined.isValid():
            raise RuntimeError(
                "GeometryRequestEngine could not "
                "combine the generated solids."
            )

        return combined

    def _build_solid_contract(
        self,
        *,
        geometry: cq.Shape,
        request: GeometryRequest,
        generated_count: int,
    ) -> Solid:
        """
        Builds the public Kernel Solid contract.
        """

        if not isinstance(
            geometry,
            cq.Shape,
        ):
            raise TypeError(
                "Solid geometry must be "
                "a CadQuery Shape."
            )

        if not geometry.isValid():
            raise ValueError(
                "Cannot create Solid contract from "
                "invalid geometry."
            )

        volume = float(
            geometry.Volume()
        )

        if volume <= 0:
            raise ValueError(
                "Generated geometry has zero or "
                "negative volume."
            )

        center = geometry.Center()

        backend_bounds = (
            geometry.BoundingBox()
        )

        bounding_box = BoundingBox(
            minimum=(
                float(
                    backend_bounds.xmin
                ),
                float(
                    backend_bounds.ymin
                ),
                float(
                    backend_bounds.zmin
                ),
            ),
            maximum=(
                float(
                    backend_bounds.xmax
                ),
                float(
                    backend_bounds.ymax
                ),
                float(
                    backend_bounds.zmax
                ),
            ),
        )

        bounding_box.validate()

        solid = Solid(
            geometry=geometry,
            volume=volume,
            center_of_mass=(
                float(
                    center.x
                ),
                float(
                    center.y
                ),
                float(
                    center.z
                ),
            ),
            bounding_box=bounding_box,
            validation=SolidValidation(
                is_valid=True,
                is_closed=True,
                is_manifold=True,
                is_watertight=True,
                errors=(),
                warnings=(),
            ),
            source=(
                "geometry_request_engine"
            ),
            metadata={
                "request_id": request.id,
                "output_id": request.output_id,
                "operation": (
                    request.operation.value
                ),
                "geometry_definition_count": (
                    request.geometry.count
                ),
                "generated_solid_count": (
                    generated_count
                ),
                **request.metadata,
            },
        )

        solid.validate()

        return solid

    @staticmethod
    def _normalize_vector(
        value: object,
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

        result: Vector3 = (
            x / length,
            y / length,
            z / length,
        )

        return result