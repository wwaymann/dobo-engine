"""
DOBO Features

Advanced Feature Builder Support
"""
from __future__ import annotations
from features.contracts import BooleanMode
from kernel.contracts.boolean_request import BooleanOperation as KernelBooleanMode
from kernel.contracts.operations import BooleanOperation

def kernel_boolean_mode(mode: BooleanMode) -> KernelBooleanMode:
    if mode is BooleanMode.JOIN:
        return KernelBooleanMode.UNION
    if mode is BooleanMode.CUT:
        return KernelBooleanMode.CUT
    if mode is BooleanMode.INTERSECT:
        return KernelBooleanMode.INTERSECT
    raise ValueError("NEW_BODY does not require BooleanOperation.")

def build_boolean_operation(
    *,
    feature_id: str,
    feature_name: str,
    feature_type: str,
    mode: BooleanMode,
    target_body_id: str | None,
    tool_id: str,
    output_id: str,
    metadata: dict[str, object],
) -> BooleanOperation:
    if target_body_id is None:
        raise ValueError(f"{feature_type} Boolean mode requires target_body_id.")
    operation = BooleanOperation(
        id=f"{feature_id}:boolean-operation",
        name=f"{feature_name} {mode.value}",
        mode=kernel_boolean_mode(mode),
        target_id=target_body_id,
        tool_id=tool_id,
        output_id=output_id,
        tolerance=0.01,
        metadata={
            "feature_id": feature_id,
            "feature_type": feature_type,
            "boolean_mode": mode.value,
            **metadata,
        },
    )
    operation.validate()
    return operation
