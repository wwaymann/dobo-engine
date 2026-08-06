from __future__ import annotations
from features.builders.shell_operation_builder import ShellOperationBuilder
from features.contracts import FeatureContext
from features.definitions.shell_feature_definition import ShellFeatureDefinition
from kernel.contracts.model_state import ModelState

def main() -> None:
    context = FeatureContext(model=ModelState())
    feature = ShellFeatureDefinition(
        id="shell_001",
        name="Shell Test",
        source_body_id="source_body",
        output_id="shell_body",
        thickness=-2.0,
        remove_face_indices=(5,),
    )
    plan = ShellOperationBuilder().build(feature, context)
    plan.validate()
    print("DOBO Shell Operation Builder")
    print("Operations:", plan.operation_count)
    print("Output:", plan.final_output_id)
    print("Valid: OK")

if __name__ == "__main__":
    main()
