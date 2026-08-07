from __future__ import annotations

import os
from dataclasses import dataclass

from kernel.contracts.boolean_request import (
    BooleanOperation as BooleanMode,
)
from kernel.contracts.config import (
    ExportConfiguration,
    ExportFormat,
)
from kernel.contracts.geometry_definition import GeometryDefinition
from kernel.contracts.geometry_definition_set import GeometryDefinitionSet
from kernel.contracts.geometry_operation_type import GeometryOperationType
from kernel.contracts.geometry_request import GeometryRequest
from kernel.contracts.operations import (
    BooleanOperation,
    ExportOperation,
    GeometryOperation,
)
from kernel.core.execution_context import KernelExecutionContext
from testing import build_dispatcher, build_rectangle_region_set

from features.builders.extrude_operation_builder import ExtrudeOperationBuilder
from features.contracts import BooleanMode as FeatureBooleanMode, FeatureContext
from features.definitions.extrude_feature_definition import ExtrudeFeatureDefinition
from kernel.contracts.model_state import ModelState

from .generator import DecorativePatternGenerator
from .specification import PatternSpecification


@dataclass(frozen=True, slots=True)
class PatternGalleryCase:
    id: str
    name: str
    specification: PatternSpecification


GALLERY_CASES = (
    PatternGalleryCase(
        id="grid",
        name="Grid Pattern Panel",
        specification=PatternSpecification(
            id="gallery_grid",
            pattern="grid",
            width=100.0,
            height=100.0,
            element_width=9.0,
            element_height=9.0,
            spacing_x=5.0,
            spacing_y=5.0,
            rows=6,
            columns=6,
        ),
    ),
    PatternGalleryCase(
        id="brick",
        name="Brick Pattern Panel",
        specification=PatternSpecification(
            id="gallery_brick",
            pattern="brick",
            width=100.0,
            height=100.0,
            element_width=14.0,
            element_height=8.0,
            spacing_x=3.0,
            spacing_y=4.0,
            rows=7,
            columns=6,
        ),
    ),
    PatternGalleryCase(
        id="diamond",
        name="Diamond Pattern Panel",
        specification=PatternSpecification(
            id="gallery_diamond",
            pattern="diamond",
            width=100.0,
            height=100.0,
            element_width=12.0,
            element_height=12.0,
            spacing_x=5.0,
            spacing_y=5.0,
            rows=6,
            columns=6,
        ),
    ),
    PatternGalleryCase(
        id="chevron",
        name="Chevron Pattern Panel",
        specification=PatternSpecification(
            id="gallery_chevron",
            pattern="chevron",
            width=100.0,
            height=100.0,
            element_width=16.0,
            element_height=12.0,
            spacing_x=5.0,
            spacing_y=6.0,
            rows=5,
            columns=5,
        ),
    ),
    PatternGalleryCase(
        id="hex",
        name="Hex Pattern Panel",
        specification=PatternSpecification(
            id="gallery_hex",
            pattern="hex",
            width=100.0,
            height=100.0,
            element_width=13.0,
            element_height=12.0,
            spacing_x=4.0,
            spacing_y=4.0,
            rows=6,
            columns=6,
        ),
    ),
    PatternGalleryCase(
        id="wave_band",
        name="Wave Band Pattern Panel",
        specification=PatternSpecification(
            id="gallery_wave",
            pattern="wave_band",
            width=100.0,
            height=100.0,
            element_width=10.0,
            element_height=13.0,
            spacing_x=5.0,
            spacing_y=14.0,
            rows=4,
            columns=3,
        ),
    ),
)


