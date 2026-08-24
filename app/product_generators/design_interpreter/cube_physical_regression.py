from __future__ import annotations

import json
from pathlib import Path

import trimesh

from .semantic_parser import SemanticProgramParser
from .semantic_surface_bridge import SemanticSurfaceIntentBridge
from .structural_pipeline import DoboStructuralPipeline


def run(output_root: str | Path = "outputs-ci/cube-physical-regression") -> dict:
    fixture = Path(__file__).with_name("fixtures") / "primitive_cube.semantic.json"
    semantic = SemanticProgramParser().parse_file(fixture)
    semantic.validate()
    intents = SemanticSurfaceIntentBridge.compile(semantic)
    result = DoboStructuralPipeline().generate_from_semantic(
        semantic,
        output_root=output_root,
        interpreter_version="validated-live-fixture",
        model="not-used",
        response_id="not-used",
        surface_intents=intents,
    )
    result.validate()
    mesh = trimesh.load_mesh(result.stl_path, process=True)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    motor = json.loads(Path(result.motor_path).read_text(encoding="utf-8"))
    morphology = motor.get("morphogenesis", {}).get("profile")
    report = {
        "morphology_profile": morphology,
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "stl": result.stl_path,
        "three_mf": result.three_mf_path,
    }
    target = Path(output_root) / "CUBE_PHYSICAL_REGRESSION.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if morphology != "cuboid":
        raise RuntimeError(f"Cube morphology regressed: {morphology!r}")
    if not mesh.is_watertight:
        raise RuntimeError("Cube physical regression failed: mesh is not watertight")
    if not mesh.is_winding_consistent:
        raise RuntimeError("Cube physical regression failed: winding is inconsistent")
    return report


if __name__ == "__main__":
    run()
