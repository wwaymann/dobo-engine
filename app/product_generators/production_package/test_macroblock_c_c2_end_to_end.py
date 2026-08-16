from __future__ import annotations

import json
import os
from pathlib import Path
import trimesh

from product_generators.surface_designer.v2_prototype_1 import build_v2_prototype_1
from product_generators.surface_designer.v2_prototype_1_spec import V2Prototype1Parser
from product_generators.design_interpreter.three_mf_export import ThreeMFMeshExporter

from .bundle import ProductionPackageBuilder
from .content_addressed import ContentAddressedPackageWriter
from .render_contract import RenderContract, RenderIntent
from .render_executor import DeterministicRenderExecutor

SPEC_PATH = Path(__file__).resolve().parents[1] / "surface_designer" / "v2_prototype_1_dobo.json"
B_CHECKPOINT = "b9ceaddf89b31d0b9cbd50f07657dc56ad355d72"


def _canonical_manufacturing_mesh(stl_path: str | Path) -> trimesh.Trimesh:
    """Load exported STL as a welded production mesh for topology validation.

    STL stores triangles independently and may duplicate vertices at every face.
    ``process=True`` performs Trimesh's deterministic vertex welding and normal
    cleanup before we evaluate connectivity/watertightness. This does not repair
    open geometry: genuine holes or disconnected shells remain invalid.
    """
    loaded = trimesh.load_mesh(stl_path, process=True)
    if isinstance(loaded, trimesh.Scene):
        geometry = tuple(loaded.geometry.values())
        if not geometry:
            raise RuntimeError("Production STL contains no mesh geometry.")
        loaded = trimesh.util.concatenate(geometry)
        loaded.process(validate=True)
    if not isinstance(loaded, trimesh.Trimesh):
        raise RuntimeError(f"Unsupported production mesh type: {type(loaded)!r}")
    loaded.process(validate=True)
    if len(loaded.vertices) <= 0 or len(loaded.faces) <= 0:
        raise RuntimeError("Canonical production mesh is empty.")
    return loaded


def main() -> None:
    motor_revision = os.environ.get("DOBO_MOTOR_SOURCE_REVISION", "unknown-local-revision").strip()
    if not motor_revision:
        raise RuntimeError("Motor/source revision is empty.")

    specification = V2Prototype1Parser().parse_file(SPEC_PATH)
    generated = build_v2_prototype_1(specification)
    if not generated.shape.isValid() or generated.solid_count != 1:
        raise RuntimeError("Generated CAD product is not one valid solid.")
    output = Path(generated.stl_path).parent

    contract = RenderContract.standard(RenderIntent.PRODUCTION)
    renders = DeterministicRenderExecutor.execute(
        generated.stl_path,
        contract,
        output / "c2_renders",
    )
    if len(renders) != len(contract.views):
        raise RuntimeError("Render executor did not satisfy the complete contract.")

    mesh = _canonical_manufacturing_mesh(generated.stl_path)
    three_mf_path = output / "v2_prototype_1_c2.3mf"
    exported = ThreeMFMeshExporter.export(
        mesh,
        three_mf_path,
        name="v2_prototype_1_c2",
    )

    components = tuple(mesh.split(only_watertight=False))
    manufacturing_path = output / "manufacturing_evidence_c2.json"
    manufacturing_path.write_text(
        json.dumps(
            {
                "schema_version": "dobo.manufacturing-evidence.v1",
                "macroblock_b_checkpoint": B_CHECKPOINT,
                "cad_valid": bool(generated.shape.isValid()),
                "cad_solid_count": int(generated.solid_count),
                "mesh_processing": "trimesh-process-validate",
                "watertight": bool(mesh.is_watertight),
                "winding_consistent": bool(mesh.is_winding_consistent),
                "component_count": len(components),
                "volume_mm3": float(abs(mesh.volume)),
                "vertex_count": int(len(mesh.vertices)),
                "face_count": int(len(mesh.faces)),
                "source_stl": Path(generated.stl_path).name,
                "three_mf": Path(exported.path).name,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    provenance_path = output / "production_provenance_c3.json"
    provenance_path.write_text(
        json.dumps(
            {
                "schema_version": "dobo.production-provenance.v1",
                "motor_source_revision": motor_revision,
                "macroblock_b_checkpoint": B_CHECKPOINT,
                "source_json": SPEC_PATH.name,
                "render_contract_version": contract.schema_version,
                "motor_stage": "macroblock-c.C3",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    artifacts = {
        "stl": generated.stl_path,
        "3mf": exported.path,
        "manufacturing_evidence": manufacturing_path,
        "production_provenance": provenance_path,
    }
    for render in renders:
        artifacts[f"render_{render.view_name}"] = render.path

    required = (
        "stl",
        "3mf",
        "manufacturing_evidence",
        "production_provenance",
    ) + tuple(f"render_{view.name}" for view in contract.views)
    manifest = ProductionPackageBuilder().build(
        source_specification=SPEC_PATH,
        motor_version="macroblock-c.C3",
        source_revision=f"git:{motor_revision};macroblock-b:{B_CHECKPOINT}",
        artifacts=artifacts,
        render_contract=contract,
        required_artifacts=required,
    )
    package_root = ContentAddressedPackageWriter.materialize(
        manifest,
        source_specification=SPEC_PATH,
        output_root=output / "production_packages",
    )

    if package_root.name != manifest.package_sha256:
        raise RuntimeError("Package directory is not content-addressed.")
    if not (package_root / "source" / SPEC_PATH.name).is_file():
        raise RuntimeError("Source JSON was not preserved in production package.")
    if len(tuple((package_root / "artifacts").iterdir())) != len(manifest.artifacts):
        raise RuntimeError("Materialized package lost production artifacts.")

    print("DOBO Macroblock C - End-to-End C3")
    print("-----------------------------------")
    print("Macroblock B checkpoint", B_CHECKPOINT, "PRESERVED")
    print("Motor/source revision", motor_revision, "BOUND")
    print("deterministic render views", len(renders), "OK")
    print("CAD solid", generated.solid_count, "VALID")
    print("manufacturing mesh watertight", mesh.is_watertight, "OK")
    print("manufacturing mesh winding", mesh.is_winding_consistent, "OK")
    print("manufacturing mesh components", len(components), "OK")
    print("STL + 3MF", "OK")
    print("manufacturing evidence", manufacturing_path.name, "OK")
    print("provenance evidence", provenance_path.name, "OK")
    print("source JSON preserved", SPEC_PATH.name, "OK")
    print("content-addressed package", manifest.package_sha256, "OK")
    print("package root", package_root)
    print("-----------------------------------")
    print("Macroblock C C3 End-to-End Package: Valid OK")


if __name__ == "__main__":
    main()
