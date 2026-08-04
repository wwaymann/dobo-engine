import os
from typing import Any, cast

import cadquery as cq

from kernel.contracts.placement import Placement
from kernel.contracts.provider_request import ProviderRequest
from kernel.contracts.surface import (
    Surface,
    SurfaceType,
)
from kernel.providers.svg_provider import SVGProvider
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

    if surface_placement.placed_contours.is_empty:
        raise RuntimeError("Cylinder placement returned no contours.")

    wire = surface_placement.placed_contours.contours[0].geometry

    if not isinstance(
        wire,
        cq.Wire,
    ):
        raise TypeError("Cylinder diagnostic expected " "a CadQuery Wire.")

    typed_wire = cast(
        Any,
        wire,
    )

    output_directory = os.path.join(
        "outputs",
        "kernel",
        "diagnostics",
    )

    os.makedirs(
        output_directory,
        exist_ok=True,
    )

    output_path = os.path.join(
        output_directory,
        "cylinder_wire.step",
    )

    cq.exporters.export(
        wire,
        output_path,
    )

    print()
    print("DOBO Cylinder Wire Diagnostic")
    print("-----------------------------")
    print(
        "Wire valid:",
        wire.isValid(),
    )
    print(
        "Closed:",
        typed_wire.IsClosed(),
    )
    print(
        "Edges:",
        len(wire.Edges()),
    )
    print(
        "Vertices:",
        len(wire.Vertices()),
    )
    print(
        "Length:",
        typed_wire.Length(),
    )
    print(
        "STEP:",
        output_path,
    )
    print()


if __name__ == "__main__":
    main()
