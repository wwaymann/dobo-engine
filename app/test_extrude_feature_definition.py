"""
DOBO Features

Extrude Feature Definition Test
"""

from __future__ import annotations

from features.contracts import (
    BooleanMode,
)
from features.definitions import (
    ExtrudeFeatureDefinition,
)


def main() -> None:

    feature = ExtrudeFeatureDefinition(
        name="Base Extrusion",
        region_set_id="regions_001",
        region_id="profile_001",
        output_id="body_001",
        distance=25.0,
        direction=(
            0.0,
            0.0,
            5.0,
        ),
        mode=BooleanMode.NEW_BODY,
        symmetric=False,
        draft_angle=2.0,
    )

    feature.validate()

    print()
    print(
        "DOBO Extrude Feature Definition"
    )
    print(
        "--------------------------------"
    )

    print(
        "Name:",
        feature.name,
    )

    print(
        "Feature type:",
        feature.feature_type,
    )

    print(
        "Region Set:",
        feature.region_set_id,
    )

    print(
        "Region:",
        feature.region_id,
    )

    print(
        "Output:",
        feature.output_id,
    )

    print(
        "Distance:",
        feature.distance,
    )

    print(
        "Direction:",
        feature.direction,
    )

    print(
        "Normalized:",
        feature.normalized_direction,
    )

    print(
        "Mode:",
        feature.mode.value,
    )

    print(
        "Requires Target:",
        feature.mode.requires_target_body,
    )

    print(
        "Creates Body:",
        feature.mode.creates_new_body,
    )

    print(
        "Boolean:",
        feature.mode.performs_boolean,
    )

    print(
        "Start:",
        feature.signed_start_distance,
    )

    print(
        "End:",
        feature.signed_end_distance,
    )

    print(
        "Merge:",
        feature.merge,
    )

    print(
        "Draft:",
        feature.draft_angle,
    )

    print(
        "Valid: OK",
    )

    print()


if __name__ == "__main__":
    main()