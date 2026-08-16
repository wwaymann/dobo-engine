from __future__ import annotations

from pathlib import Path

from kernel.geometry.mesh_brep_conversion import trimesh_to_brep
from product_generators.surface_designer.native_text_face import NativeTextFaceDecorator

from .phase_5_design_matrix import design_matrix
from .structural_pipeline import DoboStructuralPipeline


def main() -> None:
    case = next(item for item in design_matrix() if item.id == "geometric")
    modern = DoboStructuralPipeline().generate_from_semantic(
        case.program,
        output_root=Path("outputs/c0_mesh_brep_probe"),
    )
    mesh = modern.mesh_result.mesh

    converted = trimesh_to_brep(mesh)
    converted.validate()

    target_face = max(converted.shape.Faces(), key=lambda face: float(face.Area()))
    decorator = NativeTextFaceDecorator()
    decorated = decorator.decorate(
        base_shape=converted.shape,
        target_face=target_face,
        text_value="D",
        size=3.0,
        mode="emboss",
        depth=0.30,
        width_fraction=0.50,
        height_fraction=0.50,
    )
    decorated.validate()

    if decorated.final_volume <= decorated.base_volume:
        raise RuntimeError("Existing text emboss did not add material after conversion.")

    print("DOBO C0 Mesh -> BRep Existing Stack Probe")
    print("------------------------------------------")
    print("modern vertices", converted.input_vertices, "OK")
    print("modern faces", converted.input_faces, "OK")
    print("converted BRep faces", converted.brep_faces, "OK")
    print("converted solids", converted.solids, "OK")
    print("existing NativeTextFaceDecorator", "PASS")
    print("text emboss volume increase", decorated.final_volume - decorated.base_volume, "OK")
    print("binary verdict", "MINIMAL_BREP_REUSE_COMPATIBLE")
    print("------------------------------------------")


if __name__ == "__main__":
    main()
