from kernel.contracts.placement import Placement
from kernel.contracts.surface import (
    Surface,
    SurfaceType,
)
from kernel.providers.circle_definition_provider import (
    CircleDefinitionProvider,
)
from kernel.contracts.provider_request import (
    ProviderRequest,
)
from kernel.services.geometry_projection_engine import (
    GeometryProjectionEngine,
)


def main() -> None:
    definitions = (
        CircleDefinitionProvider().execute(
            ProviderRequest(
                provider=(
                    "circle_definition"
                ),
                parameters={
                    "radius": 10.0,
                    "samples": 64,
                },
            )
        )
    )

    engine = GeometryProjectionEngine()

    plane_result = engine.project(
        contours=definitions,
        placement=Placement(
            position=(
                5.0,
                10.0,
                2.0,
            ),
        ),
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

    cylinder_result = engine.project(
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

    first_cylinder_point = (
        cylinder_result
        .contours[0]
        .points[0]
    )

    print()
    print("DOBO Geometry Projection Engine")
    print("-------------------------------")
    print(
        "Plane contours:",
        plane_result.count,
    )
    print(
        "Plane points:",
        plane_result.point_count,
    )
    print(
        "Cylinder contours:",
        cylinder_result.count,
    )
    print(
        "Cylinder points:",
        cylinder_result.point_count,
    )
    print(
        "First cylinder point:",
        first_cylinder_point.tuple,
    )
    print(
        "Valid: OK"
    )
    print()


if __name__ == "__main__":
    main()