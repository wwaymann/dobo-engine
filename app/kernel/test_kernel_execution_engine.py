"""
DOBO CAD Kernel

Kernel Execution Engine Integration Test
"""

from __future__ import annotations

import os

from kernel.contracts.boolean_request import (
    BooleanOperation as BooleanMode,
)
from kernel.contracts.config import (
    ExportConfiguration,
    ExportFormat,
    GeometryPipelineConfiguration,
    OffsetConfiguration,
    ProviderConfiguration,
    SurfaceConfiguration,
)
from kernel.contracts.operations import (
    BooleanOperation,
    ExportOperation,
    GeometryOperation,
)
from kernel.contracts.placement import Placement
from kernel.contracts.surface import Surface, SurfaceType
from kernel.core.boolean_operation_executor import (
    BooleanOperationExecutor,
)
from kernel.core.export_operation_executor import (
    ExportOperationExecutor,
)
from kernel.core.geometry_operation_executor import (
    GeometryOperationExecutor,
)
from kernel.core.kernel_execution_engine import (
    KernelExecutionEngine,
)
from kernel.core.kernel_model import KernelModel
from kernel.core.operation_dispatcher import OperationDispatcher
from kernel.pipeline.geometry_pipeline import GeometryPipeline
from kernel.providers.circle_definition_provider import (
    CircleDefinitionProvider,
)
from kernel.providers.definition_registry import (
    DefinitionProviderRegistry,
)
from kernel.services.boolean_engine import BooleanEngine
from kernel.services.geometry_projection_engine import (
    GeometryProjectionEngine,
)
from kernel.services.offset_engine import OffsetEngine
from kernel.services.offset_solid_builder import OffsetSolidBuilder


def build_geometry_pipeline() -> GeometryPipeline:
    registry = DefinitionProviderRegistry()
    registry.register_provider(CircleDefinitionProvider())

    return GeometryPipeline(
        provider_registry=registry,
        projection_engine=GeometryProjectionEngine(),
        offset_engine=OffsetEngine(),
        solid_builder=OffsetSolidBuilder(),
    )


def build_dispatcher() -> OperationDispatcher:
    dispatcher = OperationDispatcher()

    dispatcher.register(
        GeometryOperationExecutor(
            pipeline=build_geometry_pipeline()
        )
    )
    dispatcher.register(
        BooleanOperationExecutor(
            boolean_engine=BooleanEngine()
        )
    )
    dispatcher.register(
        ExportOperationExecutor()
    )

    dispatcher.validate()
    return dispatcher


def build_geometry_operation(
    *,
    name: str,
    output_id: str,
    radius: float,
    position_x: float,
) -> GeometryOperation:
    return GeometryOperation(
        name=name,
        output_id=output_id,
        configuration=GeometryPipelineConfiguration(
            project_name="Kernel Execution Engine Test",
            provider=ProviderConfiguration(
                name="circle_definition",
                parameters={
                    "radius": radius,
                    "samples": 64,
                },
            ),
            surface=SurfaceConfiguration(
                surface=Surface(
                    type=SurfaceType.PLANE,
                    parameters={
                        "origin": (0.0, 0.0, 0.0),
                        "normal": (0.0, 0.0, 1.0),
                    },
                ),
                placement=Placement(
                    position=(
                        position_x,
                        0.0,
                        0.0,
                    ),
                ),
            ),
            offset=OffsetConfiguration(
                distance=4.0,
                symmetric=True,
            ),
        ),
        tags=(
            "integration-test",
            "circle",
        ),
    )


def build_model(destination: str) -> KernelModel:
    model = KernelModel(
        name="DOBO Kernel v2 Integration Model",
        metadata={
            "test": True,
        },
    )

    model.add_operation(
        build_geometry_operation(
            name="Create base body",
            output_id="base_body",
            radius=20.0,
            position_x=0.0,
        )
    )

    model.add_operation(
        build_geometry_operation(
            name="Create cutting body",
            output_id="cutting_body",
            radius=8.0,
            position_x=5.0,
        )
    )

    model.add_operation(
        BooleanOperation(
            name="Cut smaller body",
            mode=BooleanMode.CUT,
            target_id="base_body",
            tool_id="cutting_body",
            output_id="final_body",
            tolerance=0.01,
        )
    )

    model.add_operation(
        ExportOperation(
            name="Export final body",
            source_id="final_body",
            configuration=ExportConfiguration(
                enabled=True,
                format=ExportFormat.STEP,
                destination=destination,
                tolerance=0.01,
                angular_tolerance=0.1,
                units="mm",
            ),
            overwrite=True,
        )
    )

    model.validate()
    return model


def main() -> None:
    destination = os.path.join(
        "outputs",
        "kernel",
        "kernel_execution_engine.step",
    )

    absolute_destination = os.path.abspath(destination)

    if os.path.isfile(absolute_destination):
        os.remove(absolute_destination)

    engine = KernelExecutionEngine(
        dispatcher=build_dispatcher(),
        stop_on_error=True,
    )

    result = engine.execute(
        build_model(destination),
        metadata={
            "test_name": "kernel_execution_engine",
        },
    )

    result.validate()

    if not result.succeeded:
        failures = tuple(
            item.error_message
            for item in result.operations
            if item.failed
        )
        raise RuntimeError(
            f"Kernel execution failed: {failures}"
        )

    if result.final_solid is None:
        raise RuntimeError(
            "Kernel execution produced no final Solid."
        )

    if len(result.exports) != 1:
        raise RuntimeError(
            "Kernel execution must produce one export."
        )

    exported_path = result.exports[0]

    if not os.path.isfile(exported_path):
        raise RuntimeError(
            "Kernel execution export does not exist."
        )

    print()
    print("DOBO Kernel Execution Engine")
    print("----------------------------")
    print("Model:", result.model.name)
    print("Operations:", result.operation_count)
    print("Completed:", result.completed_count)
    print("Failed:", result.failed_count)
    print("Skipped:", result.skipped_count)
    print("Succeeded:", result.succeeded)
    print("Solid IDs:", tuple(result.solids.keys()))
    print("Final volume:", result.final_solid.volume)
    print("Exports:", len(result.exports))
    print("STEP:", exported_path)
    print("File exists:", os.path.isfile(exported_path))
    print("Duration ms:", result.duration_ms)
    print("Valid: OK")
    print()
   

if __name__ == "__main__":
    main()
