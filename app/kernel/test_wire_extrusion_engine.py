import os

import cadquery as cq

from kernel.contracts.extrusion_profile import (
    ExtrusionProfile,
)
from kernel.contracts.placement import Placement
from kernel.contracts.provider_request import (
    ProviderRequest,
)
from kernel.contracts.surface import (
    Surface,
    SurfaceType,
)
from kernel.providers.circle_definition_provider import (
    CircleDefinitionProvider,
)
from kernel.services.geometry_projection_engine import (
    GeometryProjectionEngine,
)
from kernel.services.wire_builder import WireBuilder
from kernel.services.wire_extrusion_engine import (
    WireExtrusionEngine,
)


def main() -> None:
    definitions = (
        CircleDefinitionProvider().execute(
            ProviderRequest(
                provider="circle_definition",
                parameters={
                    "radius": 10.0,
                    "samples": 64,
                },
            )
        )
    )

    projected = GeometryProjectionEngine().project(
        contours=definitions,
        placement=Placement(),
        surface=Surface(
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
        ),
    )

    wire_result = WireBuilder().build(
        projected
    )

    solid = WireExtrusionEngine().extrude(
        wire_result=wire_result,
        profile=ExtrusionProfile(
            depth=5.0,
        ),
    )

    geometry = solid.geometry

    if not isinstance(
        geometry,
        cq.Shape,
    ):
        raise TypeError(
            "Wire extrusion test requires "
            "CadQuery Shape geometry."
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
        "wire_extrusion.step",
    )

    cq.exporters.export(
        geometry,
        output_path,
    )

    print()
    print("DOBO Wire Extrusion Engine")
    print("--------------------------")
    print(
        "Wires:",
        wire_result.count,
    )
    print(
        "Volume:",
        solid.volume,
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