from __future__ import annotations
from features.builders.revolve_operation_builder import RevolveOperationBuilder
from features.contracts import BooleanMode, FeatureContext
from features.definitions.revolve_feature_definition import RevolveFeatureDefinition
from kernel.contracts.model_state import ModelState
from kernel.core.kernel_model import KernelModel
from testing import build_kernel_engine, build_rectangle_region_set

def main() -> None:
    regions = build_rectangle_region_set(region_set_id="revolve_regions", width=10.0, height=20.0)
    context = FeatureContext(model=ModelState())
    context.register_regions("revolve_regions", regions)
    feature = RevolveFeatureDefinition(
        id="revolve_e2e",
        name="Revolve E2E",
        region_set_id="revolve_regions",
        region_id=regions.regions[0].id,
        output_id="revolve_body",
        angle=360.0,
        axis_origin=(0.0, 0.0, 0.0),
        axis_direction=(0.0, 1.0, 0.0),
        mode=BooleanMode.NEW_BODY,
    )
    plan = RevolveOperationBuilder().build(feature, context)
    model = KernelModel(name="Revolve Feature Model")
    for operation in plan.operations:
        model.add_operation(operation)
    result = build_kernel_engine(include_boolean=False, include_export=False).execute(model)
    result.validate()
    assert result.succeeded
    assert "revolve_body" in result.solids
    print("DOBO Revolve Feature Kernel Execution")
    print("Volume:", result.solids["revolve_body"].volume)
    print("Valid: OK")

if __name__ == "__main__":
    main()
