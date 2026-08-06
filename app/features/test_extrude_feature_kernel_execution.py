"""
DOBO Features

Extrude Feature Kernel Execution Test

Validates the complete flow:

ExtrudeFeatureDefinition
-> ExtrudeOperationBuilder
-> FeaturePlan
-> KernelExecutionEngine
-> GeometryOperationExecutor
-> GeometryExecutionService
-> ExtrudeRequestExecutor
-> Solid
"""

from __future__ import annotations

import math

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

from kernel.contracts.model_state import (
    ModelState,
)
from kernel.core.geometry_operation_executor import (
    GeometryOperationExecutor,
)
from kernel.core.kernel_execution_engine import (
    KernelExecutionEngine,
)
from kernel.core.kernel_model import (
    KernelModel,
)
from kernel.core.operation_dispatcher import (
    OperationDispatcher,
)
from kernel.geometry import (
    ExtrudeRequestExecutor,
    GeometryRequestExecutorRegistry,
)
from kernel.pipeline.geometry_pipeline import (
    GeometryPipeline,
)
from kernel.providers.circle_definition_provider import (
    CircleDefinitionProvider,
)
from kernel.providers.definition_registry import (
    DefinitionProviderRegistry,
)
from kernel.providers.region_definition_provider import (
    RegionDefinitionProvider,
)
from kernel.services.geometry_execution_service import (
    GeometryExecutionService,
)
from kernel.services.geometry_projection_engine import (
    GeometryProjectionEngine,
)
from kernel.services.offset_engine import (
    OffsetEngine,
)
from kernel.services.offset_solid_builder import (
    OffsetSolidBuilder,
)

from testing.region_builders import (
    build_plate_with_hole,
)


def build_legacy_pipeline() -> GeometryPipeline:
    """
    Builds the legacy pipeline required during
    the controlled Kernel migration.

    This test executes the GeometryRequest route,
    but GeometryExecutionService currently supports
    both routes.
    """

    provider_registry = (
        DefinitionProviderRegistry()
    )

    provider_registry.register_provider(
        CircleDefinitionProvider()
    )

    return GeometryPipeline(
        provider_registry=provider_registry,
        projection_engine=(
            GeometryProjectionEngine()
        ),
        offset_engine=OffsetEngine(),
        solid_builder=OffsetSolidBuilder(),
    )


def build_request_registry(
) -> GeometryRequestExecutorRegistry:
    """
    Builds the GeometryRequest executor registry.
    """

    registry = (
        GeometryRequestExecutorRegistry()
    )

    registry.register(
        ExtrudeRequestExecutor()
    )

    registry.validate()

    return registry


def build_kernel_engine(
) -> KernelExecutionEngine:
    """
    Builds the Kernel engine for GeometryRequest
    execution.
    """

    geometry_service = (
        GeometryExecutionService(
            pipeline=build_legacy_pipeline(),
            request_registry=(
                build_request_registry()
            ),
        )
    )

    dispatcher = OperationDispatcher()

    dispatcher.register(
        GeometryOperationExecutor(
            geometry_service=geometry_service,
        )
    )

    dispatcher.validate()

    return KernelExecutionEngine(
        dispatcher=dispatcher,
        stop_on_error=True,
    )


