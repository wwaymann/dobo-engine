"""
DOBO Sketch

Backend-independent 2D sketch system.

Provides:

- Sketch
- Sketch entities
- Profile Builder
"""

from .entities import (
    CircleEntity,
    LineEntity,
    Point2D,
    PolylineEntity,
    SketchEntity,
    SketchEntityType,
    SketchEntityValue,
    SketchPoint,
)

from .profiles import (
    Profile,
    ProfileBuilder,
    ProfileSet,
)

from .services import (
    SketchContourBuilder,
)

from .sketch import (
    Bounds2D,
    Sketch,
)

from .topology import (
    Region,
    RegionBuilder,
    RegionSet,
)

__all__ = [
    # basic geometry
    "Point2D",
    "Bounds2D",
    "SketchPoint",
    # entities
    "SketchEntityType",
    "SketchEntity",
    "SketchEntityValue",
    "LineEntity",
    "CircleEntity",
    "PolylineEntity",
    # sketch
    "Sketch",
    # profile system
    "Profile",
    "ProfileSet",
    "ProfileBuilder",
    # kernel bridge
    "SketchContourBuilder",
    "Region",
    "RegionBuilder",
    "RegionSet",
]
