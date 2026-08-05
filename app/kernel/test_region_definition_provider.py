"""
DOBO CAD Kernel

Region Definition Provider Test
"""

from __future__ import annotations

from kernel.providers.region_definition_provider import (
    RegionDefinitionProvider,
)
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
        name="Region Definition Provider Test",
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

    definitions = (
        RegionDefinitionProvider().execute(
            regions
        )
    )

    definitions.validate()

    definition = definitions.definitions[0]

    if definitions.count != 1:
        raise RuntimeError(
            "Expected one GeometryDefinition."
        )

    if definition.hole_count != 1:
        raise RuntimeError(
            "Expected one inner contour."
        )

    if definition.point_count != 68:
        raise RuntimeError(
            "Unexpected GeometryDefinition point count."
        )

    print()
    print("DOBO Region Definition Provider")
    print("-------------------------------")
    print(
        "Regions:",
        regions.count,
    )
    print(
        "Definitions:",
        definitions.count,
    )
    print(
        "Contours:",
        definitions.contour_count,
    )
    print(
        "Holes:",
        definitions.hole_count,
    )
    print(
        "Points:",
        definitions.point_count,
    )
    print(
        "Bounds:",
        definitions.bounds,
    )
    print(
        "Outer clockwise:",
        definition.outer_contour.metadata[
            "clockwise"
        ],
    )
    print(
        "Inner clockwise:",
        definition.inner_contours[0].metadata[
            "clockwise"
        ],
    )
    print("Valid: OK")
    print()


if __name__ == "__main__":
    main()
