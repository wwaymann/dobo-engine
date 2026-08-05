from datetime import UTC
from datetime import datetime
from datetime import timedelta

from kernel.contracts.config import (
    GeometryPipelineConfiguration,
    OffsetConfiguration,
    ProviderConfiguration,
    SurfaceConfiguration,
)
from kernel.contracts.operations import (
    GeometryOperation,
)
from kernel.contracts.placement import Placement
from kernel.contracts.surface import (
    Surface,
    SurfaceType,
)
from kernel.core.kernel_execution_result import (
    KernelExecutionResult,
    OperationExecutionResult,
    OperationExecutionStatus,
)
from kernel.core.kernel_model import KernelModel


def build_operation() -> GeometryOperation:
    configuration = GeometryPipelineConfiguration(
        project_name="Execution Result Test",
        provider=ProviderConfiguration(
            name="circle_definition",
            parameters={
                "radius": 10.0,
                "samples": 64,
            },
        ),
        surface=SurfaceConfiguration(
            surface=Surface(
                type=SurfaceType.PLANE,
                parameters={
                    "origin": (
                        0.0,
                        0.0,
                        0.0,
                    ),
                    "normal": (
                        0.0,
                        0.0,
                        1.0,
                    ),
                },
            ),
            placement=Placement(),
        ),
        offset=OffsetConfiguration(
            distance=4.0,
            symmetric=True,
        ),
    )

    return GeometryOperation(
        name="Create test geometry",
        output_id="test_body",
        configuration=configuration,
    )


def main() -> None:
    operation = build_operation()

    model = KernelModel(
        name="Execution Result Model"
    )

    model.add_operation(
        operation
    )

    started_at = datetime.now(UTC)

    finished_at = (
        started_at
        + timedelta(
            milliseconds=25,
        )
    )

    operation_result = (
        OperationExecutionResult(
            operation=operation,
            status=(
                OperationExecutionStatus.COMPLETED
            ),
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=25.0,
            output_id="test_body",
            metadata={
                "test": True,
            },
        )
    )

    result = KernelExecutionResult(
        model=model,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=25.0,
        operations=(
            operation_result,
        ),
        solids={},
        exports=(),
        metadata={
            "test": True,
        },
    )

    result.validate()

    print()
    print("DOBO Kernel Execution Result")
    print("----------------------------")
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
        "Skipped:",
        result.skipped_count,
    )
    print(
        "Succeeded:",
        result.succeeded,
    )
    print(
        "Duration ms:",
        result.duration_ms,
    )
    print("Valid: OK")
    print()


if __name__ == "__main__":
    main()