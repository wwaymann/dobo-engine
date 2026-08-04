import os

import cadquery as cq

from kernel.contracts.boolean_request import (
    BooleanOperation,
)
from kernel.contracts.config import (
    BooleanConfiguration,
    ExtrusionConfiguration,
    ProviderConfiguration,
    SurfaceConfiguration,
)
from kernel.contracts.configuration import (
    Configuration,
)
from kernel.contracts.extrusion_profile import (
    ExtrusionProfile,
)
from kernel.contracts.placement import Placement
from kernel.contracts.surface import (
    Surface,
    SurfaceType,
)
from kernel.pipeline.pipeline import (
    KernelPipeline,
)
from kernel.providers.circle_provider import (
    CircleProvider,
)
from kernel.providers.polygon_provider import (
    PolygonProvider,
)
from kernel.providers.registry import (
    ProviderRegistry,
)
from kernel.providers.svg_provider import (
    SVGProvider,
)
from kernel.services.boolean_engine import (
    BooleanEngine,
)
from kernel.services.extrusion_engine import (
    ExtrusionEngine,
)
from kernel.services.surface_engine import (
    SurfaceEngine,
)


def build_registry() -> ProviderRegistry:
    registry = ProviderRegistry()

    registry.register_provider(
        CircleProvider()
    )

    registry.register_provider(
        PolygonProvider()
    )

    registry.register_provider(
        SVGProvider()
    )

    return registry


def main() -> None:
    pipeline = KernelPipeline(
        provider_registry=build_registry(),
        surface_engine=SurfaceEngine(),
        extrusion_engine=ExtrusionEngine(),
        boolean_engine=BooleanEngine(),
    )

    configuration = Configuration(
        project_name="Kernel Pipeline Test",
        provider=ProviderConfiguration(
            name="svg",
            parameters={
                "file": (
                    "assets/svg/test.svg"
                ),
                "width": 30.0,
                "samples_per_path": 128,
                "flip_y": True,
            },
        ),
        surface=SurfaceConfiguration(
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
            placement=Placement(),
        ),
        extrusion=ExtrusionConfiguration(
            profile=ExtrusionProfile(
                depth=3.0,
            ),
        ),
        boolean=BooleanConfiguration(
            operation=(
                BooleanOperation.UNION
            ),
            label="Initialize SVG model",
        ),
    )

    result = pipeline.execute(
        configuration
    )

    if result.model.solid is None:
        raise RuntimeError(
            "KernelPipeline returned "
            "an empty ModelState."
        )

    geometry = (
        result.model.solid.geometry
    )

    if not isinstance(
        geometry,
        cq.Shape,
    ):
        raise TypeError(
            "KernelPipeline result geometry "
            "must be a CadQuery Shape."
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
        "kernel_pipeline.step",
    )

    cq.exporters.export(
        geometry,
        output_path,
    )

    print()
    print("DOBO Kernel Pipeline")
    print("--------------------")
    print(
        "Model version:",
        result.model.version,
    )
    print(
        "Model operations:",
        result.model.operation_count,
    )
    print(
        "Provider:",
        result.provider_result.request.provider,
    )
    print(
        "Contours:",
        result.provider_result.contours.count,
    )
    print(
        "Stages:",
        result.context.stage_count,
    )
    print(
        "Duration ms:",
        result.context.duration_ms,
    )
    print(
        "Solid valid:",
        result.extrusion_result.solid.is_valid,
    )
    print(
        "STEP:",
        output_path,
    )
    print()


if __name__ == "__main__":
    main()