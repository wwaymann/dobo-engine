"""
DOBO CAD Kernel

Loft Request Executor
"""

from __future__ import annotations

import cadquery as cq

from kernel.contracts.geometry_operation_type import GeometryOperationType
from kernel.contracts.geometry_request import GeometryRequest
from kernel.contracts.geometry_result import GeometryResult

from .geometry_request_executor import GeometryRequestExecutor
from .solid_factory import SolidFactory


class LoftRequestExecutor(GeometryRequestExecutor):
    @property
    def operation_type(self) -> GeometryOperationType:
        return GeometryOperationType.LOFT

    def execute(self, request: GeometryRequest) -> GeometryResult:
        if not isinstance(request, GeometryRequest):
            raise TypeError("LoftRequestExecutor requires GeometryRequest.")

        request.validate()

        if not self.supports(request.operation):
            raise ValueError("LoftRequestExecutor only supports LOFT.")

        solid_mode = bool(request.get_parameter("solid", True))
        ruled = bool(request.get_parameter("ruled", False))
        section_offsets = request.get_parameter("section_offsets", ())

        definitions = request.geometry.definitions

        if section_offsets:
            if not isinstance(section_offsets, tuple):
                raise TypeError("section_offsets must be a tuple.")
            if len(section_offsets) != len(definitions):
                raise ValueError(
                    "section_offsets count must match GeometryDefinitions."
                )
        else:
            section_offsets = tuple(
                (0.0, 0.0, float(index))
                for index in range(len(definitions))
            )

        wires: list[cq.Wire] = []

        for definition, offset in zip(definitions, section_offsets):
            definition.validate()

            if definition.inner_contours:
                raise NotImplementedError(
                    "Loft holes require matched inner-wire lofts and are "
                    "not enabled in this first implementation."
                )

            wire = self._wire(definition.outer_contour.points)
            translation = cq.Vector(
                float(offset[0]),
                float(offset[1]),
                float(offset[2]),
            )
            translated = wire.translate(translation)

            if not isinstance(translated, cq.Wire) or not translated.isValid():
                raise RuntimeError("Invalid translated loft section.")

            wires.append(translated)

        shape = cq.Solid.makeLoft(
            wires,
            ruled=ruled,
            closed=False,
        ).clean()

        if not shape.isValid():
            raise RuntimeError("Loft generated invalid geometry.")

        if not solid_mode:
            raise NotImplementedError(
                "Surface-only loft output is not supported by SolidFactory."
            )

        solid = SolidFactory.from_shape(
            geometry=shape,
            source="loft_request_executor",
            metadata={
                "request_id": request.id,
                "section_count": len(wires),
                "ruled": ruled,
                **request.metadata,
            },
        )

        result = GeometryResult(
            request=request,
            solid=solid,
            generated_geometry=(shape,),
            metadata={
                "executor": "loft_request_executor",
                "section_count": len(wires),
                "ruled": ruled,
            },
        )
        result.validate()
        return result

    @staticmethod
    def _wire(points: tuple[tuple[float, float], ...]) -> cq.Wire:
        vectors = [cq.Vector(float(x), float(y), 0.0) for x, y in points]
        wire = cq.Wire.makePolygon(vectors, close=True)
        if not wire.isValid():
            raise RuntimeError("Invalid loft section wire.")
        return wire
