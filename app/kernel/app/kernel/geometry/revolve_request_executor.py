"""
DOBO CAD Kernel

Revolve Request Executor
"""

from __future__ import annotations

import cadquery as cq

from kernel.contracts.geometry_operation_type import GeometryOperationType
from kernel.contracts.geometry_request import GeometryRequest
from kernel.contracts.geometry_result import GeometryResult

from .geometry_request_executor import GeometryRequestExecutor
from .solid_factory import SolidFactory


class RevolveRequestExecutor(GeometryRequestExecutor):
    @property
    def operation_type(self) -> GeometryOperationType:
        return GeometryOperationType.REVOLVE

    def execute(self, request: GeometryRequest) -> GeometryResult:
        if not isinstance(request, GeometryRequest):
            raise TypeError("RevolveRequestExecutor requires GeometryRequest.")

        request.validate()

        if not self.supports(request.operation):
            raise ValueError("RevolveRequestExecutor only supports REVOLVE.")

        angle = float(request.get_parameter("angle"))
        axis_origin = tuple(float(v) for v in request.get_parameter("axis_origin"))
        axis_direction = tuple(float(v) for v in request.get_parameter("axis_direction"))

        axis_start = cq.Vector(*axis_origin)
        axis_end = cq.Vector(
            axis_origin[0] + axis_direction[0],
            axis_origin[1] + axis_direction[1],
            axis_origin[2] + axis_direction[2],
        )

        generated: list[cq.Shape] = []

        for definition in request.geometry.definitions:
            definition.validate()

            outer = self._wire(definition.outer_contour.points)
            inners = [
                self._wire(contour.points)
                for contour in definition.inner_contours
            ]

            shape = cq.Solid.revolve(
                outer,
                inners,
                angle,
                axis_start,
                axis_end,
            ).clean()

            if not shape.isValid():
                raise RuntimeError("Revolve generated invalid geometry.")

            generated.append(shape)

        combined = self._combine(tuple(generated))

        solid = SolidFactory.from_shape(
            geometry=combined,
            source="revolve_request_executor",
            metadata={
                "request_id": request.id,
                "angle": angle,
                "axis_origin": axis_origin,
                "axis_direction": axis_direction,
                **request.metadata,
            },
        )

        result = GeometryResult(
            request=request,
            solid=solid,
            generated_geometry=tuple(generated),
            metadata={
                "executor": "revolve_request_executor",
                "angle": angle,
            },
        )
        result.validate()
        return result

    @staticmethod
    def _wire(points: tuple[tuple[float, float], ...]) -> cq.Wire:
        vectors = [cq.Vector(float(x), float(y), 0.0) for x, y in points]
        wire = cq.Wire.makePolygon(vectors, close=True)
        if not wire.isValid():
            raise RuntimeError("Invalid revolve profile wire.")
        return wire

    @staticmethod
    def _combine(shapes: tuple[cq.Shape, ...]) -> cq.Shape:
        if not shapes:
            raise RuntimeError("Revolve generated no geometry.")
        if len(shapes) == 1:
            return shapes[0]
        compound = cq.Compound.makeCompound(list(shapes))
        if not compound.isValid():
            raise RuntimeError("Invalid revolve compound.")
        return compound
