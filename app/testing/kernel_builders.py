"""
DOBO Test Support

Kernel Builders

Reusable factories for building Kernel execution
infrastructure inside tests.
"""

from __future__ import annotations

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
from kernel.services.boolean_engine import (
    BooleanEngine,
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


def build_provider_registry(
) -> DefinitionProviderRegistry:
    """
    Builds the legacy Definition Provider registry.
    """

    registry = DefinitionProviderRegistry()

    registry.register_provider(
        CircleDefinitionProvider()
    )

    return registry


def build_geometry_pipeline(
) -> GeometryPipeline:
    """
    Builds the legacy GeometryPipeline.

    It remains available while the Kernel supports
    GeometryPipelineConfiguration compatibility.
    """

    return GeometryPipeline(
        provider_registry=(
            build_provider_registry()
        ),
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


def build_geometry_service(
) -> GeometryExecutionService:
    """
    Builds a GeometryExecutionService supporting
    legacy and GeometryRequest routes.
    """

    return GeometryExecutionService(
        pipeline=build_geometry_pipeline(),
        request_registry=(
            build_request_registry()
        ),
    )


def build_dispatcher(
    *,
    include_geometry: bool = True,
    include_boolean: bool = True,
    include_export: bool = True,
) -> OperationDispatcher:
    """
    Builds and validates an OperationDispatcher.

    Executor groups may be disabled for isolated tests.
    """

    if not isinstance(
        include_geometry,
        bool,
    ):
        raise TypeError(
            "include_geometry must be boolean."
        )

    if not isinstance(
        include_boolean,
        bool,
    ):
        raise TypeError(
            "include_boolean must be boolean."
        )

    if not isinstance(
        include_export,
        bool,
    ):
        raise TypeError(
            "include_export must be boolean."
        )

    dispatcher = OperationDispatcher()

    if include_geometry:
        dispatcher.register(
            GeometryOperationExecutor(
                geometry_service=(
                    build_geometry_service()
                )
            )
        )

    if include_boolean:
        dispatcher.register(
            BooleanOperationExecutor(
                boolean_engine=BooleanEngine()
            )
        )

    if include_export:
        dispatcher.register(
            ExportOperationExecutor()
        )

    dispatcher.validate()

    return dispatcher


def build_kernel_engine(
    *,
    include_geometry: bool = True,
    include_boolean: bool = True,
    include_export: bool = True,
    stop_on_error: bool = True,
) -> KernelExecutionEngine:
    """
    Builds a complete KernelExecutionEngine.
    """

    if not isinstance(
        stop_on_error,
        bool,
    ):
        raise TypeError(
            "stop_on_error must be boolean."
        )

    return KernelExecutionEngine(
        dispatcher=build_dispatcher(
            include_geometry=include_geometry,
            include_boolean=include_boolean,
            include_export=include_export,
        ),
        stop_on_error=stop_on_error,
    )