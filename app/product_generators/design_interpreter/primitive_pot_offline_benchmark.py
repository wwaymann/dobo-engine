from __future__ import annotations

import json
import shutil
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import trimesh

from .phase_5_design_matrix import _program
from .structural_pipeline import DoboStructuralPipeline
from product_generators.manufacturability.profile import ManufacturingProfile


CASES = (
    dict(id="01_cube", label="Cubo", family="organic", tags=["cuboid"], expected="cuboid", height=110.0, width=110.0, depth=110.0, opening="polygonal"),
    dict(id="02_rectangular", label="Prisma rectangular", family="organic", tags=["rectangular_prism"], expected="rectangular_prism", height=105.0, width=145.0, depth=95.0, opening="polygonal"),
    dict(id="03_cylinder", label="Cilindro", family="cylindrical", tags=["cylindrical"], expected="cylindrical", height=115.0, width=110.0, depth=110.0, opening="circular"),
    dict(id="04_cone", label="Tronco de cono", family="tapered", tags=["tapered_revolution"], expected="tapered_revolution", height=120.0, width=120.0, depth=120.0, opening="circular"),
    dict(id="05_sphere", label="Esfera", family="spherical", tags=["spherical"], expected="spherical", height=112.0, width=122.0, depth=122.0, opening="circular"),
    dict(id="06_ovoid", label="Ovoide", family="organic", tags=["ovoid"], expected="ovoid", height=125.0, width=112.0, depth=106.0, opening="elliptical"),
    dict(id="07_triangular", label="Prisma triangular", family="hexagonal", tags=["triangular_prism"], expected="triangular_prism", height=112.0, width=120.0, depth=120.0, opening="polygonal"),
)


def _semantic(case):
    return _program(
        f"offline_{case['id']}",
        f"Offline fixed semantic fixture for {case['label']}",
        family=case["family"],
        height=case["height"],
        width=case["width"],
        depth=case["depth"],
        opening_shape=case["opening"],
        opening_width=0.58,
        opening_depth=0.58,
        style_tags=case["tags"],
        features=[],
        relations=[],
    )


def _mesh(path: Path) -> trimesh.Trimesh:
    mesh = trimesh.load_mesh(path, process=True)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    if not isinstance(mesh, trimesh.Trimesh) or len(mesh.faces) == 0:
        raise RuntimeError("STL did not contain a usable mesh")
    return mesh


def _valid_3mf(path: Path) -> bool:
    with ZipFile(path, "r") as archive:
        corrupt = archive.testzip()
        names = set(archive.namelist())
    return corrupt is None and {"[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"}.issubset(names)


def run(output_root: str | Path = "outputs-ci/primitive-pot-offline") -> dict:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    pipeline = DoboStructuralPipeline()
    profile = ManufacturingProfile()
    records = []

    for case in CASES:
        case_dir = root / case["id"]
        case_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "id": case["id"], "label": case["label"], "expected_profile": case["expected"],
            "status": "FAIL", "error": None, "morphology_profile": None,
            "watertight": False, "winding_consistent": False,
            "production_size_valid": False, "three_mf_valid": False,
        }
        try:
            semantic = _semantic(case)
            semantic.validate()
            result = pipeline.generate_from_semantic(semantic, output_root=case_dir / "generated")
            result.validate()
            motor = json.loads(Path(result.motor_path).read_text(encoding="utf-8"))
            record["morphology_profile"] = motor.get("morphogenesis", {}).get("profile")
            stl = case_dir / f"{case['id']}.stl"
            three_mf = case_dir / f"{case['id']}.3mf"
            shutil.copy2(result.stl_path, stl)
            shutil.copy2(result.three_mf_path, three_mf)
            mesh = _mesh(stl)
            record["watertight"] = bool(mesh.is_watertight)
            record["winding_consistent"] = bool(mesh.is_winding_consistent)
            record["extents_mm"] = np.asarray(mesh.extents, dtype=float).tolist()
            record["production_size_valid"] = bool(mesh.extents[0] <= profile.max_size_x and mesh.extents[1] <= profile.max_size_y and mesh.extents[2] <= profile.max_size_z)
            record["three_mf_valid"] = _valid_3mf(three_mf)
            checks = (
                record["morphology_profile"] == case["expected"],
                record["watertight"], record["winding_consistent"],
                record["production_size_valid"], record["three_mf_valid"],
                stl.is_file(), three_mf.is_file(),
            )
            record["status"] = "PASS" if all(checks) else "FAIL"
            record["stl"] = str(stl)
            record["three_mf"] = str(three_mf)
        except Exception as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
        records.append(record)
        (case_dir / "AUDIT.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    summary = {
        "schema": "dobo.primitive_pots.offline.1",
        "case_count": len(records),
        "pass": sum(r["status"] == "PASS" for r in records),
        "fail": sum(r["status"] != "PASS" for r in records),
        "openai_used": False,
        "cases": records,
    }
    (root / "OFFLINE_BENCHMARK_SUMMARY.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"case_count": summary["case_count"], "pass": summary["pass"], "fail": summary["fail"], "openai_used": False}, indent=2))
    for record in records:
        print(record["id"], record["status"], "profile=", record["morphology_profile"], "error=", record["error"])
    if summary["pass"] != len(CASES):
        raise RuntimeError(f"Offline primitive planter gate failed: {summary['pass']}/{len(CASES)} PASS")
    return summary


if __name__ == "__main__":
    run()
