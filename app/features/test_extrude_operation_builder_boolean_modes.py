"""
DOBO Features

Extrude Operation Builder Boolean Modes Test

Validates the translation of JOIN, CUT and INTERSECT
Extrude Features into GeometryOperation +
BooleanOperation plans.
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

from kernel.contracts.boolean_request import (
    BooleanOperation as KernelBooleanMode,
)
from kernel.contracts.model_state import (
    ModelState,
)
from kernel.contracts.operations import (
    BooleanOperation,
    GeometryOperation,
)
from kernel.providers.region_definition_provider import (
    RegionDefinitionProvider,
)

from testing.region_builders import (
    build_rectangle_region_set,
)


EXPECTED_KERNEL_MODES: dict[
    BooleanMode,
    KernelBooleanMode,
] = {
    BooleanMode.JOIN: (
        KernelBooleanMode.UNION
    ),
    BooleanMode.CUT: (
        KernelBooleanMode.CUT
    ),
    BooleanMode.INTERSECT: (
        KernelBooleanMode.INTERSECT
    ),
}


def validate_mode(
    *,
    mode: BooleanMode,
    builder: ExtrudeOperationBuilder,
    context: FeatureContext,
    region_id: str,
) -> None:
    """
    Validates one Boolean Extrude mode.
    """

    output_id = (
        f"{mode.value}_body"
    )

    feature = ExtrudeFeatureDefinition(
        id=f"feature_{mode.value}",
        name=(
            f"Extrude {mode.value}"
        ),
        region_set_id="tool_regions",
        region_id=region_id,
        output_id=output_id,
        distance=15.0,
        direction=(
            0.0,
            0.0,
            2.0,
        ),
        mode=mode,
        target_body_id="base_body",
        symmetric=False,
        draft_angle=0.0,
        merge=True,
        metadata={
            "test": True,
            "mode": mode.value,
        },
    )

    feature.validate()

    plan = builder.build(
        feature,
        context,
    )

    plan.validate()

    if plan.operation_count != 2:
        raise RuntimeError(
            f"{mode.value} must produce "
            "two Kernel operations."
        )

    geometry_operation = (
        plan.operations[0]
    )

    boolean_operation = (
        plan.operations[1]
    )

    if not isinstance(
        geometry_operation,
        GeometryOperation,
    ):
        raise RuntimeError(
            "First operation must be "
            "GeometryOperation."
        )

    if not isinstance(
        boolean_operation,
        BooleanOperation,
    ):
        raise RuntimeError(
            "Second operation must be "
            "BooleanOperation."
        )

    geometry_operation.validate()
    boolean_operation.validate()

    expected_tool_id = (
        f"{output_id}:tool"
    )

    if (
        geometry_operation.resolved_output_id
        != expected_tool_id
    ):
        raise RuntimeError(
            "Unexpected temporary tool output."
        )

    if (
        boolean_operation.target_id
        != "base_body"
    ):
        raise RuntimeError(
            "Boolean target_id is incorrect."
        )

    if (
        boolean_operation.tool_id
        != expected_tool_id
    ):
        raise RuntimeError(
            "Boolean tool_id is incorrect."
        )

    if (
        boolean_operation.output_id
        != output_id
    ):
        raise RuntimeError(
            "Boolean output_id is incorrect."
        )

    expected_kernel_mode = (
        EXPECTED_KERNEL_MODES[
            mode
        ]
    )

    if (
        boolean_operation.mode
        is not expected_kernel_mode
    ):
        raise RuntimeError(
            "Feature BooleanMode was mapped "
            "incorrectly."
        )

    if plan.expected_output_ids != (
        expected_tool_id,
        output_id,
    ):
        raise RuntimeError(
            "Unexpected FeaturePlan outputs."
        )

    if (
        plan.final_output_id
        != output_id
    ):
        raise RuntimeError(
            "Unexpected final output id."
        )

    print(
        f"{mode.value}:",
        "OK",
    )


def main() -> None:
    """
    Validates every Boolean Extrude mode.
    """

    regions = (
        build_rectangle_region_set(
            region_set_id="tool_regions",
            width=20.0,
            height=15.0,
        )
    )

    regions.validate()

    context = FeatureContext(
        model=ModelState(),
    )

    context.register_regions(
        "tool_regions",
        regions,
    )

    context.validate()

    region_id = (
        regions.regions[0].id
    )

    builder = ExtrudeOperationBuilder(
        region_provider=(
            RegionDefinitionProvider()
        ),
    )

    for mode in (
        BooleanMode.JOIN,
        BooleanMode.CUT,
        BooleanMode.INTERSECT,
    ):
        validate_mode(
            mode=mode,
            builder=builder,
            context=context,
            region_id=region_id,
        )

    print()
    print(
        "DOBO Extrude Boolean Plans"
    )
    print(
        "--------------------------"
    )
    print(
        "Modes:",
        tuple(
            mode.value
            for mode in (
                BooleanMode.JOIN,
                BooleanMode.CUT,
                BooleanMode.INTERSECT,
            )
        ),
    )
    print(
        "Operations per plan:",
        2,
    )
    print(
        "Target:",
        "base_body",
    )
    print(
        "Valid: OK"
    )
    print()


if __name__ == "__main__":
    main()