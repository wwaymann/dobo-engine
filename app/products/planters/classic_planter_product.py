"""
DOBO Products

Classic Planter Product
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from features.builders.extrude_operation_builder import ExtrudeOperationBuilder
from features.builders.shell_operation_builder import ShellOperationBuilder
from features.contracts import BooleanMode, FeatureContext
from features.definitions.extrude_feature_definition import ExtrudeFeatureDefinition
from features.definitions.shell_feature_definition import ShellFeatureDefinition
from kernel.contracts.config import ExportConfiguration, ExportFormat
from kernel.contracts.model_state import ModelState
from kernel.contracts.operations import ExportOperation
from kernel.core.kernel_model import KernelModel
from testing import build_rectangle_region_set


@dataclass(frozen=True, slots=True)
class ClassicPlanterSpecification:
    """Parametric dimensions in millimeters."""

    width: float = 120.0
    depth: float = 120.0
    height: float = 140.0
    wall_thickness: float = 4.0
    shell_tolerance: float = 0.01
    top_face_index: int = 5
    output_directory: str = "outputs/products/planters"
    output_filename: str = "dobo_classic_planter_v1.step"

    def validate(self) -> None:
        for name, value in (
            ("width", self.width),
            ("depth", self.depth),
            ("height", self.height),
            ("wall_thickness", self.wall_thickness),
            ("shell_tolerance", self.shell_tolerance),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be numeric.")

        if self.width <= 0 or self.depth <= 0 or self.height <= 0:
            raise ValueError("Planter dimensions must be greater than zero.")

        if self.wall_thickness <= 0:
            raise ValueError("wall_thickness must be greater than zero.")

        if self.wall_thickness * 2 >= min(self.width, self.depth):
            raise ValueError("wall_thickness is too large for the planter.")

        if self.shell_tolerance <= 0:
            raise ValueError("shell_tolerance must be greater than zero.")

        if isinstance(self.top_face_index, bool) or not isinstance(
            self.top_face_index,
            int,
        ):
            raise TypeError("top_face_index must be an integer.")

        if self.top_face_index < 0:
            raise ValueError("top_face_index cannot be negative.")

        if not isinstance(self.output_directory, str) or not self.output_directory:
            raise ValueError("output_directory cannot be empty.")

        if not isinstance(self.output_filename, str) or not self.output_filename:
            raise ValueError("output_filename cannot be empty.")

    @property
    def export_path(self) -> str:
        return os.path.join(self.output_directory, self.output_filename)


class ClassicPlanterProduct:
    """Builds DOBO Classic Planter v1."""

    REGION_SET_ID = "classic_planter_regions"
    SOURCE_BODY_ID = "classic_planter_source"
    FINAL_BODY_ID = "classic_planter_body"

    def __init__(
        self,
        specification: ClassicPlanterSpecification | None = None,
    ) -> None:
        self.specification = specification or ClassicPlanterSpecification()
        self.specification.validate()

    def build_context(self) -> FeatureContext:
        regions = build_rectangle_region_set(
            region_set_id=self.REGION_SET_ID,
            width=float(self.specification.width),
            height=float(self.specification.depth),
        )

        context = FeatureContext(model=ModelState())
        context.register_regions(self.REGION_SET_ID, regions)
        context.validate()
        return context

    def build_model(self) -> KernelModel:
        context = self.build_context()
        regions = context.regions[self.REGION_SET_ID]

        base_feature = ExtrudeFeatureDefinition(
            id="classic_planter_base_feature",
            name="Classic Planter Base",
            region_set_id=self.REGION_SET_ID,
            region_id=regions.regions[0].id,
            output_id=self.SOURCE_BODY_ID,
            distance=float(self.specification.height),
            direction=(0.0, 0.0, 1.0),
            mode=BooleanMode.NEW_BODY,
            target_body_id=None,
            symmetric=False,
            draft_angle=0.0,
            merge=True,
            metadata={"product": "classic_planter_v1", "stage": "base"},
        )

        shell_feature = ShellFeatureDefinition(
            id="classic_planter_shell_feature",
            name="Classic Planter Shell",
            source_body_id=self.SOURCE_BODY_ID,
            output_id=self.FINAL_BODY_ID,
            thickness=-float(self.specification.wall_thickness),
            tolerance=float(self.specification.shell_tolerance),
            remove_face_indices=(self.specification.top_face_index,),
            metadata={"product": "classic_planter_v1", "stage": "shell"},
        )

        base_plan = ExtrudeOperationBuilder().build(base_feature, context)
        shell_plan = ShellOperationBuilder().build(shell_feature, context)

        export_operation = ExportOperation(
            id="classic_planter_export_operation",
            name="Export Classic Planter STEP",
            source_id=self.FINAL_BODY_ID,
            configuration=ExportConfiguration(
                enabled=True,
                format=ExportFormat.STEP,
                destination=self.specification.export_path,
                tolerance=0.01,
                angular_tolerance=0.1,
                units="mm",
                metadata={"product": "classic_planter_v1"},
            ),
            overwrite=True,
            metadata={"product": "classic_planter_v1", "stage": "export"},
        )

        model = KernelModel(
            name="DOBO Classic Planter v1",
            metadata={
                "product": "classic_planter_v1",
                "category": "planter",
                "width": self.specification.width,
                "depth": self.specification.depth,
                "height": self.specification.height,
                "wall_thickness": self.specification.wall_thickness,
            },
        )

        for operation in (
            *base_plan.operations,
            *shell_plan.operations,
            export_operation,
        ):
            model.add_operation(operation)

        model.validate()
        return model
