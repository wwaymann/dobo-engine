"""
DOBO Features

Extrude Operation Builder

Translates ExtrudeFeatureDefinition objects into
validated Kernel FeaturePlan operations.
"""

from __future__ import annotations

from features.contracts import (
    BooleanMode,
    FeatureContext,
    FeaturePlan,
)
from features.definitions import (
    ExtrudeFeatureDefinition,
)

from kernel.contracts.boolean_request import (
    BooleanOperation as KernelBooleanMode,
)
from kernel.contracts.geometry_operation_type import (
    GeometryOperationType,
)
from kernel.contracts.geometry_request import (
    GeometryRequest,
)
from kernel.contracts.operations import (
    BooleanOperation,
    GeometryOperation,
)
from kernel.providers.region_definition_provider import (
    RegionDefinitionProvider,
)

from sketch.topology import (
    RegionSet,
)

from .feature_operation_builder import (
    FeatureOperationBuilder,
)


class ExtrudeOperationBuilder(
    FeatureOperationBuilder[
        ExtrudeFeatureDefinition
    ],
):
    """
    Builds Kernel operations for one Extrude Feature.
    """

    def __init__(
        self,
        region_provider: (
            RegionDefinitionProvider
            | None
        ) = None,
    ) -> None:
        self._region_provider = (
            region_provider
            if region_provider is not None
            else RegionDefinitionProvider()
        )

    @property
    def feature_type(
        self,
    ) -> type[
        ExtrudeFeatureDefinition
    ]:
        """
        Returns the supported Feature definition type.
        """

        return ExtrudeFeatureDefinition

    def build(
        self,
        feature: ExtrudeFeatureDefinition,
        context: FeatureContext,
    ) -> FeaturePlan:
        """
        Builds a complete FeaturePlan.
        """

        self.validate(
            feature,
            context,
        )

        region_set = self._resolve_region_set(
            feature=feature,
            context=context,
        )

        selected_region = (
            region_set.region_by_id(
                feature.region_id
            )
        )

        selected_region_set = RegionSet(
            id=(
                f"{region_set.id}:"
                f"{selected_region.id}"
            ),
            regions=(
                selected_region,
            ),
            source_profile_set_id=(
                region_set
                .source_profile_set_id
            ),
            metadata={
                "source_region_set_id": (
                    region_set.id
                ),
                "selected_region_id": (
                    selected_region.id
                ),
                **region_set.metadata,
            },
        )

        selected_region_set.validate()

        geometry = self._region_provider.execute(
            selected_region_set
        )

        request_output_id = (
            feature.output_id
            if feature.mode
            is BooleanMode.NEW_BODY
            else self._tool_output_id(
                feature
            )
        )

        request = GeometryRequest(
            id=(
                f"{feature.id}:"
                "geometry-request"
            ),
            geometry=geometry,
            operation=(
                GeometryOperationType.EXTRUDE
            ),
            parameters={
                "distance": float(
                    feature.distance
                ),
                "direction": (
                    feature
                    .normalized_direction
                ),
                "symmetric": (
                    feature.symmetric
                ),
                "draft_angle": float(
                    feature.draft_angle
                ),
            },
            output_id=request_output_id,
            metadata={
                "feature_id": feature.id,
                "feature_name": (
                    feature.name
                ),
                "feature_type": (
                    feature.feature_type
                ),
                "region_set_id": (
                    feature.region_set_id
                ),
                "region_id": (
                    feature.region_id
                ),
                "boolean_mode": (
                    feature.mode.value
                ),
                "merge": feature.merge,
                **feature.metadata,
            },
        )

        request.validate()

        geometry_operation = (
            GeometryOperation(
                id=(
                    f"{feature.id}:"
                    "geometry-operation"
                ),
                name=(
                    f"{feature.name} geometry"
                ),
                request=request,
                output_id=request_output_id,
                tags=(
                    "feature",
                    "extrude",
                    feature.mode.value,
                ),
                metadata={
                    "feature_id": feature.id,
                    "feature_type": (
                        feature.feature_type
                    ),
                    **feature.metadata,
                },
            )
        )

        geometry_operation.validate()

        if (
            feature.mode
            is BooleanMode.NEW_BODY
        ):
            plan = FeaturePlan(
                feature=feature,
                operations=(
                    geometry_operation,
                ),
                expected_output_ids=(
                    feature.output_id,
                ),
                metadata={
                    "builder": (
                        "extrude_operation_builder"
                    ),
                    "boolean": False,
                    "region_id": (
                        feature.region_id
                    ),
                    **feature.metadata,
                },
            )

            plan.validate()

            return plan

        boolean_operation = (
            BooleanOperation(
                id=(
                    f"{feature.id}:"
                    "boolean-operation"
                ),
                name=(
                    f"{feature.name} "
                    f"{feature.mode.value}"
                ),
                mode=self._kernel_boolean_mode(
                    feature.mode
                ),
                target_id=self._require_target_id(
                    feature
                ),
                tool_id=request_output_id,
                output_id=feature.output_id,
                tolerance=0.01,
                metadata={
                    "feature_id": feature.id,
                    "feature_type": (
                        feature.feature_type
                    ),
                    "boolean_mode": (
                        feature.mode.value
                    ),
                    **feature.metadata,
                },
            )
        )

        boolean_operation.validate()

        plan = FeaturePlan(
            feature=feature,
            operations=(
                geometry_operation,
                boolean_operation,
            ),
            expected_output_ids=(
                request_output_id,
                feature.output_id,
            ),
            metadata={
                "builder": (
                    "extrude_operation_builder"
                ),
                "boolean": True,
                "boolean_mode": (
                    feature.mode.value
                ),
                "region_id": (
                    feature.region_id
                ),
                **feature.metadata,
            },
        )

        plan.validate()

        return plan

    @staticmethod
    def _resolve_region_set(
        *,
        feature: ExtrudeFeatureDefinition,
        context: FeatureContext,
    ) -> RegionSet:
        """
        Resolves the referenced RegionSet.
        """

        try:
            region_set = context.regions[
                feature.region_set_id
            ]

        except KeyError as error:
            raise KeyError(
                "ExtrudeOperationBuilder cannot "
                "find RegionSet "
                f"'{feature.region_set_id}'."
            ) from error

        region_set.validate()

        return region_set

    @staticmethod
    def _tool_output_id(
        feature: ExtrudeFeatureDefinition,
    ) -> str:
        """
        Returns the temporary boolean tool id.
        """

        return (
            f"{feature.output_id}"
            ":tool"
        )

    @staticmethod
    def _require_target_id(
        feature: ExtrudeFeatureDefinition,
    ) -> str:
        """
        Returns the validated target body id.
        """

        if feature.target_body_id is None:
            raise ValueError(
                "Boolean Extrude requires "
                "target_body_id."
            )

        return feature.target_body_id

    @staticmethod
    def _kernel_boolean_mode(
        mode: BooleanMode,
    ) -> KernelBooleanMode:
        """
        Maps Feature BooleanMode to Kernel mode.
        """

        if mode is BooleanMode.JOIN:
            return KernelBooleanMode.UNION

        if mode is BooleanMode.CUT:
            return KernelBooleanMode.CUT

        if mode is BooleanMode.INTERSECT:
            return (
                KernelBooleanMode.INTERSECT
            )

        raise ValueError(
            "NEW_BODY does not require a "
            "Kernel BooleanOperation."
        )