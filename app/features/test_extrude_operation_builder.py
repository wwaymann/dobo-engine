"""
DOBO Features

Extrude Operation Builder Test

Validates the translation:

ExtrudeFeatureDefinition
-> ExtrudeOperationBuilder
-> FeaturePlan
-> GeometryOperation
-> GeometryRequest
-> GeometryDefinitionSet
"""

from __future__ import annotations

from features.builders import (
    ExtrudeOperationBuilder,
)
from features.contracts import (
    BooleanMode,
    FeatureContext,
)
from features.definitions import (
    ExtrudeFeatureDefinition,
)

from kernel.contracts.geometry_operation_type import (
    GeometryOperationType,
)
from kernel.contracts.geometry_request import (
    GeometryRequest,
)
from kernel.contracts.model_state import (
    ModelState,
)
from kernel.contracts.operations import (
    GeometryOperation,
)
from kernel.providers.region_definition_provider import (
    RegionDefinitionProvider,
)

from testing.region_builders import (
    build_plate_with_hole,
)


def main() -> None:
    """
    Validates Feature-to-Kernel operation translation.
    """

    regions = build_plate_with_hole(
        region_set_id="regions_001",
        width=40.0,
        height=30.0,
        hole_radius=5.0,
        circle_samples=64,
    )

    regions.validate()

    if regions.count != 1:
        raise RuntimeError(
            "Expected one test Region."
        )

    region = regions.regions[0]

    if region.hole_count != 1:
        raise RuntimeError(
            "Expected one test hole."
        )

    context = FeatureContext(
        model=ModelState(),
    )

    context.register_regions(
        "regions_001",
        regions,
    )

    context.validate()

    feature = ExtrudeFeatureDefinition(
        id="feature_extrude_001",
        name="Base Extrusion",
        region_set_id="regions_001",
        region_id=region.id,
        output_id="body_001",
        distance=25.0,
        direction=(
            0.0,
            0.0,
            5.0,
        ),
        mode=BooleanMode.NEW_BODY,
        target_body_id=None,
        symmetric=False,
        draft_angle=0.0,
        merge=True,
        metadata={
            "test": True,
        },
    )

    feature.validate()

    builder = ExtrudeOperationBuilder(
        region_provider=(
            RegionDefinitionProvider()
        ),
    )

    plan = builder.build(
        feature,
        context,
    )

    plan.validate()

    if plan.feature is not feature:
        raise RuntimeError(
            "FeaturePlan does not reference "
            "the source Feature."
        )

    if plan.operation_count != 1:
        raise RuntimeError(
            "NEW_BODY extrusion must produce "
            "one Kernel operation."
        )

    if plan.final_output_id != "body_001":
        raise RuntimeError(
            "Unexpected final FeaturePlan output."
        )

    operation = plan.operations[0]

    if not isinstance(
        operation,
        GeometryOperation,
    ):
        raise RuntimeError(
            "Expected GeometryOperation."
        )

    operation.validate()

    if not operation.uses_request:
        raise RuntimeError(
            "GeometryOperation must use "
            "the GeometryRequest route."
        )

    if operation.uses_configuration:
        raise RuntimeError(
            "GeometryOperation must not use "
            "the legacy configuration route."
        )

    if (
        operation.resolved_output_id
        != feature.output_id
    ):
        raise RuntimeError(
            "GeometryOperation output does not "
            "match the Feature output."
        )

    request = operation.request

    if not isinstance(
        request,
        GeometryRequest,
    ):
        raise RuntimeError(
            "GeometryOperation must contain "
            "a GeometryRequest."
        )

    request.validate()

    if (
        request.operation
        is not GeometryOperationType.EXTRUDE
    ):
        raise RuntimeError(
            "Expected EXTRUDE GeometryRequest."
        )

    if request.output_id != feature.output_id:
        raise RuntimeError(
            "GeometryRequest output does not "
            "match the Feature output."
        )

    if (
        request.get_parameter(
            "distance"
        )
        != 25.0
    ):
        raise RuntimeError(
            "Unexpected extrusion distance."
        )

    if request.get_parameter(
        "direction"
    ) != (
        0.0,
        0.0,
        1.0,
    ):
        raise RuntimeError(
            "Builder did not normalize "
            "the extrusion direction."
        )

    if request.get_parameter(
        "symmetric"
    ):
        raise RuntimeError(
            "Expected non-symmetric extrusion."
        )

    if (
        request.get_parameter(
            "draft_angle"
        )
        != 0.0
    ):
        raise RuntimeError(
            "Unexpected draft angle."
        )

    geometry = request.geometry

    geometry.validate()

    if geometry.count != 1:
        raise RuntimeError(
            "Expected one GeometryDefinition."
        )

    definition = geometry.definitions[0]

    definition.validate()

    if definition.contour_count != 2:
        raise RuntimeError(
            "Expected one exterior contour "
            "and one inner contour."
        )

    if definition.hole_count != 1:
        raise RuntimeError(
            "Expected one GeometryDefinition hole."
        )

    if definition.point_count != 68:
        raise RuntimeError(
            "Expected 68 geometry points."
        )

    print()
    print(
        "DOBO Extrude Operation Builder"
    )
    print(
        "------------------------------"
    )
    print(
        "Feature:",
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
        "Kernel operations:",
        plan.operation_count,
    )
    print(
        "Operation route:",
        (
            "request"
            if operation.uses_request
            else "configuration"
        ),
    )
    print(
        "Geometry operation:",
        request.operation.value,
    )
    print(
        "Geometry definitions:",
        geometry.count,
    )
    print(
        "Contours:",
        definition.contour_count,
    )
    print(
        "Holes:",
        definition.hole_count,
    )
    print(
        "Points:",
        definition.point_count,
    )
    print(
        "Distance:",
        request.get_parameter(
            "distance"
        ),
    )
    print(
        "Direction:",
        request.get_parameter(
            "direction"
        ),
    )
    print(
        "Output:",
        request.output_id,
    )
    print(
        "Valid: OK"
    )
    print()


if __name__ == "__main__":
    main()