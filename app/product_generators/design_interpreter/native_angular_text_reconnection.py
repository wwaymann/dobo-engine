from __future__ import annotations

"""Reconnect semantic text to the shared native planar CAD capability."""

from typing import Any

from .body_family_expansion import GeneralBodyFamilyExpander
from .native_cad_primitive_adapter import (
    prepare_native_angular_text_contract,
    uses_native_angular_text,
)


ANGULAR_TEXT_RECONNECTION_VERSION = "ATR.1"
_ORIGINAL_APPLY = GeneralBodyFamilyExpander.apply.__func__


def _strip_text_nodes(motor: dict[str, Any], program) -> None:
    text_ids = {
        str(feature.id)
        for feature in program.features
        if feature.form_hint == "text"
    }
    if not text_ids:
        return
    template_ids = {f"{feature_id}_template" for feature_id in text_ids}
    hierarchy = motor.get("hierarchy_program")
    if not isinstance(hierarchy, dict):
        return

    def prune(node: dict[str, Any]):
        node_id = str(node.get("id", ""))
        ids = {str(value) for value in node.get("template_ids", [])}
        if node_id in text_ids or ids.intersection(template_ids):
            return None
        cleaned = dict(node)
        cleaned["children"] = [
            kept
            for child in node.get("children", [])
            if not isinstance(child, dict) or (kept := prune(child)) is not None
        ]
        return cleaned

    roots = []
    for root in hierarchy.get("roots", []):
        if isinstance(root, dict):
            kept = prune(root)
            if kept is not None:
                roots.append(kept)
        else:
            roots.append(root)
    hierarchy["roots"] = roots
    hierarchy["templates"] = [
        template
        for template in hierarchy.get("templates", [])
        if not isinstance(template, dict)
        or str(template.get("id", "")) not in template_ids
    ]


def _apply_with_native_angular_text(cls, motor_program, program):
    result = _ORIGINAL_APPLY(cls, motor_program, program)
    if uses_native_angular_text(program):
        _strip_text_nodes(motor_program, program)
        prepare_native_angular_text_contract(motor_program, program)
    return result


def install_native_angular_text_reconnection() -> str:
    current = GeneralBodyFamilyExpander.apply.__func__
    if getattr(current, "_dobo_native_angular_text", False):
        return ANGULAR_TEXT_RECONNECTION_VERSION
    # Install only while the original expansion function is still directly
    # reachable.  Later consolidation wrappers capture this function and keep it
    # in their delegation chain.
    _apply_with_native_angular_text._dobo_native_angular_text = True
    GeneralBodyFamilyExpander.apply = classmethod(_apply_with_native_angular_text)
    return ANGULAR_TEXT_RECONNECTION_VERSION
