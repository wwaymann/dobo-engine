from app.kernel.services.geometry_request_engine import GeometryRequestEngine
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
from kernel.core.execution_context import (
    KernelExecutionContext,
)
from kernel.core.geometry_operation_executor import (
    GeometryOperationExecutor,
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
from kernel.geometry import (
    ExtrudeRequestExecutor,
    GeometryRequestExecutorRegistry,
)
from kernel.services.geometry_execution_service import (
    GeometryExecutionService,
)

def build_pipeline() -> GeometryPipeline:
    registry = DefinitionProviderRegistry()

    registry.register_provider(
        CircleDefinitionProvider()
    )

    return GeometryPipeline(
        provider_registry=registry,
        projection_engine=(
            GeometryProjectionEngine()
        ),
        offset_engine=OffsetEngine(),
        solid_builder=OffsetSolidBuilder(),
    )
def build_geometry_service() -> GeometryExecutionService:
    """
    Creates the geometry execution service.
    """

    request_registry = (
        GeometryRequestExecutorRegistry()
    )

    request_registry.register(
        ExtrudeRequestExecutor()
    )

    request_registry.validate()

    return GeometryExecutionService(
        pipeline=build_pipeline(),
        request_registry=request_registry,
    )

def build_operation() -> GeometryOperation:
    configuration = (
        GeometryPipelineConfiguration(
            project_name=(
                "Geometry Executor Test"
            ),
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
    )

    return GeometryOperation(
        name="Generate test circle",
        output_id="test_circle",
        configuration=configuration,
        tags=(
            "test",
            "circle",
        ),
    )


def main() -> None:
    operation = build_operation()

    context = KernelExecutionContext(
        metadata={
            "test": True,
        },
    )

    executor = GeometryOperationExecutor(
    geometry_service=(
        build_geometry_service()
    )
)
   

    context.begin_operation(
        operation
    )

    payload = executor.execute(
        operation,
        context,
    )

    if payload.solid is None:
        raise RuntimeError(
            "Geometry executor returned no Solid."
        )

    if payload.output_id is None:
        raise RuntimeError(
            "Geometry executor returned no output ID."
        )

    context.solids.register(
        payload.output_id,
        payload.solid,
    )

    context.end_operation(
        operation
    )

    context.validate()

    print()
    print("DOBO Geometry Operation Executor")
    print("--------------------------------")
    print(
        "Output:",
        payload.output_id,
    )
    print(
        "Solid valid:",
        payload.solid.is_valid,
    )
    print(
        "Volume:",
        payload.solid.volume,
    )
    print(
        "Registry solids:",
        context.solids.count,
    )
    print(
        "Registry IDs:",
        context.solids.ids,
    )
    print(
        "Logs:",
        context.log_count,
    )
    print("Valid: OK")
    print()


if __name__ == "__main__":
    main()