from __future__ import annotations

import math

import cadquery as cq

from OCP.BRepTools import BRepTools_WireExplorer
from OCP.TopoDS import TopoDS

from product_generators.vector_geometry.contracts import (
    VectorContour,
    VectorDocument,
)


Point2D = tuple[float, float]


class TextOutlineExtractor:
    """
    Real OCC glyph outline extractor.

    BRepTools_WireExplorer is used for native topological wire order.
    """

    def __init__(
        self,
        *,
        sample_spacing: float = 0.75,
        minimum_edge_samples: int = 3,
        join_tolerance: float = 1e-6,
    ) -> None:
        self._sample_spacing = float(sample_spacing)
        self._minimum_edge_samples = int(minimum_edge_samples)
        self._join_tolerance_sq = float(join_tolerance) ** 2

    def extract(
        self,
        text: str,
        *,
        size: float,
        font: str = "Arial",
        kind: str = "regular",
        halign: str = "left",
        valign: str = "bottom",
        document_id: str = "surface_text",
    ) -> VectorDocument:
        if not text or not text.strip():
            raise ValueError("text cannot be empty.")

        shape = cq.Compound.makeText(
            text,
            float(size),
            1.0,
            font=font,
            kind=kind,
            halign=halign,
            valign=valign,
        )

        if not shape.isValid():
            raise RuntimeError(
                "CadQuery generated invalid text geometry."
            )

        contours = []
        counter = 0

        for face in self._bottom_faces(shape):
            for wire in (face.outerWire(), *face.innerWires()):
                points = self._wire_points(wire)

                if len(points) < 3:
                    continue

                contour = VectorContour(
                    id=f"{document_id}:contour:{counter}",
                    points=points,
                    closed=True,
                )
                contour.validate()
                contours.append(contour)
                counter += 1

        if not contours:
            raise RuntimeError(
                "Text outline extraction produced no contours."
            )

        document = VectorDocument(
            id=document_id,
            contours=tuple(contours),
            source="cadquery_text",
        )
        document.validate()
        return document

    @staticmethod
    def _bottom_faces(
        shape: cq.Shape,
        tolerance: float = 1e-6,
    ):
        z_min = float(shape.BoundingBox().zmin)

        return tuple(
            face
            for face in shape.Faces()
            if (
                abs(
                    float(face.BoundingBox().zmax)
                    - float(face.BoundingBox().zmin)
                )
                <= tolerance
                and abs(
                    float(face.BoundingBox().zmin)
                    - z_min
                )
                <= tolerance
            )
        )

    def _wire_points(
        self,
        wire: cq.Wire,
    ) -> tuple[Point2D, ...]:
        explorer = BRepTools_WireExplorer(
            wire.wrapped
        )

        edges: list[cq.Edge] = []

        while explorer.More():
            edge = cq.Edge(
                TopoDS.Edge_s(
                    explorer.Current()
                )
            )
            edges.append(edge)
            explorer.Next()

        points: list[Point2D] = []

        for edge in edges:
            sampled = list(
                self._sample_edge(edge)
            )

            if not sampled:
                continue

            if points:
                forward = self._distance_sq(
                    points[-1],
                    sampled[0],
                )
                reverse = self._distance_sq(
                    points[-1],
                    sampled[-1],
                )

                if reverse < forward:
                    sampled.reverse()

                if (
                    sampled
                    and self._distance_sq(
                        points[-1],
                        sampled[0],
                    )
                    <= self._join_tolerance_sq
                ):
                    sampled = sampled[1:]

            points.extend(sampled)

        cleaned: list[Point2D] = []

        for point in points:
            if (
                cleaned
                and self._distance_sq(
                    cleaned[-1],
                    point,
                )
                <= self._join_tolerance_sq
            ):
                continue
            cleaned.append(point)

        if (
            len(cleaned) >= 2
            and self._distance_sq(
                cleaned[0],
                cleaned[-1],
            )
            <= self._join_tolerance_sq
        ):
            cleaned.pop()

        return tuple(cleaned)

    def _sample_edge(
        self,
        edge: cq.Edge,
    ) -> tuple[Point2D, ...]:
        length = float(edge.Length())

        if length <= 1e-12:
            return ()

        count = max(
            self._minimum_edge_samples,
            int(
                math.ceil(
                    length
                    / self._sample_spacing
                )
            )
            + 1,
        )

        positions = edge.positions(
            tuple(
                length * index / (count - 1)
                for index in range(count)
            ),
            mode="length",
        )

        return tuple(
            (
                float(position.x),
                float(position.y),
            )
            for position in positions
        )

    @staticmethod
    def _distance_sq(
        a: Point2D,
        b: Point2D,
    ) -> float:
        return (
            (a[0] - b[0]) ** 2
            + (a[1] - b[1]) ** 2
        )
