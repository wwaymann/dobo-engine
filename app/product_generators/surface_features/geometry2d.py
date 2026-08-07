from __future__ import annotations


Point2D = tuple[float, float]


def bounding_box(
    points: tuple[Point2D, ...],
) -> tuple[
    tuple[float, float],
    tuple[float, float],
]:
    xs = [
        float(point[0])
        for point in points
    ]

    ys = [
        float(point[1])
        for point in points
    ]

    return (
        (
            min(xs),
            min(ys),
        ),
        (
            max(xs),
            max(ys),
        ),
    )


def box_contains_box(
    outer: tuple[
        tuple[float, float],
        tuple[float, float],
    ],
    inner: tuple[
        tuple[float, float],
        tuple[float, float],
    ],
    *,
    tolerance: float = 1e-9,
) -> bool:
    return (
        inner[0][0]
        >= outer[0][0] - tolerance
        and inner[0][1]
        >= outer[0][1] - tolerance
        and inner[1][0]
        <= outer[1][0] + tolerance
        and inner[1][1]
        <= outer[1][1] + tolerance
    )


def point_in_polygon(
    point: Point2D,
    polygon: tuple[Point2D, ...],
) -> bool:
    """
    Even-odd ray-casting test.
    """

    x = float(point[0])
    y = float(point[1])

    inside = False

    count = len(
        polygon
    )

    j = count - 1

    for i in range(count):
        xi = float(
            polygon[i][0]
        )

        yi = float(
            polygon[i][1]
        )

        xj = float(
            polygon[j][0]
        )

        yj = float(
            polygon[j][1]
        )

        intersects = (
            (yi > y)
            != (yj > y)
        )

        if intersects:
            denominator = (
                yj - yi
            )

            if abs(
                denominator
            ) < 1e-15:
                j = i
                continue

            crossing_x = (
                (xj - xi)
                * (y - yi)
                / denominator
                + xi
            )

            if x < crossing_x:
                inside = not inside

        j = i

    return inside


def representative_point(
    points: tuple[Point2D, ...],
) -> Point2D:
    """
    Returns a practical representative point.

    The first vertex is intentionally not used because
    nested contours may share alignment with parent edges.
    """

    if len(points) < 3:
        raise ValueError(
            "representative_point requires "
            "at least three points."
        )

    x = sum(
        float(point[0])
        for point in points
    ) / len(points)

    y = sum(
        float(point[1])
        for point in points
    ) / len(points)

    centroid = (
        x,
        y,
    )

    if point_in_polygon(
        centroid,
        points,
    ):
        return centroid

    first = points[0]
    second = points[1]

    return (
        (
            float(first[0])
            + float(second[0])
        )
        / 2.0,
        (
            float(first[1])
            + float(second[1])
        )
        / 2.0,
    )
