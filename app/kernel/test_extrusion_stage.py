from kernel.contracts.extrusion_profile import (
    ExtrusionProfile,
)
from kernel.contracts.placement import Placement
from kernel.contracts.surface import (
    Surface,
    SurfaceType,
)
from kernel.providers.circle_provider import (
    CircleProvider,
)
from kernel.providers.registry import (
    ProviderRegistry,
)
from kernel.services.extrusion_engine import (
    ExtrusionEngine,
)
from kernel.services.surface_engine import (
    SurfaceEngine,
)
from kernel.stages.extrusion_stage import (
    ExtrusionStage,
)
from kernel.stages.provider_stage import (
    ProviderStage,
)
from kernel.stages.surface_stage import (
    SurfaceStage,
)


def main() -> None:

    registry = ProviderRegistry()

    registry.register_provider(CircleProvider())

    provider_stage = ProviderStage(registry)

    provider_result = provider_stage.execute(
        provider_name="circle",
        parameters={
            "radius": 20,
        },
    )

    surface_stage = SurfaceStage(SurfaceEngine())

    surface_result = surface_stage.execute(
        contours=provider_result.contours,
        placement=Placement(),
        surface=Surface(
            type=SurfaceType.PLANE,
            parameters={
                "origin": (
                    0,
                    0,
                    0,
                ),
                "normal": (
                    0,
                    0,
                    1,
                ),
            },
        ),
    )

    extrusion_stage = ExtrusionStage(ExtrusionEngine())

    extrusion_result = extrusion_stage.execute(
        placement=surface_result.placement,
        profile=ExtrusionProfile(
            depth=10,
        ),
    )

    print()

    print("DOBO Extrusion Stage")

    print("--------------------")

    print(
        "Volume:",
        extrusion_result.solid.volume,
    )

    print(
        "Valid:",
        extrusion_result.solid.is_valid,
    )

    print()


if __name__ == "__main__":
    main()
