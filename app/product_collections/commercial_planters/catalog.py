from __future__ import annotations

from .specification import CommercialPlanterSpecification


COMMERCIAL_PLANTER_CATALOG = (
    CommercialPlanterSpecification(
        id="raised_nameplate_planter",
        name="Raised Nameplate Planter",
        decoration="plate",
        mode="emboss",
        decoration_width=68.0,
        decoration_height=26.0,
        decoration_depth=3.0,
    ),
    CommercialPlanterSpecification(
        id="recessed_nameplate_planter",
        name="Recessed Nameplate Planter",
        decoration="plate",
        mode="deboss",
        decoration_width=68.0,
        decoration_height=26.0,
        decoration_depth=2.5,
    ),
    CommercialPlanterSpecification(
        id="round_badge_planter",
        name="Round Badge Planter",
        decoration="circle",
        mode="emboss",
        decoration_width=38.0,
        decoration_height=38.0,
        decoration_depth=3.0,
    ),
    CommercialPlanterSpecification(
        id="diamond_badge_planter",
        name="Diamond Badge Planter",
        decoration="diamond",
        mode="emboss",
        decoration_width=42.0,
        decoration_height=42.0,
        decoration_depth=3.0,
    ),
    CommercialPlanterSpecification(
        id="framed_panel_planter",
        name="Framed Panel Planter",
        decoration="frame",
        mode="emboss",
        decoration_width=72.0,
        decoration_height=36.0,
        decoration_depth=2.5,
    ),
    CommercialPlanterSpecification(
        id="geometric_brand_planter",
        name="Geometric Brand Planter",
        decoration="brand_mark",
        mode="emboss",
        decoration_width=54.0,
        decoration_height=34.0,
        decoration_depth=3.0,
    ),
)

for _specification in COMMERCIAL_PLANTER_CATALOG:
    _specification.validate()
