"""
DOBO CAD Kernel

Export Operation Executor Test

Validates this complete flow:

GeometryOperation
-> OperationDispatcher
-> SolidRegistry
-> ExportOperation
-> STEP file
"""

from __future__ import annotations

import os

from kernel.contracts.config import (
    ExportConfiguration,
    ExportFormat,
    GeometryPipelineConfiguration,
    OffsetConfiguration,
    ProviderConfiguration,
    SurfaceConfiguration,
)
from kernel.contracts.operations import (
    ExportOperation,
    GeometryOperation,
)
from kernel.contracts.placement import Placement
from kernel.contracts.surface import (
    Surface,
    SurfaceType,
)
from kernel.core.execution_context import (
    KernelExecutionContext,
)
from kernel.core.export_operation_executor import (
    ExportOperationExecutor,
)
from kernel.core.geometry_operation_executor import (
    GeometryOperationExecutor,
)
from kernel.core.operation_dispatcher import (
    OperationDispatcher,
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
from kernel.services.geometry_projection_engine import (
    GeometryProjectionEngine,
)
from kernel.services.offset_engine import (
    OffsetEngine,
)
from kernel.services.offset_solid_builder import (
    OffsetSolidBuilder,
)


def build_pipeline() -> GeometryPipeline:
    """
    Creates the Kernel v2 GeometryPipeline.
    """

    registry = DefinitionProviderRegistry()

    registry.register_provider(CircleDefinitionProvider())

    return GeometryPipeline(
        provider_registry=registry,
        projection_engine=(GeometryProjectionEngine()),
        offset_engine=OffsetEngine(),
        solid_builder=OffsetSolidBuilder(),
    )


def build_geometry_operation() -> GeometryOperation:
    """
    Creates one planar circular geometry operation.
    """

    configuration = GeometryPipelineConfiguration(
        project_name="Export Executor Test",
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
        name="Create export test circle",
        output_id="export_body",
        configuration=configuration,
        tags=(
            "test",
            "export",
        ),
    )


def build_export_operation(
    destination: str,
) -> ExportOperation:
    """
    Creates one STEP export operation.
    """

    return ExportOperation(
        name="Export test body",
        source_id="export_body",
        configuration=ExportConfiguration(
            enabled=True,
            format=ExportFormat.STEP,
            destination=destination,
            tolerance=0.01,
            angular_tolerance=0.1,
            units="mm",
            metadata={
                "test": True,
            },
        ),
        overwrite=True,
        metadata={
            "test": True,
        },
    )


def main() -> None:
    destination = os.path.join(
        "outputs",
        "kernel",
        "export_operation_executor.step",
    )

    absolute_destination = os.path.abspath(destination)

    if os.path.isfile(absolute_destination):
        os.remove(absolute_destination)

    context = KernelExecutionContext(
        metadata={
            "test": True,
        },
    )

    dispatcher = OperationDispatcher()

    dispatcher.register(GeometryOperationExecutor(pipeline=build_pipeline()))

    dispatcher.register(ExportOperationExecutor())

    geometry_operation = build_geometry_operation()

    geometry_payload = dispatcher.dispatch(
        geometry_operation,
        context,
    )

    if geometry_payload.solid is None:
        raise RuntimeError("Geometry executor returned no Solid.")

    if not context.solids.contains("export_body"):
        raise RuntimeError("Geometry Solid was not registered.")

    export_operation = build_export_operation(destination)

    export_payload = dispatcher.dispatch(
        export_operation,
        context,
    )

    if export_payload.export_path is None:
        raise RuntimeError("Export executor returned no path.")

    if context.export_count != 1:
        raise RuntimeError(
            "Export path was not registered " "in the execution context."
        )

    if not os.path.isfile(export_payload.export_path):
        raise RuntimeError("Export executor did not create " "the STEP file.")

    context.validate()

    print()
    print("DOBO Export Operation Executor")
    print("------------------------------")
    print(
        "Solid IDs:",
        context.solids.ids,
    )
    print(
        "Exports:",
        context.export_count,
    )
    print(
        "Destination:",
        export_payload.export_path,
    )
    print(
        "File exists:",
        os.path.isfile(export_payload.export_path),
    )
    print(
        "File size:",
        os.path.getsize(export_payload.export_path),
    )
    print(
        "Logs:",
        context.log_count,
    )
    print("Valid: OK")
    print()


if __name__ == "__main__":
    main()
