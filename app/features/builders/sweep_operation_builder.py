"""
DOBO Features

Sweep Operation Builder
"""
from __future__ import annotations
from features.contracts import BooleanMode, FeatureContext, FeaturePlan
from features.definitions.sweep_feature_definition import SweepFeatureDefinition
from kernel.contracts.geometry_operation_type import GeometryOperationType
from kernel.contracts.geometry_request import GeometryRequest
from kernel.contracts.operations import GeometryOperation
from kernel.providers.region_definition_provider import RegionDefinitionProvider
from sketch.topology import RegionSet
from .advanced_feature_builder_support import build_boolean_operation
from .feature_operation_builder import FeatureOperationBuilder

class SweepOperationBuilder(FeatureOperationBuilder[SweepFeatureDefinition]):
    def __init__(self, region_provider: RegionDefinitionProvider | None = None) -> None:
        self._region_provider = region_provider or RegionDefinitionProvider()

    @property
    def feature_type(self) -> type[SweepFeatureDefinition]:
        return SweepFeatureDefinition

    def build(self, feature: SweepFeatureDefinition, context: FeatureContext) -> FeaturePlan:
        self.validate(feature, context)
        region_set = context.regions[feature.region_set_id]
        region = region_set.region_by_id(feature.region_id)
        selected = RegionSet(
            id=f"{region_set.id}:{region.id}",
            regions=(region,),
            source_profile_set_id=region_set.source_profile_set_id,
            metadata={
                "source_region_set_id": region_set.id,
                "selected_region_id": region.id,
                **region_set.metadata,
            },
        )
        selected.validate()
        geometry = self._region_provider.execute(selected)
        tool_id = feature.output_id if feature.mode is BooleanMode.NEW_BODY else f"{feature.output_id}:tool"
        request = GeometryRequest(
            id=f"{feature.id}:geometry-request",
            geometry=geometry,
            operation=GeometryOperationType.SWEEP,
            parameters={
                "path": tuple((float(x), float(y), float(z)) for x, y, z in feature.path),
                "is_frenet": feature.is_frenet,
                "transition": feature.transition,
            },
            output_id=tool_id,
            metadata={"feature_id": feature.id, **feature.metadata},
        )
        request.validate()
        geometry_operation = GeometryOperation(
            id=f"{feature.id}:geometry-operation",
            name=f"{feature.name} geometry",
            request=request,
            output_id=tool_id,
            tags=("feature", "sweep", feature.mode.value),
            metadata={"feature_id": feature.id, **feature.metadata},
        )
        geometry_operation.validate()
        operations = [geometry_operation]
        expected = [tool_id]
        if feature.mode is not BooleanMode.NEW_BODY:
            operations.append(build_boolean_operation(
                feature_id=feature.id,
                feature_name=feature.name,
                feature_type=feature.feature_type,
                mode=feature.mode,
                target_body_id=feature.target_body_id,
                tool_id=tool_id,
                output_id=feature.output_id,
                metadata=feature.metadata,
            ))
            expected.append(feature.output_id)
        plan = FeaturePlan(
            feature=feature,
            operations=tuple(operations),
            expected_output_ids=tuple(expected),
            metadata={"builder": "sweep_operation_builder"},
        )
        plan.validate()
        return plan
