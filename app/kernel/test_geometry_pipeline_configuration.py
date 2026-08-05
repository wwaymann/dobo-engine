from kernel.contracts.config import (
    GeometryPipelineConfiguration,
    OffsetConfiguration,
    ProviderConfiguration,
    SurfaceConfiguration,
)
from kernel.contracts.placement import Placement
from kernel.contracts.surface import (
    Surface,
    SurfaceType,
)


def main() -> None:
    configuration = GeometryPipelineConfiguration(
        project_name=(
            "Geometry Pipeline Configuration Test"
        ),
        provider=ProviderConfiguration(
            name="circle_definition",
            parameters={
                "radius": 10.0,
                "samples": 64,
            },
        ),
        surface=SurfaceConfiguration(
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
                },
            ),
            placement=Placement(
                position=(
                    0.0,
                    0.0,
                    40.0,
                ),
                angle_degrees=0.0,
            ),
        ),
        offset=OffsetConfiguration(
            distance=4.0,
            symmetric=True,
        ),
        metadata={
            "test": True,
        },
    )

    configuration.validate()

    print()
    print("DOBO Geometry Pipeline Configuration")
    print("------------------------------------")
    print(
        "Project:",
        configuration.project_name,
    )
    print(
        "Provider:",
        configuration.provider.name,
    )
    print(
        "Surface:",
        configuration.surface.surface.type.value,
    )
    print(
        "Offset:",
        configuration.offset.distance,
    )
    print(
        "Symmetric:",
        configuration.offset.symmetric,
    )
    print(
        "Units:",
        configuration.units,
    )
    print("Valid: OK")
    print()


if __name__ == "__main__":
    main()