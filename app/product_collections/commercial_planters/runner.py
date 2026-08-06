from __future__ import annotations

import os
from dataclasses import dataclass

from kernel.core.execution_context import KernelExecutionContext
from testing import build_dispatcher

from product_collections.basic_planters.geometry_inspector import (
    BasicPlanterGeometryInspector,
)

from .builder import CommercialPlanterCollectionBuilder
from .specification import CommercialPlanterSpecification


@dataclass(slots=True)
class CommercialPlanterRunResult:
    specification: CommercialPlanterSpecification
    context: KernelExecutionContext
    decoration_count: int
    export_path: str

    @property
    def final_body_id(self) -> str:
        return f"{self.specification.id}:body"


class CommercialPlanterCollectionRunner:
    def __init__(self) -> None:
        self._builder = CommercialPlanterCollectionBuilder()
        self._inspector = BasicPlanterGeometryInspector()

    def run(
        self,
        specification: CommercialPlanterSpecification,
    ) -> CommercialPlanterRunResult:
        specification.validate()

        dispatcher = build_dispatcher(
            include_geometry=True,
            include_boolean=True,
            include_shell=True,
            include_modeling=True,
            include_export=True,
        )

        context = KernelExecutionContext(
            metadata={
                "collection": "commercial_planters",
                "product_id": specification.id,
            }
        )

        dispatcher.dispatch(
            self._builder.build_base_geometry(
                specification
            ),
            context,
        )

        source_id = self._builder.base_source_id(
            specification
        )

        source = context.solids.get(
            source_id
        )

        top_face_index = (
            self._inspector.top_face_index(
                source
            )
        )

        dispatcher.dispatch(
            self._builder.build_base_shell(
                specification,
                top_face_index=top_face_index,
            ),
            context,
        )

        current_target = self._builder.base_body_id(
            specification
        )

        decoration_operations = (
            self._builder
            .build_decoration_geometry_operations(
                specification
            )
        )

        for index, geometry_operation in enumerate(
            decoration_operations
        ):
            dispatcher.dispatch(
                geometry_operation,
                context,
            )

            rotate_operation = (
                self._builder.build_rotate_operation(
                    specification,
                    index=index,
                )
            )

            dispatcher.dispatch(
                rotate_operation,
                context,
            )

            move_operation = (
                self._builder.build_move_operation(
                    specification,
                    index=index,
                )
            )

            dispatcher.dispatch(
                move_operation,
                context,
            )

            is_last = (
                index
                == len(decoration_operations) - 1
            )

            boolean_operation = (
                self._builder.build_boolean_operation(
                    specification,
                    index=index,
                    target_id=current_target,
                    is_last=is_last,
                )
            )

            dispatcher.dispatch(
                boolean_operation,
                context,
            )

            current_target = (
                boolean_operation.output_id
            )

        final_id = self._builder.final_body_id(
            specification
        )

        if not context.solids.contains(
            final_id
        ):
            raise RuntimeError(
                f"{specification.id}: final body missing."
            )

        final_solid = context.solids.get(
            final_id
        )
        final_solid.validate()

        if (
            final_solid.volume is None
            or final_solid.volume <= 0
        ):
            raise RuntimeError(
                f"{specification.id}: invalid volume."
            )

        payload = dispatcher.dispatch(
            self._builder.build_export(
                specification
            ),
            context,
        )

        if (
            payload.export_path is None
            or not os.path.isfile(
                payload.export_path
            )
        ):
            raise RuntimeError(
                f"{specification.id}: STEP export failed."
            )

        context.validate()

        return CommercialPlanterRunResult(
            specification=specification,
            context=context,
            decoration_count=len(
                decoration_operations
            ),
            export_path=payload.export_path,
        )
