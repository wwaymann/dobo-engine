from __future__ import annotations

from dataclasses import dataclass

import cadquery as cq

from product_generators.surface_mapping.contracts import (
    MappedContour,
    SurfaceSample,
)


@dataclass(frozen=True, slots=True)
class NormalExtrusionResult:
    contour_id: str
    shape: cq.Shape
    sample_count: int
    depth: float
    radius: float

    def validate(self) -> None:
        if not isinstance(self.contour_id, str) or not self.contour_id.strip():
            raise ValueError("contour_id cannot be empty.")

        if not isinstance(self.shape, cq.Shape):
            raise TypeError("shape must be a CadQuery Shape.")

        if not self.shape.isValid():
            raise RuntimeError("Normal extrusion produced invalid geometry.")

        if isinstance(self.sample_count, bool) or not isinstance(
            self.sample_count,
            int,
        ):
            raise TypeError("sample_count must be an integer.")

        if self.sample_count < 1:
            raise ValueError("sample_count must be positive.")

        if self.depth <= 0.0:
            raise ValueError("depth must be positive.")

        if self.radius <= 0.0:
            raise ValueError("radius must be positive.")


class SurfaceNormalExtruder:
    """
    Creates real 3D solids aligned to local surface normals.

    Phase 3.2 deliberately validates the difficult orientation problem
    separately from filled-region emboss construction.

    Every mapped sample produces one cylindrical solid whose axis follows
    the local surface normal. The resulting compound can be inspected,
    exported, patterned and later consumed by higher-level feature builders.
    """

    def extrude_contour(
        self,
        contour: MappedContour,
        *,
        depth: float,
        radius: float = 0.7,
        inward: bool = False,
        base_offset: float = 0.0,
    ) -> NormalExtrusionResult:
        contour.validate()

        depth = float(depth)
        radius = float(radius)
        base_offset = float(base_offset)

        if depth <= 0.0:
            raise ValueError("depth must be greater than zero.")

        if radius <= 0.0:
            raise ValueError("radius must be greater than zero.")

        shapes: list[cq.Shape] = []

        for sample in contour.samples:
            shapes.append(
                self._sample_solid(
                    sample,
                    depth=depth,
                    radius=radius,
                    inward=inward,
                    base_offset=base_offset,
                )
            )

        compound = cq.Compound.makeCompound(
            shapes
        )

        if not compound.isValid():
            raise RuntimeError(
                "Normal extrusion compound is invalid."
            )

        result = NormalExtrusionResult(
            contour_id=contour.id,
            shape=compound,
            sample_count=len(contour.samples),
            depth=depth,
            radius=radius,
        )
        result.validate()
        return result

    @staticmethod
    def _sample_solid(
        sample: SurfaceSample,
        *,
        depth: float,
        radius: float,
        inward: bool,
        base_offset: float,
    ) -> cq.Shape:
        sample.validate()

        normal = sample.frame.normal

        direction_scale = (
            -1.0
            if inward
            else 1.0
        )

        direction = cq.Vector(
            normal[0] * direction_scale,
            normal[1] * direction_scale,
            normal[2] * direction_scale,
        )

        origin = cq.Vector(
            sample.point[0]
            + normal[0]
            * base_offset
            * direction_scale,
            sample.point[1]
            + normal[1]
            * base_offset
            * direction_scale,
            sample.point[2]
            + normal[2]
            * base_offset
            * direction_scale,
        )

        solid = cq.Solid.makeCylinder(
            radius,
            depth,
            origin,
            direction,
        )

        if not isinstance(
            solid,
            cq.Shape,
        ):
            raise RuntimeError(
                "Normal extrusion did not produce a Shape."
            )

        if not solid.isValid():
            raise RuntimeError(
                "Normal extrusion sample is invalid."
            )

        return solid
