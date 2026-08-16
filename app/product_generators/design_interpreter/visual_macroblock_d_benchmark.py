from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import trimesh

from .phase_d_visual_matrix import d_visual_matrix
from .structural_pipeline import DoboStructuralPipeline


BENCHMARK_VERSION = "D1.0"


def _load_mesh(path: str) -> trimesh.Trimesh:
    mesh = trimesh.load_mesh(path, process=True)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh


def _shape_metrics(mesh: trimesh.Trimesh) -> dict[str, float]:
    vertices = np.asarray(mesh.vertices, dtype=float)
    center = np.mean(vertices[:, :2], axis=0)
    radial = np.linalg.norm(vertices[:, :2] - center, axis=1)
    mean = float(np.mean(radial))
    return {
        "radial_cv": float(np.std(radial) / mean) if mean > 1e-9 else 0.0,
        "height_mm": float(mesh.extents[2]),
        "width_mm": float(mesh.extents[0]),
        "depth_mm": float(mesh.extents[1]),
        "volume_mm3": float(abs(mesh.volume)),
    }


def run(output_root: str | Path) -> dict:
    root = Path(output_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    meshes: dict[str, trimesh.Trimesh] = {}

    for case in d_visual_matrix():
        try:
            result = DoboStructuralPipeline().generate_from_semantic(
                case.program,
                output_root=root / "generated" / case.id,
            )
            mesh = _load_mesh(result.stl_path)
            meshes[case.id] = mesh
            records.append({
                "id": case.id,
                "label": case.label,
                "goal": case.visual_goal,
                "profile": result.trace.body_profile,
                "status": "PASS",
                "failure": None,
                "stl": result.stl_path,
                "three_mf": result.three_mf_path,
                "watertight": bool(mesh.is_watertight),
                "components": len(tuple(mesh.split(only_watertight=False))),
                "metrics": _shape_metrics(mesh),
            })
        except Exception as exc:
            records.append({
                "id": case.id,
                "label": case.label,
                "goal": case.visual_goal,
                "profile": case.expected_profile,
                "status": "FAIL",
                "failure": f"{type(exc).__name__}: {exc}",
            })
            print("D1 FAMILY FAILURE", case.id, type(exc).__name__, exc)

    fig = plt.figure(figsize=(15, 23))
    for row, record in enumerate(records):
        info = fig.add_subplot(len(records), 4, row * 4 + 1)
        info.axis("off")
        info.text(0.0, 0.92, f"{row + 1:02d} {record['label']}", weight="bold", fontsize=10)
        info.text(0.0, 0.72, f"Profile: {record['profile']}\nPhysical: {record['status']}\n{record['goal']}", fontsize=7.5, va="top", wrap=True)
        if record.get("failure"):
            info.text(0.0, 0.22, record["failure"], fontsize=6.5, va="top", wrap=True)
        mesh = meshes.get(record["id"])
        if mesh is None:
            for offset in (2, 3, 4):
                ax = fig.add_subplot(len(records), 4, row * 4 + offset)
                ax.axis("off")
                ax.text(0.5, 0.5, "GENERATION FAILED", ha="center", va="center")
            continue
        vertices = mesh.vertices.copy()
        center = (vertices.min(0) + vertices.max(0)) / 2.0
        vertices -= center
        scale = float(max(vertices.max(0) - vertices.min(0)))
        vertices /= max(scale, 1e-9)
        for offset, (elev, azim, title) in enumerate(((24, -42, "Perspective"), (0, -90, "Front"), (90, -90, "Top")), 2):
            ax = fig.add_subplot(len(records), 4, row * 4 + offset, projection="3d")
            ax.plot_trisurf(vertices[:, 0], vertices[:, 1], vertices[:, 2], triangles=mesh.faces, linewidth=0.03, shade=True)
            ax.view_init(elev=elev, azim=azim)
            ax.set_axis_off()
            ax.set_xlim(-0.56, 0.56); ax.set_ylim(-0.56, 0.56); ax.set_zlim(-0.56, 0.56)
            if row == 0:
                ax.set_title(title, fontsize=9)

    fig.suptitle("DOBO Macroblock D1 — Real Expressive Construction Benchmark", fontsize=16, y=0.997)
    fig.tight_layout(rect=(0.015, 0.01, 0.985, 0.985))
    board = root / "d1_real_expressive_construction_board.png"
    fig.savefig(board, dpi=165)
    plt.close(fig)

    passed = sum(record["status"] == "PASS" for record in records)
    payload = {
        "benchmark_version": BENCHMARK_VERSION,
        "summary": {"PASS": passed, "FAIL": len(records) - passed},
        "anti_cheat": {"product_specific_generator_branches": 0, "human_visual_gate_required": True},
        "records": records,
        "board": str(board),
    }
    manifest = root / "d1_real_expressive_construction_manifest.json"
    manifest.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    payload["manifest"] = str(manifest)
    print("DOBO Macroblock D1 - Real Expressive Construction Benchmark")
    print("PASS", passed, "FAIL", len(records) - passed)
    print("board", board)
    print("manifest", manifest)
    if passed != len(records):
        raise SystemExit(1)
    return payload


if __name__ == "__main__":
    run("outputs/macroblock_d_visual_benchmark")
