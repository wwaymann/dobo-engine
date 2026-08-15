from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import trimesh

from .phase_6_morphogenesis_matrix import morphogenesis_matrix
from .structural_pipeline import DoboStructuralPipeline


BENCHMARK_VERSION = "B27.1"


@dataclass(frozen=True, slots=True)
class BenchmarkTarget:
    id: str
    label: str
    base_family: str
    stress: str
    source_case: str
    pass_profiles: tuple[str, ...]
    partial_profiles: tuple[str, ...]


TARGETS: tuple[BenchmarkTarget, ...] = (
    BenchmarkTarget(
        "organic_asymmetric",
        "Organic asymmetric",
        "freeform_organic",
        "global asymmetry + smooth morphological transitions",
        "helical",
        ("helical_chain",),
        (),
    ),
    BenchmarkTarget(
        "truncated_cone",
        "Truncated cone",
        "tapered_revolution",
        "strong base-to-mouth taper without cylindrical fallback",
        "helical",
        ("tapered_revolution",),
        ("helical_chain",),
    ),
    BenchmarkTarget(
        "cubic_architectural",
        "Cubic architectural",
        "cuboid",
        "planar faces + controlled corners + non-radial opening",
        "faceted",
        ("cuboid",),
        ("axial_faceted",),
    ),
    BenchmarkTarget(
        "rectangular_planter",
        "Rectangular horizontal",
        "rectangular_prism",
        "elongated non-radial body with large aspect ratio",
        "faceted",
        ("rectangular_prism",),
        ("axial_faceted",),
    ),
    BenchmarkTarget(
        "ovoid_sculptural",
        "Ovoid sculptural",
        "ovoid",
        "continuous bulbous volume with intentional opening",
        "bilateral",
        ("ovoid",),
        ("bilateral_mass",),
    ),
    BenchmarkTarget(
        "polygonal_faceted",
        "Polygonal faceted",
        "polygonal_faceted",
        "facets remain legible through the complete vessel height",
        "faceted",
        ("axial_faceted",),
        (),
    ),
    BenchmarkTarget(
        "freeform_dynamic",
        "Freeform dynamic",
        "freeform_asymmetric",
        "non-revolution silhouette + directional visual flow",
        "helical",
        ("helical_chain",),
        (),
    ),
    BenchmarkTarget(
        "compound_multivolume",
        "Compound multivolume",
        "compound_multivolume",
        "two or more visually distinct masses fused into one functional vessel",
        "radial",
        ("compound_multivolume",),
        ("radial_petal", "bilateral_mass"),
    ),
)


def _classification(profile: str, target: BenchmarkTarget) -> str:
    if profile in target.pass_profiles:
        return "PASS"
    if profile in target.partial_profiles:
        return "PARTIAL"
    return "FAIL"


