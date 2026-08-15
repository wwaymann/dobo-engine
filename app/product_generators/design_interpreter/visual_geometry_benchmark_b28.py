from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import trimesh

from .phase_b28_capability_matrix import b28_capability_matrix
from .structural_pipeline import DoboStructuralPipeline

BENCHMARK_VERSION = "B28.3"


def _mesh(path: str) -> trimesh.Trimesh:
    mesh = trimesh.load_mesh(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh


def run_benchmark(output_root: str | Path) -> dict:
    root = Path(output_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    meshes: dict[str, trimesh.Trimesh] = {}

    # Every family is generated independently. A physical failure must not hide
    # the evidence for the remaining families: B28 is a capability matrix, not
    # a first-error smoke test.
    for case in b28_capability_matrix():
        try:
            result = DoboStructuralPipeline().generate_from_semantic(
                case.program, output_root=root / "generated" / case.id
            )
            actual = result.trace.body_profile
            status = "PASS" if actual == case.expected_profile else "PARTIAL"
            meshes[case.id] = _mesh(result.stl_path)
            records.append({
                "id": case.id,
                "label": case.label,
                "base_family": case.base_family,
                "expected_profile": case.expected_profile,
                "actual_profile": actual,
                "visual_status": status,
                "physical_generation": "OK",
                "failure": None,
                "stl": result.stl_path,
                "three_mf": result.three_mf_path,
                "watertight": result.mesh_result.watertight,
                "components": result.mesh_result.component_count,
            })
        except Exception as exc:
            records.append({
                "id": case.id,
                "label": case.label,
                "base_family": case.base_family,
                "expected_profile": case.expected_profile,
                "actual_profile": None,
                "visual_status": "FAIL",
                "physical_generation": "FAIL",
                "failure": f"{type(exc).__name__}: {exc}",
                "stl": None,
                "three_mf": None,
                "watertight": False,
                "components": None,
            })
            print(f"B28 FAMILY FAILURE {case.id}: {type(exc).__name__}: {exc}")

    fig = plt.figure(figsize=(13.5, 22))
    for row, record in enumerate(records):
        ax = fig.add_subplot(len(records), 4, row * 4 + 1)
        ax.axis("off")
        ax.text(0, .9, f"{row+1:02d} {record['label']}", weight="bold")
        detail = (
            f"Base: {record['base_family']}\nExpected: {record['expected_profile']}\n"
            f"Actual: {record['actual_profile']}\nResult: {record['visual_status']}"
        )
        if record["failure"]:
            detail += f"\nPhysical failure:\n{record['failure']}"
        ax.text(0, .68, detail, fontsize=8, va="top", wrap=True)
        mesh = meshes.get(record["id"])
        if mesh is None:
            for offset in (2, 3, 4):
                view = fig.add_subplot(len(records), 4, row * 4 + offset)
                view.axis("off")
                view.text(.5, .5, "PHYSICAL GENERATION FAILED", ha="center", va="center", fontsize=8)
            continue
        vertices = mesh.vertices.copy()
        center = (vertices.min(0) + vertices.max(0)) / 2
        vertices -= center
        scale = max(vertices.max(0) - vertices.min(0))
        vertices /= scale
        for offset, (elev, azim, title) in enumerate(((24, -42, "Perspective"), (0, -90, "Front"), (90, -90, "Top")), 2):
            view = fig.add_subplot(len(records), 4, row * 4 + offset, projection="3d")
            view.plot_trisurf(vertices[:, 0], vertices[:, 1], vertices[:, 2], triangles=mesh.faces, linewidth=.05, shade=True)
            view.view_init(elev=elev, azim=azim)
            view.set_axis_off()
            view.set_xlim(-.55, .55); view.set_ylim(-.55, .55); view.set_zlim(-.55, .55)
            if row == 0:
                view.set_title(title, fontsize=9)

    fig.suptitle("DOBO B28 — Expanded Physical Geometry Benchmark", fontsize=16, y=.997)
    fig.tight_layout(rect=(.02, .01, .98, .985))
    board = root / "b28_expanded_geometry_board.png"
    fig.savefig(board, dpi=150)
    plt.close(fig)

    summary = {s: sum(r["visual_status"] == s for r in records) for s in ("PASS", "PARTIAL", "FAIL")}
    payload = {
        "benchmark_version": BENCHMARK_VERSION,
        "anti_cheat": {"product_specific_generator_branches": 0, "general_family_expander": True},
        "summary": summary,
        "targets": records,
        "board": str(board),
    }
    manifest = root / "b28_expanded_geometry_manifest.json"
    manifest.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    payload["manifest"] = str(manifest)
    return payload


def main() -> None:
    payload = run_benchmark("outputs/visual_geometry_benchmark_b28")
    print("DOBO B28 Expanded Physical Geometry Benchmark")
    print("-----------------------------------")
    print("PASS", payload["summary"]["PASS"])
    print("PARTIAL", payload["summary"]["PARTIAL"])
    print("FAIL", payload["summary"]["FAIL"])
    print("product-specific generator branches", 0)
    print("board", payload["board"])
    print("manifest", payload["manifest"])
    failures = [r for r in payload["targets"] if r["physical_generation"] == "FAIL"]
    if failures:
        print("-----------------------------------")
        for record in failures:
            print("PHYSICAL FAIL", record["id"], record["failure"])
        raise SystemExit(1)


if __name__ == "__main__":
    main()
