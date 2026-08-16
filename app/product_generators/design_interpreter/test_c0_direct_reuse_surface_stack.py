from __future__ import annotations

from pathlib import Path

import cadquery as cq

from product_generators.surface_designer.native_face_decorator import NativeFaceDecorator

from .phase_5_design_matrix import design_matrix
from .structural_pipeline import DoboStructuralPipeline


def main() -> None:
    case = next(item for item in design_matrix() if item.id == "botanical")
    output_root = Path("outputs/c0_direct_reuse_probe")

    modern = DoboStructuralPipeline().generate_from_semantic(
        case.program,
        output_root=output_root,
    )
    mesh = modern.mesh_result.mesh

    if mesh.__class__.__module__.split(".")[0] != "trimesh":
        raise RuntimeError(
            "Binary probe requires the real modern morphology output to be a trimesh mesh; "
            f"got {type(mesh)!r}."
        )

    # Build valid BRep auxiliary inputs so the only variable under test is whether
    # the existing surface stack accepts the modern morphology body directly.
    brep = cq.Workplane("XY").cylinder(10.0, 20.0).val()
    target_face = max(brep.Faces(), key=lambda face: float(face.Area()))
    planar = cq.Workplane("XY").rect(2.0, 2.0).val()

    decorator = NativeFaceDecorator()
    try:
        decorator.decorate(
            base_shape=mesh,  # intentionally the unmodified modern D output
            target_face=target_face,
            planar_shape=planar,
            mode="emboss",
            depth=1.0,
        )
    except TypeError as error:
        message = str(error)
        expected = "base_shape must be CadQuery Shape."
        if expected not in message:
            raise RuntimeError(
                "Direct reuse failed for an unexpected reason: " + message
            ) from error

        print("DOBO C0 Direct Reuse Binary Probe")
        print("---------------------------------")
        print("modern morphology type", type(mesh).__name__, "OK")
        print("existing surface stack entry", "NativeFaceDecorator.decorate")
        print("direct unmodified handoff", "FAIL")
        print("failure", message)
        print("binary verdict", "DIRECT_REUSE_INCOMPATIBLE")
        print("---------------------------------")
        return

    raise RuntimeError(
        "Binary probe unexpectedly passed: the existing BRep surface stack accepted "
        "the modern mesh body directly. Re-audit the representation boundary."
    )


if __name__ == "__main__":
    main()
