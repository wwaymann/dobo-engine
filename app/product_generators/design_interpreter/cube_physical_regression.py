from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import trimesh

from .semantic_parser import SemanticProgramParser
from .semantic_surface_bridge import SemanticSurfaceIntentBridge
from .structural_pipeline import DoboStructuralPipeline


CASES = (
    ("cube", "primitive_cube.semantic.json", "cuboid"),
    ("rectangular", "primitive_rectangular.semantic.json", "rectangular_prism"),
)


def _mesh(path: str) -> trimesh.Trimesh:
    mesh = trimesh.load_mesh(path, process=True)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    if not isinstance(mesh, trimesh.Trimesh):
        raise RuntimeError("Angular CAD regression did not produce a mesh.")
    mesh.merge_vertices()
    mesh.remove_unreferenced_vertices()
    return mesh


def _render(mesh: trimesh.Trimesh, target: Path, elev: float, azim: float) -> None:
    vertices = np.asarray(mesh.vertices, dtype=float)
    faces = np.asarray(mesh.faces, dtype=np.int64)
    vertices = vertices - (vertices.min(axis=0) + vertices.max(axis=0)) / 2.0
    scale = float(max(np.maximum(np.ptp(vertices, axis=0), 1.0)))
    vertices = vertices / scale
    fig = plt.figure(figsize=(6.2, 6.2))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_trisurf(
        vertices[:, 0], vertices[:, 1], vertices[:, 2],
        triangles=faces, linewidth=0.02, shade=True,
    )
    ax.view_init(elev=elev, azim=azim)
    ax.set_xlim(-0.58, 0.58)
    ax.set_ylim(-0.58, 0.58)
    ax.set_zlim(-0.58, 0.58)
    ax.set_box_aspect((1, 1, 1))
    ax.set_axis_off()
    fig.tight_layout(pad=0)
    fig.savefig(target, dpi=180, bbox_inches="tight", pad_inches=0)
    plt.close(fig)


def _outer_top_corners_present(
    mesh: trimesh.Trimesh,
    width: float,
    depth: float,
    height: float,
    tolerance: float = 0.2,
) -> bool:
    vertices = np.asarray(mesh.vertices, dtype=float)
    targets = np.asarray([
        [sx * 0.5 * width, sy * 0.5 * depth, height]
        for sx in (-1.0, 1.0)
        for sy in (-1.0, 1.0)
    ])
    for target in targets:
        distances = np.linalg.norm(vertices - target, axis=1)
        if float(np.min(distances)) > tolerance:
            return False
    return True


def _case(
    case_id: str,
    fixture_name: str,
    expected_morphology: str,
    output_root: Path,
) -> dict:
    fixture = Path(__file__).with_name("fixtures") / fixture_name
    semantic = SemanticProgramParser().parse_file(fixture)
    semantic.validate()
    intents = SemanticSurfaceIntentBridge.compile(semantic)
    case_root = output_root / case_id
    result = DoboStructuralPipeline().generate_from_semantic(
        semantic,
        output_root=case_root,
        interpreter_version="validated-angular-fixture",
        model="not-used",
        response_id="not-used",
        surface_intents=intents,
    )
    result.validate()

    mesh = _mesh(result.stl_path)
    motor = json.loads(Path(result.motor_path).read_text(encoding="utf-8"))
    morphology = motor.get("morphogenesis", {}).get("profile")
    route = motor.get("_capability_route")
    components = len(tuple(mesh.split(only_watertight=False)))
    expected = np.asarray([
        float(semantic.body.width_mm),
        float(semantic.body.depth_mm),
        float(semantic.body.height_mm),
    ])
    extents = np.asarray(mesh.extents, dtype=float)
    extent_error = np.abs(extents - expected)
    dimension_match = bool(np.all(extent_error <= 0.2))
    top_corners = _outer_top_corners_present(
        mesh,
        expected[0],
        expected[1],
        expected[2],
    )
    semantic_checks = dict(getattr(result.mesh_result, "semantic_checks", {}))
    cavity_real = bool(semantic_checks.get("cavity_is_empty", False))
    opening_real = bool(semantic_checks.get("opening_is_clear", False))
    drain_real = bool(semantic_checks.get("drain_is_clear", False))
    wall_real = bool(semantic_checks.get("wall_is_solid", False))
    base_real = bool(semantic_checks.get("base_is_solid", False))

    case_root.mkdir(parents=True, exist_ok=True)
    iso_path = case_root / f"{case_id}_iso.png"
    top_path = case_root / f"{case_id}_top.png"
    front_path = case_root / f"{case_id}_front.png"
    side_path = case_root / f"{case_id}_side.png"
    _render(mesh, iso_path, 28, 42)
    _render(mesh, top_path, 90, -90)
    _render(mesh, front_path, 0, 0)
    _render(mesh, side_path, 0, 90)

    checks = {
        "native_cad_route": route == "analytic_cad_angular_primitive",
        "morphology_correct": morphology == expected_morphology,
        "dimension_match": dimension_match,
        "outer_top_corners_present": top_corners,
        "cavity_real": cavity_real,
        "opening_real": opening_real,
        "drain_real": drain_real,
        "wall_real": wall_real,
        "base_real": base_real,
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "single_component": components == 1,
    }
    report = {
        "case": case_id,
        "morphology_profile": morphology,
        "capability_route": route,
        "expected_extents_mm": expected.tolist(),
        "mesh_extents_mm": extents.tolist(),
        "extent_error_mm": extent_error.tolist(),
        "component_count": components,
        "semantic_checks": semantic_checks,
        "checks": checks,
        "pass": all(checks.values()),
        "stl": result.stl_path,
        "three_mf": result.three_mf_path,
        "renders": {
            "iso": str(iso_path),
            "top": str(top_path),
            "front": str(front_path),
            "side": str(side_path),
        },
    }
    (case_root / f"{case_id.upper()}_CAD_AUDIT.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    if not report["pass"]:
        failed = [name for name, passed in checks.items() if not passed]
        raise RuntimeError(f"{case_id} angular CAD regression failed: {failed}")
    return report


def run(output_root: str | Path = "outputs-ci/cube-physical-regression") -> dict:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    reports = [
        _case(case_id, fixture, morphology, root)
        for case_id, fixture, morphology in CASES
    ]
    summary = {
        "schema": "dobo.angular_cad_physical_regression.1",
        "case_count": len(reports),
        "pass": sum(bool(report["pass"]) for report in reports),
        "cases": reports,
    }
    target = root / "ANGULAR_CAD_PHYSICAL_REGRESSION.json"
    target.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if summary["pass"] != len(CASES):
        raise RuntimeError("Angular CAD physical regression did not fully pass.")
    return summary


if __name__ == "__main__":
    run()
