import json
import os

import cadquery as cq

from body import build_body
from context import EngineContext
from decoration import build_decoration
from drain import build_drain
from export import export_model
from pattern import build_pattern
from pipeline import run_pipeline
from text import build_text


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


def build_pipeline(config: dict) -> list:
    """
    Construye el pipeline según los componentes
    habilitados en la configuración.
    """

    components = config.get("components", {})

    pipeline = [
        build_body,
    ]

    if components.get(
        "drain",
        config.get("drain_hole", False),
    ):
        pipeline.append(build_drain)

    if components.get("text", False):
        pipeline.append(build_text)

    if components.get("pattern", False):
        pipeline.append(build_pattern)

    if components.get("decoration", False):
        pipeline.append(build_decoration)

    return pipeline


def generate_pot() -> cq.Workplane:
    """
    Ejecuta el pipeline completo del Motor DOBO.
    """

    # ------------------------
    # Configuration
    # ------------------------

    config = load_config()

    # ------------------------
    # Engine context
    # ------------------------

    context = EngineContext(config)

    # ------------------------
    # Dynamic pipeline
    # ------------------------

    pipeline = build_pipeline(config)

    pot = run_pipeline(
        pipeline,
        context,
    )

    # ------------------------
    # Export
    # ------------------------

    step_path, stl_path = export_model(
        pot,
        "dobo_pot",
    )

    # ------------------------
    # Console output
    # ------------------------

    print("\nDOBO Engine v0.6")
    print("----------------------------")

    print(
        f"Top diameter    : "
        f"{config['top_diameter']} mm"
    )

    print(
        f"Bottom diameter : "
        f"{config['bottom_diameter']} mm"
    )

    print(
        f"Height          : "
        f"{config['height']} mm"
    )

    print(
        f"Wall thickness  : "
        f"{config['wall_thickness']} mm"
    )

    print(
        f"Bottom thickness: "
        f"{config['bottom_thickness']} mm"
    )

    if config.get("drain_hole", False):
        print(
            f"Drain diameter  : "
            f"{config['drain_diameter']} mm"
        )

        print(
            f"Drain count     : "
            f"{config['drain_count']}"
        )

    print("\nEnabled pipeline:")

    for stage in pipeline:
        print(f"- {stage.__name__}")

    print("\nExecuted operations:")

    for operation in context.operations:
        print(f"- {operation}")

    print("\nGenerated files:")
    print(f"- STEP: {step_path}")
    print(f"- STL : {stl_path}")

    return pot


if __name__ == "__main__":
    generate_pot()