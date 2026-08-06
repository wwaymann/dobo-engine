"""
DOBO Features

Extrude Boolean Kernel Execution Test

Validates complete Feature-to-Kernel execution for:

- JOIN
- CUT
- INTERSECT
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
from kernel.core.kernel_model import (
    KernelModel,
)
from kernel.providers.region_definition_provider import (
    RegionDefinitionProvider,
)

from testing import (
    build_kernel_engine,
    build_rectangle_region_set,
)


BASE_WIDTH = 40.0
BASE_HEIGHT = 30.0

TOOL_WIDTH = 20.0
TOOL_HEIGHT = 40.0

DISTANCE = 25.0

BASE_VOLUME = (
    BASE_WIDTH
    * BASE_HEIGHT
    * DISTANCE
)

TOOL_VOLUME = (
    TOOL_WIDTH
    * TOOL_HEIGHT
    * DISTANCE
)

OVERLAP_VOLUME = (
    min(
        BASE_WIDTH,
        TOOL_WIDTH,
    )
    * min(
        BASE_HEIGHT,
        TOOL_HEIGHT,
    )
    * DISTANCE
)

EXPECTED_VOLUMES: dict[
    BooleanMode,
    float,
] = {
    BooleanMode.JOIN: (
        BASE_VOLUME
        + TOOL_VOLUME
        - OVERLAP_VOLUME
    ),
    BooleanMode.CUT: (
        BASE_VOLUME
        - OVERLAP_VOLUME
    ),
    BooleanMode.INTERSECT: (
        OVERLAP_VOLUME
    ),
}


def build_context() -> FeatureContext:
    """
    Builds the FeatureContext containing the base and
    tool RegionSet fixtures.
    """

    base_regions = build_rectangle_region_set(
        region_set_id="base_regions",
        width=BASE_WIDTH,
        height=BASE_HEIGHT,
    )

    tool_regions = build_rectangle_region_set(
        region_set_id="tool_regions",
        width=TOOL_WIDTH,
        height=TOOL_HEIGHT,
    )

    context = FeatureContext(
        model=ModelState(),
    )

    context.register_regions(
        "base_regions",
        base_regions,
    )

    context.register_regions(
        "tool_regions",
        tool_regions,
    )

    context.validate()

    return context


def build_base_feature(
    context: FeatureContext,
) -> ExtrudeFeatureDefinition:
    """
    Builds the base NEW_BODY Extrude Feature.
    """

    base_regions = context.regions[
        "base_regions"
    ]

    feature = ExtrudeFeatureDefinition(
        id="feature_base_body",
        name="Base Body",
        region_set_id="base_regions",
        region_id=(
            base_regions.regions[0].id
        ),
        output_id="base_body",
        distance=DISTANCE,
        direction=(
            0.0,
            0.0,
            1.0,
        ),
        mode=BooleanMode.NEW_BODY,
        target_body_id=None,
        symmetric=False,
        draft_angle=0.0,
        merge=True,
        metadata={
            "test": True,
            "role": "base",
        },
    )

    feature.validate()

    return feature


def build_boolean_feature(
    *,
    mode: BooleanMode,
    context: FeatureContext,
) -> ExtrudeFeatureDefinition:
    """
    Builds one Boolean Extrude Feature.
    """

    tool_regions = context.regions[
        "tool_regions"
    ]

    feature = ExtrudeFeatureDefinition(
        id=f"feature_{mode.value}",
        name=f"Extrude {mode.value}",
        region_set_id="tool_regions",
        region_id=(
            tool_regions.regions[0].id
        ),
        output_id=f"{mode.value}_result",
        distance=DISTANCE,
        direction=(
            0.0,
            0.0,
            1.0,
        ),
        mode=mode,
        target_body_id="base_body",
        symmetric=False,
        draft_angle=0.0,
        merge=True,
        metadata={
            "test": True,
            "role": "boolean_tool",
            "mode": mode.value,
        },
    )

    feature.validate()

    return feature


def execute_mode(
    mode: BooleanMode,
) -> float:
    """
    Executes one complete Boolean Extrude model.
    """

    context = build_context()

    builder = ExtrudeOperationBuilder(
        region_provider=(
            RegionDefinitionProvider()
        ),
    )

    base_feature = build_base_feature(
        context
    )

    boolean_feature = build_boolean_feature(
        mode=mode,
        context=context,
    )

    base_plan = builder.build(
        base_feature,
        context,
    )

    boolean_plan = builder.build(
        boolean_feature,
        context,
    )

    base_plan.validate()
    boolean_plan.validate()

    if base_plan.operation_count != 1:
        raise RuntimeError(
            "Base Feature must produce "
            "one Kernel operation."
        )

    if boolean_plan.operation_count != 2:
        raise RuntimeError(
            f"{mode.value} Feature must produce "
            "two Kernel operations."
        )

    model = KernelModel(
        name=(
            f"DOBO Extrude "
            f"{mode.value} Model"
        ),
        metadata={
            "test": True,
            "boolean_mode": mode.value,
        },
    )

    for operation in base_plan.operations:
        model.add_operation(
            operation
        )

    for operation in boolean_plan.operations:
        model.add_operation(
            operation
        )

    model.validate()

    if len(model.operations) != 3:
        raise RuntimeError(
            "Boolean Extrude model must contain "
            "three Kernel operations."
        )

    engine = build_kernel_engine(
        include_geometry=True,
        include_boolean=True,
        include_export=False,
        stop_on_error=True,
    )

    result = engine.execute(
        model,
        metadata={
            "test_name": (
                "extrude_boolean_kernel_execution"
            ),
            "boolean_mode": mode.value,
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
            f"{mode.value} execution failed: "
            f"{failures}"
        )

    if result.operation_count != 3:
        raise RuntimeError(
            "Expected three executed operations."
        )

    if result.completed_count != 3:
        raise RuntimeError(
            "Expected three completed operations."
        )

    if result.failed_count != 0:
        raise RuntimeError(
            "Boolean execution contains failures."
        )

    if result.skipped_count != 0:
        raise RuntimeError(
            "Boolean execution contains "
            "skipped operations."
        )

    output_id = (
        boolean_feature.output_id
    )

    if output_id not in result.solids:
        raise RuntimeError(
            f"Expected output '{output_id}' "
            "was not registered."
        )

    expected_tool_id = (
        f"{output_id}:tool"
    )

    expected_ids = (
        "base_body",
        expected_tool_id,
        output_id,
    )

    actual_ids = tuple(
        result.solids.keys()
    )

    if actual_ids != expected_ids:
        raise RuntimeError(
            "Unexpected Solid IDs: "
            f"{actual_ids}."
        )

    solid = result.solids[
        output_id
    ]

    solid.validate()

    if solid.volume is None:
        raise RuntimeError(
            "Boolean result has no volume."
        )

    expected_volume = (
        EXPECTED_VOLUMES[
            mode
        ]
    )

    if not math.isclose(
        solid.volume,
        expected_volume,
        rel_tol=1e-7,
        abs_tol=1e-6,
    ):
        raise RuntimeError(
            f"Unexpected {mode.value} volume: "
            f"{solid.volume}; "
            f"expected {expected_volume}."
        )

    if mode is BooleanMode.JOIN:
        if solid.volume <= BASE_VOLUME:
            raise RuntimeError(
                "JOIN must increase the base volume."
            )

    elif mode is BooleanMode.CUT:
        if not (
            0.0
            < solid.volume
            < BASE_VOLUME
        ):
            raise RuntimeError(
                "CUT must reduce the base volume."
            )

    elif mode is BooleanMode.INTERSECT:
        if not (
            0.0
            < solid.volume
            <= min(
                BASE_VOLUME,
                TOOL_VOLUME,
            )
        ):
            raise RuntimeError(
                "INTERSECT produced an "
                "invalid volume."
            )

    else:
        raise RuntimeError(
            "Unsupported test Boolean mode."
        )

    print(
        f"{mode.value}:",
        solid.volume,
        "OK",
    )

    return solid.volume


def main() -> None:
    """
    Executes every Boolean Extrude mode.
    """

    results: dict[
        str,
        float,
    ] = {}

    for mode in (
        BooleanMode.JOIN,
        BooleanMode.CUT,
        BooleanMode.INTERSECT,
    ):
        results[
            mode.value
        ] = execute_mode(
            mode
        )

    print()
    print(
        "DOBO Extrude Boolean Kernel Execution"
    )
    print(
        "-------------------------------------"
    )
    print(
        "Base volume:",
        BASE_VOLUME,
    )
    print(
        "Tool volume:",
        TOOL_VOLUME,
    )
    print(
        "Overlap volume:",
        OVERLAP_VOLUME,
    )
    print(
        "JOIN volume:",
        results[
            BooleanMode.JOIN.value
        ],
    )
    print(
        "CUT volume:",
        results[
            BooleanMode.CUT.value
        ],
    )
    print(
        "INTERSECT volume:",
        results[
            BooleanMode.INTERSECT.value
        ],
    )
    print(
        "Modes validated:",
        tuple(
            results.keys()
        ),
    )
    print(
        "Valid: OK"
    )
    print()


if __name__ == "__main__":
    main()