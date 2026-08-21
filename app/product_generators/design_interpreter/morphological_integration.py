from __future__ import annotations

from dataclasses import dataclass

from .semantic_contract import FeatureIntent


ADVANCED_MORPHOLOGICAL_INTEGRATION_VERSION = "A2.1"


@dataclass(frozen=True, slots=True)
class ParentLocalAnchor:
    horizontal: float
    vertical: float

    def validate(self) -> None:
        if not -1.0 <= self.horizontal <= 1.0:
            raise ValueError("Parent-local horizontal anchor is outside its safe range.")
        if not 0.0 <= self.vertical <= 1.0:
            raise ValueError("Parent-local vertical anchor is outside its safe range.")


@dataclass(frozen=True, slots=True)
class ChildExposurePolicy:
    translate_y_mm: float
    depth_scale: float

    def validate(self) -> None:
        if self.translate_y_mm >= 0.0:
            raise ValueError("Raised child exposure must move toward the visible surface.")
        if not 0.75 <= self.depth_scale <= 1.10:
            raise ValueError("Raised child depth scale is outside its safe range.")


@dataclass(frozen=True, slots=True)
class SpanInterfacePolicy:
    kind: str
    width_scale: float
    depth_scale: float
    height_scale: float
    blend_scale: float

    def validate(self) -> None:
        if self.kind not in {"ellipsoid", "rounded_box"}:
            raise ValueError("Unsupported span interface kind.")
        if min(
            self.width_scale,
            self.depth_scale,
            self.height_scale,
            self.blend_scale,
        ) <= 0.0:
            raise ValueError("Span interface scales must be positive.")


class AdvancedMorphologicalIntegration:
    """Product-agnostic rules that make structural hierarchy read as one design.

    A.1 proved that arbitrary spans, branches, nested negative volumes and
    surface programs can be compiled and manufactured. A.2 keeps that
    topology intact while improving three generic interfaces that were still
    visually weak in the real matrix:

    * semantic child positions must survive conversion to parent-local space;
    * raised descendants must remain visible while still overlapping parents;
    * structural span feet must match the style instead of always reading as
      rectangular pads glued to the vessel.
    """

    @staticmethod
    def parent_local_anchor(
        feature: FeatureIntent,
        *,
        preserve_legacy_facial_center: bool,
    ) -> ParentLocalAnchor:
        if preserve_legacy_facial_center:
            result = ParentLocalAnchor(0.0, 0.58)
        else:
            # Semantic anchors are already normalized. Reusing them in the
            # parent frame preserves intentional left/right and vertical
            # separation instead of collapsing every compound child to x=0.
            result = ParentLocalAnchor(
                horizontal=max(-0.78, min(0.78, float(feature.anchor.horizontal))),
                vertical=max(0.18, min(0.82, float(feature.anchor.vertical))),
            )
        result.validate()
        return result

    @staticmethod
    def raised_child_exposure(
        *,
        parent_depth_mm: float,
        child_depth_mm: float,
        minimum_feature_mm: float,
    ) -> ChildExposurePolicy:
        # Local -Y is the outward direction of a surface-anchored hierarchy.
        # Keep a deep overlap with the parent (for fusion) but move the child
        # far enough outward to preserve its silhouette and hierarchy level.
        overlap_shift = max(
            0.35,
            0.16 * parent_depth_mm + 0.08 * child_depth_mm,
            0.18 * minimum_feature_mm,
        )
        overlap_shift = min(overlap_shift, 0.42 * max(parent_depth_mm, 1e-6))
        result = ChildExposurePolicy(
            translate_y_mm=-overlap_shift,
            depth_scale=1.0,
        )
        result.validate()
        return result

    @staticmethod
    def span_interface(style_name: str) -> SpanInterfacePolicy:
        if style_name == "geometric":
            result = SpanInterfacePolicy(
                kind="rounded_box",
                width_scale=0.92,
                depth_scale=0.92,
                height_scale=0.88,
                blend_scale=0.88,
            )
        else:
            # Organic/minimal/childlike spans use ellipsoidal shoulders. They
            # preserve two real load paths around the opening without leaving
            # the rectangular plates visible in A.1.
            result = SpanInterfacePolicy(
                kind="ellipsoid",
                width_scale=1.08,
                depth_scale=0.92,
                height_scale=1.02,
                blend_scale=1.08,
            )
        result.validate()
        return result
