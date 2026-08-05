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
    OperationType,
)
from kernel.contracts.placement import Placement
from kernel.contracts.surface import (
    Surface,
    SurfaceType,
)


def build_geometry_configuration(
    radius: float,
    position_x: float,
) -> GeometryPipelineConfiguration:
    """
    Creates one reusable geometry configuration.
    """

    return GeometryPipelineConfiguration(
        project_name="Operation Test",
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


def main() -> None:
    first_geometry = GeometryOperation(
        name="Create base circle",
        output_id="base_circle",
        configuration=(
            build_geometry_configuration(
                radius=20.0,
                position_x=0.0,
            )
        ),
        tags=(
            "base",
            "circle",
        ),
    )

    second_geometry = GeometryOperation(
        name="Create cutting circle",
        output_id="cutting_circle",
        configuration=(
            build_geometry_configuration(
                radius=8.0,
                position_x=5.0,
            )
        ),
        tags=(
            "tool",
            "circle",
        ),
    )

    boolean = BooleanOperation(
        name="Subtract cutting circle",
        mode=BooleanMode.CUT,
        target_id="base_circle",
        tool_id="cutting_circle",
        output_id="final_body",
        tolerance=0.01,
    )

    export = ExportOperation(
        name="Export final body",
        source_id="final_body",
        configuration=ExportConfiguration(
            enabled=True,
            format=ExportFormat.STEP,
            destination=(
                "outputs/kernel/"
                "operation_test.step"
            ),
        ),
        overwrite=True,
    )

    operations = (
        first_geometry,
        second_geometry,
        boolean,
        export,
    )

    for operation in operations:
        operation.validate()

    print()
    print("DOBO Kernel Operations")
    print("----------------------")
    print(
        "Operations:",
        len(
            operations
        ),
    )
    print(
        "First type:",
        first_geometry.operation_type.value,
    )
    print(
        "Second output:",
        second_geometry.output_id,
    )
    print(
        "Boolean type:",
        boolean.operation_type.value,
    )
    print(
        "Boolean mode:",
        boolean.mode.value,
    )
    print(
        "Boolean output:",
        boolean.output_id,
    )
    print(
        "Export type:",
        export.operation_type.value,
    )
    print(
        "Export format:",
        export.format_name,
    )
    print(
        "Export destination:",
        export.destination,
    )
    print(
        "Types valid:",
        (
            first_geometry.operation_type
            == OperationType.GEOMETRY
            and boolean.operation_type
            == OperationType.BOOLEAN
            and export.operation_type
            == OperationType.EXPORT
        ),
    )
    print("Valid: OK")
    print()


if __name__ == "__main__":
    main()