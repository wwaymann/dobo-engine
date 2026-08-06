"""
DOBO Test Support

Region Builders

Reusable factories for validated Sketch RegionSet
objects used by Kernel and Features tests.
"""

from __future__ import annotations

from sketch.entities import (
    CircleEntity,
    PolylineEntity,
    SketchPoint,
)
from sketch.profiles import (
    ProfileBuilder,
)
from sketch.sketch import (
    Sketch,
)
from sketch.topology import (
    RegionBuilder,
    RegionSet,
)


def build_rectangle_region_set(
    *,
    region_set_id: str = "rectangle_regions",
    width: float = 40.0,
    height: float = 30.0,
) -> RegionSet:
    """
    Builds one rectangular Region without holes.
    """

    if width <= 0.0:
        raise ValueError(
            "Rectangle width must be greater than zero."
        )

    if height <= 0.0:
        raise ValueError(
            "Rectangle height must be greater than zero."
        )

    sketch = Sketch(
        name="Rectangle Region Test Fixture",
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
                    width,
                    0.0,
                ),
                SketchPoint(
                    width,
                    height,
                ),
                SketchPoint(
                    0.0,
                    height,
                ),
            ),
            closed=True,
        )
    )

    profiles = ProfileBuilder().build(
        sketch
    )

    regions = RegionBuilder().build(
        profiles
    )

    result = RegionSet(
        id=region_set_id,
        regions=regions.regions,
        source_profile_set_id=(
            regions.source_profile_set_id
        ),
        metadata={
            "fixture": "rectangle",
            "width": width,
            "height": height,
            **regions.metadata,
        },
    )

    result.validate()

    return result


def build_plate_with_hole(
    *,
    region_set_id: str = "plate_regions",
    width: float = 40.0,
    height: float = 30.0,
    hole_radius: float = 5.0,
    hole_center: tuple[
        float,
        float,
    ] | None = None,
    circle_samples: int = 64,
) -> RegionSet:
    """
    Builds one rectangular Region with one circular hole.
    """

    if width <= 0.0:
        raise ValueError(
            "Plate width must be greater than zero."
        )

    if height <= 0.0:
        raise ValueError(
            "Plate height must be greater than zero."
        )

    if hole_radius <= 0.0:
        raise ValueError(
            "Hole radius must be greater than zero."
        )

    if circle_samples < 8:
        raise ValueError(
            "circle_samples must be at least 8."
        )

    center = (
        hole_center
        if hole_center is not None
        else (
            width / 2.0,
            height / 2.0,
        )
    )

    center_x = float(
        center[0]
    )

    center_y = float(
        center[1]
    )

    if (
        center_x - hole_radius <= 0.0
        or center_x + hole_radius >= width
        or center_y - hole_radius <= 0.0
        or center_y + hole_radius >= height
    ):
        raise ValueError(
            "Hole must remain completely inside "
            "the rectangular plate."
        )

    sketch = Sketch(
        name="Plate With Hole Test Fixture",
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
                    width,
                    0.0,
                ),
                SketchPoint(
                    width,
                    height,
                ),
                SketchPoint(
                    0.0,
                    height,
                ),
            ),
            closed=True,
        )
    )

    sketch.add_entity(
        CircleEntity(
            id="inner_hole",
            center=SketchPoint(
                center_x,
                center_y,
            ),
            radius=hole_radius,
        )
    )

    profiles = ProfileBuilder().build(
        sketch,
        circle_samples=circle_samples,
    )

    regions = RegionBuilder().build(
        profiles
    )

    result = RegionSet(
        id=region_set_id,
        regions=regions.regions,
        source_profile_set_id=(
            regions.source_profile_set_id
        ),
        metadata={
            "fixture": "plate_with_hole",
            "width": width,
            "height": height,
            "hole_radius": hole_radius,
            "hole_center": (
                center_x,
                center_y,
            ),
            "circle_samples": circle_samples,
            **regions.metadata,
        },
    )

    result.validate()

    return result


def build_two_rectangle_regions(
    *,
    region_set_id: str = "two_rectangle_regions",
    width: float = 20.0,
    height: float = 10.0,
    gap: float = 10.0,
) -> RegionSet:
    """
    Builds two independent rectangular Regions.
    """

    if width <= 0.0:
        raise ValueError(
            "Rectangle width must be greater than zero."
        )

    if height <= 0.0:
        raise ValueError(
            "Rectangle height must be greater than zero."
        )

    if gap <= 0.0:
        raise ValueError(
            "Rectangle gap must be greater than zero."
        )

    second_start_x = (
        width
        + gap
    )

    sketch = Sketch(
        name="Two Rectangle Regions Test Fixture",
    )

    sketch.add_entity(
        PolylineEntity(
            id="left_rectangle",
            points=(
                SketchPoint(
                    0.0,
                    0.0,
                ),
                SketchPoint(
                    width,
                    0.0,
                ),
                SketchPoint(
                    width,
                    height,
                ),
                SketchPoint(
                    0.0,
                    height,
                ),
            ),
            closed=True,
        )
    )

    sketch.add_entity(
        PolylineEntity(
            id="right_rectangle",
            points=(
                SketchPoint(
                    second_start_x,
                    0.0,
                ),
                SketchPoint(
                    second_start_x + width,
                    0.0,
                ),
                SketchPoint(
                    second_start_x + width,
                    height,
                ),
                SketchPoint(
                    second_start_x,
                    height,
                ),
            ),
            closed=True,
        )
    )

    profiles = ProfileBuilder().build(
        sketch
    )

    regions = RegionBuilder().build(
        profiles
    )

    result = RegionSet(
        id=region_set_id,
        regions=regions.regions,
        source_profile_set_id=(
            regions.source_profile_set_id
        ),
        metadata={
            "fixture": "two_rectangles",
            "width": width,
            "height": height,
            "gap": gap,
            **regions.metadata,
        },
    )

    result.validate()

    return result