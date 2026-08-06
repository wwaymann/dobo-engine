from __future__ import annotations

import os
from dataclasses import dataclass

from kernel.core.execution_context import KernelExecutionContext
from testing import build_dispatcher

from .builder import OrganicPlanterCollectionBuilder
from .specification import OrganicPlanterSpecification


@dataclass(slots=True)
class OrganicPlanterRunResult:
    specification: OrganicPlanterSpecification
    context: KernelExecutionContext
    export_path: str

    @property
    def final_body_id(self) -> str:
        return f"{self.specification.id}:body"


class OrganicPlanterCollectionRunner:
    """
    Builds an organic planter using:

    outer loft -> inner loft -> boolean cut -> export
    """

    def __init__(self) -> None:
        self._builder = OrganicPlanterCollectionBuilder()

    def run(
        self,
        specification: OrganicPlanterSpecification,
    ) -> OrganicPlanterRunResult:
        specification.validate()

        dispatcher = build_dispatcher(
            include_geometry=True,
            include_boolean=True,
            include_shell=False,
            include_modeling=False,
            include_export=True,
        )

        context = KernelExecutionContext(
            metadata={
                "collection": "organic_planters",
                "product_id": specification.id,
            }
        )

        outer_operation = (
            self._builder
            .build_outer_geometry_operation(
                specification
            )
        )

        dispatcher.dispatch(
            outer_operation,
            context,
        )

        if not context.solids.contains(
            outer_operation.output_id
        ):
            raise RuntimeError(
                f"{specification.id}: outer body missing."
            )

        inner_operation = (
            self._builder
            .build_inner_geometry_operation(
                specification
            )
        )

        dispatcher.dispatch(
            inner_operation,
            context,
        )

        if not context.solids.contains(
            inner_operation.output_id
        ):
            raise RuntimeError(
                f"{specification.id}: inner tool missing."
            )

        cut_operation = (
            self._builder
            .build_cavity_cut_operation(
                specification
            )
        )

        dispatcher.dispatch(
            cut_operation,
            context,
        )

        final_id = self._builder.final_body_id(
            specification
        )

        if not context.solids.contains(final_id):
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
                f"{specification.id}: invalid final volume."
            )

        payload = dispatcher.dispatch(
            self._builder.build_export_operation(
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

        return OrganicPlanterRunResult(
            specification=specification,
            context=context,
            export_path=payload.export_path,
        )
