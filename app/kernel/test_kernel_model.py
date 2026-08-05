from kernel.contracts.boolean_request import (
    BooleanOperation as BooleanMode,
)
from kernel.contracts.config import (
    ExportConfiguration,
    ExportFormat,
    GeometryPipelineConfiguration,
    OffsetConfiguration,
    ProviderConfiguration,
    SurfaceConfiguration,
)
from kernel.contracts.operations import (
    BooleanOperation,
    ExportOperation,
    GeometryOperation,
)
from kernel.contracts.placement import Placement
from kernel.contracts.surface import (
    Surface,
    SurfaceType,
)
from kernel.core.kernel_model import KernelModel


def build_geometry_operation(
    output_id: str,
    radius: float,
    position_x: float,
) -> GeometryOperation:
    """
    Creates one reusable geometry operation.
    """

    configuration = GeometryPipelineConfiguration(
        project_name="Kernel Model Test",
        provider=ProviderConfiguration(
            name="circle_definition",
            parameters={
                "radius": radius,
                "samples": 64,
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
                    position_x,
                    0.0,
                    0.0,
                ),
            ),
        ),
        offset=OffsetConfiguration(
            distance=4.0,
            symmetric=True,
        ),
    )

    return GeometryOperation(
        name=f"Create {output_id}",
        output_id=output_id,
        configuration=configuration,
    )


def main() -> None:
    model = KernelModel(
        name="Parametric Circle Model",
        metadata={
            "test": True,
        },
    )

    model.add_operation(
        build_geometry_operation(
            output_id="base_circle",
            radius=20.0,
            position_x=0.0,
        )
    )

    model.add_operation(
        build_geometry_operation(
            output_id="cutting_circle",
            radius=8.0,
            position_x=5.0,
        )
    )

    model.add_operation(
        BooleanOperation(
            name="Cut center",
            mode=BooleanMode.CUT,
            target_id="base_circle",
            tool_id="cutting_circle",
            output_id="final_body",
        )
    )

    model.add_operation(
        ExportOperation(
            name="Export final body",
            source_id="final_body",
            configuration=ExportConfiguration(
                enabled=True,
                format=ExportFormat.STEP,
                destination=(
                    "outputs/kernel/"
                    "kernel_model.step"
                ),
            ),
            overwrite=True,
        )
    )

    model.validate()

    print()
    print("DOBO Kernel Model")
    print("-----------------")
    print(
        "Name:",
        model.name,
    )
    print(
        "Operations:",
        model.count,
    )
    print(
        "Enabled:",
        model.enabled_count,
    )
    print(
        "Outputs:",
        model.output_ids,
    )
    print(
        "First operation:",
        model.operations[0].display_name,
    )
    print(
        "Final operation:",
        model.operations[-1].display_name,
    )
    print("Valid: OK")
    print()


if __name__ == "__main__":
    main()