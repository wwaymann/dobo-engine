from __future__ import annotations

import os

from kernel.contracts.boolean_request import (
    BooleanOperation as BooleanMode,
)
from kernel.contracts.config import (
    ExportConfiguration,
    ExportFormat,
)
from kernel.contracts.geometry_operation_type import GeometryOperationType
from kernel.contracts.geometry_request import GeometryRequest
from kernel.contracts.operations import (
    BooleanOperation,
    ExportOperation,
    GeometryOperation,
)

from product_collections.basic_planters.builder import (
    BasicPlanterCollectionBuilder,
)
from product_collections.basic_planters.specification import (
    BasicPlanterSpecification,
)

from .specification import TexturedPlanterSpecification
from .texture_generator import TexturedPlanterTextureGenerator


class TexturedPlanterCollectionBuilder:
    OUTPUT_DIRECTORY = "outputs/product_collections/textured_planters"

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

    def build_texture_geometry(
        self,
        spec: TexturedPlanterSpecification,
    ) -> GeometryOperation:
        geometry = self._textures.generate(
            product_id=spec.id,
            width=spec.width,
            depth=spec.depth,
            texture=spec.texture,
            count=spec.texture_count,
            rib_width=spec.texture_width,
            rib_depth=spec.texture_depth,
        )

        output_id = f"{spec.id}:texture-tool"

        request = GeometryRequest(
            id=f"{spec.id}:texture-request",
            geometry=geometry,
            operation=GeometryOperationType.EXTRUDE,
            parameters={
                "distance": float(spec.height),
                "direction": (0.0, 0.0, 1.0),
                "symmetric": False,
                "draft_angle": 0.0,
            },
            output_id=output_id,
            metadata={
                "collection": "textured_planters",
                "product_id": spec.id,
                "texture": spec.texture,
            },
        )
        request.validate()

        operation = GeometryOperation(
            id=f"{spec.id}:texture-geometry-operation",
            name=f"{spec.name} Texture",
            request=request,
            output_id=output_id,
            tags=("collection", "textured_planters", spec.texture),
        )
        operation.validate()
        return operation

    def build_texture_join(
        self,
        spec: TexturedPlanterSpecification,
    ) -> BooleanOperation:
        operation = BooleanOperation(
            id=f"{spec.id}:texture-join",
            name=f"{spec.name} Texture Join",
            mode=BooleanMode.UNION,
            target_id=self.base_final_id(spec),
            tool_id=f"{spec.id}:texture-tool",
            output_id=self.final_body_id(spec),
            tolerance=0.01,
            metadata={
                "collection": "textured_planters",
                "product_id": spec.id,
                "texture": spec.texture,
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

    def base_source_id(self, spec: TexturedPlanterSpecification) -> str:
        return f"{spec.id}:base:source"

    def base_final_id(self, spec: TexturedPlanterSpecification) -> str:
        return f"{spec.id}:base:body"

    def final_body_id(self, spec: TexturedPlanterSpecification) -> str:
        return f"{spec.id}:body"
