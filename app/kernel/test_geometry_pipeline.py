import os

import cadquery as cq

from kernel.contracts.placement import Placement
from kernel.contracts.surface import (
    Surface,
    SurfaceType,
)
from kernel.pipeline.geometry_pipeline import (
    GeometryPipeline,
)
from kernel.providers.circle_definition_provider import (
    CircleDefinitionProvider,
)
from kernel.providers.definition_registry import (
    DefinitionProviderRegistry,
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


def build_registry() -> DefinitionProviderRegistry:
    registry = DefinitionProviderRegistry()

    registry.register_provider(
        CircleDefinitionProvider()
    )

    return registry


def export_shape(
    geometry: object,
    filename: str,
) -> str:
    if not isinstance(
        geometry,
        cq.Shape,
    ):
        raise TypeError(
            "GeometryPipeline test requires "
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
    pipeline = GeometryPipeline(
        provider_registry=build_registry(),
        projection_engine=(
            GeometryProjectionEngine()
        ),
        offset_engine=OffsetEngine(),
        solid_builder=OffsetSolidBuilder(),
    )

    plane_result = pipeline.execute(
        provider_name="circle_definition",
        provider_parameters={
            "radius": 10.0,
            "samples": 64,
        },
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
        offset_distance=4.0,
    )

    cylinder_result = pipeline.execute(
        provider_name="circle_definition",
        provider_parameters={
            "radius": 10.0,
            "samples": 64,
        },
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
        offset_distance=4.0,
    )

    plane_path = export_shape(
        plane_result.solid.geometry,
        "geometry_pipeline_plane.step",
    )

    cylinder_path = export_shape(
        cylinder_result.solid.geometry,
        "geometry_pipeline_cylinder.step",
    )

    print()
    print("DOBO Geometry Pipeline")
    print("----------------------")
    print(
        "Plane definitions:",
        plane_result.definitions.point_count,
    )
    print(
        "Plane projected:",
        plane_result.projected.point_count,
    )
    print(
        "Plane offset:",
        plane_result.offset.point_count,
    )
    print(
        "Plane valid:",
        plane_result.solid.is_valid,
    )
    print(
        "Cylinder definitions:",
        cylinder_result.definitions.point_count,
    )
    print(
        "Cylinder projected:",
        cylinder_result.projected.point_count,
    )
    print(
        "Cylinder offset:",
        cylinder_result.offset.point_count,
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