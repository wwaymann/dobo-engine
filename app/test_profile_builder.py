"""
DOBO Sketch

Profile Builder Test

Validates the complete flow:

Sketch
-> ProfileBuilder
-> ProfileSet
-> Profile metrics
"""

from __future__ import annotations

import math

from sketch.entities import (
    CircleEntity,
    PolylineEntity,
    SketchPoint,
)
from sketch.profiles import (
    ProfileBuilder,
)
from sketch.sketch import Sketch


def main() -> None:
    sketch = Sketch(
        name="DOBO Profile Builder Test",
        metadata={
            "test": True,
        },
    )

    sketch.add_entity(
        PolylineEntity(
            id="rectangle",
            points=(
                SketchPoint(
                    0.0,
                    0.0,
                ),
                SketchPoint(
                    20.0,
                    0.0,
                ),
                SketchPoint(
                    20.0,
                    10.0,
                ),
                SketchPoint(
                    0.0,
                    10.0,
                ),
            ),
            closed=True,
        )
    )

    sketch.add_entity(
        CircleEntity(
            id="circle",
            center=SketchPoint(
                30.0,
                5.0,
            ),
            radius=5.0,
        )
    )

    sketch.validate()

    profiles = ProfileBuilder().build(
        sketch,
        circle_samples=64,
    )

    profiles.validate()

    rectangle = profiles.profiles[0]
    circle = profiles.profiles[1]

    expected_rectangle_area = 200.0

    expected_rectangle_perimeter = 60.0

    expected_circle_area = (
        math.pi
        * 5.0
        * 5.0
    )

    expected_circle_perimeter = (
        2.0
        * math.pi
        * 5.0
    )

    if not math.isclose(
        rectangle.area,
        expected_rectangle_area,
        rel_tol=1e-9,
        abs_tol=1e-9,
    ):
        raise RuntimeError(
            "Rectangle area is incorrect."
        )

    if not math.isclose(
        rectangle.perimeter,
        expected_rectangle_perimeter,
        rel_tol=1e-9,
        abs_tol=1e-9,
    ):
        raise RuntimeError(
            "Rectangle perimeter is incorrect."
        )

    if not math.isclose(
        circle.area,
        expected_circle_area,
        rel_tol=0.01,
        abs_tol=0.01,
    ):
        raise RuntimeError(
            "Circle sampled area is incorrect."
        )

    if not math.isclose(
        circle.perimeter,
        expected_circle_perimeter,
        rel_tol=0.01,
        abs_tol=0.01,
    ):
        raise RuntimeError(
            "Circle sampled perimeter is incorrect."
        )

    if rectangle.centroid != (
        10.0,
        5.0,
    ):
        raise RuntimeError(
            "Rectangle centroid is incorrect."
        )

    circle_centroid = circle.centroid

    if not math.isclose(
        circle_centroid[0],
        30.0,
        abs_tol=1e-9,
    ):
        raise RuntimeError(
            "Circle centroid X is incorrect."
        )

    if not math.isclose(
        circle_centroid[1],
        5.0,
        abs_tol=1e-9,
    ):
        raise RuntimeError(
            "Circle centroid Y is incorrect."
        )

    if not rectangle.contains_point(
        SketchPoint(
            10.0,
            5.0,
        )
    ):
        raise RuntimeError(
            "Rectangle should contain "
            "its center point."
        )

    if rectangle.contains_point(
        SketchPoint(
            25.0,
            5.0,
        )
    ):
        raise RuntimeError(
            "Rectangle should not contain "
            "an external point."
        )

    if not circle.contains_point(
        SketchPoint(
            30.0,
            5.0,
        )
    ):
        raise RuntimeError(
            "Circle should contain "
            "its center point."
        )

    if profiles.count != 2:
        raise RuntimeError(
            "ProfileBuilder returned "
            "an unexpected profile count."
        )

    if profiles.point_count != 68:
        raise RuntimeError(
            "ProfileBuilder returned "
            "an unexpected point count."
        )

    print()
    print("DOBO Profile Builder")
    print("--------------------")
    print(
        "Sketch entities:",
        sketch.count,
    )
    print(
        "Profiles:",
        profiles.count,
    )
    print(
        "Points:",
        profiles.point_count,
    )
    print(
        "Rectangle area:",
        rectangle.area,
    )
    print(
        "Rectangle perimeter:",
        rectangle.perimeter,
    )
    print(
        "Rectangle centroid:",
        rectangle.centroid,
    )
    print(
        "Rectangle bounds:",
        rectangle.bounds,
    )
    print(
        "Circle area:",
        circle.area,
    )
    print(
        "Circle perimeter:",
        circle.perimeter,
    )
    print(
        "Circle centroid:",
        circle.centroid,
    )
    print(
        "Circle bounds:",
        circle.bounds,
    )
    print(
        "ProfileSet bounds:",
        profiles.bounds,
    )
    print(
        "Total area:",
        profiles.total_area,
    )
    print(
        "Largest profile area:",
        profiles.largest_profile.area,
    )
    print("Valid: OK")
    print()


if __name__ == "__main__":
    main()