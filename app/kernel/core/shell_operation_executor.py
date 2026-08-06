"""
DOBO CAD Kernel

Shell Operation Executor

Creates a hollow solid from an existing Solid by
removing selected faces and applying wall thickness.
"""

from __future__ import annotations

import cadquery as cq

from kernel.contracts.operations.shell_operation import (
    ShellOperation,
)
from kernel.core.execution_context import (
    KernelExecutionContext,
)
from kernel.core.operation_executor import (
    OperationExecutor,
    OperationExecutorPayload,
)
from kernel.geometry.solid_factory import (
    SolidFactory,
)


class ShellOperationExecutor(
    OperationExecutor[ShellOperation],
):
    """
    Executes ShellOperation objects over existing
    CadQuery solids.
    """

    @property
    def operation_class(
        self,
    ) -> type[ShellOperation]:
        """
        Returns the supported operation contract.
        """

        return ShellOperation

    def _execute(
        self,
        operation: ShellOperation,
        context: KernelExecutionContext,
    ) -> OperationExecutorPayload:
        """
        Executes one ShellOperation.
        """

        operation.validate()
        context.validate()

        source = context.solids.get(
            operation.source_id
        )

        source.validate()

        geometry = source.geometry

        if not isinstance(
            geometry,
            cq.Shape,
        ):
            raise TypeError(
                "Shell source geometry must be "
                "a CadQuery Shape."
            )

        faces = list(
            geometry.Faces()
        )

        if not faces:
            raise RuntimeError(
                "Shell source geometry contains "
                "no faces."
            )

        remove_faces: list[cq.Face] = []

        for index in (
            operation.remove_face_indices
        ):
            if index >= len(
                faces
            ):
                raise IndexError(
                    "Shell face index "
                    f"{index} is out of range. "
                    f"Available faces: {len(faces)}."
                )

            face = faces[
                index
            ]

            if not isinstance(
                face,
                cq.Face,
            ):
                raise TypeError(
                    "Shell face selection did not "
                    "produce a CadQuery Face."
                )

            remove_faces.append(
                face
            )

        if not remove_faces:
            raise ValueError(
                "ShellOperation requires at least "
                "one face to remove."
            )

        try:
            workplane = cq.Workplane(
                obj=geometry
            )

            selected_faces = (
                workplane.newObject(
                    remove_faces
                )
            )

            shelled_workplane = (
                selected_faces.shell(
                    float(
                        operation.thickness
                    ),
                    kind="arc",
                )
            )

            shelled_value = (
                shelled_workplane.val()
            )

        except Exception as error:
            raise RuntimeError(
                "ShellOperationExecutor could not "
                "generate the shell."
            ) from error

        if not isinstance(
            shelled_value,
            cq.Shape,
        ):
            raise RuntimeError(
                "Shell operation did not produce "
                "a CadQuery Shape."
            )

        try:
            shelled = (
                shelled_value.clean()
            )

        except Exception as error:
            raise RuntimeError(
                "Shell operation could not clean "
                "the generated geometry."
            ) from error

        #
        # Normalize OpenCascade output.
        #
        # CadQuery / OpenCascade may return a Compound
        # that contains exactly one Solid after shell().
        #
        # That geometry is valid, but downstream boolean
        # operations are more reliable when they receive
        # the actual Solid instead of the single-solid
        # Compound wrapper.
        #
        if isinstance(
            shelled,
            cq.Compound,
):
            solids = list(
             shelled.Solids()
            )

        if len(solids) == 1:
         normalized_solid = solids[0]

        if not isinstance(
            normalized_solid,
            cq.Solid,
        ):
            raise RuntimeError(
                "Shell normalization did not "
                "produce a CadQuery Solid."
            )

        shelled = normalized_solid.clean()

        if not shelled.isValid():
            raise RuntimeError(
                "Shell operation generated "
                "invalid geometry."
            )

        solid = SolidFactory.from_shape(
            geometry=shelled,
            source=(
                "shell_operation_executor"
            ),
            metadata={
                "source_id": (
                    operation.source_id
                ),
                "output_id": (
                    operation.output_id
                ),
                "thickness": float(
                    operation.thickness
                ),
                "tolerance": float(
                    operation.tolerance
                ),
                "remove_face_indices": (
                    operation.remove_face_indices
                ),
                "removed_face_count": len(
                    remove_faces
                ),
                "normalized_shape_type": (
                    shelled.ShapeType()
                ),
                **operation.metadata,
            },
        )

        solid.validate()

        context.log(
            level="info",
            message=(
                "Shell operation generated "
                f"'{operation.output_id}'."
            ),
            operation_id=operation.id,
            metadata={
                "source_id": (
                    operation.source_id
                ),
                "output_id": (
                    operation.output_id
                ),
                "thickness": (
                    operation.thickness
                ),
                "removed_face_count": len(
                    remove_faces
                ),
                "shape_type": (
                    shelled.ShapeType()
                ),
                "volume": (
                    solid.volume
                ),
            },
        )

        return OperationExecutorPayload(
            output_id=(
                operation.output_id
            ),
            solid=solid,
            metadata={
                "executor": (
                    "shell_operation_executor"
                ),
                "source_id": (
                    operation.source_id
                ),
                "output_id": (
                    operation.output_id
                ),
                "thickness": (
                    operation.thickness
                ),
                "tolerance": (
                    operation.tolerance
                ),
                "remove_face_indices": (
                    operation.remove_face_indices
                ),
                "removed_face_count": len(
                    remove_faces
                ),
                "shape_type": (
                    shelled.ShapeType()
                ),
                "volume": (
                    solid.volume
                ),
            },
        )
