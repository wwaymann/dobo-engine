"""
DOBO CAD Kernel

Kernel Pipeline

Coordinates the complete geometry pipeline:

Configuration
-> ProviderStage
-> SurfaceStage
-> ExtrusionStage
-> BooleanStage
-> ModelState
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from kernel.contracts.configuration import Configuration
from kernel.contracts.execution_context import (
    ExecutionContext,
    ExecutionError,
    StageExecution,
)
from kernel.contracts.model_state import ModelState
from kernel.providers.registry import ProviderRegistry
from kernel.services.boolean_engine import BooleanEngineInterface
from kernel.services.extrusion_engine import ExtrusionEngineInterface
from kernel.services.surface_engine import SurfaceEngineInterface
from kernel.stages.boolean_stage import (
    BooleanStage,
    BooleanStageResult,
)
from kernel.stages.extrusion_stage import (
    ExtrusionStage,
    ExtrusionStageResult,
)
from kernel.stages.provider_stage import (
    ProviderStage,
    ProviderStageResult,
)
from kernel.stages.surface_stage import (
    SurfaceStage,
    SurfaceStageResult,
)


@dataclass(frozen=True, slots=True)
class KernelPipelineResult:
    """
    Immutable result of one complete Kernel execution.
    """

    model: ModelState

    context: ExecutionContext

    provider_result: ProviderStageResult

    surface_result: SurfaceStageResult

    extrusion_result: ExtrusionStageResult

    boolean_result: BooleanStageResult

    metadata: dict[str, Any] = field(default_factory=dict)


class KernelPipeline:
    """
    Public entry point of the DOBO CAD Kernel.

    The Pipeline owns orchestration only.

    It does not generate geometry and does not perform
    CAD operations directly.
    """

    def __init__(
        self,
        provider_registry: ProviderRegistry,
        surface_engine: SurfaceEngineInterface,
        extrusion_engine: ExtrusionEngineInterface,
        boolean_engine: BooleanEngineInterface,
    ) -> None:
        self._provider_stage = ProviderStage(registry=provider_registry)

        self._surface_stage = SurfaceStage(engine=surface_engine)

        self._extrusion_stage = ExtrusionStage(engine=extrusion_engine)

        self._boolean_stage = BooleanStage(engine=boolean_engine)

    def execute(
        self,
        configuration: Configuration,
        model: ModelState | None = None,
    ) -> KernelPipelineResult:
        """
        Executes one complete Kernel operation.

        An empty ModelState is created when no model
        is supplied.
        """

        configuration.validate()

        current_model = model if model is not None else ModelState()

        current_model.validate()

        started_at = datetime.utcnow()

        stage_executions: list[StageExecution] = []

        execution_errors: list[ExecutionError] = []

        try:
            provider_result = self._execute_stage(
                name="provider",
                callback=lambda: (
                    self._provider_stage.execute(
                        provider_name=(configuration.provider.name),
                        parameters=(configuration.provider.parameters),
                        metadata=(configuration.provider.metadata),
                    )
                ),
                stage_executions=stage_executions,
            )

            surface_result = self._execute_stage(
                name="surface",
                callback=lambda: (
                    self._surface_stage.execute(
                        contours=(provider_result.contours),
                        placement=(configuration.surface.placement),
                        surface=(configuration.surface.surface),
                    )
                ),
                stage_executions=stage_executions,
            )

            extrusion_result = self._execute_stage(
                name="extrusion",
                callback=lambda: (
                    self._extrusion_stage.execute(
                        placement=(surface_result.placement),
                        profile=(configuration.extrusion.profile),
                    )
                ),
                stage_executions=stage_executions,
            )

            boolean_result = self._execute_stage(
                name="boolean",
                callback=lambda: (
                    self._boolean_stage.execute(
                        model=current_model,
                        solid=extrusion_result.solid,
                        operation=(configuration.boolean.operation),
                        tolerance=(configuration.boolean.tolerance),
                        priority=(configuration.boolean.priority),
                        label=(configuration.boolean.label),
                        metadata=(configuration.boolean.metadata),
                    )
                ),
                stage_executions=stage_executions,
            )

        except Exception as error:
            execution_errors.append(
                ExecutionError(
                    stage=(
                        stage_executions[-1].name if stage_executions else "pipeline"
                    ),
                    message=str(error),
                    exception_type=(type(error).__name__),
                )
            )

            raise

        finished_at = datetime.utcnow()

        context = ExecutionContext(
            started_at=started_at,
            finished_at=finished_at,
            errors=tuple(execution_errors),
            executed_stages=tuple(stage_executions),
            statistics={
                "stage_count": len(stage_executions),
                "provider": (configuration.provider.name),
                "surface": (configuration.surface.surface.type.value),
                "boolean_operation": (configuration.boolean.operation.value),
            },
            metadata={
                "configuration_id": (configuration.id),
                "project_name": (configuration.project_name),
                **configuration.metadata,
            },
        )

        context.validate()

        return KernelPipelineResult(
            model=boolean_result.model,
            context=context,
            provider_result=provider_result,
            surface_result=surface_result,
            extrusion_result=extrusion_result,
            boolean_result=boolean_result,
            metadata={
                "configuration_id": (configuration.id),
            },
        )

    @staticmethod
    def _execute_stage(
        name: str,
        callback: Any,
        stage_executions: list[StageExecution],
    ) -> Any:
        """
        Executes one stage and records its duration.
        """

        started_at = datetime.utcnow()

        result = callback()

        finished_at = datetime.utcnow()

        duration = (finished_at - started_at).total_seconds() * 1000.0

        stage_executions.append(
            StageExecution(
                name=name,
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=duration,
            )
        )

        return result
