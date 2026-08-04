import os

import cadquery as cq

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
from kernel.services.offset_solid_builder import (
    OffsetSolidBuilder,
)


def build_plane_offset():
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

    projected = (
        GeometryProjectionEngine().project(
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

    return OffsetEngine().offset(
        contours=projected,
        distance=4.0,
        symmetric=True,
    )


def build_cylinder_offset():
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

    projected = (
        GeometryProjectionEngine().project(
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

    return OffsetEngine().offset(
        contours=projected,
        distance=4.0,
        symmetric=True,
    )


def export_shape(
    geometry: object,
    filename: str,
) -> str:
    if not isinstance(
        geometry,
        cq.Shape,
    ):
        raise TypeError(
            "Offset solid diagnostic requires "
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
        filename,
    )

    cq.exporters.export(
        geometry,
        output_path,
    )

    return output_path


def main() -> None:
    builder = OffsetSolidBuilder()

    plane_result = builder.build(
        build_plane_offset()
    )

    cylinder_result = builder.build(
        build_cylinder_offset()
    )

    plane_path = export_shape(
        plane_result.solid.geometry,
        "offset_solid_plane.step",
    )

    cylinder_path = export_shape(
        cylinder_result.solid.geometry,
        "offset_solid_cylinder.step",
    )

    print()
    print("DOBO Offset Solid Builder")
    print("-------------------------")
    print(
        "Plane solids:",
        plane_result.count,
    )
    print(
        "Plane volume:",
        plane_result.solid.volume,
    )
    print(
        "Plane valid:",
        plane_result.solid.is_valid,
    )
    print(
        "Cylinder solids:",
        cylinder_result.count,
    )
    print(
        "Cylinder volume:",
        cylinder_result.solid.volume,
    )
    print(
        "Cylinder valid:",
        cylinder_result.solid.is_valid,
    )
    print(
        "Plane STEP:",
        plane_path,
    )
    print(
        "Cylinder STEP:",
        cylinder_path,
    )
    print()


if __name__ == "__main__":
    main()