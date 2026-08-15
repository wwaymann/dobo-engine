from __future__ import annotations

from dataclasses import dataclass


VISIBLE_MORPHOLOGICAL_CONTINUITY_VERSION = "A4.1"


@dataclass(frozen=True, slots=True)
class VisibleRootFlarePolicy:
    kind: str
    lateral_scale: float
    depth_scale: float
    vertical_scale: float
    outward_shift_scale: float
    blend_scale: float

    def validate(self) -> None:
        if self.kind not in {"ellipsoid", "rounded_box"}:
            raise ValueError("Unsupported visible root flare kind.")
        if min(
            self.lateral_scale,
            self.depth_scale,
            self.vertical_scale,
            self.outward_shift_scale,
            self.blend_scale,
        ) <= 0.0:
            raise ValueError("Visible root flare scales must be positive.")
        if self.lateral_scale > 1.12 or self.vertical_scale > 1.12:
            raise ValueError("Visible root flare exceeds its silhouette reserve.")


@dataclass(frozen=True, slots=True)
class HierarchyBridgePolicy:
    start_fraction: float
    end_fraction: float
    radius_scale: float
    blend_scale: float

    def validate(self) -> None:
        if not 0.0 < self.start_fraction < self.end_fraction < 1.0:
            raise ValueError("Hierarchy bridge fractions are invalid.")
        if not 0.10 <= self.radius_scale <= 0.55:
            raise ValueError("Hierarchy bridge radius scale is outside its safe range.")
        if self.blend_scale <= 0.0:
            raise ValueError("Hierarchy bridge blend scale must be positive.")


@dataclass(frozen=True, slots=True)
class SpanVisibleRootPolicy:
    kind: str
    width_scale: float
    depth_scale: float
    height_scale: float
    outward_shift_scale: float
    blend_scale: float

    def validate(self) -> None:
        if self.kind not in {"ellipsoid", "rounded_box"}:
            raise ValueError("Unsupported span root kind.")
        if min(
            self.width_scale,
            self.depth_scale,
            self.height_scale,
            self.outward_shift_scale,
            self.blend_scale,
        ) <= 0.0:
            raise ValueError("Span visible root scales must be positive.")


class VisibleMorphologicalContinuity:
    """A.4 rules that make structural continuity visible, not merely valid.

    A.3 added deep collars that strengthened fusion but intentionally stayed
    inside the source silhouette. The automated A2/A3 visual gate proved that
    this changed the visible outline only marginally. A.4 therefore adds a
    controlled *external* transition layer while preserving the semantic
    component itself:

    * a root flare around additive branches and terminals;
    * a short capsule bridge across parent/child branch hierarchy;
    * visible span shoulders near the vessel skin.

    These are topology-role and style rules. They are not product-specific
    branches and do not modify subtractive volumes.
    """

    @staticmethod
    def root_flare(*, style_name: str, topology_role: str) -> VisibleRootFlarePolicy:
        if style_name == "geometric":
            result = VisibleRootFlarePolicy(
                kind="rounded_box",
                lateral_scale=0.90,
                depth_scale=0.92,
                vertical_scale=0.86,
                outward_shift_scale=0.08,
                blend_scale=1.06,
            )
        elif topology_role == "terminal":
            result = VisibleRootFlarePolicy(
                kind="ellipsoid",
                lateral_scale=0.86,
                depth_scale=0.92,
                vertical_scale=0.82,
                outward_shift_scale=0.18,
                blend_scale=1.30,
            )
        else:
            result = VisibleRootFlarePolicy(
                kind="ellipsoid",
                lateral_scale=0.96,
                depth_scale=0.98,
                vertical_scale=0.90,
                outward_shift_scale=0.14,
                blend_scale=1.34,
            )
        result.validate()
        return result

    @staticmethod
    def hierarchy_bridge(
        *,
        style_name: str,
        topology_role: str,
    ) -> HierarchyBridgePolicy:
        if style_name == "geometric":
            result = HierarchyBridgePolicy(
                start_fraction=0.28,
                end_fraction=0.76,
                radius_scale=0.22,
                blend_scale=1.02,
            )
        elif topology_role == "terminal":
            result = HierarchyBridgePolicy(
                start_fraction=0.20,
                end_fraction=0.86,
                radius_scale=0.30,
                blend_scale=1.30,
            )
        else:
            result = HierarchyBridgePolicy(
                start_fraction=0.18,
                end_fraction=0.84,
                radius_scale=0.34,
                blend_scale=1.36,
            )
        result.validate()
        return result

    @staticmethod
    def span_visible_root(style_name: str) -> SpanVisibleRootPolicy:
        if style_name == "geometric":
            result = SpanVisibleRootPolicy(
                kind="rounded_box",
                width_scale=1.08,
                depth_scale=0.90,
                height_scale=1.00,
                outward_shift_scale=0.06,
                blend_scale=1.04,
            )
        else:
            result = SpanVisibleRootPolicy(
                kind="ellipsoid",
                width_scale=1.42,
                depth_scale=1.02,
                height_scale=1.22,
                outward_shift_scale=0.16,
                blend_scale=1.28,
            )
        result.validate()
        return result
