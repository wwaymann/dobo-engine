"""DOBO Classic Planter Product Integration Test."""

from __future__ import annotations

import os

from products.planters import ClassicPlanterProduct, ClassicPlanterSpecification
from testing import build_kernel_engine


def main() -> None:
    specification = ClassicPlanterSpecification()
    export_path = os.path.abspath(specification.export_path)

    if os.path.isfile(export_path):
        os.remove(export_path)

    product = ClassicPlanterProduct(specification)
    model = product.build_model()

    engine = build_kernel_engine(
        include_geometry=True,
        include_boolean=False,
        include_shell=True,
        include_modeling=False,
        include_export=True,
        stop_on_error=True,
    )

    result = engine.execute(
        model,
        metadata={"test": "classic_planter_product"},
    )
    result.validate()

    if not result.succeeded:
        errors = [
            item.error_message
            for item in result.operations
            if item.failed
        ]
        raise RuntimeError(f"Classic Planter execution failed: {errors}")

    if result.operation_count != 3 or result.completed_count != 3:
        raise RuntimeError("Classic Planter must complete three operations.")

    if product.FINAL_BODY_ID not in result.solids:
        raise RuntimeError("Classic Planter final Solid was not registered.")

    final_solid = result.solids[product.FINAL_BODY_ID]
    final_solid.validate()

    if final_solid.volume is None or final_solid.volume <= 0:
        raise RuntimeError("Classic Planter final volume must be positive.")

    if not os.path.isfile(export_path):
        raise RuntimeError("Classic Planter STEP file was not created.")

    print()
    print("DOBO Classic Planter v1")
    print("-----------------------")
    print("Operations:", result.operation_count)
    print("Completed:", result.completed_count)
    print("Failed:", result.failed_count)
    print("Solid IDs:", tuple(result.solids.keys()))
    print("Width:", specification.width)
    print("Depth:", specification.depth)
    print("Height:", specification.height)
    print("Wall thickness:", specification.wall_thickness)
    print("Final volume:", final_solid.volume)
    print("STEP:", export_path)
    print("File exists:", os.path.isfile(export_path))
    print("File size:", os.path.getsize(export_path))
    print("Valid: OK")
    print()


if __name__ == "__main__":
    main()
