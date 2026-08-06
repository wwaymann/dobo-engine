"""
DOBO Test Support

Reusable test-data and infrastructure factories.
"""

from .kernel_builders import (
    build_dispatcher,
    build_geometry_pipeline,
    build_geometry_service,
    build_kernel_engine,
    build_provider_registry,
    build_request_registry,
)
from .region_builders import (
    build_plate_with_hole,
    build_rectangle_region_set,
    build_two_rectangle_regions,
)


__all__ = [
    "build_provider_registry",
    "build_geometry_pipeline",
    "build_request_registry",
    "build_geometry_service",
    "build_dispatcher",
    "build_kernel_engine",
    "build_rectangle_region_set",
    "build_plate_with_hole",
    "build_two_rectangle_regions",
]