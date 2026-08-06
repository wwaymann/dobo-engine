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
            include_modeling=False,
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
            raise RuntimeError(f"{spec.id}: base source missing.")

        source = context.solids.get(source_id)
        top_face_index = self._inspector.top_face_index(source)

        dispatcher.dispatch(
            self._builder.build_base_shell(
                spec,
                top_face_index=top_face_index,
            ),
            context,
        )

        dispatcher.dispatch(
            self._builder.build_texture_geometry(spec),
            context,
        )

        dispatcher.dispatch(
            self._builder.build_texture_join(spec),
            context,
        )

        final_id = self._builder.final_body_id(spec)
        if not context.solids.contains(final_id):
            raise RuntimeError(f"{spec.id}: final textured body missing.")

        payload = dispatcher.dispatch(
            self._builder.build_export(spec),
            context,
        )

        if payload.export_path is None or not os.path.isfile(
            payload.export_path
        ):
            raise RuntimeError(f"{spec.id}: STEP export failed.")

        context.validate()

        return TexturedPlanterRunResult(
            specification=spec,
            context=context,
            top_face_index=top_face_index,
            export_path=payload.export_path,
        )
