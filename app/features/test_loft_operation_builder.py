from __future__ import annotations
from features.builders.loft_operation_builder import LoftOperationBuilder
from features.contracts import BooleanMode, FeatureContext
from features.definitions.loft_feature_definition import LoftFeatureDefinition
from kernel.contracts.model_state import ModelState
from testing import build_rectangle_region_set

def main() -> None:
    first = build_rectangle_region_set(region_set_id="loft_first", width=20.0, height=20.0)
    second = build_rectangle_region_set(region_set_id="loft_second", width=12.0, height=12.0)
    context = FeatureContext(model=ModelState())
    context.register_regions("loft_first", first)
    context.register_regions("loft_second", second)
    feature = LoftFeatureDefinition(
        id="loft_001",
        name="Loft Test",
        region_references=(
            ("loft_first", first.regions[0].id),
            ("loft_second", second.regions[0].id),
        ),
        section_offsets=((0.0, 0.0, 0.0), (4.0, 4.0, 30.0)),
        output_id="loft_body",
        mode=BooleanMode.NEW_BODY,
    )
    plan = LoftOperationBuilder().build(feature, context)
    plan.validate()
    print("DOBO Loft Operation Builder")
    print("Operations:", plan.operation_count)
    print("Output:", plan.final_output_id)
    print("Valid: OK")

if __name__ == "__main__":
    main()
