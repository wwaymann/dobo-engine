"""
DOBO CAD Kernel

Export Operation Contract

Describes how a named Solid result must be exported.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from kernel.contracts.config.export_configuration import (
    ExportConfiguration,
)

from .base_operation import (
    BaseOperation,
    OperationType,
)


@dataclass(frozen=True, slots=True)
class ExportOperation(BaseOperation):
    """
    Exports one previously generated Solid.

    source_id references the Solid registry entry
    produced by GeometryOperation or BooleanOperation.
    """

    source_id: str = ""

    configuration: ExportConfiguration = field(
        default_factory=ExportConfiguration
    )

    overwrite: bool = False

    @property
    def operation_type(self) -> OperationType:
        return OperationType.EXPORT

    def validate(self) -> None:
        """
        Validates the Export operation.
        """

        BaseOperation.validate(self)

        if not isinstance(
            self.source_id,
            str,
        ) or not self.source_id.strip():
            raise ValueError(
                "ExportOperation source_id "
                "cannot be empty."
            )

        if not isinstance(
            self.configuration,
            ExportConfiguration,
        ):
            raise TypeError(
                "ExportOperation configuration must be "
                "an ExportConfiguration."
            )

        if not self.configuration.enabled:
            raise ValueError(
                "ExportOperation requires an enabled "
                "ExportConfiguration."
            )

        self.configuration.validate()

        if not isinstance(
            self.overwrite,
            bool,
        ):
            raise TypeError(
                "ExportOperation overwrite "
                "must be boolean."
            )

    @property
    def destination(self) -> str:
        """
        Returns the configured export destination.
        """

        return self.configuration.destination

    @property
    def format_name(self) -> str:
        """
        Returns the configured export format.
        """

        return self.configuration.format.value