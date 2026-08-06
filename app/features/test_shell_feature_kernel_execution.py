"""
DOBO Features

Shell Feature Kernel Execution Test

Validates the complete flow:

ExtrudeFeatureDefinition
    ↓
ExtrudeOperationBuilder
    ↓
GeometryOperation
    ↓
ShellFeatureDefinition
    ↓
ShellOperationBuilder
    ↓
ShellOperation
    ↓
KernelExecutionEngine
    ↓
Shelled Solid
"""

from __future__ import annotations

from features.builders.extrude_operation_builder import (
    ExtrudeOperationBuilder,
)
from features.builders.shell_operation_builder import (
    ShellOperationBuilder,
)
from features.contracts import (
    BooleanMode,
    FeatureContext,
)
from features.definitions.extrude_feature_definition import (
    ExtrudeFeatureDefinition,
)
from features.definitions.shell_feature_definition import (
    ShellFeatureDefinition,
)
from kernel.contracts.model_state import (
    ModelState,
)
from kernel.core.kernel_model import (
    KernelModel,
)
from testing import (
    build_kernel_engine,
    build_rectangle_region_set,
)


SOURCE_BODY_ID = "source_body"
SHELL_BODY_ID = "shell_body"

WIDTH = 30.0
HEIGHT = 30.0
DISTANCE = 30.0

THICKNESS = -2.0
TOLERANCE = 0.01

REMOVE_FACE_INDICES = (
    5,
)


def build_context() -> FeatureContext:
    """
    Builds the FeatureContext and rectangular fixture.
    """

    regions = build_rectangle_region_set(
        region_set_id="shell_base_regions",
        width=WIDTH,
        height=HEIGHT,
    )

    context = FeatureContext(
        model=ModelState(),
    )

    context.register_regions(
        "shell_base_regions",
        regions,
    )

    context.validate()

    return context


def build_base_feature(
    context: FeatureContext,
) -> ExtrudeFeatureDefinition:
    """
    Builds the solid that will be hollowed.
    """

    regions = context.regions[
        "shell_base_regions"
    ]

    feature = ExtrudeFeatureDefinition(
        id="shell_base_feature",
        name="Shell Base",
        region_set_id="shell_base_regions",
        region_id=regions.regions[0].id,
        output_id=SOURCE_BODY_ID,
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
            "role": "shell_source",
        },
    )

    feature.validate()

    return feature


def build_shell_feature() -> ShellFeatureDefinition:
    """
    Builds the Shell Feature definition.
    """

    feature = ShellFeatureDefinition(
        id="shell_feature",
        name="Shell Body",
        source_body_id=SOURCE_BODY_ID,
        output_id=SHELL_BODY_ID,
        thickness=THICKNESS,
        tolerance=TOLERANCE,
        remove_face_indices=(
            REMOVE_FACE_INDICES
        ),
        metadata={
            "test": True,
            "role": "shell_result",
        },
    )

    feature.validate()

    return feature


def print_failed_result(
    result: object,
) -> None:
    """
    Prints complete Kernel diagnostics.

    The loose object annotation avoids coupling this
    diagnostic helper to a concrete result contract.
    """

    print()
    print(
        "DOBO Shell Execution Failed"
    )
    print(
        "---------------------------"
    )

    print(
        "Succeeded:",
        getattr(
            result,
            "succeeded",
            None,
        ),
    )

    print(
        "Operation count:",
        getattr(
            result,
            "operation_count",
            None,
        ),
    )

    print(
        "Completed:",
        getattr(
            result,
            "completed_count",
            None,
        ),
    )

    print(
        "Failed:",
        getattr(
            result,
            "failed_count",
            None,
        ),
    )

    print(
        "Skipped:",
        getattr(
            result,
            "skipped_count",
            None,
        ),
    )

    solids = getattr(
        result,
        "solids",
        {},
    )

    print(
        "Solid IDs:",
        tuple(
            solids.keys()
        ),
    )

    operation_results = getattr(
        result,
        "operations",
        (),
    )

    for index, operation_result in enumerate(
        operation_results
    ):
        print()
        print(
            "Operation result:",
            index,
        )

        operation_id = getattr(
            operation_result,
            "operation_id",
            None,
        )

        if operation_id is None:
            operation = getattr(
                operation_result,
                "operation",
                None,
            )

            operation_id = getattr(
                operation,
                "id",
                None,
            )

        print(
            "Operation ID:",
            operation_id,
        )

        status = getattr(
            operation_result,
            "status",
            None,
        )

        status_value = getattr(
            status,
            "value",
            status,
        )

        print(
            "Status:",
            status_value,
        )

        print(
            "Completed:",
            getattr(
                operation_result,
                "completed",
                None,
            ),
        )

        print(
            "Failed:",
            getattr(
                operation_result,
                "failed",
                None,
            ),
        )

        print(
            "Skipped:",
            getattr(
                operation_result,
                "skipped",
                None,
            ),
        )

        print(
            "Error:",
            getattr(
                operation_result,
                "error_message",
                None,
            ),
        )

        print(
            "Metadata:",
            getattr(
                operation_result,
                "metadata",
                None,
            ),
        )

    logs = getattr(
        result,
        "logs",
        (),
    )

    if logs:
        print()
        print(
            "Execution logs"
        )
        print(
            "--------------"
        )

        for log in logs:
            level = getattr(
                log,
                "level",
                None,
            )

            level_value = getattr(
                level,
                "value",
                level,
            )

            print(
                level_value,
                getattr(
                    log,
                    "message",
                    None,
                ),
            )


