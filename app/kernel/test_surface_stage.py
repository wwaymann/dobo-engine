from kernel.contracts.placement import Placement
from kernel.contracts.surface import (
    Surface,
    SurfaceType,
)
from kernel.providers.circle_provider import CircleProvider
from kernel.providers.registry import ProviderRegistry
from kernel.services.surface_engine import SurfaceEngine
from kernel.stages.provider_stage import ProviderStage
from kernel.stages.surface_stage import SurfaceStage


def main() -> None:
    registry = ProviderRegistry()

    registry.register_provider(
        CircleProvider()
    )

    provider_stage = ProviderStage(
        registry=registry
    )

    provider_result = provider_stage.execute(
        provider_name="circle",
        parameters={
            "radius": 20.0,
        },
    )

    surface_stage = SurfaceStage(
        engine=SurfaceEngine()
    )

    surface_result = surface_stage.execute(
        contours=provider_result.contours,
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

    placed_surface = (
        surface_result.placement.surface
    )

    if placed_surface is None:
        raise RuntimeError(
            "SurfaceStage returned a placement "
            "without a Surface."
        )

    print()
    print("DOBO Surface Stage")
    print("------------------")
    print(
        "Contours:",
        surface_result
        .placement
        .placed_contours
        .count,
    )
    print(
        "Surface:",
        placed_surface.type.value,
    )
    print(
        "Strategy:",
        surface_result
        .placement
        .quality
        .strategy,
    )
    print()


if __name__ == "__main__":
    main()