from __future__ import annotations

import os

from kernel.contracts.boolean_request import (
    BooleanOperation as BooleanMode,
)
from kernel.contracts.config import (
    ExportConfiguration,
    ExportFormat,
)
from kernel.contracts.geometry_definition_set import (
    GeometryDefinitionSet,
)
from kernel.contracts.geometry_operation_type import (
    GeometryOperationType,
)
from kernel.contracts.geometry_request import GeometryRequest
from kernel.contracts.operations import (
    BooleanOperation,
    ExportOperation,
    GeometryOperation,
    ModelingOperation,
    ModelingTool,
)

from product_collections.basic_planters.builder import (
    BasicPlanterCollectionBuilder,
)
from product_collections.basic_planters.specification import (
    BasicPlanterSpecification,
)

from .decoration_generator import CommercialDecorationGenerator
from .specification import CommercialPlanterSpecification


class CommercialPlanterCollectionBuilder:
    OUTPUT_DIRECTORY = (
        "outputs/product_collections/commercial_planters"
    )

    def __init__(self) -> None:
        self._base = BasicPlanterCollectionBuilder()
        self._decorations = CommercialDecorationGenerator()

    def base_specification(
        self,
        specification: CommercialPlanterSpecification,
    ) -> BasicPlanterSpecification:
        return BasicPlanterSpecification(
            id=f"{specification.id}:base",
            name=f"{specification.name} Base",
            profile="rectangle",
            width=specification.width,
            depth=specification.depth,
            height=specification.height,
            wall_thickness=specification.wall_thickness,
        )

    def build_base_geometry(
        self,
        specification: CommercialPlanterSpecification,
    ) -> GeometryOperation:
        return self._base.build_geometry_operation(
            self.base_specification(specification)
        )

    def build_base_shell(
        self,
        specification: CommercialPlanterSpecification,
        *,
        top_face_index: int,
    ):
        return self._base.build_shell_operation(
            self.base_specification(specification),
            top_face_index=top_face_index,
        )

    def build_decoration_geometry_operations(
        self,
        specification: CommercialPlanterSpecification,
    ) -> tuple[GeometryOperation, ...]:
        definitions = self._decorations.generate(
            specification
        )

        operations: list[GeometryOperation] = []

        for index, definition in enumerate(definitions):
            geometry = GeometryDefinitionSet(
                id=(
                    f"{specification.id}:"
                    f"decoration-set:{index}"
                ),
                definitions=(definition,),
                source="commercial_planters",
            )
            geometry.validate()

            raw_id = (
                f"{specification.id}:"
                f"decoration-raw:{index}"
            )

            request = GeometryRequest(
                id=(
                    f"{specification.id}:"
                    f"decoration-request:{index}"
                ),
                geometry=geometry,
                operation=GeometryOperationType.EXTRUDE,
                parameters={
                    "distance": float(
                        specification.decoration_depth
                    ),
                    "direction": (0.0, 0.0, 1.0),
                    "symmetric": False,
                    "draft_angle": 0.0,
                },
                output_id=raw_id,
                metadata={
                    "collection": "commercial_planters",
                    "product_id": specification.id,
                    "decoration": specification.decoration,
                    "mode": specification.mode,
                    "index": index,
                },
            )
            request.validate()

            operation = GeometryOperation(
                id=(
                    f"{specification.id}:"
                    f"decoration-geometry:{index}"
                ),
                name=(
                    f"{specification.name} "
                    f"Decoration {index}"
                ),
                request=request,
                output_id=raw_id,
            )
            operation.validate()
            operations.append(operation)

        return tuple(operations)

    def build_rotate_operation(
        self,
        specification: CommercialPlanterSpecification,
        *,
        index: int,
    ) -> ModelingOperation:
        operation = ModelingOperation(
            id=(
                f"{specification.id}:"
                f"decoration-rotate:{index}"
            ),
            name=(
                f"{specification.name} "
                f"Decoration Rotate {index}"
            ),
            source_id=(
                f"{specification.id}:"
                f"decoration-raw:{index}"
            ),
            output_id=(
                f"{specification.id}:"
                f"decoration-rotated:{index}"
            ),
            tool=ModelingTool.ROTATE,
            parameters={
                "axis_origin": (0.0, 0.0, 0.0),
                "axis_direction": (1.0, 0.0, 0.0),
                "angle": 90.0,
            },
        )
        operation.validate()
        return operation

    def build_move_operation(
        self,
        specification: CommercialPlanterSpecification,
        *,
        index: int,
    ) -> ModelingOperation:
        # After +90° X rotation the extrusion occupies negative Y.
        # Move into the front wall so the Boolean has real overlap.
        y_overlap = (
            1.0
            if specification.mode == "emboss"
            else min(
                2.0,
                float(specification.wall_thickness) * 0.5,
            )
        )

        operation = ModelingOperation(
            id=(
                f"{specification.id}:"
                f"decoration-move:{index}"
            ),
            name=(
                f"{specification.name} "
                f"Decoration Move {index}"
            ),
            source_id=(
                f"{specification.id}:"
                f"decoration-rotated:{index}"
            ),
            output_id=(
                f"{specification.id}:"
                f"decoration-tool:{index}"
            ),
            tool=ModelingTool.MOVE,
            parameters={
                "vector": (
                    0.0,
                    y_overlap,
                    0.0,
                ),
            },
        )
        operation.validate()
        return operation

    def build_boolean_operation(
        self,
        specification: CommercialPlanterSpecification,
        *,
        index: int,
        target_id: str,
        is_last: bool,
    ) -> BooleanOperation:
        mode = (
            BooleanMode.UNION
            if specification.mode == "emboss"
            else BooleanMode.CUT
        )

        output_id = (
            self.final_body_id(specification)
            if is_last
            else (
                f"{specification.id}:"
                f"decorated:{index}"
            )
        )

        operation = BooleanOperation(
            id=(
                f"{specification.id}:"
                f"decoration-boolean:{index}"
            ),
            name=(
                f"{specification.name} "
                f"Decoration Boolean {index}"
            ),
            mode=mode,
            target_id=target_id,
            tool_id=(
                f"{specification.id}:"
                f"decoration-tool:{index}"
            ),
            output_id=output_id,
            tolerance=0.01,
            metadata={
                "collection": "commercial_planters",
                "product_id": specification.id,
                "mode": specification.mode,
                "index": index,
            },
        )
        operation.validate()
        return operation

    def build_export(
        self,
        specification: CommercialPlanterSpecification,
    ) -> ExportOperation:
        destination = os.path.join(
            self.OUTPUT_DIRECTORY,
            specification.resolved_export_filename,
        )

        operation = ExportOperation(
            id=f"{specification.id}:export",
            name=f"Export {specification.name}",
            source_id=self.final_body_id(specification),
            configuration=ExportConfiguration(
                enabled=True,
                format=ExportFormat.STEP,
                destination=destination,
                tolerance=0.01,
                angular_tolerance=0.1,
                units="mm",
                metadata={
                    "collection": "commercial_planters",
                    "product_id": specification.id,
                },
            ),
            overwrite=True,
        )
        operation.validate()
        return operation

    @staticmethod
    def base_source_id(
        specification: CommercialPlanterSpecification,
    ) -> str:
        return f"{specification.id}:base:source"

    @staticmethod
    def base_body_id(
        specification: CommercialPlanterSpecification,
    ) -> str:
        return f"{specification.id}:base:body"

    @staticmethod
    def final_body_id(
        specification: CommercialPlanterSpecification,
    ) -> str:
        return f"{specification.id}:body"
