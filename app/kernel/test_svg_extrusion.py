import os

import cadquery as cq

from kernel.contracts.extrusion_profile import (
    ExtrusionProfile,
)
from kernel.contracts.placement import Placement
from kernel.contracts.provider_request import (
    ProviderRequest,
)
from kernel.contracts.solid import Solid
from kernel.contracts.surface import (
    Surface,
    SurfaceType,
)
from kernel.providers.svg_provider import (
    SVGProvider,
)
from kernel.services.extrusion_engine import (
    ExtrusionEngine,
)
from kernel.services.surface_engine import (
    SurfaceEngine,
)


def build_svg_solid() -> Solid:
    """
    Executes the SVG Provider, Surface Engine
    and Extrusion Engine stages.
    """

    provider = SVGProvider()

    contours = provider.execute(
        ProviderRequest(
            provider="svg",
            parameters={
                "file": "assets/svg/test.svg",
                "width": 30.0,
                "samples_per_path": 128,
                "flip_y": True,
            },
        )
    )

    surface = Surface(
        type=SurfaceType.PLANE,
        parameters={
            "origin": (
                0.0,
                0.0,
                0.0,
            ),
            "normal": (
                0.0,
                0.0,
                1.0,
            ),
        },
    )

    placement = Placement(
        position=(
            0.0,
            0.0,
            0.0,
        ),
        rotation=(
            0.0,
            0.0,
            0.0,
        ),
        scale=(
            1.0,
            1.0,
            1.0,
        ),
    )

    surface_placement = SurfaceEngine().place(
        contours=contours,
        placement=placement,
        surface=surface,
    )

    solid = ExtrusionEngine().extrude(
        placement=surface_placement,
        profile=ExtrusionProfile(
            depth=3.0,
        ),
    )

    return solid


def main() -> None:
    solid = build_svg_solid()

    geometry = solid.geometry

    if not isinstance(
        geometry,
        cq.Shape,
    ):
        raise TypeError(
            "SVG extrusion geometry must be "
            "a CadQuery Shape."
        )

    output_directory = os.path.join(
        "outputs",
        "kernel",
    )

    os.makedirs(
        output_directory,
        exist_ok=True,
    )

    output_path = os.path.join(
        output_directory,
        "svg_extrusion.step",
    )

    cq.exporters.export(
        geometry,
        output_path,
    )

    print()
    print("DOBO SVG Extrusion")
    print("------------------")
    print("Valid:", solid.is_valid)
    print("Volume:", solid.volume)
    print(
        "Bounding-box size:",
        (
            solid.bounding_box.size
            if solid.bounding_box
            else None
        ),
    )
    print("STEP:", output_path)
    print()


if __name__ == "__main__":
    main()