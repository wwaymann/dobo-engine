import os

import cadquery as cq

from kernel.contracts.extrusion_profile import ExtrusionProfile
from kernel.contracts.placement import Placement
from kernel.contracts.provider_request import ProviderRequest
from kernel.contracts.surface import (
    Surface,
    SurfaceType,
)
from kernel.providers.svg_provider import SVGProvider
from kernel.services.extrusion_engine import ExtrusionEngine
from kernel.services.surface_engine import SurfaceEngine


def main() -> None:
    contours = SVGProvider().execute(
        ProviderRequest(
            provider="svg",
            parameters={
                "file": "assets/svg/test.svg",
                "width": 20.0,
                "samples_per_path": 128,
            },
        )
    )

    surface_placement = SurfaceEngine().place(
        contours=contours,
        placement=Placement(
            position=(
                0.0,
                0.0,
                40.0,
            ),
            rotation=(
                0.0,
                0.0,
                0.0,
            ),
            angle_degrees=0.0,
        ),
        surface=Surface(
            type=SurfaceType.CYLINDER,
            parameters={
                "radius": 35.0,
                "height": 80.0,
                "origin": (
                    0.0,
                    0.0,
                    0.0,
                ),
                "samples_per_edge": 48,
            },
        ),
    )

    solid = ExtrusionEngine().extrude(
        placement=surface_placement,
        profile=ExtrusionProfile(
            depth=3.0,
        ),
    )

    geometry = solid.geometry

    if not isinstance(
        geometry,
        cq.Shape,
    ):
        raise TypeError(
            "Cylinder test requires CadQuery Shape geometry."
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
        "cylinder_surface.step",
    )

    cq.exporters.export(
        geometry,
        output_path,
    )

    placed_surface = surface_placement.surface

    if placed_surface is None:
        raise RuntimeError(
            "Cylinder SurfacePlacement has no Surface."
        )

    coordinate_system = (
        surface_placement.local_coordinate_systems[0]
    )

    print()
    print("DOBO Cylinder Surface")
    print("---------------------")
    print(
        "Surface:",
        placed_surface.type.value,
    )
    print(
        "Strategy:",
        surface_placement.quality.strategy,
    )
    print(
        "Origin:",
        coordinate_system.origin,
    )
    print(
        "Normal:",
        coordinate_system.normal,
    )
    print(
        "Valid:",
        solid.is_valid,
    )
    print(
        "STEP:",
        output_path,
    )
    print()


if __name__ == "__main__":
    main()