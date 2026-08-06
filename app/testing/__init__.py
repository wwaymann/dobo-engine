"""
DOBO Test Support

Reusable test-data factories.
"""

from .region_builders import (
    build_plate_with_hole,
    build_rectangle_region_set,
    build_two_rectangle_regions,
)


__all__ = [
    "build_rectangle_region_set",
    "build_plate_with_hole",
    "build_two_rectangle_regions",
]