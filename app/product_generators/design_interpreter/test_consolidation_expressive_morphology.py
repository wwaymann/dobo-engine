from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import trimesh

from .phase_5_design_matrix import _feature, _program
from .structural_compiler import StructuralSemanticCompiler
from .structural_pipeline import DoboStructuralPipeline


CASES = (
    ("undulating_shell", ["organic", "organic_asymmetric", "undulating"]),
    ("spiral_ribbed", ["spiral_ribbed", "dynamic_spiral", "helical_ribs"]),
    ("origami_crown", ["geometric", "origami", "architectural_folded"]),
    ("sculptural_cluster", ["sculptural_cluster", "compound_sculpture"]),
)


def _semantic(case_id: str, tags: list[str], *, continuity: bool = False):
    features = []
    if continuity:
        features = [
            _feature(
                "text_dobo",
                "text_dobo",
                "text",
                "raised",
                region="front",
                horizontal=0.0,
                vertical=0.52,
                width=0.34,
                height=0.12,
                depth=2.0,
            ),
            _feature(
                "decorative_ridge",
                "ridge",
                "slit",
                "recessed",
                region="front",
                horizontal=0.0,
                vertical=0.30,
                width=0.44,
                height=0.035,
                depth=1.2,
            ),
        ]
    return _program(
        f"consolidation_{case_id}",
        "Maceta expresiva hueca con abertura superior, texto DOBO en sobrerrelieve frontal y detalle decorativo.",
        family="organic",
        height=112.0,
        width=132.0,
        depth=118.0,
        opening_shape="elliptical",
        opening_width=0.58,
        opening_depth=0.54,
        style_tags=tags,
        features=features,
        relations=[],
    )


def _load_mesh(path: str) -> trimesh.Trimesh:
    mesh = trimesh.load_mesh(path, process=True)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    if not isinstance(mesh, trimesh.Trimesh):
        raise RuntimeError("Expected one mesh from expressive continuity STL.")
    return mesh


def _render(mesh: trimesh.Trimesh, target: Path) -> None:
    vertices = mesh.vertices.copy()
    center = (vertices.min(0) + vertices.max(0)) / 2.0
    vertices -= center
    scale = float(max(vertices.max(0) - vertices.min(0)))
    vertices /= max(scale, 1e-9)
    figure = plt.figure(figsize=(6, 6))
    axis = figure.add_subplot(111, projection="3d")
    axis.plot_trisurf(
        vertices[:, 0],
        vertices[:, 1],
        vertices[:, 2],
        triangles=mesh.faces,
        linewidth=0.02,
        shade=True,
    )
    axis.view_init(elev=24, azim=-42)
    axis.set_axis_off()
    figure.tight_layout()
    figure.savefig(target, dpi=160)
    plt.close(figure)


def main() -> None:
    print("DOBO Consolidation - Expressive Morphology Boundary")
    print("-----------------------------------")

    resolved_profiles: set[str] = set()
    for expected, tags in CASES:
        program = _semantic(expected, tags)
        compiled = StructuralSemanticCompiler.compile(program)
        actual = str(compiled.motor_program["morphogenesis"]["profile"])
        if actual != expected:
            raise RuntimeError(f"Expected {expected}, got {actual}.")
        kinds = {
            str(field.get("kind", "ellipsoid"))
            for field in compiled.motor_program["fields"]
            if str(field["id"])
            in set(compiled.motor_program["vessel"]["shell_field_ids"])
        }
        if not (kinds & {"lobed_ellipsoid", "twisted_faceted"}):
            raise RuntimeError(f"{expected} did not activate an expressive field family.")
        resolved_profiles.add(actual)
        print(expected, ",".join(sorted(kinds)), "OK")

    if len(resolved_profiles) != 4:
        raise RuntimeError("Four distinct expressive morphology families were not preserved.")

    output_root = Path("outputs/consolidation_expressive_morphology").resolve()
    program = _semantic("undulating_shell", list(CASES[0][1]), continuity=True)
    result = DoboStructuralPipeline().generate_from_semantic(
        program,
        output_root=output_root / "generated",
    )
    result.validate()
    mesh = _load_mesh(result.stl_path)
    if not mesh.is_watertight or not mesh.is_winding_consistent:
        raise RuntimeError("Expressive continuity STL is not watertight/consistent.")

    motor = json.loads(Path(result.motor_path).read_text(encoding="utf-8"))
    if motor.get("morphogenesis", {}).get("profile") != "undulating_shell":
        raise RuntimeError("Continuity case lost the requested expressive body profile.")
    if not motor.get("vessel", {}).get("shell_field_ids"):
        raise RuntimeError("Continuity case lost the hollow vessel shell definition.")
    if not Path(result.three_mf_path).is_file() or Path(result.three_mf_path).stat().st_size <= 0:
        raise RuntimeError("Expressive continuity 3MF is missing.")

    board = output_root / "expressive_continuity.png"
    output_root.mkdir(parents=True, exist_ok=True)
    _render(mesh, board)
    evidence = {
        "profiles": sorted(resolved_profiles),
        "continuity_profile": motor["morphogenesis"]["profile"],
        "stl": result.stl_path,
        "three_mf": result.three_mf_path,
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "text_feature": "text_dobo",
        "decoration_feature": "decorative_ridge",
        "opening_shape": program.body.opening_shape,
        "manufacturing_preflight": "PASS",
        "visual_evidence": str(board),
    }
    evidence_path = output_root / "EXPRESSIVE_CONTINUITY_EVIDENCE.json"
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print("-----------------------------------")
    print("profiles", len(resolved_profiles), "OK")
    print("continuity STL", result.stl_path)
    print("continuity 3MF", result.three_mf_path)
    print("evidence", evidence_path)
    print("DOBO Consolidation Expressive Morphology: Valid OK")


if __name__ == "__main__":
    main()
