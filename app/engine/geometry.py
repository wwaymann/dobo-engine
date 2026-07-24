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

    top_diameter = config["top_diameter"]
    bottom_diameter = config["bottom_diameter"]

    height = config["height"]

    wall = config["wall_thickness"]
    bottom = config["bottom_thickness"]

    top_radius = top_diameter / 2
    bottom_radius = bottom_diameter / 2

    # ------------------------
    # Validations
    # ------------------------

    assert wall >= 2, "Wall thickness must be >= 2 mm"
    assert bottom >= 3, "Bottom thickness must be >= 3 mm"

    # ------------------------
    # Outer shell
    # ------------------------

    pot = (
        cq.Workplane("XY")
        .circle(bottom_radius)
        .workplane(offset=height)
        .circle(top_radius)
        .loft()
    )

    # ------------------------
    # Inner cavity
    # ------------------------

    inner_pot = (
        cq.Workplane("XY")
        .circle(bottom_radius - wall)
        .workplane(offset=height)
        .circle(top_radius - wall)
        .loft()
    )

    pot = pot.cut(
        inner_pot.translate((0, 0, bottom))
    )

    # ------------------------
    # Drain hole
    # ------------------------

    if config["drain_hole"]:

        pot = (
            pot.faces("<Z")
            .workplane()
            .hole(config["drain_diameter"])
        )

    # ------------------------
    # Export
    # ------------------------

    os.makedirs(
        "outputs/models",
        exist_ok=True
    )

    cq.exporters.export(
        pot,
        "outputs/models/dobo_pot.step"
    )

    cq.exporters.export(
        pot,
        "outputs/models/dobo_pot.stl"
    )

    # ------------------------
    # Console output
    # ------------------------

    print("\nDOBO Engine v0.4")
    print("----------------------------")

    print(
        f"Top diameter    : {top_diameter} mm"
    )

    print(
        f"Bottom diameter : {bottom_diameter} mm"
    )

    print(
        f"Height          : {height} mm"
    )

    print(
        f"Wall thickness  : {wall} mm"
    )

    print(
        f"Bottom thickness: {bottom} mm"
    )

    if config["drain_hole"]:

        print(
            f"Drain diameter  : "
            f"{config['drain_diameter']} mm"
        )

    print("\nGenerated files:")
    print(
        "outputs/models/dobo_pot.step"
    )

    print(
        "outputs/models/dobo_pot.stl"
    )


if __name__ == "__main__":
    generate_pot()