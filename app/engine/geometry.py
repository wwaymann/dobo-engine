import cadquery as cq
import json
import os


def load_config():
    config_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "config",
        "pot_config.json"
    )

    with open(config_path, "r") as file:
        return json.load(file)


def generate_pot():
    config = load_config()

    diameter = config["diameter"]
    height = config["height"]
    wall = config["wall_thickness"]
    bottom = config["bottom_thickness"]

    outer_radius = diameter / 2
    inner_radius = outer_radius - wall

    pot = (
        cq.Workplane("XY")
        .circle(outer_radius)
        .extrude(height)
        .faces(">Z")
        .workplane()
        .circle(inner_radius)
        .cutBlind(-(height - bottom))
    )

    output = "outputs/models/dobo_pot.step"

    cq.exporters.export(
        pot,
        output
    )

    print("DOBO Pot CAD generated!")
    print(output)


if __name__ == "__main__":
    generate_pot()