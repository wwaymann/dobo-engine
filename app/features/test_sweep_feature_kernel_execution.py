from __future__ import annotations
from features.builders.sweep_operation_builder import SweepOperationBuilder
from features.contracts import BooleanMode, FeatureContext
from features.definitions.sweep_feature_definition import SweepFeatureDefinition
from kernel.contracts.model_state import ModelState
from kernel.core.kernel_model import KernelModel
from testing import build_kernel_engine, build_rectangle_region_set

def main() -> None:
    regions = build_rectangle_region_set(region_set_id="sweep_regions", width=4.0, height=4.0)
    context = FeatureContext(model=ModelState())
    context.register_regions("sweep_regions", regions)
    feature = SweepFeatureDefinition(
        id="sweep_e2e",
        name="Sweep E2E",
        region_set_id="sweep_regions",
        region_id=regions.regions[0].id,
        path=((0.0, 0.0, 0.0), (0.0, 0.0, 20.0), (10.0, 0.0, 30.0)),
        output_id="sweep_body",
        mode=BooleanMode.NEW_BODY,
    )
    plan = SweepOperationBuilder().build(feature, context)
    model = KernelModel(name="Sweep Feature Model")
    for operation in plan.operations:
        model.add_operation(operation)
    result = build_kernel_engine(include_boolean=False, include_export=False).execute(model)
    result.validate()
    assert result.succeeded
    assert "sweep_body" in result.solids
    print("DOBO Sweep Feature Kernel Execution")
    print("Volume:", result.solids["sweep_body"].volume)
    print("Valid: OK")

if __name__ == "__main__":
    main()
