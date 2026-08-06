from __future__ import annotations

import os

from .catalog import ORGANIC_PLANTER_CATALOG
from .runner import OrganicPlanterCollectionRunner


def main() -> None:
    runner = OrganicPlanterCollectionRunner()

    print()
    print("DOBO Organic Planters - Phase 3")
    print("-------------------------------")

    completed = 0

    for specification in ORGANIC_PLANTER_CATALOG:
        result = runner.run(
            specification
        )

        solid = result.context.solids.get(
            result.final_body_id
        )
        solid.validate()

        if solid.volume is None or solid.volume <= 0:
            raise RuntimeError(
                f"{specification.id}: invalid final volume."
            )

        if not os.path.isfile(result.export_path):
            raise RuntimeError(
                f"{specification.id}: STEP file missing."
            )

        print(
            specification.id,
            len(specification.sections),
            "sections",
            round(float(solid.volume), 3),
            "OK",
        )

        completed += 1

    print("-------------------------------")
    print("Products:", completed)
    print("Phase 3: Valid OK")
    print()


if __name__ == "__main__":
    main()
