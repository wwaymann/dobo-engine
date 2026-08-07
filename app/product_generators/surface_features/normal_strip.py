from __future__ import annotations

import cadquery as cq

from product_generators.surface_mapping.contracts import (
    MappedContour,
)


class SurfaceNormalStripBuilder:
    """
    Builds side strips between a mapped contour and
    its normal-offset copy.

    Each side is a ruled surface between two 3D edges.
    This is required because the four corner points are
    generally not coplanar on curved surfaces.
    """

    def build(
        self,
        contour: MappedContour,
        *,
        depth: float,
        inward: bool = False,
    ) -> cq.Shape:
        contour.validate()

        depth = float(depth)

        if depth <= 0.0:
            raise ValueError(
                "depth must be greater than zero."
            )

        samples = contour.samples

        if len(samples) < 2:
            raise ValueError(
                "Normal strip requires at least two samples."
            )

        faces: list[cq.Shape] = []

        pair_count = (
            len(samples)
            if contour.closed
            else len(samples) - 1
        )

        sign = (
            -1.0
            if inward
            else 1.0
        )

        for index in range(pair_count):
            a = samples[index]
            b = samples[
                (index + 1)
                % len(samples)
            ]

            a0 = cq.Vector(
                float(a.point[0]),
                float(a.point[1]),
                float(a.point[2]),
            )

            b0 = cq.Vector(
                float(b.point[0]),
                float(b.point[1]),
                float(b.point[2]),
            )

            a1 = cq.Vector(
                float(a.point[0])
                + float(a.frame.normal[0])
                * depth
                * sign,
                float(a.point[1])
                + float(a.frame.normal[1])
                * depth
                * sign,
                float(a.point[2])
                + float(a.frame.normal[2])
                * depth
                * sign,
            )

            b1 = cq.Vector(
                float(b.point[0])
                + float(b.frame.normal[0])
                * depth
                * sign,
                float(b.point[1])
                + float(b.frame.normal[1])
                * depth
                * sign,
                float(b.point[2])
                + float(b.frame.normal[2])
                * depth
                * sign,
            )

            base_edge = cq.Edge.makeLine(
                a0,
                b0,
            )

            offset_edge = cq.Edge.makeLine(
                a1,
                b1,
            )

            face = cq.Face.makeRuledSurface(
                base_edge,
                offset_edge,
            )

            if not isinstance(
                face,
                cq.Shape,
            ):
                raise RuntimeError(
                    "Normal strip did not produce "
                    "a CadQuery Shape."
                )

            if not face.isValid():
                raise RuntimeError(
                    "Normal strip generated "
                    "an invalid ruled face."
                )

            faces.append(
                face
            )

        compound = cq.Compound.makeCompound(
            faces
        )

        if not compound.isValid():
            raise RuntimeError(
                "Normal strip compound is invalid."
            )

        return compound
