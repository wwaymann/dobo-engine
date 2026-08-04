import math

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
from kernel.services.offset_engine import (
    OffsetEngine,
)


def distance(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
) -> float:
    return math.sqrt(
        (
            second[0]
            - first[0]
        )
        ** 2
        + (
            second[1]
            - first[1]
        )
        ** 2
        + (
            second[2]
            - first[2]
        )
        ** 2
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

    projection_engine = (
        GeometryProjectionEngine()
    )

    offset_engine = OffsetEngine()

    plane_projection = (
        projection_engine.project(
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
    )

    plane_offset = offset_engine.offset(
        contours=plane_projection,
        distance=4.0,
        symmetric=True,
    )

    cylinder_projection = (
        projection_engine.project(
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
    )

    cylinder_offset = offset_engine.offset(
        contours=cylinder_projection,
        distance=4.0,
        symmetric=True,
    )

    plane_first = (
        plane_offset
        .contours[0]
        .points[0]
    )

    cylinder_first = (
        cylinder_offset
        .contours[0]
        .points[0]
    )

    plane_thickness = distance(
        plane_first.inner_tuple,
        plane_first.outer_tuple,
    )

    cylinder_thickness = distance(
        cylinder_first.inner_tuple,
        cylinder_first.outer_tuple,
    )

    print()
    print("DOBO Offset Engine")
    print("------------------")
    print(
        "Plane contours:",
        plane_offset.count,
    )
    print(
        "Plane points:",
        plane_offset.point_count,
    )
    print(
        "Plane thickness:",
        plane_thickness,
    )
    print(
        "Cylinder contours:",
        cylinder_offset.count,
    )
    print(
        "Cylinder points:",
        cylinder_offset.point_count,
    )
    print(
        "Cylinder thickness:",
        cylinder_thickness,
    )
    print(
        "First cylinder inner:",
        cylinder_first.inner_tuple,
    )
    print(
        "First cylinder outer:",
        cylinder_first.outer_tuple,
    )
    print("Valid: OK")
    print()


if __name__ == "__main__":
    main()