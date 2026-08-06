from __future__ import annotations

from .specification import TexturedPlanterSpecification


TEXTURED_PLANTER_CATALOG = (
    TexturedPlanterSpecification(
        id="vertical_rib_planter",
        name="Vertical Rib Planter",
        texture="vertical_ribs",
        texture_count=10,
        texture_width=5.0,
        texture_depth=3.0,
    ),
    TexturedPlanterSpecification(
        id="wide_rib_planter",
        name="Wide Rib Planter",
        texture="wide_ribs",
        texture_count=6,
        texture_width=10.0,
        texture_depth=4.0,
    ),
    TexturedPlanterSpecification(
        id="fine_fluted_planter",
        name="Fine Fluted Planter",
        texture="fine_fluting",
        texture_count=18,
        texture_width=2.5,
        texture_depth=2.0,
    ),
    TexturedPlanterSpecification(
        id="corner_rib_planter",
        name="Corner Rib Planter",
        texture="corner_ribs",
        texture_count=4,
        texture_width=8.0,
        texture_depth=4.0,
    ),
    TexturedPlanterSpecification(
        id="front_panel_planter",
        name="Front Panel Planter",
        texture="front_panels",
        texture_count=5,
        texture_width=15.0,
        texture_depth=2.5,
    ),
    TexturedPlanterSpecification(
        id="alternating_rib_planter",
        name="Alternating Rib Planter",
        texture="alternating_ribs",
        texture_count=10,
        texture_width=5.0,
        texture_depth=4.0,
    ),
)

for _spec in TEXTURED_PLANTER_CATALOG:
    _spec.validate()
