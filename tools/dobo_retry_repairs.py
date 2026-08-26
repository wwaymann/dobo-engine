from __future__ import annotations

"""Conservative 3F recovery extension used only by the live capability lab.

The production retry policy is kept intact. This bridge adds recovery profiles
that preserve semantic features while making disconnected additive surface
features overlap the vessel by a guaranteed amount. It also preserves the
failure reason for every attempt so local failures are reproducible.
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


def _embed_additive_hierarchy(candidate: dict[str, Any], *, depth_mm: float, blend_mm: float) -> None:
    hierarchy = candidate.get("hierarchy_program")
    if not isinstance(hierarchy, dict):
        return

    templates = hierarchy.get("templates", [])
    additive_ids: set[str] = set()
    for template in templates:
        if not isinstance(template, dict) or template.get("operation") != "add":
            continue
        additive_ids.add(str(template.get("id")))
        if "blend_mm" in template:
            template["blend_mm"] = max(float(template.get("blend_mm", 0.0)), blend_mm)

    def visit(node: dict[str, Any]) -> None:
        ids = {str(value) for value in node.get("template_ids", [])}
        if additive_ids.intersection(ids):
            anchor = node.get("surface_anchor")
            if isinstance(anchor, dict):
                # Negative offset moves the additive mass into the vessel along
                # the resolved inward normal while keeping the exterior part visible.
                anchor["offset_mm"] = min(float(anchor.get("offset_mm", 0.0)), -depth_mm)
        for child in node.get("children", []):
            if isinstance(child, dict):
                visit(child)

    for root in hierarchy.get("roots", []):
        if isinstance(root, dict):
            visit(root)


def _high_resolution_profile(motor_program: dict[str, Any]) -> dict[str, Any]:
    candidate = deepcopy(motor_program)
    candidate.pop("mesh_quality", None)

    grid = candidate.get("grid")
    vessel = candidate.get("vessel")
    original_voxel = float(grid.get("voxel_mm", 1.0)) if isinstance(grid, dict) else 1.0
    wall = float(vessel.get("wall_mm", 0.0)) if isinstance(vessel, dict) else 0.0

    if isinstance(grid, dict):
        target = 0.72 * original_voxel
        if wall > 0.0:
            target = min(target, wall / 4.1)
        grid["voxel_mm"] = max(0.35, target)

    voxel = float(candidate.get("grid", {}).get("voxel_mm", original_voxel))
    composition = candidate.get("composition")
    if isinstance(composition, dict) and "blend_mm" in composition:
        composition["blend_mm"] = max(float(composition["blend_mm"]), 4.5 * voxel)

    penetration = max(2.4, 4.0 * voxel, 0.65 * wall if wall > 0.0 else 0.0)
    _embed_additive_hierarchy(
        candidate,
        depth_mm=penetration,
        blend_mm=max(1.6, 2.5 * voxel),
    )
    return candidate


def _deep_embedded_profile(motor_program: dict[str, Any]) -> dict[str, Any]:
    """Final connectivity recovery without removing requested features."""
    candidate = _high_resolution_profile(motor_program)
    grid = candidate.get("grid", {})
    vessel = candidate.get("vessel", {})
    voxel = float(grid.get("voxel_mm", 1.0))
    wall = float(vessel.get("wall_mm", 0.0))
    penetration = max(3.4, 5.5 * voxel, 0.85 * wall if wall > 0.0 else 0.0)
    _embed_additive_hierarchy(
        candidate,
        depth_mm=penetration,
        blend_mm=max(2.2, 3.2 * voxel),
    )
    return candidate


def _profiles(motor_program: dict[str, Any]):
    base = list(_ORIGINAL_PROFILES(motor_program))
    base.append(("high_resolution_preserve_features", _high_resolution_profile(motor_program)))
    base.append(("deep_embedded_preserve_features", _deep_embedded_profile(motor_program)))
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
        "including the embedded feature preservation profiles. "
        f"Attempts: {detail}. The semantic and Motor JSON checkpoints were preserved."
    ) from last_error


def install_retry_repairs() -> None:
    DoboDesignPipeline._mesh_quality_profiles = staticmethod(_profiles)
    DoboDesignPipeline._generate_with_retry = classmethod(_generate_with_retry)
