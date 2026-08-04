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
from kernel.contracts.model_state import ModelState
from kernel.contracts.placement import Placement
from kernel.contracts.surface import (
    Surface,
    SurfaceType,
)
from kernel.pipeline.pipeline import KernelPipeline
from kernel.providers.circle_provider import (
    CircleProvider,
)
from kernel.providers.polygon_provider import (
    PolygonProvider,
)
from kernel.providers.registry import (
    ProviderRegistry,
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
    """
    Creates the Provider Registry used by the test.
    """

    registry = ProviderRegistry()

    registry.register_provider(CircleProvider())

    registry.register_provider(PolygonProvider())

    return registry


def build_pipeline(
    registry: ProviderRegistry,
) -> KernelPipeline:
    """
    Creates the complete Kernel Pipeline.
    """

    return KernelPipeline(
        provider_registry=registry,
        surface_engine=SurfaceEngine(),
        extrusion_engine=ExtrusionEngine(),
        boolean_engine=BooleanEngine(),
    )


def build_circle_configuration() -> Configuration:
    """
    Creates a circle configuration that initializes
    the ModelState.
    """

    return Configuration(
        project_name="Circle Pipeline Test",
        provider=ProviderConfiguration(
            name="circle",
            parameters={
                "radius": 20.0,
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
                depth=10.0,
            ),
        ),
        boolean=BooleanConfiguration(
            operation=BooleanOperation.UNION,
            label="Initialize circle model",
        ),
    )


def build_polygon_configuration() -> Configuration:
    """
    Creates a polygon configuration that is added
    to the existing ModelState.
    """

    return Configuration(
        project_name="Polygon Pipeline Test",
        provider=ProviderConfiguration(
            name="polygon",
            parameters={
                "sides": 6,
                "diameter": 30.0,
                "rotation_degrees": 30.0,
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
            placement=Placement(
                position=(
                    15.0,
                    0.0,
                    0.0,
                ),
            ),
        ),
        extrusion=ExtrusionConfiguration(
            profile=ExtrusionProfile(
                depth=10.0,
            ),
        ),
        boolean=BooleanConfiguration(
            operation=BooleanOperation.UNION,
            label="Union polygon model",
        ),
    )


def main() -> None:
    registry = build_registry()

    pipeline = build_pipeline(registry)

    initial_model = ModelState()

    circle_result = pipeline.execute(
        configuration=(build_circle_configuration()),
        model=initial_model,
    )

    polygon_result = pipeline.execute(
        configuration=(build_polygon_configuration()),
        model=circle_result.model,
    )

    print()
    print("DOBO Kernel Pipeline")
    print("--------------------")
    print(
        "Circle contours:",
        circle_result.provider_result.contours.count,
    )
    print(
        "Polygon contours:",
        polygon_result.provider_result.contours.count,
    )
    print(
        "Registered providers:",
        registry.names(),
    )
    print(
        "Final model version:",
        polygon_result.model.version,
    )
    print(
        "Final operations:",
        polygon_result.model.operation_count,
    )
    print(
        "Final model empty:",
        polygon_result.model.is_empty,
    )
    print(
        "Circle stages:",
        circle_result.context.stage_count,
    )
    print(
        "Polygon stages:",
        polygon_result.context.stage_count,
    )
    print()


if __name__ == "__main__":
    main()
