from __future__ import annotations

import cadquery as cq

from product_generators.surface_features.topology import (
    SurfaceFeatureTopologyAnalyzer,
)
from product_generators.vector_geometry.svg_parser import (
    SvgVectorParser,
)


class SvgPlanarFaceBuilder:
    """
    Converts existing DOBO SVG/vector topology into planar CadQuery faces.

    The result remains exact planar B-Rep input for faceOn().
    """

    def __init__(self) -> None:
        self._parser = SvgVectorParser()
        self._topology = SurfaceFeatureTopologyAnalyzer()

    def build(
        self,
        svg: str,
        *,
        document_id: str = "surface_svg",
    ) -> cq.Shape:
        document = self._parser.parse_string(
            svg,
            document_id=document_id,
        )

        document.validate()

        topology = self._topology.analyze(document)

        by_id = {
            contour.id: contour
            for contour in document.contours
        }

        roots = tuple(
            loop
            for loop in topology.loops
            if loop.depth == 0
        )

        if not roots:
            raise RuntimeError(
                "SVG contains no outer loops."
            )

        faces: list[cq.Face] = []

        for root in roots:
            outer_contour = by_id[root.id]

            outer_wire = self._wire(
                outer_contour.points
            )

            direct_holes = tuple(
                loop
                for loop in topology.loops
                if loop.parent_id == root.id
                and loop.depth == 1
            )

            inner_wires = [
                self._wire(
                    by_id[loop.id].points
                )
                for loop in direct_holes
            ]

            face = cq.Face.makeFromWires(
                outer_wire,
                inner_wires,
            )

            if not face.isValid():
                raise RuntimeError(
                    f"SVG root '{root.id}' produced invalid planar face."
                )

            faces.append(face)

            # depth-2 islands become independent additive faces
            islands = tuple(
                loop
                for loop in topology.loops
                if loop.depth == 2
                and self._root_id(loop, topology.loops) == root.id
            )

            for island in islands:
                island_face = cq.Face.makeFromWires(
                    self._wire(
                        by_id[island.id].points
                    )
                )

                if not island_face.isValid():
                    raise RuntimeError(
                        f"SVG island '{island.id}' is invalid."
                    )

                faces.append(island_face)

        if len(faces) == 1:
            return faces[0]

        compound = cq.Compound.makeCompound(faces)

        if not compound.isValid():
            raise RuntimeError(
                "SVG planar compound is invalid."
            )

        return compound

    @staticmethod
    def _wire(
        points,
    ) -> cq.Wire:
        vectors = tuple(
            cq.Vector(
                float(x),
                float(y),
                0.0,
            )
            for x, y in points
        )

        if len(vectors) < 3:
            raise ValueError(
                "Contour requires at least three points."
            )

        wire = cq.Wire.makePolygon(
            vectors,
            close=True,
        )

        if not wire.isValid():
            raise RuntimeError(
                "Planar SVG wire is invalid."
            )

        return wire

    @staticmethod
    def _root_id(
        loop,
        loops,
    ) -> str:
        by_id = {
            item.id: item
            for item in loops
        }

        current = loop

        while current.parent_id is not None:
            current = by_id[current.parent_id]

        return current.id