def main() -> None:
    """
    Executes one Extrude Feature end to end.
    """

    width = 40.0
    height = 30.0
    hole_radius = 5.0
    distance = 25.0
    circle_samples = 64

    regions = build_plate_with_hole(
        region_set_id="regions_001",
        width=width,
        height=height,
        hole_radius=hole_radius,
        circle_samples=circle_samples,
    )

    regions.validate()

    region = regions.regions[0]

    context = FeatureContext(
        model=ModelState(),
    )

    context.register_regions(
        "regions_001",
        regions,
    )

    context.validate()

    feature = ExtrudeFeatureDefinition(
        id="feature_extrude_e2e_001",
        name="Plate Extrusion",
        region_set_id="regions_001",
        region_id=region.id,
        output_id="body_001",
        distance=distance,
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
            "test_type": "end_to_end",
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

    model = KernelModel(
        name="DOBO Extrude Feature Model",
        metadata={
            "feature_id": feature.id,
            "feature_type": feature.feature_type,
            "test": True,
        },
    )

    for operation in plan.operations:
        model.add_operation(
            operation
        )

    model.validate()

    engine = build_kernel_engine()

    result = engine.execute(
        model,
        metadata={
            "feature_plan_id": plan.id,
            "feature_id": feature.id,
        },
    )

    result.validate()

    if not result.succeeded:
        failures = tuple(
            operation.error_message
            for operation in result.operations
            if operation.failed
        )

        raise RuntimeError(
            "Extrude Feature execution failed: "
            f"{failures}"
        )

    if result.operation_count != 1:
        raise RuntimeError(
            "NEW_BODY Extrude must execute "
            "one Kernel operation."
        )

    if result.completed_count != 1:
        raise RuntimeError(
            "Kernel did not complete the "
            "Extrude operation."
        )

    if result.failed_count != 0:
        raise RuntimeError(
            "Extrude execution contains failures."
        )

    if result.skipped_count != 0:
        raise RuntimeError(
            "Extrude execution contains skipped "
            "operations."
        )

    if result.final_solid is None:
        raise RuntimeError(
            "Extrude Feature produced no final Solid."
        )

    if feature.output_id not in result.solids:
        raise RuntimeError(
            "Expected Feature output was not "
            "registered in Kernel results."
        )

    solid = result.solids[
        feature.output_id
    ]

    solid.validate()

    polygonal_hole_area = (
        circle_samples
        * hole_radius
        * hole_radius
        * math.sin(
            2.0
            * math.pi
            / circle_samples
        )
        / 2.0
    )

    expected_volume = (
        (
            width
            * height
            - polygonal_hole_area
        )
        * distance
    )

    if solid.volume is None:
        raise RuntimeError(
            "Generated Solid has no volume."
        )

    if not math.isclose(
        solid.volume,
        expected_volume,
        rel_tol=1e-6,
        abs_tol=1e-6,
    ):
        raise RuntimeError(
            "Unexpected Feature Solid volume: "
            f"{solid.volume}; "
            f"expected {expected_volume}."
        )

    if solid.bounding_box is None:
        raise RuntimeError(
            "Generated Solid has no bounding box."
        )

    expected_minimum = (
        0.0,
        0.0,
        0.0,
    )

    expected_maximum = (
        width,
        height,
        distance,
    )

    for actual, expected in zip(
        solid.bounding_box.minimum,
        expected_minimum,
    ):
        if not math.isclose(
            actual,
            expected,
            abs_tol=1e-7,
        ):
            raise RuntimeError(
                "Unexpected minimum bounding box: "
                f"{solid.bounding_box.minimum}."
            )

    for actual, expected in zip(
        solid.bounding_box.maximum,
        expected_maximum,
    ):
        if not math.isclose(
            actual,
            expected,
            abs_tol=1e-7,
        ):
            raise RuntimeError(
                "Unexpected maximum bounding box: "
                f"{solid.bounding_box.maximum}."
            )

    print()
    print(
        "DOBO Extrude Feature Kernel Execution"
    )
    print(
        "-------------------------------------"
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
        "Feature plan:",
        plan.id,
    )
    print(
        "Kernel operations:",
        result.operation_count,
    )
    print(
        "Completed:",
        result.completed_count,
    )
    print(
        "Failed:",
        result.failed_count,
    )
    print(
        "Succeeded:",
        result.succeeded,
    )
    print(
        "Solid IDs:",
        tuple(
            result.solids.keys()
        ),
    )
    print(
        "Output:",
        feature.output_id,
    )
    print(
        "Volume:",
        solid.volume,
    )
    print(
        "Expected volume:",
        expected_volume,
    )
    print(
        "Center:",
        solid.center_of_mass,
    )
    print(
        "Bounds:",
        (
            solid.bounding_box.minimum,
            solid.bounding_box.maximum,
        ),
    )
    print(
        "Valid:",
        solid.is_valid,
    )
    print(
        "Valid: OK"
    )
    print()


if __name__ == "__main__":
    main()