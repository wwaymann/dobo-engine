from kernel.contracts.boolean_request import (
    BooleanOperation,
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
from kernel.providers.circle_provider import (
    CircleProvider,
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
from kernel.stages.boolean_stage import (
    BooleanStage,
)
from kernel.stages.extrusion_stage import (
    ExtrusionStage,
)
from kernel.stages.provider_stage import (
    ProviderStage,
)
from kernel.stages.surface_stage import (
    SurfaceStage,
)


def build_solid(
    radius: float,
    position_x: float,
):
    registry = ProviderRegistry()
    registry.register_provider(
        CircleProvider()
    )

    provider_result = ProviderStage(
        registry=registry
    ).execute(
        provider_name="circle",
        parameters={
            "radius": radius,
        },
    )

    surface_result = SurfaceStage(
        engine=SurfaceEngine()
    ).execute(
        contours=provider_result.contours,
        placement=Placement(
            position=(
                position_x,
                0.0,
                0.0,
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

    return ExtrusionStage(
        engine=ExtrusionEngine()
    ).execute(
        placement=surface_result.placement,
        profile=ExtrusionProfile(
            depth=10.0,
        ),
    ).solid


def main() -> None:
    first_solid = build_solid(
        radius=20.0,
        position_x=0.0,
    )

    second_solid = build_solid(
        radius=12.0,
        position_x=15.0,
    )

    stage = BooleanStage(
        engine=BooleanEngine()
    )

    first_result = stage.execute(
        model=ModelState(),
        solid=first_solid,
        operation=BooleanOperation.UNION,
        label="Initialize model",
    )

    second_result = stage.execute(
        model=first_result.model,
        solid=second_solid,
        operation=BooleanOperation.UNION,
        label="Union second solid",
    )

    print()
    print("DOBO Boolean Stage")
    print("------------------")
    print(
        "Model version:",
        second_result.model.version,
    )
    print(
        "Operations:",
        second_result.model.operation_count,
    )
    print(
        "Model empty:",
        second_result.model.is_empty,
    )
    print()


if __name__ == "__main__":
    main()