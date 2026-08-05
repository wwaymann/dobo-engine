"""
DOBO Sketch

Region Builder Test
"""

from __future__ import annotations

import math

from sketch.entities import (
    CircleEntity,
    PolylineEntity,
    SketchPoint,
)
from sketch.profiles import ProfileBuilder
from sketch.sketch import Sketch
from sketch.topology import RegionBuilder


def main() -> None:
    sketch = Sketch(
        name="Region Builder Test",
    )

    sketch.add_entity(
        PolylineEntity(
            id="outer_rectangle",
            points=(
                SketchPoint(
                    0.0,
                    0.0,
                ),
                SketchPoint(
                    40.0,
                    0.0,
                ),
                SketchPoint(
                    40.0,
                    30.0,
                ),
                SketchPoint(
                    0.0,
                    30.0,
                ),
            ),
            closed=True,
        )
    )

    sketch.add_entity(
        CircleEntity(
            id="inner_hole",
            center=SketchPoint(
                20.0,
                15.0,
            ),
            radius=5.0,
        )
    )

    profiles = ProfileBuilder().build(
        sketch,
        circle_samples=64,
    )

    regions = RegionBuilder().build(
        profiles
    )

    regions.validate()

    if regions.count != 1:
        raise RuntimeError(
            "Expected one Region."
        )

    region = regions.regions[0]

    if region.hole_count != 1:
        raise RuntimeError(
            "Expected one hole."
        )

    expected_area = (
        40.0
        * 30.0
        - math.pi
        * 5.0
        * 5.0
    )

    if not math.isclose(
        region.area,
        expected_area,
        rel_tol=0.01,
        abs_tol=0.01,
    ):
        raise RuntimeError(
            "Region area is incorrect."
        )

    if not region.contains_point(
        SketchPoint(
            5.0,
            5.0,
        )
    ):
        raise RuntimeError(
            "Region should contain material point."
        )

    if region.contains_point(
        SketchPoint(
            20.0,
            15.0,
        )
    ):
        raise RuntimeError(
            "Region must not contain hole center."
        )

    print()
    print("DOBO Region Builder")
    print("-------------------")
    print(
        "Profiles:",
        profiles.count,
    )
    print(
        "Regions:",
        regions.count,
    )
    print(
        "Holes:",
        regions.hole_count,
    )
    print(
        "Region profiles:",
        region.profile_count,
    )
    print(
        "Region area:",
        region.area,
    )
    print(
        "Region perimeter:",
        region.perimeter,
    )
    print(
        "Bounds:",
        region.bounds,
    )
    print(
        "Outer clockwise:",
        region.outer_profile.clockwise,
    )
    print(
        "Hole clockwise:",
        region.inner_profiles[0].clockwise,
    )
    print("Valid: OK")
    print()


if __name__ == "__main__":
    main()
