import cadquery as cq
from config import POT_DIAMETER, POT_HEIGHT, WALL_THICKNESS


def create_pot():
    outer_radius = POT_DIAMETER / 2
    inner_radius = outer_radius - WALL_THICKNESS

    outer = (
        cq.Workplane("XY")
        .circle(outer_radius)
        .extrude(POT_HEIGHT)
    )

    inner = (
        cq.Workplane("XY")
        .circle(inner_radius)
        .extrude(POT_HEIGHT - WALL_THICKNESS)
        .translate((0, 0, WALL_THICKNESS))
    )

    pot = outer.cut(inner)

    return pot


if __name__ == "__main__":
    pot = create_pot()

    pot.export("outputs/pot.step")
    pot.export("outputs/pot.stl")

    print("DOBO Hollow Pot generated!")