def _mesh_for_view(path: str | Path) -> trimesh.Trimesh:
    mesh = trimesh.load_mesh(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        geometry = tuple(mesh.geometry.values())
        if not geometry:
            raise RuntimeError(f"No mesh geometry in {path}")
        mesh = trimesh.util.concatenate(geometry)
    if not isinstance(mesh, trimesh.Trimesh):
        raise RuntimeError(f"Unsupported mesh evidence type: {type(mesh)!r}")
    return mesh


def _normalized_vertices(mesh: trimesh.Trimesh) -> np.ndarray:
    vertices = np.asarray(mesh.vertices, dtype=float).copy()
    center = 0.5 * (vertices.min(axis=0) + vertices.max(axis=0))
    vertices -= center
    scale = float(np.max(vertices.max(axis=0) - vertices.min(axis=0)))
    if scale > 1.0e-9:
        vertices /= scale
    return vertices


def _draw_mesh(ax, mesh: trimesh.Trimesh, view: str) -> None:
    vertices = _normalized_vertices(mesh)
    faces = np.asarray(mesh.faces, dtype=int)
    ax.plot_trisurf(
        vertices[:, 0],
        vertices[:, 1],
        vertices[:, 2],
        triangles=faces,
        linewidth=0.05,
        antialiased=True,
        shade=True,
    )
    if view == "front":
        ax.view_init(elev=0.0, azim=-90.0)
    elif view == "top":
        ax.view_init(elev=90.0, azim=-90.0)
    else:
        ax.view_init(elev=24.0, azim=-42.0)
    ax.set_xlim(-0.55, 0.55)
    ax.set_ylim(-0.55, 0.55)
    ax.set_zlim(-0.55, 0.55)
    ax.set_axis_off()


def _write_board(
    *,
    records: list[dict[str, object]],
    meshes: dict[str, trimesh.Trimesh],
    path: Path,
) -> None:
    figure = plt.figure(figsize=(13.5, 22.0))
    for row, record in enumerate(records):
        target_id = str(record["id"])
        source_case = str(record["source_case"])
        target_ax = figure.add_subplot(len(records), 4, row * 4 + 1)
        target_ax.axis("off")
        target_ax.text(
            0.0,
            0.92,
            f"{row + 1:02d}  {record['label']}",
            fontsize=11,
            fontweight="bold",
            va="top",
        )
        target_ax.text(
            0.0,
            0.68,
            f"Base: {record['base_family']}\n"
            f"Stress: {record['stress']}\n"
            f"Motor profile: {record['motor_profile']}\n"
            f"Result: {record['visual_status']}",
            fontsize=8.2,
            va="top",
            wrap=True,
        )
        mesh = meshes[source_case]
        for offset, view in enumerate(("perspective", "front", "top"), start=2):
            ax = figure.add_subplot(len(records), 4, row * 4 + offset, projection="3d")
            _draw_mesh(ax, mesh, view)
            if row == 0:
                ax.set_title(view.capitalize(), fontsize=9)
        # Keep target id in records even though evidence geometry is deliberately
        # reused when the current engine collapses distinct target families.
        record["evidence_key"] = f"{target_id}:{source_case}"

    figure.suptitle(
        "DOBO B27 — Visual Geometry Benchmark v1\n"
        "Frozen design DNA targets vs. current Motor DOBO geometry",
        fontsize=16,
        y=0.997,
    )
    figure.tight_layout(rect=(0.02, 0.01, 0.98, 0.985))
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=150)
    plt.close(figure)


def run_benchmark(output_root: str | Path) -> dict[str, object]:
    root = Path(output_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    cases = {case.id: case for case in morphogenesis_matrix()}
    required_cases = sorted({target.source_case for target in TARGETS})

    pipeline = DoboStructuralPipeline()
    generated: dict[str, object] = {}
    meshes: dict[str, trimesh.Trimesh] = {}
    for case_id in required_cases:
        case = cases[case_id]
        result = pipeline.generate_from_semantic(
            case.program,
            output_root=root / "generated",
        )
        generated[case_id] = result
        meshes[case_id] = _mesh_for_view(result.stl_path)

    records: list[dict[str, object]] = []
    for target in TARGETS:
        result = generated[target.source_case]
        motor_profile = str(result.compilation.report.morphology_profile)
        records.append(
            {
                **asdict(target),
                "motor_profile": motor_profile,
                "visual_status": _classification(motor_profile, target),
                "stl": result.stl_path,
                "three_mf": result.three_mf_path,
                "watertight": bool(result.mesh_result.watertight),
                "component_count": int(result.mesh_result.component_count),
                "vertex_count": int(result.mesh_result.vertex_count),
                "face_count": int(result.mesh_result.face_count),
            }
        )

    board_path = root / "b27_visual_geometry_board.png"
    _write_board(records=records, meshes=meshes, path=board_path)
    counts = {status: sum(r["visual_status"] == status for r in records) for status in ("PASS", "PARTIAL", "FAIL")}
    payload: dict[str, object] = {
        "benchmark_version": BENCHMARK_VERSION,
        "anti_cheat": {
            "product_specific_generator_branches": 0,
            "engine_geometry_modified_for_benchmark": False,
            "unique_existing_source_programs": len(required_cases),
            "target_count": len(TARGETS),
        },
        "summary": counts,
        "targets": records,
        "board": str(board_path),
    }
    manifest_path = root / "b27_visual_geometry_manifest.json"
    manifest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    payload["manifest"] = str(manifest_path)
    return payload


def main() -> None:
    payload = run_benchmark("outputs/visual_geometry_benchmark")
    summary = payload["summary"]
    print("DOBO Macroblock B27 - Visual Geometry Benchmark v1")
    print("-----------------------------------")
    print("targets", len(payload["targets"]))
    print("PASS", summary["PASS"])
    print("PARTIAL", summary["PARTIAL"])
    print("FAIL", summary["FAIL"])
    print("product-specific generator branches", payload["anti_cheat"]["product_specific_generator_branches"])
    print("board", payload["board"])
    print("manifest", payload["manifest"])
    print("-----------------------------------")
    print("B27 benchmark completed; failures are evidence, not CI failures.")


if __name__ == "__main__":
    main()
