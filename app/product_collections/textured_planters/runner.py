from __future__ import annotations

import os
from dataclasses import dataclass

from kernel.core.execution_context import KernelExecutionContext
from testing import build_dispatcher

from product_collections.basic_planters.geometry_inspector import (
    BasicPlanterGeometryInspector,
)

from .builder import TexturedPlanterCollectionBuilder
from .specification import TexturedPlanterSpecification


@dataclass(slots=True)
class TexturedPlanterRunResult:
    specification: TexturedPlanterSpecification
    context: KernelExecutionContext
    top_face_index: int
    texture_count: int
    export_path: str

    @property
    def final_body_id(self) -> str:
        return f"{self.specification.id}:body"


class TexturedPlanterCollectionRunner:
    def __init__(self) -> None:
        self._builder = TexturedPlanterCollectionBuilder()
        self._inspector = BasicPlanterGeometryInspector()

    def run(
        self,
        spec: TexturedPlanterSpecification,
    ) -> TexturedPlanterRunResult:
        spec.validate()

        dispatcher = build_dispatcher(
            include_geometry=True,
            include_boolean=True,
            include_shell=True,
            include_modeling=True,
            include_export=True,
        )

        context = KernelExecutionContext(
            metadata={
                "collection": "textured_planters",
                "product_id": spec.id,
            }
        )

        dispatcher.dispatch(
            self._builder.build_base_geometry(spec),
            context,
        )

        source_id = self._builder.base_source_id(spec)

        if not context.solids.contains(source_id):
            raise RuntimeError(
                f"{spec.id}: base source missing."
            )

        source = context.solids.get(source_id)

        top_face_index = (
            self._inspector.top_face_index(
                source
            )
        )

        dispatcher.dispatch(
            self._builder.build_base_shell(
                spec,
                top_face_index=top_face_index,
            ),
            context,
        )

        current_target = (
            self._builder.base_final_id(spec)
        )

        if not context.solids.contains(
            current_target
        ):
            raise RuntimeError(
                f"{spec.id}: base shell missing."
            )

        texture_operations = (
            self._builder
            .build_texture_geometry_operations(
                spec
            )
        )

        if not texture_operations:
            raise RuntimeError(
                f"{spec.id}: no texture operations."
            )

        for index, texture_operation in enumerate(
            texture_operations
        ):
            dispatcher.dispatch(
                texture_operation,
                context,
            )

            raw_tool_id = texture_operation.output_id

            if not context.solids.contains(
                raw_tool_id
            ):
                raise RuntimeError(
                    f"{spec.id}: raw texture tool "
                    f"{index} missing."
                )

            move_operation = (
                self._builder
                .build_texture_move_operation(
                    spec,
                    index=index,
                )
            )

            dispatcher.dispatch(
                move_operation,
                context,
            )

            tool_id = move_operation.output_id

            if not context.solids.contains(
                tool_id
            ):
                raise RuntimeError(
                    f"{spec.id}: moved texture tool "
                    f"{index} missing."
                )

            is_last = (
                index
                == len(texture_operations) - 1
            )

            join_operation = (
                self._builder
                .build_texture_join_operation(
                    spec,
                    index=index,
                    target_id=current_target,
                    is_last=is_last,
                )
            )

            dispatcher.dispatch(
                join_operation,
                context,
            )

            current_target = (
                join_operation.output_id
            )

            if not context.solids.contains(
                current_target
            ):
                raise RuntimeError(
                    f"{spec.id}: texture join "
                    f"{index} failed."
                )

        payload = dispatcher.dispatch(
            self._builder.build_export(spec),
            context,
        )

        if (
            payload.export_path is None
            or not os.path.isfile(
                payload.export_path
            )
        ):
            raise RuntimeError(
                f"{spec.id}: STEP export failed."
            )

        context.validate()

        return TexturedPlanterRunResult(
            specification=spec,
            context=context,
            top_face_index=top_face_index,
            texture_count=len(
                texture_operations
            ),
            export_path=payload.export_path,
        )
