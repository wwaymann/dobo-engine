from __future__ import annotations

import os

from .catalog import TEXTURED_PLANTER_CATALOG
from .runner import TexturedPlanterCollectionRunner


def main() -> None:
    runner = TexturedPlanterCollectionRunner()

    print()
    print("DOBO Textured Planters - Phase 2")
    print("--------------------------------")

    completed = 0

    for spec in TEXTURED_PLANTER_CATALOG:
        result = runner.run(spec)
        solid = result.context.solids.get(result.final_body_id)
        solid.validate()

        if solid.volume is None or solid.volume <= 0:
            raise RuntimeError(f"{spec.id}: invalid final volume.")

        if not os.path.isfile(result.export_path):
            raise RuntimeError(f"{spec.id}: STEP file missing.")

        print(
            spec.id,
            spec.texture,
            round(float(solid.volume), 3),
            "OK",
        )
        completed += 1

    print("--------------------------------")
    print("Products:", completed)
    print("Phase 2: Valid OK")
    print()


if __name__ == "__main__":
    main()