def main() -> None:
    """
    Executes one complete Shell Feature model.
    """

    context = build_context()

    base_feature = build_base_feature(
        context
    )

    shell_feature = build_shell_feature()

    base_builder = (
        ExtrudeOperationBuilder()
    )

    shell_builder = (
        ShellOperationBuilder()
    )

    base_plan = base_builder.build(
        base_feature,
        context,
    )

    shell_plan = shell_builder.build(
        shell_feature,
        context,
    )

    base_plan.validate()
    shell_plan.validate()

    if base_plan.operation_count != 1:
        raise RuntimeError(
            "Base Extrude must produce exactly "
            "one Kernel operation."
        )

    if shell_plan.operation_count != 1:
        raise RuntimeError(
            "Shell Feature must produce exactly "
            "one Kernel operation."
        )

    model = KernelModel(
        name="DOBO Shell Feature Model",
        metadata={
            "test": True,
            "feature_type": "shell",
        },
    )

    for operation in (
        *base_plan.operations,
        *shell_plan.operations,
    ):
        model.add_operation(
            operation
        )

    model.validate()

    if model.count != 2:
        raise RuntimeError(
            "Shell integration model must contain "
            "exactly two Kernel operations."
        )

    engine = build_kernel_engine(
        include_geometry=True,
        include_boolean=False,
        include_shell=True,
        include_export=False,
        stop_on_error=True,
    )

    result = engine.execute(
        model,
        metadata={
            "test_name": (
                "shell_feature_kernel_execution"
            ),
        },
    )

    result.validate()

    if not result.succeeded:
        print_failed_result(
            result
        )

        raise RuntimeError(
            "Shell Feature Kernel execution failed."
        )

    if result.operation_count != 2:
        raise RuntimeError(
            "Expected two executed operations."
        )

    if result.completed_count != 2:
        raise RuntimeError(
            "Expected two completed operations."
        )

    if result.failed_count != 0:
        raise RuntimeError(
            "Shell execution contains failures."
        )

    if result.skipped_count != 0:
        raise RuntimeError(
            "Shell execution contains skipped "
            "operations."
        )

    if SOURCE_BODY_ID not in result.solids:
        raise RuntimeError(
            "Shell execution did not register "
            f"'{SOURCE_BODY_ID}'."
        )

    if SHELL_BODY_ID not in result.solids:
        raise RuntimeError(
            "Shell execution did not register "
            f"'{SHELL_BODY_ID}'."
        )

    source_solid = result.solids[
        SOURCE_BODY_ID
    ]

    shell_solid = result.solids[
        SHELL_BODY_ID
    ]

    source_solid.validate()
    shell_solid.validate()

    if source_solid.volume is None:
        raise RuntimeError(
            "Source Solid has no volume."
        )

    if shell_solid.volume is None:
        raise RuntimeError(
            "Shell Solid has no volume."
        )

    if shell_solid.volume <= 0.0:
        raise RuntimeError(
            "Shell Solid volume must be positive."
        )

    if shell_solid.volume >= source_solid.volume:
        raise RuntimeError(
            "Shell Solid volume must be smaller "
            "than source Solid volume."
        )

    print()
    print(
        "DOBO Shell Feature Kernel Execution"
    )
    print(
        "-----------------------------------"
    )
    print(
        "Operations:",
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
        "Solid IDs:",
        tuple(
            result.solids.keys()
        ),
    )
    print(
        "Source volume:",
        source_solid.volume,
    )
    print(
        "Shell volume:",
        shell_solid.volume,
    )
    print(
        "Removed volume:",
        (
            source_solid.volume
            - shell_solid.volume
        ),
    )
    print(
        "Thickness:",
        THICKNESS,
    )
    print(
        "Removed faces:",
        REMOVE_FACE_INDICES,
    )
    print(
    "Source valid: OK"
    )
    print(
    "Shell valid: OK"
    )
    
    print(
        "Valid: OK"
    )
    print()


if __name__ == "__main__":
    main()
