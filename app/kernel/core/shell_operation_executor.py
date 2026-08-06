"""
DOBO CAD Kernel

Shell Operation Executor
"""

from __future__ import annotations

import cadquery as cq

from kernel.contracts.operations.shell_operation import ShellOperation
from kernel.core.execution_context import KernelExecutionContext
from kernel.core.operation_executor import (
    OperationExecutor,
    OperationExecutorPayload,
)
from kernel.geometry.solid_factory import SolidFactory


class ShellOperationExecutor(OperationExecutor[ShellOperation]):
    @property
    def operation_class(self) -> type[ShellOperation]:
        return ShellOperation

    def _execute(
        self,
        operation: ShellOperation,
        context: KernelExecutionContext,
    ) -> OperationExecutorPayload:
        operation.validate()
        context.validate()

        source = context.solids.get(operation.source_id)
        source.validate()

        geometry = source.geometry

        if not isinstance(geometry, cq.Shape):
            raise TypeError("Shell source geometry must be a CadQuery Shape.")

        faces = list(geometry.Faces())
        remove_faces = []

        for index in operation.remove_face_indices:
            try:
                remove_faces.append(faces[index])
            except IndexError as error:
                raise IndexError(
                    f"Shell face index {index} is out of range."
                ) from error

        shelled = geometry.shell(
            remove_faces,
            float(operation.thickness),
            float(operation.tolerance),
        ).clean()

        if not shelled.isValid():
            raise RuntimeError("Shell operation generated invalid geometry.")

        solid = SolidFactory.from_shape(
            geometry=shelled,
            source="shell_operation_executor",
            metadata={
                "source_id": operation.source_id,
                "thickness": float(operation.thickness),
                "remove_face_indices": operation.remove_face_indices,
                **operation.metadata,
            },
        )

        context.log(
            level="info",
            message=f"Shell operation generated '{operation.output_id}'.",
            operation_id=operation.id,
            metadata={
                "source_id": operation.source_id,
                "thickness": operation.thickness,
                "volume": solid.volume,
            },
        )

        return OperationExecutorPayload(
            output_id=operation.output_id,
            solid=solid,
            metadata={
                "executor": "shell_operation_executor",
                "source_id": operation.source_id,
                "thickness": operation.thickness,
                "volume": solid.volume,
            },
        )
