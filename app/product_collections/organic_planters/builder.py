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
)

from .profile_generator import OrganicProfileGenerator
from .specification import OrganicPlanterSpecification


class OrganicPlanterCollectionBuilder:
    OUTPUT_DIRECTORY = (
        "outputs/product_collections/organic_planters"
    )

    def __init__(self) -> None:
        self._profiles = OrganicProfileGenerator()

    def build_outer_geometry_operation(
        self,
        specification: OrganicPlanterSpecification,
    ) -> GeometryOperation:
        definitions, offsets = (
            self._profiles.generate_outer_sections(
                specification
            )
        )

        return self._build_loft_operation(
            specification=specification,
            definitions=definitions,
            offsets=offsets,
            role="outer",
            output_id=self.outer_body_id(
                specification
            ),
        )

    def build_inner_geometry_operation(
        self,
        specification: OrganicPlanterSpecification,
    ) -> GeometryOperation:
        definitions, offsets = (
            self._profiles.generate_inner_sections(
                specification
            )
        )

        return self._build_loft_operation(
            specification=specification,
            definitions=definitions,
            offsets=offsets,
            role="inner",
            output_id=self.inner_tool_id(
                specification
            ),
        )

    def _build_loft_operation(
        self,
        *,
        specification: OrganicPlanterSpecification,
        definitions,
        offsets,
        role: str,
        output_id: str,
    ) -> GeometryOperation:
        specification.validate()

        geometry = GeometryDefinitionSet(
            id=(
                f"{specification.id}:"
                f"{role}-geometry"
            ),
            definitions=definitions,
            source="organic_planters",
            metadata={
                "collection": "organic_planters",
                "product_id": specification.id,
                "role": role,
            },
        )
        geometry.validate()

        request = GeometryRequest(
            id=(
                f"{specification.id}:"
                f"{role}-loft-request"
            ),
            geometry=geometry,
            operation=GeometryOperationType.LOFT,
            parameters={
                "solid": True,
                "ruled": specification.ruled,
                "section_offsets": offsets,
            },
            output_id=output_id,
            metadata={
                "collection": "organic_planters",
                "product_id": specification.id,
                "role": role,
                "section_count": len(definitions),
            },
        )
        request.validate()

        operation = GeometryOperation(
            id=(
                f"{specification.id}:"
                f"{role}-geometry-operation"
            ),
            name=(
                f"{specification.name} "
                f"{role.title()} Loft"
            ),
            request=request,
            output_id=output_id,
            tags=(
                "collection",
                "organic_planters",
                specification.id,
                role,
            ),
        )
        operation.validate()

        return operation

    def build_cavity_cut_operation(
        self,
        specification: OrganicPlanterSpecification,
    ) -> BooleanOperation:
        operation = BooleanOperation(
            id=f"{specification.id}:cavity-cut",
            name=f"{specification.name} Cavity Cut",
            mode=BooleanMode.CUT,
            target_id=self.outer_body_id(
                specification
            ),
            tool_id=self.inner_tool_id(
                specification
            ),
            output_id=self.final_body_id(
                specification
            ),
            tolerance=0.01,
            metadata={
                "collection": "organic_planters",
                "product_id": specification.id,
                "role": "cavity",
            },
        )
        operation.validate()

        return operation

    def build_export_operation(
        self,
        specification: OrganicPlanterSpecification,
    ) -> ExportOperation:
        destination = os.path.join(
            self.OUTPUT_DIRECTORY,
            specification.resolved_export_filename,
        )

        operation = ExportOperation(
            id=f"{specification.id}:export",
            name=f"Export {specification.name}",
            source_id=self.final_body_id(
                specification
            ),
            configuration=ExportConfiguration(
                enabled=True,
                format=ExportFormat.STEP,
                destination=destination,
                tolerance=0.01,
                angular_tolerance=0.1,
                units="mm",
                metadata={
                    "collection": "organic_planters",
                    "product_id": specification.id,
                },
            ),
            overwrite=True,
            metadata={
                "collection": "organic_planters",
                "product_id": specification.id,
            },
        )
        operation.validate()

        return operation

    @staticmethod
    def outer_body_id(
        specification: OrganicPlanterSpecification,
    ) -> str:
        return f"{specification.id}:outer"

    @staticmethod
    def inner_tool_id(
        specification: OrganicPlanterSpecification,
    ) -> str:
        return f"{specification.id}:inner-tool"

    @staticmethod
    def final_body_id(
        specification: OrganicPlanterSpecification,
    ) -> str:
        return f"{specification.id}:body"
