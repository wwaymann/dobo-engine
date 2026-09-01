from __future__ import annotations

from dataclasses import replace
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import trimesh

from .semantic_contract import FeatureIntent, FeatureSizeIntent, SemanticAnchor
from .semantic_parser import SemanticProgramParser
from .semantic_surface_bridge import SemanticSurfaceIntentBridge
from .structural_pipeline import DoboStructuralPipeline


CASES = (
    ("cube_emboss", "primitive_cube.semantic.json", "raised", "cuboid"),
    ("rectangular_deboss", "primitive_rectangular.semantic.json", "recessed", "rectangular_prism"),
)


def _mesh(path: str) -> trimesh.Trimesh:
    mesh = trimesh.load_mesh(path, process=True)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    if not isinstance(mesh, trimesh.Trimesh):
        raise RuntimeError("Angular native text regression produced no mesh.")
    mesh.merge_vertices()
    mesh.remove_unreferenced_vertices()
    return mesh


def _render(mesh: trimesh.Trimesh, target: Path) -> None:
    vertices = np.asarray(mesh.vertices, dtype=float)
    faces = np.asarray(mesh.faces, dtype=np.int64)
    vertices = vertices - (vertices.min(axis=0) + vertices.max(axis=0)) / 2.0
    scale = float(max(np.maximum(np.ptp(vertices, axis=0), 1.0)))
    vertices = vertices / scale
    fig = plt.figure(figsize=(6.2, 6.2))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_trisurf(
        vertices[:, 0], vertices[:, 1], vertices[:, 2],
        triangles=faces, linewidth=0.01, shade=True,
    )
    ax.view_init(elev=18, azim=-42)
    ax.set_xlim(-0.58, 0.58)
    ax.set_ylim(-0.58, 0.58)
    ax.set_zlim(-0.58, 0.58)
    ax.set_box_aspect((1, 1, 1))
    ax.set_axis_off()
    fig.tight_layout(pad=0)
    fig.savefig(target, dpi=180, bbox_inches="tight", pad_inches=0)
    plt.close(fig)


def _program_with_text(fixture_name: str, surface_effect: str):
    fixture = Path(__file__).with_name("fixtures") / fixture_name
    base = SemanticProgramParser().parse_file(fixture)
    feature = FeatureIntent(
        id="walter_text",
        concept="walter_text",
        form_hint="text",
        surface_effect=surface_effect,
        anchor=SemanticAnchor(region="front", horizontal=0.0, vertical=0.5),
        size=FeatureSizeIntent(width_ratio=0.62, height_ratio=0.15, depth_mm=1.2),
        priority="required",
        can_omit=False,
        confidence=1.0,
    )
    program = replace(base, features=(feature,))
    program.validate()
    return program


def _case(case_id: str, fixture: str, effect: str, expected_morphology: str, root: Path) -> dict:
    program = _program_with_text(fixture, effect)
    intents = SemanticSurfaceIntentBridge.compile(program)
    result = DoboStructuralPipeline().generate_from_semantic(
        program,
        output_root=root / case_id,
        interpreter_version="validated-angular-native-text-fixture",
        model="not-used",
        response_id="not-used",
        surface_intents=intents,
    )
    result.validate()
    motor = json.loads(Path(result.motor_path).read_text(encoding="utf-8"))
    route = motor.get("_analytic_angular", {})
    mesh = _mesh(result.stl_path)
    width = float(route["width_mm"])
    depth = float(route["depth_mm"])
    height = float(route["height_mm"])
    wall = float(route["wall_mm"])
    bottom = float(route["bottom_mm"])
    drain_diameter = float(route["drain_diameter_mm"])
    base_volume = (
        width * depth * height
        - (width - 2.0 * wall) * (depth - 2.0 * wall) * (height - bottom)
        - math.pi * (0.5 * drain_diameter) ** 2 * bottom
    )
    mode = "deboss" if effect == "recessed" else "emboss"
    volume_direction = (
        float(abs(mesh.volume)) < base_volume - 1e-3
        if mode == "deboss"
        else float(abs(mesh.volume)) > base_volume + 1e-3
    )
    checks = dict(result.mesh_result.semantic_checks)
    physical = {
        "native_cad_route": motor.get("_capability_route") == "analytic_cad_angular_primitive",
        "morphology_correct": motor.get("morphogenesis", {}).get("profile") == expected_morphology,
        "native_text_present": len(route.get("text_entries", [])) == 1,
        "literal_is_walter": route.get("text_entries", [{}])[0].get("literal") == "WALTER",
        "mode_correct": route.get("text_entries", [{}])[0].get("mode") == mode,
        "text_volume_direction": bool(volume_direction),
        "native_text_volume_changed": bool(checks.get("native_text_volume_changed")),
        "cavity_real": bool(checks.get("cavity_is_empty")),
        "opening_real": bool(checks.get("opening_is_clear")),
        "drain_real": bool(checks.get("drain_is_clear")),
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "single_component": len(tuple(mesh.split(only_watertight=False))) == 1,
    }
    case_root = root / case_id
    case_root.mkdir(parents=True, exist_ok=True)
    render_path = case_root / f"{case_id}.png"
    _render(mesh, render_path)
    report = {
        "case": case_id,
        "mode": mode,
        "capability_route": motor.get("_capability_route"),
        "morphology": motor.get("morphogenesis", {}).get("profile"),
        "base_volume_mm3": base_volume,
        "final_volume_mm3": float(abs(mesh.volume)),
        "mesh_extents_mm": np.asarray(mesh.extents, float).tolist(),
        "checks": physical,
        "pass": all(physical.values()),
        "stl": result.stl_path,
        "three_mf": result.three_mf_path,
        "render": str(render_path),
    }
    (case_root / f"{case_id.upper()}_AUDIT.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    if not report["pass"]:
        failed = [name for name, value in physical.items() if not value]
        raise RuntimeError(f"{case_id} native angular text failed: {failed}")
    return report


def run(output_root: str | Path = "outputs-ci/angular-native-text-regression") -> dict:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    reports = [_case(*case, root) for case in CASES]
    summary = {
        "schema": "dobo.angular_native_text_regression.1",
        "case_count": len(reports),
        "pass": sum(bool(report["pass"]) for report in reports),
        "cases": reports,
    }
    (root / "ANGULAR_NATIVE_TEXT_REGRESSION.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    if summary["pass"] != len(CASES):
        raise RuntimeError("Angular native text regression did not fully pass.")
    return summary


if __name__ == "__main__":
    run()
