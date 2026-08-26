from __future__ import annotations

"""Conservative 3F recovery extension used only by the live capability lab.

The production retry policy is kept intact. This bridge adds one final
high-resolution recovery profile and preserves the failure reason for every
attempt so local failures are reproducible instead of collapsing into a generic
3F error.
"""

from copy import deepcopy
from typing import Any

from product_generators.design_interpreter.design_pipeline import DoboDesignPipeline


_RECOVERABLE = {
    "Localized mesh refinement exceeded its displacement limit.",
    "Smooth union did not create one connected surface.",
    "Localized mesh refinement exceeded total volume drift from input.",
}

_ORIGINAL_PROFILES = DoboDesignPipeline._mesh_quality_profiles


def _high_resolution_profile(motor_program: dict[str, Any]) -> dict[str, Any]:
    candidate = deepcopy(motor_program)
    candidate.pop("mesh_quality", None)

    grid = candidate.get("grid")
    vessel = candidate.get("vessel")
    if isinstance(grid, dict):
        voxel = float(grid.get("voxel_mm", 1.0))
        target = 0.72 * voxel
        if isinstance(vessel, dict):
            wall = float(vessel.get("wall_mm", 0.0))
            bottom = float(vessel.get("bottom_mm", 0.0))
            positive = [value for value in (wall, bottom) if value > 0.0]
            if positive:
                target = min(target, min(positive) / 4.1)
        grid["voxel_mm"] = max(0.35, target)

    composition = candidate.get("composition")
    if isinstance(composition, dict) and "blend_mm" in composition:
        composition["blend_mm"] = max(
            float(composition["blend_mm"]),
            4.5 * float(candidate.get("grid", {}).get("voxel_mm", 1.0)),
        )

    # Preserve every semantic feature. Only additive hierarchy anchors are
    # moved slightly inward so a requested raised feature cannot float off the
    # vessel surface after discretization.
    hierarchy = candidate.get("hierarchy_program")
    if isinstance(hierarchy, dict):
        templates = hierarchy.get("templates", [])
        additive = {
            str(template.get("id"))
            for template in templates
            if isinstance(template, dict) and template.get("operation") == "add"
        }

        def visit(node: dict[str, Any]) -> None:
            ids = {str(value) for value in node.get("template_ids", [])}
            if additive.intersection(ids):
                anchor = node.get("surface_anchor")
                if isinstance(anchor, dict):
                    anchor["offset_mm"] = min(float(anchor.get("offset_mm", 0.0)), -1.4)
            for child in node.get("children", []):
                if isinstance(child, dict):
                    visit(child)

        for root in hierarchy.get("roots", []):
            if isinstance(root, dict):
                visit(root)

    return candidate


def _profiles(motor_program: dict[str, Any]):
    base = list(_ORIGINAL_PROFILES(motor_program))
    base.append(("high_resolution_preserve_features", _high_resolution_profile(motor_program)))
    return tuple(base)


def _generate_with_retry(cls, motor_program: dict[str, Any], *, parser: Any, engine: Any):
    diagnostics: list[str] = []
    profiles = cls._mesh_quality_profiles(motor_program)
    last_error: RuntimeError | None = None

    for attempt, (profile_name, candidate) in enumerate(profiles, start=1):
        specification = parser.parse_dict(candidate)
        try:
            result = engine.generate(specification)
        except RuntimeError as error:
            message = str(error)
            diagnostics.append(f"{profile_name}: {message}")
            if message not in _RECOVERABLE:
                raise RuntimeError(
                    f"Mesh generation failed in profile {profile_name}: {message}"
                ) from error
            last_error = error
            continue
        return result, candidate, attempt, profile_name

    detail = " | ".join(diagnostics)
    raise RuntimeError(
        "Mesh generation failed under every approved 3F recovery profile, "
        "including the high-resolution preservation profile. "
        f"Attempts: {detail}. The semantic and Motor JSON checkpoints were preserved."
    ) from last_error


def install_retry_repairs() -> None:
    DoboDesignPipeline._mesh_quality_profiles = staticmethod(_profiles)
    DoboDesignPipeline._generate_with_retry = classmethod(_generate_with_retry)
