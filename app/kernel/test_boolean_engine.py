import os

import cadquery as cq

from kernel.contracts.boolean_request import (
    BooleanOperation,
    BooleanRequest,
)
from kernel.contracts.extrusion_profile import (
    ExtrusionProfile,
)
from kernel.contracts.model_state import ModelState
from kernel.contracts.placement import Placement
from kernel.contracts.provider_request import (
    ProviderRequest,
)
from kernel.contracts.solid import Solid
from kernel.contracts.surface import (
    Surface,
    SurfaceType,
)
from kernel.providers.circle_provider import (
    CircleProvider,
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


def build_cylinder(
    radius: float,
    depth: float,
    position_x: float,
) -> Solid:
    """
    Generates a cylindrical Solid using the complete
    Provider, Surface and Extrusion flow.
    """

    provider = CircleProvider()

    contours = provider.execute(
        ProviderRequest(
            provider="circle",
            parameters={
                "radius": radius,
            },
        )
    )

    surface_placement = SurfaceEngine().place(
        contours=contours,
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

    solid = ExtrusionEngine().extrude(
        placement=surface_placement,
        profile=ExtrusionProfile(
            depth=depth,
        ),
    )

    return solid


def main() -> None:
    first_solid = build_cylinder(
        radius=20.0,
        depth=10.0,
        position_x=0.0,
    )

    second_solid = build_cylinder(
        radius=12.0,
        depth=10.0,
        position_x=15.0,
    )

    engine = BooleanEngine()

    model = engine.apply(
        model=ModelState(),
        request=BooleanRequest(
            operation=BooleanOperation.UNION,
            operand=first_solid,
            label="Initialize model",
        ),
    )

    model = engine.apply(
        model=model,
        request=BooleanRequest(
            operation=BooleanOperation.UNION,
            operand=second_solid,
            label="Union second cylinder",
        ),
    )

    if model.solid is None:
        raise RuntimeError(
            "Boolean test produced an empty model."
        )

    result_geometry = model.solid.geometry

    if not isinstance(
        result_geometry,
        cq.Shape,
    ):
        raise TypeError(
            "Boolean result geometry must be "
            "a CadQuery Shape."
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
        "boolean_union.step",
    )

    cq.exporters.export(
        result_geometry,
        output_path,
    )

    print()
    print("DOBO Boolean Engine")
    print("-------------------")
    print("Model empty:", model.is_empty)
    print("Version:", model.version)
    print(
        "Operations:",
        model.operation_count,
    )
    print(
        "Volume:",
        model.solid.volume,
    )
    print("STEP:", output_path)
    print()


if __name__ == "__main__":
    main()