"""
DOBO CAD Kernel

Sweep Request Executor
"""

from __future__ import annotations

import cadquery as cq

from kernel.contracts.geometry_operation_type import GeometryOperationType
from kernel.contracts.geometry_request import GeometryRequest
from kernel.contracts.geometry_result import GeometryResult

from .geometry_request_executor import GeometryRequestExecutor
from .solid_factory import SolidFactory


class SweepRequestExecutor(GeometryRequestExecutor):
    @property
    def operation_type(self) -> GeometryOperationType:
        return GeometryOperationType.SWEEP

    def execute(self, request: GeometryRequest) -> GeometryResult:
        if not isinstance(request, GeometryRequest):
            raise TypeError("SweepRequestExecutor requires GeometryRequest.")

        request.validate()

        if not self.supports(request.operation):
            raise ValueError("SweepRequestExecutor only supports SWEEP.")

        if request.geometry.count != 1:
            raise ValueError("Sweep requires exactly one profile definition.")

        definition = request.geometry.definitions[0]
        definition.validate()

        profile = self._wire(definition.outer_contour.points)
        inner_wires = [
            self._wire(contour.points)
            for contour in definition.inner_contours
        ]

        path_points = request.get_parameter("path")
        path_vectors = [
            cq.Vector(float(x), float(y), float(z))
            for x, y, z in path_points
        ]
        path = cq.Wire.makePolygon(path_vectors, close=False)

        if not path.isValid():
            raise RuntimeError("Sweep path is invalid.")

        is_frenet = bool(request.get_parameter("is_frenet", False))
        transition = request.get_parameter("transition", "transformed")

        shape = cq.Solid.sweep(
            profile,
            inner_wires,
            path,
            makeSolid=True,
            isFrenet=is_frenet,
            transitionMode=transition,
        ).clean()

        if not shape.isValid():
            raise RuntimeError("Sweep generated invalid geometry.")

        solid = SolidFactory.from_shape(
            geometry=shape,
            source="sweep_request_executor",
            metadata={
                "request_id": request.id,
                "path_point_count": len(path_points),
                "is_frenet": is_frenet,
                "transition": transition,
                **request.metadata,
            },
        )

        result = GeometryResult(
            request=request,
            solid=solid,
            generated_geometry=(shape,),
            metadata={
                "executor": "sweep_request_executor",
                "path_point_count": len(path_points),
            },
        )
        result.validate()
        return result

    @staticmethod
    def _wire(points: tuple[tuple[float, float], ...]) -> cq.Wire:
        vectors = [cq.Vector(float(x), float(y), 0.0) for x, y in points]
        wire = cq.Wire.makePolygon(vectors, close=True)
        if not wire.isValid():
            raise RuntimeError("Invalid sweep profile wire.")
        return wire
