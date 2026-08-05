"""
DOBO CAD Kernel

Export Operation Executor

Exports one Solid stored inside
KernelExecutionContext.

This executor is part of the CAD backend boundary
and uses CadQuery exporters directly.
"""

from __future__ import annotations

import os

import cadquery as cq

from kernel.contracts.config.export_configuration import (
    ExportFormat,
)
from kernel.contracts.operations import (
    ExportOperation,
)
from kernel.core.execution_context import (
    KernelExecutionContext,
)
from kernel.core.operation_executor import (
    OperationExecutor,
    OperationExecutorPayload,
)


class ExportOperationExecutor(
    OperationExecutor[ExportOperation],
):
    """
    Executes ExportOperation objects.

    Flow:

    SolidRegistry
    -> CadQuery geometry
    -> output file
    -> OperationExecutorPayload
    """

    @property
    def operation_class(
        self,
    ) -> type[ExportOperation]:
        """
        Returns the supported operation class.
        """

        return ExportOperation

    def _execute(
        self,
        operation: ExportOperation,
        context: KernelExecutionContext,
    ) -> OperationExecutorPayload:
        """
        Exports one registered Solid.
        """

        operation.validate()
        context.validate()

        solid = context.solids.get(
            operation.source_id
        )

        solid.validate()

        geometry = solid.geometry

        if not isinstance(
            geometry,
            cq.Shape,
        ):
            raise TypeError(
                "ExportOperationExecutor requires "
                "CadQuery Shape geometry."
            )

        configuration = (
            operation.configuration
        )

        configuration.validate()

        destination = self._normalize_destination(
            destination=configuration.destination,
            export_format=configuration.format,
        )

        self._prepare_destination(
            destination=destination,
            overwrite=operation.overwrite,
        )

        self._export_geometry(
            geometry=geometry,
            destination=destination,
            export_format=configuration.format,
            tolerance=configuration.tolerance,
            angular_tolerance=(
                configuration.angular_tolerance
            ),
        )

        if not os.path.isfile(
            destination
        ):
            raise RuntimeError(
                "ExportOperationExecutor completed "
                "without creating the output file."
            )

        context.log(
            level="info",
            message=(
                f"Exported solid "
                f"'{operation.source_id}'."
            ),
            operation_id=operation.id,
            metadata={
                "source_id": operation.source_id,
                "destination": destination,
                "format": (
                    configuration.format.value
                ),
                "units": configuration.units,
                "file_size": os.path.getsize(
                    destination
                ),
            },
        )

        return OperationExecutorPayload(
            export_path=destination,
            metadata={
                "executor": (
                    "export_operation_executor"
                ),
                "source_id": operation.source_id,
                "destination": destination,
                "format": (
                    configuration.format.value
                ),
                "units": configuration.units,
                "tolerance": (
                    configuration.tolerance
                ),
                "angular_tolerance": (
                    configuration.angular_tolerance
                ),
                "file_size": os.path.getsize(
                    destination
                ),
            },
        )

    @staticmethod
    def _normalize_destination(
        destination: str,
        export_format: ExportFormat,
    ) -> str:
        """
        Normalizes the output path and ensures that
        its extension matches the configured format.
        """

        if not isinstance(
            destination,
            str,
        ):
            raise TypeError(
                "Export destination must be a string."
            )

        normalized = destination.strip()

        if not normalized:
            raise ValueError(
                "Export destination cannot be empty."
            )

        expected_extension = (
            ExportOperationExecutor
            ._format_extension(
                export_format
            )
        )

        root, current_extension = (
            os.path.splitext(
                normalized
            )
        )

        if not current_extension:
            normalized = (
                normalized
                + expected_extension
            )

        elif (
            current_extension.lower()
            != expected_extension
        ):
            raise ValueError(
                "Export destination extension "
                f"'{current_extension}' does not match "
                f"format '{export_format.value}'."
            )

        return os.path.abspath(
            normalized
        )

    @staticmethod
    def _prepare_destination(
        destination: str,
        overwrite: bool,
    ) -> None:
        """
        Creates the parent directory and validates
        overwrite behavior.
        """

        if not isinstance(
            overwrite,
            bool,
        ):
            raise TypeError(
                "Export overwrite must be boolean."
            )

        parent_directory = os.path.dirname(
            destination
        )

        if parent_directory:
            os.makedirs(
                parent_directory,
                exist_ok=True,
            )

        if (
            os.path.exists(
                destination
            )
            and not overwrite
        ):
            raise FileExistsError(
                "Export destination already exists: "
                f"{destination}"
            )

    @staticmethod
    def _export_geometry(
        geometry: cq.Shape,
        destination: str,
        export_format: ExportFormat,
        tolerance: float,
        angular_tolerance: float,
    ) -> None:
        """
        Exports CadQuery geometry using the configured
        backend format.
        """

        if export_format == ExportFormat.STEP:
            ExportOperationExecutor._export_step(
                geometry=geometry,
                destination=destination,
            )

            return

        if export_format == ExportFormat.STL:
            ExportOperationExecutor._export_stl(
                geometry=geometry,
                destination=destination,
                tolerance=tolerance,
                angular_tolerance=(
                    angular_tolerance
                ),
            )

            return

        if export_format == ExportFormat.THREE_MF:
            ExportOperationExecutor._export_3mf(
                geometry=geometry,
                destination=destination,
                tolerance=tolerance,
                angular_tolerance=(
                    angular_tolerance
                ),
            )

            return

        raise NotImplementedError(
            "ExportOperationExecutor does not support "
            f"format '{export_format.value}'."
        )

    @staticmethod
    def _export_step(
        geometry: cq.Shape,
        destination: str,
    ) -> None:
        """
        Exports STEP geometry.
        """

        try:
            cq.exporters.export(
                geometry,
                destination,
                exportType="STEP",
            )

        except Exception as error:
            raise RuntimeError(
                "ExportOperationExecutor could not "
                "export STEP geometry."
            ) from error

    @staticmethod
    def _export_stl(
        geometry: cq.Shape,
        destination: str,
        tolerance: float,
        angular_tolerance: float,
    ) -> None:
        """
        Exports STL geometry.
        """

        try:
            cq.exporters.export(
                geometry,
                destination,
                exportType="STL",
                tolerance=tolerance,
                angularTolerance=(
                    angular_tolerance
                ),
            )

        except Exception as error:
            raise RuntimeError(
                "ExportOperationExecutor could not "
                "export STL geometry."
            ) from error

    @staticmethod
    def _export_3mf(
        geometry: cq.Shape,
        destination: str,
        tolerance: float,
        angular_tolerance: float,
    ) -> None:
        """
        Exports 3MF geometry.
        """

        try:
            cq.exporters.export(
                geometry,
                destination,
                exportType="3MF",
                tolerance=tolerance,
                angularTolerance=(
                    angular_tolerance
                ),
            )

        except Exception as error:
            raise RuntimeError(
                "ExportOperationExecutor could not "
                "export 3MF geometry."
            ) from error

    @staticmethod
    def _format_extension(
        export_format: ExportFormat,
    ) -> str:
        """
        Returns the expected file extension.
        """

        if export_format == ExportFormat.STEP:
            return ".step"

        if export_format == ExportFormat.STL:
            return ".stl"

        if export_format == ExportFormat.THREE_MF:
            return ".3mf"

        raise NotImplementedError(
            "Unknown export format: "
            f"{export_format}"
        )