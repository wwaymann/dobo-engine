from __future__ import annotations


Point2D = tuple[float, float]


def signed_area(
    points: tuple[Point2D, ...],
) -> float:
    if len(points) < 3:
        raise ValueError(
            "signed_area requires at least three points."
        )

    total = 0.0

    for index, point in enumerate(points):
        next_point = points[
            (index + 1) % len(points)
        ]

        total += (
            float(point[0])
            * float(next_point[1])
            - float(next_point[0])
            * float(point[1])
        )

    return total / 2.0


def is_counter_clockwise(
    points: tuple[Point2D, ...],
) -> bool:
    return signed_area(points) > 0.0


def normalized_counter_clockwise(
    points: tuple[Point2D, ...],
) -> tuple[Point2D, ...]:
    if is_counter_clockwise(points):
        return points

    return tuple(
        reversed(points)
    )
