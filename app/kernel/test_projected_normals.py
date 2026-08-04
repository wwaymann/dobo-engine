import math

from kernel.contracts.placement import Placement
from kernel.contracts.provider_request import ProviderRequest
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


def main() -> None:
    definitions = CircleDefinitionProvider().execute(
        ProviderRequest(
            provider="circle_definition",
            parameters={
                "radius": 10.0,
                "samples": 64,
            },
        )
    )

    projected = GeometryProjectionEngine().project(
        contours=definitions,
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
            },
        ),
    )

    contour = projected.contours[0]

    if not contour.has_normals:
        raise RuntimeError(
            "Cylinder projection did not generate normals."
        )

    first_normal = contour.normals[0]

    normal_length = math.sqrt(
        first_normal[0] ** 2
        + first_normal[1] ** 2
        + first_normal[2] ** 2
    )

    print()
    print("DOBO Projected Normals")
    print("----------------------")
    print(
        "Points:",
        contour.count,
    )
    print(
        "Normals:",
        len(
            contour.normals
        ),
    )
    print(
        "First normal:",
        first_normal,
    )
    print(
        "Normal length:",
        normal_length,
    )
    print("Valid: OK")
    print()


if __name__ == "__main__":
    main()