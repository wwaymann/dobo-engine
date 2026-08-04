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
from kernel.providers.circle_provider import (
    CircleProvider,
)
from kernel.services.extrusion_engine import (
    ExtrusionEngine,
)
from kernel.services.surface_engine import (
    SurfaceEngine,
)


def main() -> None:
    provider = CircleProvider()

    contours = provider.execute(
        ProviderRequest(
            provider="circle",
            parameters={
                "radius": 20,
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
    )

    surface_engine = SurfaceEngine()

    surface_placement = surface_engine.place(
        contours=contours,
        placement=placement,
        surface=surface,
    )

    extrusion_engine = ExtrusionEngine()

    solid = extrusion_engine.extrude(
        placement=surface_placement,
        profile=ExtrusionProfile(
            depth=10.0,
        ),
    )

    output_path = "outputs/kernel/" "circle_extrusion.step"

    cq.exporters.export(
        solid.geometry,
        output_path,
    )

    print()
    print("DOBO Extrusion Engine")
    print("---------------------")
    print("Valid:", solid.is_valid)
    print("Volume:", solid.volume)
    print(
        "Bounding-box size:",
        solid.bounding_box.size if solid.bounding_box else None,
    )
    print("STEP:", output_path)
    print()


if __name__ == "__main__":
    main()
