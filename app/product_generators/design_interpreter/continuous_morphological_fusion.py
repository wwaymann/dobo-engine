from __future__ import annotations

from dataclasses import dataclass


CONTINUOUS_MORPHOLOGICAL_FUSION_VERSION = "A3.1"


@dataclass(frozen=True, slots=True)
class AttachmentSpreadPolicy:
    lateral_scale: float

    def validate(self) -> None:
        if not 1.0 <= self.lateral_scale <= 1.8:
            raise ValueError("Attachment lateral scale is outside its safe range.")


@dataclass(frozen=True, slots=True)
class TransitionMassPolicy:
    kind: str
    lateral_scale: float
    depth_scale: float
    vertical_scale: float
    inward_shift_scale: float
    blend_scale: float

    def validate(self) -> None:
        if self.kind not in {"ellipsoid", "rounded_box"}:
            raise ValueError("Unsupported transition mass kind.")
        if min(
            self.lateral_scale,
            self.depth_scale,
            self.vertical_scale,
            self.inward_shift_scale,
            self.blend_scale,
        ) <= 0.0:
            raise ValueError("Transition mass scales must be positive.")
        if self.lateral_scale >= 1.0 or self.vertical_scale >= 1.0:
            raise ValueError("Transition mass must stay inside the source silhouette.")


@dataclass(frozen=True, slots=True)
class SpanContinuityPolicy:
    inward_shift_scale: float
    width_scale: float
    depth_scale: float
    height_scale: float
    blend_scale: float

    def validate(self) -> None:
        if min(
            self.inward_shift_scale,
            self.width_scale,
            self.depth_scale,
            self.height_scale,
            self.blend_scale,
        ) <= 0.0:
            raise ValueError("Span continuity scales must be positive.")


class ContinuousMorphologicalFusion:
    """Generic A.3 rules for continuous structural interfaces.

    A.2 fixed semantic placement and exposed hierarchy. A.3 keeps those
    positions but adds a smaller, deeper transition mass at additive
    interfaces. In the local surface frame +Y points into the parent/body,
    so these collars blend inward while remaining narrower than the visible
    component. That makes a raised component read as grown from the vessel
    rather than as a badge glued onto it.
    """

    @staticmethod
    def attachment_spread(
        *,
        topology_role: str,
        parent_width_mm: float,
        child_width_mm: float,
    ) -> AttachmentSpreadPolicy:
        ratio = child_width_mm / max(parent_width_mm, 1e-6)
        if topology_role == "branch":
            scale = 1.28 + 0.24 * min(1.6, ratio)
        elif topology_role == "terminal":
            scale = 1.16 + 0.18 * min(1.4, ratio)
        else:
            scale = 1.0
        result = AttachmentSpreadPolicy(lateral_scale=min(1.72, scale))
        result.validate()
        return result

    @staticmethod
    def transition_mass(
        *,
        style_name: str,
        topology_role: str,
        is_child: bool,
    ) -> TransitionMassPolicy:
        if style_name == "geometric":
            result = TransitionMassPolicy(
                kind="rounded_box",
                lateral_scale=0.76,
                depth_scale=1.08,
                vertical_scale=0.76,
                inward_shift_scale=0.48,
                blend_scale=1.02,
            )
        elif topology_role == "terminal":
            result = TransitionMassPolicy(
                kind="ellipsoid",
                lateral_scale=0.58,
                depth_scale=1.34,
                vertical_scale=0.58,
                inward_shift_scale=0.72 if is_child else 0.58,
                blend_scale=1.24,
            )
        else:
            result = TransitionMassPolicy(
                kind="ellipsoid",
                lateral_scale=0.70,
                depth_scale=1.28,
                vertical_scale=0.70,
                inward_shift_scale=0.68 if is_child else 0.55,
                blend_scale=1.20,
            )
        result.validate()
        return result

    @staticmethod
    def span_continuity(style_name: str) -> SpanContinuityPolicy:
        if style_name == "geometric":
            result = SpanContinuityPolicy(
                inward_shift_scale=0.48,
                width_scale=1.02,
                depth_scale=1.03,
                height_scale=1.00,
                blend_scale=1.00,
            )
        else:
            result = SpanContinuityPolicy(
                inward_shift_scale=0.56,
                width_scale=1.18,
                depth_scale=1.14,
                height_scale=1.10,
                blend_scale=1.16,
            )
        result.validate()
        return result
