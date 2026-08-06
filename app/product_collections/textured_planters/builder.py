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

from .specification import TexturedPlanterSpecification
from .texture_generator import TexturedPlanterTextureGenerator


TEXTURE_VERTICAL_MARGIN = 1.0


class TexturedPlanterCollectionBuilder:
    OUTPUT_DIRECTORY = (
        "outputs/product_collections/textured_planters"
    )

    def __init__(self) -> None:
        self._base = BasicPlanterCollectionBuilder()
        self._textures = TexturedPlanterTextureGenerator()

    def base_specification(
        self,
        spec: TexturedPlanterSpecification,
    ) -> BasicPlanterSpecification:
        return BasicPlanterSpecification(
            id=f"{spec.id}:base",
            name=f"{spec.name} Base",
            profile="rectangle",
            width=spec.width,
            depth=spec.depth,
            height=spec.height,
            wall_thickness=spec.wall_thickness,
        )

    def build_base_geometry(
        self,
        spec: TexturedPlanterSpecification,
    ) -> GeometryOperation:
        return self._base.build_geometry_operation(
            self.base_specification(spec)
        )

    def build_base_shell(
        self,
        spec: TexturedPlanterSpecification,
        *,
        top_face_index: int,
    ):
        return self._base.build_shell_operation(
            self.base_specification(spec),
            top_face_index=top_face_index,
        )

    def build_texture_geometry_operations(
        self,
        spec: TexturedPlanterSpecification,
    ) -> tuple[GeometryOperation, ...]:
        definitions = (
            self._textures.generate_definitions(
                product_id=spec.id,
                width=spec.width,
                depth=spec.depth,
                texture=spec.texture,
                count=spec.texture_count,
                rib_width=spec.texture_width,
                rib_depth=spec.texture_depth,
            )
        )

        extrusion_height = (
            float(spec.height)
            - 2.0 * TEXTURE_VERTICAL_MARGIN
        )

        if extrusion_height <= 0.0:
            raise ValueError(
                "Texture extrusion height must be positive."
            )

        operations: list[GeometryOperation] = []

        for index, definition in enumerate(
            definitions
        ):
            geometry = GeometryDefinitionSet(
                id=f"{spec.id}:texture-set:{index}",
                definitions=(definition,),
                source="textured_planters",
                metadata={
                    "texture": spec.texture,
                    "texture_index": index,
                },
            )
            geometry.validate()

            output_id = (
                f"{spec.id}:texture-tool-raw:{index}"
            )

            request = GeometryRequest(
                id=f"{spec.id}:texture-request:{index}",
                geometry=geometry,
                operation=GeometryOperationType.EXTRUDE,
                parameters={
                    "distance": extrusion_height,
                    "direction": (0.0, 0.0, 1.0),
                    "symmetric": False,
                    "draft_angle": 0.0,
                },
                output_id=output_id,
                metadata={
                    "collection": "textured_planters",
                    "product_id": spec.id,
                    "texture": spec.texture,
                    "texture_index": index,
                    "vertical_margin": TEXTURE_VERTICAL_MARGIN,
                },
            )
            request.validate()

            operation = GeometryOperation(
                id=(
                    f"{spec.id}:"
                    f"texture-geometry-operation:{index}"
                ),
                name=(
                    f"{spec.name} Texture {index}"
                ),
                request=request,
                output_id=output_id,
                tags=(
                    "collection",
                    "textured_planters",
                    spec.texture,
                ),
            )
            operation.validate()
            operations.append(operation)

        return tuple(operations)

    def build_texture_move_operation(
        self,
        spec: TexturedPlanterSpecification,
        *,
        index: int,
    ) -> ModelingOperation:
        operation = ModelingOperation(
            id=f"{spec.id}:texture-move:{index}",
            name=f"{spec.name} Texture Move {index}",
            source_id=f"{spec.id}:texture-tool-raw:{index}",
            output_id=f"{spec.id}:texture-tool:{index}",
            tool=ModelingTool.MOVE,
            parameters={
                "vector": (
                    0.0,
                    0.0,
                    TEXTURE_VERTICAL_MARGIN,
                ),
            },
            metadata={
                "collection": "textured_planters",
                "product_id": spec.id,
                "texture": spec.texture,
                "texture_index": index,
            },
        )
        operation.validate()
        return operation

    def build_texture_join_operation(
        self,
        spec: TexturedPlanterSpecification,
        *,
        index: int,
        target_id: str,
        is_last: bool,
    ) -> BooleanOperation:
        tool_id = (
            f"{spec.id}:texture-tool:{index}"
        )

        output_id = (
            self.final_body_id(spec)
            if is_last
            else f"{spec.id}:textured:{index}"
        )

        operation = BooleanOperation(
            id=f"{spec.id}:texture-join:{index}",
            name=f"{spec.name} Texture Join {index}",
            mode=BooleanMode.UNION,
            target_id=target_id,
            tool_id=tool_id,
            output_id=output_id,
            tolerance=0.01,
            metadata={
                "collection": "textured_planters",
                "product_id": spec.id,
                "texture": spec.texture,
                "texture_index": index,
            },
        )
        operation.validate()
        return operation

    def build_export(
        self,
        spec: TexturedPlanterSpecification,
    ) -> ExportOperation:
        destination = os.path.join(
            self.OUTPUT_DIRECTORY,
            spec.resolved_export_filename,
        )

        operation = ExportOperation(
            id=f"{spec.id}:export",
            name=f"Export {spec.name}",
            source_id=self.final_body_id(spec),
            configuration=ExportConfiguration(
                enabled=True,
                format=ExportFormat.STEP,
                destination=destination,
                tolerance=0.01,
                angular_tolerance=0.1,
                units="mm",
                metadata={
                    "collection": "textured_planters",
                    "product_id": spec.id,
                },
            ),
            overwrite=True,
        )
        operation.validate()
        return operation

    def base_source_id(
        self,
        spec: TexturedPlanterSpecification,
    ) -> str:
        return f"{spec.id}:base:source"

    def base_final_id(
        self,
        spec: TexturedPlanterSpecification,
    ) -> str:
        return f"{spec.id}:base:body"

    def final_body_id(
        self,
        spec: TexturedPlanterSpecification,
    ) -> str:
        return f"{spec.id}:body"
