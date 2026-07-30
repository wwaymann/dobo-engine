import os
import cadquery as cq


def export_model(
    model: cq.Workplane,
    filename: str = "dobo_pot"
) -> tuple[str, str]:
    """
    Exporta un modelo en formato STEP y STL.

    Retorna las rutas de los archivos generados.
    """

    project_root = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            ".."
        )
    )

    output_directory = os.path.join(
        project_root,
        "outputs",
        "models"
    )

    os.makedirs(
        output_directory,
        exist_ok=True
    )

    step_path = os.path.join(
        output_directory,
        f"{filename}.step"
    )

    stl_path = os.path.join(
        output_directory,
        f"{filename}.stl"
    )

    cq.exporters.export(
        model,
        step_path
    )

    cq.exporters.export(
        model,
        stl_path
    )

    return step_path, stl_path