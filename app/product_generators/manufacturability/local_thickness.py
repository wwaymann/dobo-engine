from __future__ import annotations

from dataclasses import dataclass
import math

import cadquery as cq
from OCP.BRepIntCurveSurface import (
    BRepIntCurveSurface_Inter,
)
from OCP.gp import (
    gp_Dir,
    gp_Lin,
    gp_Pnt,
)


@dataclass(frozen=True, slots=True)
class ThicknessSample:
    face_index: int
    point: cq.Vector
    thickness: float


@dataclass(frozen=True, slots=True)
class LocalThicknessResult:
    minimum: float | None
    sample_count: int
    thin_sample_count: int
    samples: tuple[ThicknessSample, ...]


class LocalThicknessAnalyzer:
    """
    Sampled local-thickness estimator using the native OpenCascade
    curve/surface intersector.

    For a point sampled on a CAD face:
      1. get the face normal,
      2. step slightly inside the solid,
      3. create an infinite OCC line in the inward direction,
      4. intersect that line with the complete CAD shape,
      5. keep only forward intersections,
      6. discard numerical self-hits,
      7. use the nearest meaningful boundary crossing.

    This avoids boolean face/edge intersections, whose behavior varies
    between CadQuery/OCC versions.
    """

    def analyze(
        self,
        *,
        shape: cq.Shape,
        threshold: float,
        samples_per_axis: int = 3,
        inward_offset: float = 0.01,
        face_point_tolerance: float = 1.0e-4,
        intersection_tolerance: float = 1.0e-7,
    ) -> LocalThicknessResult:
        if threshold <= 0.0:
            raise ValueError(
                "Thickness threshold must be positive."
            )

        if samples_per_axis < 1:
            raise ValueError(
                "samples_per_axis must be >= 1."
            )

        if inward_offset <= 0.0:
            raise ValueError(
                "inward_offset must be positive."
            )

        collected: list[ThicknessSample] = []

        for face_index, face in enumerate(
            shape.Faces()
        ):
            try:
                (
                    u_min,
                    u_max,
                    v_min,
                    v_max,
                ) = face.uvBounds()
            except Exception:
                continue

            for u_index in range(
                samples_per_axis
            ):
                u = (
                    u_min
                    + (
                        u_max
                        - u_min
                    )
                    * (
                        u_index
                        + 0.5
                    )
                    / samples_per_axis
                )

                for v_index in range(
                    samples_per_axis
                ):
                    v = (
                        v_min
                        + (
                            v_max
                            - v_min
                        )
                        * (
                            v_index
                            + 0.5
                        )
                        / samples_per_axis
                    )

                    sample = self._sample_point(
                        shape=shape,
                        face=face,
                        face_index=face_index,
                        u=u,
                        v=v,
                        inward_offset=inward_offset,
                        face_point_tolerance=(
                            face_point_tolerance
                        ),
                        intersection_tolerance=(
                            intersection_tolerance
                        ),
                    )

                    if sample is not None:
                        collected.append(
                            sample
                        )

        if not collected:
            return LocalThicknessResult(
                minimum=None,
                sample_count=0,
                thin_sample_count=0,
                samples=(),
            )

        minimum = min(
            sample.thickness
            for sample in collected
        )

        thin_count = sum(
            1
            for sample in collected
            if sample.thickness
            < threshold
        )

        return LocalThicknessResult(
            minimum=minimum,
            sample_count=len(
                collected
            ),
            thin_sample_count=thin_count,
            samples=tuple(
                collected
            ),
        )

    @staticmethod
    def _sample_point(
        *,
        shape: cq.Shape,
        face: cq.Face,
        face_index: int,
        u: float,
        v: float,
        inward_offset: float,
        face_point_tolerance: float,
        intersection_tolerance: float,
    ) -> ThicknessSample | None:
        try:
            point = face.positionAt(
                u,
                v,
            )

            point_vertex = (
                cq.Vertex.makeVertex(
                    point.x,
                    point.y,
                    point.z,
                )
            )

            # UV bounds describe the underlying surface. Reject samples
            # outside the trimmed face.
            if (
                face.distance(
                    point_vertex
                )
                > face_point_tolerance
            ):
                return None

            normal = face.normalAt(
                point
            )

            normal_length = math.sqrt(
                normal.x * normal.x
                + normal.y * normal.y
                + normal.z * normal.z
            )

            if normal_length <= 1.0e-12:
                return None

            inward = cq.Vector(
                -normal.x / normal_length,
                -normal.y / normal_length,
                -normal.z / normal_length,
            )

            start = point.add(
                inward.multiply(
                    inward_offset
                )
            )

            line = gp_Lin(
                gp_Pnt(
                    start.x,
                    start.y,
                    start.z,
                ),
                gp_Dir(
                    inward.x,
                    inward.y,
                    inward.z,
                ),
            )

            intersector = (
                BRepIntCurveSurface_Inter()
            )

            intersector.Init(
                shape.wrapped,
                line,
                intersection_tolerance,
            )

            # The line origin is already inside the solid.
            # Ignore crossings very close to it because those are numerical
            # encounters with the sampled source boundary.
            self_hit_guard = max(
                inward_offset * 5.0,
                0.05,
            )

            forward_hits: list[float] = []

            while intersector.More():
                hit = intersector.Pnt()

                dx = (
                    hit.X()
                    - start.x
                )
                dy = (
                    hit.Y()
                    - start.y
                )
                dz = (
                    hit.Z()
                    - start.z
                )

                along = (
                    dx * inward.x
                    + dy * inward.y
                    + dz * inward.z
                )

                if along > self_hit_guard:
                    forward_hits.append(
                        along
                        + inward_offset
                    )

                intersector.Next()

            if not forward_hits:
                return None

            span = min(
                forward_hits
            )

            return ThicknessSample(
                face_index=face_index,
                point=point,
                thickness=span,
            )

        except Exception:
            # Sampling is intentionally tolerant per point; the caller can
            # detect a globally insufficient sample count.
            return None
