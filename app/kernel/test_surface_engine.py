from kernel.contracts.placement import Placement
from kernel.contracts.provider_request import ProviderRequest
from kernel.contracts.surface import (
    Surface,
    SurfaceType,
)
from kernel.providers.circle_provider import CircleProvider
from kernel.services.surface_engine import SurfaceEngine


def main() -> None:
    provider = CircleProvider()

    contours = provider.execute(
        ProviderRequest(
            provider="circle",
            parameters={
                "radius": 20.0,
            },
        )
    )

    surface = Surface(
        type=SurfaceType.PLANE,
        parameters={
            "origin": (
                0.0,
                0.0,
                10.0,
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
            15.0,
            5.0,
            0.0,
        ),
        rotation=(
            0.0,
            0.0,
            30.0,
        ),
        scale=(
            1.0,
            1.0,
            1.0,
        ),
    )

    engine = SurfaceEngine()

    result = engine.place(
        contours=contours,
        placement=placement,
        surface=surface,
    )

    # SurfacePlacement actualmente permite
    # Surface | None. Esta comprobación elimina
    # el error de Pylance y protege la ejecución.
    if result.surface is None:
        raise RuntimeError("SurfacePlacement has no Surface.")

    result.validate()

    print()
    print("DOBO Surface Engine")
    print("-------------------")
    print(
        "Surface:",
        result.surface.type.value,
    )
    print(
        "Source contours:",
        result.source_contours.count,
    )
    print(
        "Placed contours:",
        result.placed_contours.count,
    )
    print(
        "Coordinate systems:",
        len(result.local_coordinate_systems),
    )
    print(
        "Strategy:",
        result.quality.strategy,
    )
    print(
        "Valid:",
        True,
    )
    print()


if __name__ == "__main__":
    main()
