from __future__ import annotations

Point2D = tuple[float, float]


def _signed_area(
    points: tuple[Point2D, ...],
) -> float:
    total = 0.0
    for i, p in enumerate(points):
        q = points[(i + 1) % len(points)]
        total += p[0] * q[1] - q[0] * p[1]
    return total / 2.0


def _cross(
    a: Point2D,
    b: Point2D,
    c: Point2D,
) -> float:
    return (
        (b[0] - a[0]) * (c[1] - a[1])
        - (b[1] - a[1]) * (c[0] - a[0])
    )


def _point_in_triangle(
    p: Point2D,
    a: Point2D,
    b: Point2D,
    c: Point2D,
) -> bool:
    c1 = _cross(a, b, p)
    c2 = _cross(b, c, p)
    c3 = _cross(c, a, p)

    has_negative = (
        c1 < -1e-10
        or c2 < -1e-10
        or c3 < -1e-10
    )
    has_positive = (
        c1 > 1e-10
        or c2 > 1e-10
        or c3 > 1e-10
    )

    return not (
        has_negative
        and has_positive
    )


def triangulate_simple_polygon(
    points: tuple[Point2D, ...],
) -> tuple[tuple[int, int, int], ...]:
    """
    Ear-clipping triangulation for a simple polygon.

    Phase 3.3 intentionally supports one closed outer loop.
    Hole subtraction is added in the following topology integration phase.
    """
    if len(points) < 3:
        raise ValueError(
            "Polygon requires at least three points."
        )

    indices = list(
        range(len(points))
    )

    if _signed_area(points) < 0.0:
        indices.reverse()

    triangles: list[
        tuple[int, int, int]
    ] = []

    guard = 0
    max_guard = len(points) * len(points) * 2

    while len(indices) > 3:
        ear_found = False

        for position in range(
            len(indices)
        ):
            i0 = indices[
                position - 1
            ]
            i1 = indices[
                position
            ]
            i2 = indices[
                (position + 1)
                % len(indices)
            ]

            a = points[i0]
            b = points[i1]
            c = points[i2]

            if _cross(
                a,
                b,
                c,
            ) <= 1e-10:
                continue

            contains_point = False

            for candidate in indices:
                if candidate in (
                    i0,
                    i1,
                    i2,
                ):
                    continue

                if _point_in_triangle(
                    points[candidate],
                    a,
                    b,
                    c,
                ):
                    contains_point = True
                    break

            if contains_point:
                continue

            triangles.append(
                (
                    i0,
                    i1,
                    i2,
                )
            )

            del indices[
                position
            ]

            ear_found = True
            break

        guard += 1

        if not ear_found:
            raise RuntimeError(
                "Could not triangulate polygon. "
                "The contour may be self-intersecting "
                "or degenerate."
            )

        if guard > max_guard:
            raise RuntimeError(
                "Triangulation exceeded safety limit."
            )

    triangles.append(
        (
            indices[0],
            indices[1],
            indices[2],
        )
    )

    return tuple(
        triangles
    )
