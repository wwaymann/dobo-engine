from __future__ import annotations

from dataclasses import dataclass

import cadquery as cq

from product_generators.surface_mapping.contracts import (
    MappedContour,
    SurfaceSample,
)

from .triangulation import (
    triangulate_simple_polygon,
)


@dataclass(frozen=True, slots=True)
class ClosedSurfaceFeatureResult:
    contour_id: str
    shape: cq.Shape
    triangle_count: int
    depth: float
    inward: bool

    def validate(self) -> None:
        if not isinstance(
            self.contour_id,
            str,
        ) or not self.contour_id.strip():
            raise ValueError(
                "contour_id cannot be empty."
            )

        if not isinstance(
            self.shape,
            cq.Shape,
        ):
            raise TypeError(
                "shape must be a CadQuery Shape."
            )

        if not self.shape.isValid():
            raise RuntimeError(
                "Closed surface feature is invalid."
            )

        if self.triangle_count < 1:
            raise ValueError(
                "triangle_count must be positive."
            )

        if self.depth <= 0.0:
            raise ValueError(
                "depth must be positive."
            )


class ClosedSurfaceFeatureSolidBuilder:
    """
    Builds a closed 3D feature volume from a mapped contour.

    The region is triangulated in UV space. Each triangle becomes
    a closed six-face prism whose top vertices are displaced along
    each vertex's local surface normal.

    This avoids the false assumption that a complete mapped region
    or side quad is planar.
    """

    def build(
        self,
        contour: MappedContour,
        *,
        depth: float,
        inward: bool = False,
    ) -> ClosedSurfaceFeatureResult:
        contour.validate()

        if not contour.closed:
            raise ValueError(
                "Closed surface feature requires "
                "a closed contour."
            )

        depth = float(
            depth
        )

        if depth <= 0.0:
            raise ValueError(
                "depth must be greater than zero."
            )

        uv_points = tuple(
            (
                float(sample.u),
                float(sample.v),
            )
            for sample in contour.samples
        )

        triangles = (
            triangulate_simple_polygon(
                uv_points
            )
        )

        solids: list[
            cq.Shape
        ] = []

        for triangle in triangles:
            samples = (
                contour.samples[
                    triangle[0]
                ],
                contour.samples[
                    triangle[1]
                ],
                contour.samples[
                    triangle[2]
                ],
            )

            solid = (
                self._triangle_prism(
                    samples,
                    depth=depth,
                    inward=inward,
                )
            )

            if not solid.isValid():
                raise RuntimeError(
                    "Triangle feature prism is invalid."
                )

            solids.append(
                solid
            )

        compound = (
            cq.Compound.makeCompound(
                solids
            )
        )

        if not compound.isValid():
            raise RuntimeError(
                "Closed feature compound is invalid."
            )

        result = (
            ClosedSurfaceFeatureResult(
                contour_id=contour.id,
                shape=compound,
                triangle_count=len(
                    triangles
                ),
                depth=depth,
                inward=inward,
            )
        )

        result.validate()

        return result

    @staticmethod
    def _triangle_prism(
        samples: tuple[
            SurfaceSample,
            SurfaceSample,
            SurfaceSample,
        ],
        *,
        depth: float,
        inward: bool,
    ) -> cq.Shape:
        sign = (
            -1.0
            if inward
            else 1.0
        )

        base: list[
            cq.Vector
        ] = []

        top: list[
            cq.Vector
        ] = []

        for sample in samples:
            sample.validate()

            base.append(
                cq.Vector(
                    *sample.point
                )
            )

            top.append(
                cq.Vector(
                    sample.point[0]
                    + sample.frame.normal[0]
                    * depth
                    * sign,
                    sample.point[1]
                    + sample.frame.normal[1]
                    * depth
                    * sign,
                    sample.point[2]
                    + sample.frame.normal[2]
                    * depth
                    * sign,
                )
            )

        faces: list[
            cq.Face
        ] = []

        faces.append(
            ClosedSurfaceFeatureSolidBuilder
            ._triangle_face(
                base[0],
                base[1],
                base[2],
            )
        )

        faces.append(
            ClosedSurfaceFeatureSolidBuilder
            ._triangle_face(
                top[2],
                top[1],
                top[0],
            )
        )

        side_indices = (
            (0, 1),
            (1, 2),
            (2, 0),
        )

        for a, b in (
            side_indices
        ):
            faces.append(
                ClosedSurfaceFeatureSolidBuilder
                ._triangle_face(
                    base[a],
                    base[b],
                    top[b],
                )
            )

            faces.append(
                ClosedSurfaceFeatureSolidBuilder
                ._triangle_face(
                    base[a],
                    top[b],
                    top[a],
                )
            )

        shell = cq.Shell.makeShell(
            faces
        )

        if not shell.isValid():
            raise RuntimeError(
                "Triangle prism shell is invalid."
            )

        solid = cq.Solid.makeSolid(
            shell
        )

        return solid.clean()

    @staticmethod
    def _triangle_face(
        a: cq.Vector,
        b: cq.Vector,
        c: cq.Vector,
    ) -> cq.Face:
        wire = cq.Wire.makePolygon(
            (
                a,
                b,
                c,
            ),
            close=True,
        )

        face = cq.Face.makeFromWires(
            wire
        )

        if not face.isValid():
            raise RuntimeError(
                "Triangle face is invalid."
            )

        return face
