from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast
import math

import cadquery as cq


@dataclass(frozen=True, slots=True)
class StabilityResult:
    stable: bool
    support_area: float
    center_x: float
    center_y: float
    margin: float | None
    support_point_count: int


def _convex_hull(
    points: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    unique = sorted(set(points))

    if len(unique) <= 1:
        return unique

    def cross(
        o: tuple[float, float],
        a: tuple[float, float],
        b: tuple[float, float],
    ) -> float:
        return (
            (a[0] - o[0]) * (b[1] - o[1])
            - (a[1] - o[1]) * (b[0] - o[0])
        )

    lower: list[tuple[float, float]] = []

    for point in unique:
        while (
            len(lower) >= 2
            and cross(
                lower[-2],
                lower[-1],
                point,
            ) <= 0.0
        ):
            lower.pop()

        lower.append(point)

    upper: list[tuple[float, float]] = []

    for point in reversed(unique):
        while (
            len(upper) >= 2
            and cross(
                upper[-2],
                upper[-1],
                point,
            ) <= 0.0
        ):
            upper.pop()

        upper.append(point)

    return lower[:-1] + upper[:-1]


def _polygon_area(
    polygon: list[tuple[float, float]],
) -> float:
    if len(polygon) < 3:
        return 0.0

    total = 0.0

    for index in range(len(polygon)):
        x1, y1 = polygon[index]
        x2, y2 = polygon[
            (index + 1) % len(polygon)
        ]

        total += (
            x1 * y2
            - x2 * y1
        )

    return abs(total) * 0.5


def _point_in_polygon(
    point: tuple[float, float],
    polygon: list[tuple[float, float]],
) -> bool:
    x, y = point
    inside = False

    if len(polygon) < 3:
        return False

    j = len(polygon) - 1

    for i in range(len(polygon)):
        xi, yi = polygon[i]
        xj, yj = polygon[j]

        denominator = (
            yj - yi
        )

        if abs(denominator) < 1.0e-18:
            denominator = 1.0e-18

        intersects = (
            (yi > y) != (yj > y)
            and x
            < (
                (xj - xi)
                * (y - yi)
                / denominator
                + xi
            )
        )

        if intersects:
            inside = not inside

        j = i

    return inside


def _distance_to_segment(
    point: tuple[float, float],
    a: tuple[float, float],
    b: tuple[float, float],
) -> float:
    px, py = point
    ax, ay = a
    bx, by = b

    dx = bx - ax
    dy = by - ay

    length_squared = (
        dx * dx
        + dy * dy
    )

    if length_squared <= 1.0e-18:
        return math.hypot(
            px - ax,
            py - ay,
        )

    t = (
        (px - ax) * dx
        + (py - ay) * dy
    ) / length_squared

    t = max(
        0.0,
        min(
            1.0,
            t,
        ),
    )

    closest_x = ax + t * dx
    closest_y = ay + t * dy

    return math.hypot(
        px - closest_x,
        py - closest_y,
    )


def _section_edges(
    shape: cq.Shape,
    z_probe: float,
) -> tuple[cq.Edge, ...]:
    """
    Return only actual Edge objects from the CadQuery selector.

    Workplane.vals() is typed as a generic CQObject collection, so explicit
    isinstance narrowing avoids false Pylance errors for Edge.positionAt().
    """

    section = (
        cq.Workplane("XY")
        .workplane(
            offset=z_probe
        )
        .add(shape)
        .section()
    )

    raw_objects = section.edges().vals()

    edges: list[cq.Edge] = []

    for obj in raw_objects:
        if isinstance(obj, cq.Edge):
            edges.append(obj)

    return tuple(edges)


class BaseStabilityAnalyzer:
    """
    Stability from a horizontal footprint section near the print bed.

    A tiny positive Z probe is used instead of inspecting bottom-face centers
    or vertices. Organic and filleted bases may have no useful discrete
    vertices exactly at z_min.

    The probe section provides the actual solid footprint that exists just
    above the first printed layer.
    """

    def analyze(
        self,
        *,
        shape: cq.Shape,
        probe_height: float = 0.10,
        samples_per_edge: int = 12,
    ) -> StabilityResult:
        if probe_height <= 0.0:
            raise ValueError(
                "probe_height must be positive."
            )

        if samples_per_edge < 2:
            raise ValueError(
                "samples_per_edge must be >= 2."
            )

        box = shape.BoundingBox()

        z_probe = min(
            float(box.zmin)
            + probe_height,
            float(box.zmax)
            - 1.0e-6,
        )

        section_edges = _section_edges(
            shape,
            z_probe,
        )

        points: list[
            tuple[float, float]
        ] = []

        for edge in section_edges:
            for index in range(
                samples_per_edge
            ):
                parameter = (
                    index
                    / samples_per_edge
                )

                try:
                    point = cast(
                       Any,
                       edge,
                    ).positionAt(
                     parameter
)
                except Exception:
                    continue

                points.append(
                    (
                        float(point.x),
                        float(point.y),
                    )
                )

        hull = _convex_hull(
            points
        )

        support_area = _polygon_area(
            hull
        )

        # In the installed CadQuery version centerOfMass is a static method.
        center = cq.Shape.centerOfMass(
            shape
        )

        projected = (
            float(center.x),
            float(center.y),
        )

        if len(hull) < 3:
            return StabilityResult(
                stable=False,
                support_area=support_area,
                center_x=projected[0],
                center_y=projected[1],
                margin=None,
                support_point_count=len(
                    points
                ),
            )

        inside = _point_in_polygon(
            projected,
            hull,
        )

        distances = [
            _distance_to_segment(
                projected,
                hull[index],
                hull[
                    (index + 1)
                    % len(hull)
                ],
            )
            for index in range(
                len(hull)
            )
        ]

        margin = (
            min(distances)
            if distances
            else None
        )

        return StabilityResult(
            stable=inside,
            support_area=support_area,
            center_x=projected[0],
            center_y=projected[1],
            margin=margin,
            support_point_count=len(
                points
            ),
        )