class PatternGalleryBuilder:
    PANEL_WIDTH = 120.0
    PANEL_HEIGHT = 120.0
    PANEL_THICKNESS = 5.0
    RELIEF_HEIGHT = 2.5
    BORDER = 10.0
    OUTPUT_DIRECTORY = (
        "outputs/product_generators/decorative_patterns"
    )

    def __init__(self) -> None:
        self._generator = DecorativePatternGenerator()

    def run_case(
        self,
        case: PatternGalleryCase,
    ) -> str:
        dispatcher = build_dispatcher(
            include_geometry=True,
            include_boolean=True,
            include_shell=False,
            include_modeling=False,
            include_export=True,
        )

        context = KernelExecutionContext(
            metadata={
                "gallery": "decorative_patterns",
                "pattern": case.id,
            }
        )

        self._build_panel(
            case,
            dispatcher,
            context,
        )

        definitions = self._generator.generate(
            case.specification
        )

        target_id = f"{case.id}:panel"

        for index, definition in enumerate(definitions):
            tool_id = f"{case.id}:relief:{index}"

            operation = self._build_relief_operation(
                case=case,
                definition=definition,
                index=index,
                output_id=tool_id,
            )

            dispatcher.dispatch(
                operation,
                context,
            )

            join_output = (
                f"{case.id}:final"
                if index == len(definitions) - 1
                else f"{case.id}:joined:{index}"
            )

            boolean = BooleanOperation(
                id=f"{case.id}:join:{index}",
                name=f"{case.name} Join {index}",
                mode=BooleanMode.UNION,
                target_id=target_id,
                tool_id=tool_id,
                output_id=join_output,
                tolerance=0.01,
                metadata={
                    "pattern": case.id,
                    "element_index": index,
                },
            )
            boolean.validate()

            dispatcher.dispatch(
                boolean,
                context,
            )

            target_id = join_output

        export_path = os.path.join(
            self.OUTPUT_DIRECTORY,
            f"{case.id}.step",
        )

        export = ExportOperation(
            id=f"{case.id}:export",
            name=f"Export {case.name}",
            source_id=target_id,
            configuration=ExportConfiguration(
                enabled=True,
                format=ExportFormat.STEP,
                destination=export_path,
                tolerance=0.01,
                angular_tolerance=0.1,
                units="mm",
                metadata={
                    "gallery": "decorative_patterns",
                    "pattern": case.id,
                },
            ),
            overwrite=True,
        )
        export.validate()

        payload = dispatcher.dispatch(
            export,
            context,
        )

        if payload.export_path is None:
            raise RuntimeError(
                f"{case.id}: export returned no path."
            )

        if not os.path.isfile(payload.export_path):
            raise RuntimeError(
                f"{case.id}: STEP file was not created."
            )

        final_solid = context.solids.get(
            target_id
        )
        final_solid.validate()

        if final_solid.volume is None or final_solid.volume <= 0:
            raise RuntimeError(
                f"{case.id}: invalid final panel volume."
            )

        return payload.export_path

    def _build_panel(
        self,
        case,
        dispatcher,
        context,
    ) -> None:
        region_set_id = f"{case.id}:panel-regions"

        regions = build_rectangle_region_set(
            region_set_id=region_set_id,
            width=self.PANEL_WIDTH,
            height=self.PANEL_HEIGHT,
        )

        feature_context = FeatureContext(
            model=ModelState(),
        )
        feature_context.register_regions(
            region_set_id,
            regions,
        )

        feature = ExtrudeFeatureDefinition(
            id=f"{case.id}:panel-feature",
            name=f"{case.name} Base",
            region_set_id=region_set_id,
            region_id=regions.regions[0].id,
            output_id=f"{case.id}:panel",
            distance=self.PANEL_THICKNESS,
            direction=(0.0, 0.0, 1.0),
            mode=FeatureBooleanMode.NEW_BODY,
            target_body_id=None,
            symmetric=False,
            draft_angle=0.0,
            merge=True,
            metadata={
                "gallery": "decorative_patterns",
                "pattern": case.id,
            },
        )

        plan = ExtrudeOperationBuilder().build(
            feature,
            feature_context,
        )

        for operation in plan.operations:
            dispatcher.dispatch(
                operation,
                context,
            )

    def _build_relief_operation(
        self,
        *,
        case: PatternGalleryCase,
        definition: GeometryDefinition,
        index: int,
        output_id: str,
    ) -> GeometryOperation:
        shifted_definition = self._shift_definition(
            definition,
            dx=self.BORDER,
            dy=self.BORDER,
            index=index,
        )

        geometry = GeometryDefinitionSet(
            id=f"{case.id}:relief-set:{index}",
            definitions=(shifted_definition,),
            source="decorative_patterns_gallery",
        )
        geometry.validate()

        request = GeometryRequest(
            id=f"{case.id}:relief-request:{index}",
            geometry=geometry,
            operation=GeometryOperationType.EXTRUDE,
            parameters={
                "distance": self.PANEL_THICKNESS + self.RELIEF_HEIGHT,
                "direction": (0.0, 0.0, 1.0),
                "symmetric": False,
                "draft_angle": 0.0,
            },
            output_id=output_id,
            metadata={
                "gallery": "decorative_patterns",
                "pattern": case.id,
                "element_index": index,
            },
        )
        request.validate()

        operation = GeometryOperation(
            id=f"{case.id}:relief-operation:{index}",
            name=f"{case.name} Relief {index}",
            request=request,
            output_id=output_id,
        )
        operation.validate()
        return operation

    @staticmethod
    def _shift_definition(
        definition: GeometryDefinition,
        *,
        dx: float,
        dy: float,
        index: int,
    ) -> GeometryDefinition:
        definition.validate()

        points = tuple(
            (
                float(x) + float(dx),
                float(y) + float(dy),
            )
            for x, y in definition.outer_contour.points
        )

        contour = definition.outer_contour.__class__(
            id=f"{definition.outer_contour.id}:gallery:{index}",
            points=points,
            closed=True,
            source="decorative_patterns_gallery",
            metadata=dict(definition.outer_contour.metadata),
        )
        contour.validate()

        shifted = GeometryDefinition(
            id=f"{definition.id}:gallery:{index}",
            outer_contour=contour,
            source="decorative_patterns_gallery",
            metadata=dict(definition.metadata),
        )
        shifted.validate()
        return shifted
