import json
import os

import cadquery as cq

from body import build_body
from drain import build_drain
from export import export_model


def load_config() -> dict:
    """
    Carga la configuración paramétrica desde pot_config.json.
    """

    config_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "config",
            "pot_config.json",
        )
    )

    with open(
        config_path,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def generate_pot() -> cq.Workplane:
    """
    Coordina la construcción y exportación de la maceta.
    """

    config = load_config()

    # ------------------------
    # Body component
    # ------------------------

    pot = build_body(config)

    # ------------------------
    # Drain component
    # ------------------------

    pot = build_drain(pot, config)

    # ------------------------
    # Export component
    # ------------------------

    step_path, stl_path = export_model(
        pot,
        "dobo_pot",
    )

    # ------------------------
    # Console output
    # ------------------------

    print("\nDOBO Engine v0.5")
    print("----------------------------")

    print(f"Top diameter    : " f"{config['top_diameter']} mm")

    print(f"Bottom diameter : " f"{config['bottom_diameter']} mm")

    print(f"Height          : " f"{config['height']} mm")

    print(f"Wall thickness  : " f"{config['wall_thickness']} mm")

    print(f"Bottom thickness: " f"{config['bottom_thickness']} mm")

    if config.get("drain_hole", False):
        print(f"Drain diameter  : " f"{config['drain_diameter']} mm")

    print("\nGenerated files:")
    print(step_path)
    print(stl_path)

    return pot


if __name__ == "__main__":
    generate_pot()
