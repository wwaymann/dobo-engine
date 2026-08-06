from __future__ import annotations

from .specification import OrganicPlanterSpecification


ORGANIC_PLANTER_CATALOG = (
    OrganicPlanterSpecification(
        id="pebble_planter",
        name="Pebble Planter",
        width=145.0,
        depth=120.0,
        height=115.0,
        wall_thickness=4.0,
        profile="ellipse",
        sections=(
            (0.00, 0.72, 0.72, 0.00, 0.00),
            (0.22, 0.98, 0.92, 0.00, 0.00),
            (0.52, 1.10, 1.00, 0.00, 0.00),
            (0.78, 0.96, 0.90, 0.00, 0.00),
            (1.00, 0.82, 0.78, 0.00, 0.00),
        ),
    ),
    OrganicPlanterSpecification(
        id="bulged_planter",
        name="Bulged Planter",
        width=125.0,
        depth=125.0,
        height=150.0,
        wall_thickness=4.0,
        profile="circle",
        sections=(
            (0.00, 0.78, 0.78, 0.00, 0.00),
            (0.25, 0.98, 0.98, 0.00, 0.00),
            (0.50, 1.15, 1.15, 0.00, 0.00),
            (0.75, 1.02, 1.02, 0.00, 0.00),
            (1.00, 0.90, 0.90, 0.00, 0.00),
        ),
    ),
    OrganicPlanterSpecification(
        id="hourglass_planter",
        name="Hourglass Planter",
        width=135.0,
        depth=135.0,
        height=155.0,
        wall_thickness=4.0,
        profile="circle",
        sections=(
            (0.00, 1.00, 1.00, 0.00, 0.00),
            (0.25, 0.88, 0.88, 0.00, 0.00),
            (0.50, 0.72, 0.72, 0.00, 0.00),
            (0.75, 0.88, 0.88, 0.00, 0.00),
            (1.00, 1.00, 1.00, 0.00, 0.00),
        ),
    ),
    OrganicPlanterSpecification(
        id="leaning_planter",
        name="Leaning Planter",
        width=125.0,
        depth=115.0,
        height=160.0,
        wall_thickness=4.0,
        profile="ellipse",
        sections=(
            (0.00, 0.90, 0.90, 0.00, 0.00),
            (0.25, 1.00, 0.96, 0.02, 0.00),
            (0.50, 1.05, 1.00, 0.05, 0.01),
            (0.75, 1.00, 0.96, 0.08, 0.02),
            (1.00, 0.92, 0.90, 0.11, 0.03),
        ),
    ),
    OrganicPlanterSpecification(
        id="bamboo_planter",
        name="Bamboo Planter",
        width=115.0,
        depth=115.0,
        height=175.0,
        wall_thickness=4.0,
        profile="circle",
        sections=(
            (0.00, 0.92, 0.92, 0.00, 0.00),
            (0.12, 1.06, 1.06, 0.00, 0.00),
            (0.24, 0.94, 0.94, 0.00, 0.00),
            (0.38, 1.07, 1.07, 0.00, 0.00),
            (0.52, 0.95, 0.95, 0.00, 0.00),
            (0.66, 1.06, 1.06, 0.00, 0.00),
            (0.80, 0.95, 0.95, 0.00, 0.00),
            (1.00, 1.00, 1.00, 0.00, 0.00),
        ),
    ),
    OrganicPlanterSpecification(
        id="asymmetric_planter",
        name="Asymmetric Organic Planter",
        width=140.0,
        depth=120.0,
        height=145.0,
        wall_thickness=4.0,
        profile="rounded_square",
        sections=(
            (0.00, 0.80, 0.78, 0.00, 0.00),
            (0.20, 0.95, 0.88, -0.02, 0.01),
            (0.42, 1.08, 1.00, 0.04, -0.02),
            (0.65, 0.98, 1.08, 0.07, 0.03),
            (0.82, 0.90, 0.94, 0.03, 0.05),
            (1.00, 0.84, 0.86, -0.01, 0.02),
        ),
    ),
)

for _spec in ORGANIC_PLANTER_CATALOG:
    _spec.validate()
