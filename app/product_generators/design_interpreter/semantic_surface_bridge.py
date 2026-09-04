from __future__ import annotations

from .intelligent_surfaces import SurfaceLayerIntent
from .semantic_contract import DesignSemanticProgram


SEMANTIC_SURFACE_BRIDGE_VERSION = "C.1"

_PALETTE = (
    "#6D3BFF",
    "#19A974",
    "#E67E22",
    "#2471A3",
    "#C0392B",
    "#7D3C98",
)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


class SemanticSurfaceIntentBridge:
    """Translate accepted semantic surface features into IntelligentSurface intents.

    This is an integration adapter only. It does not generate geometry and does not
    introduce product-specific rules; it preserves feature kind, payload, placement,
    surface effect and physical depth already present in the semantic contract.
    """

    @classmethod
    def compile(
        cls,
        program: DesignSemanticProgram,
    ) -> tuple[SurfaceLayerIntent, ...]:
        program.validate()
        intents: list[SurfaceLayerIntent] = []

        for index, feature in enumerate(program.features):
            if feature.surface_effect == "cutout":
                # Cutouts are structural/negative-volume geometry, not a surface
                # material layer. They remain handled by the structural compiler.
                continue

            kind = "text" if feature.form_hint == "text" else "procedural_relief"
            payload = feature.concept.replace("_", " ").strip()
            if not payload:
                continue

            effect = feature.surface_effect
            if effect not in {"raised", "recessed", "marking"}:
                continue

            # Semantic horizontal is [-1, 1]; surface U is [0, 1]. Preserve the
            # semantic center while keeping a small margin for safe mapping.
            u_center = _clamp(0.5 + 0.45 * feature.anchor.horizontal, 0.05, 0.95)
            v_center = _clamp(feature.anchor.vertical, 0.05, 0.95)
            width_fraction = _clamp(feature.size.width_ratio, 0.05, 0.90)
            height_fraction = _clamp(feature.size.height_ratio, 0.05, 0.90)
            depth_mm = min(
                float(feature.size.depth_mm),
                float(program.manufacturing.maximum_relief_depth_mm),
            )
            if effect == "marking":
                depth_mm = 0.0

            intent = SurfaceLayerIntent(
                id=f"semantic_{feature.id}",
                kind=kind,
                payload=payload,
                region=feature.anchor.region,
                u_center=u_center,
                v_center=v_center,
                width_fraction=width_fraction,
                height_fraction=height_fraction,
                effect=effect,
                depth_mm=depth_mm,
                color=_PALETTE[index % len(_PALETTE)],
                filament_slot=2 + (index % 15),
            )
            intent.validate()
            intents.append(intent)

        return tuple(intents)
