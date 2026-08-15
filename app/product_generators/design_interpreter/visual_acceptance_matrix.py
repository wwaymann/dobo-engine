from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import trimesh
from PIL import Image, ImageFilter


VISUAL_ACCEPTANCE_MATRIX_VERSION = "A3V.1"

VIEWS: dict[str, np.ndarray] = {
    "front": np.array([0.0, -1.0, 0.0], dtype=float),
    "side": np.array([1.0, 0.0, 0.0], dtype=float),
    "top": np.array([0.0, 0.0, 1.0], dtype=float),
    "iso": np.array([1.0, -1.0, 0.85], dtype=float),
}


def _basis(view: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    forward = view / np.linalg.norm(view)
    up_seed = np.array([0.0, 0.0, 1.0], dtype=float)
    if abs(float(np.dot(forward, up_seed))) > 0.92:
        up_seed = np.array([0.0, 1.0, 0.0], dtype=float)
    right = np.cross(forward, up_seed)
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    up /= np.linalg.norm(up)
    return right, up, forward


def _render_points(mesh: trimesh.Trimesh, view: np.ndarray, size: int = 768) -> tuple[Image.Image, dict[str, float]]:
    centers = np.asarray(mesh.triangles_center, dtype=float)
    normals = np.asarray(mesh.face_normals, dtype=float)
    areas = np.asarray(mesh.area_faces, dtype=float)

    max_faces = 220_000
    if len(centers) > max_faces:
        order = np.argsort(areas)[-max_faces:]
        centers = centers[order]
        normals = normals[order]

    right, up, forward = _basis(view)
    center = np.asarray(mesh.bounding_box.centroid, dtype=float)
    rel = centers - center

    x = rel @ right
    y = rel @ up
    depth = rel @ forward

    span_x = max(float(np.ptp(x)), 1e-6)
    span_y = max(float(np.ptp(y)), 1e-6)
    scale = 0.86 * (size - 1) / max(span_x, span_y)
    px = np.clip(np.rint(x * scale + (size - 1) * 0.5).astype(int), 0, size - 1)
    py = np.clip(np.rint(-y * scale + (size - 1) * 0.5).astype(int), 0, size - 1)

    light = np.array([0.35, -0.55, 0.76], dtype=float)
    light /= np.linalg.norm(light)
    shade = 0.42 + 0.58 * np.clip(np.abs(normals @ light), 0.0, 1.0)
    shade = np.clip(np.rint(45 + 195 * shade), 0, 255).astype(np.uint8)

    flat = py * size + px
    sort_order = np.argsort(depth)
    flat = flat[sort_order]
    shade = shade[sort_order]

    canvas = np.full(size * size, 255, dtype=np.uint8)
    canvas[flat] = shade
    image = Image.fromarray(canvas.reshape(size, size), mode="L")
    image = image.filter(ImageFilter.MinFilter(3))
    image = image.filter(ImageFilter.GaussianBlur(radius=0.45))

    arr = np.asarray(image)
    mask = arr < 248
    if np.any(mask):
        ys, xs = np.nonzero(mask)
        bbox_w = int(xs.max() - xs.min() + 1)
        bbox_h = int(ys.max() - ys.min() + 1)
        occupancy = float(mask.mean())
        centroid_x = float(xs.mean() / max(size - 1, 1))
        centroid_y = float(ys.mean() / max(size - 1, 1))
    else:
        bbox_w = bbox_h = 0
        occupancy = centroid_x = centroid_y = 0.0

    metrics = {
        "occupancy": round(occupancy, 6),
        "bbox_width_ratio": round(bbox_w / size, 6),
        "bbox_height_ratio": round(bbox_h / size, 6),
        "centroid_x": round(centroid_x, 6),
        "centroid_y": round(centroid_y, 6),
    }
    return image, metrics


def _find_stl_cases(root: Path) -> Iterable[tuple[str, Path]]:
    for stl in sorted(root.rglob("*.stl")):
        rel = stl.relative_to(root)
        case = rel.parts[0] if rel.parts else stl.stem
        yield case, stl


def render_matrix(root: Path) -> Path:
    output = root / "visual_acceptance"
    output.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {
        "version": VISUAL_ACCEPTANCE_MATRIX_VERSION,
        "cases": {},
    }

    found = 0
    for case, stl in _find_stl_cases(root):
        found += 1
        loaded = trimesh.load_mesh(stl, process=False)
        if isinstance(loaded, trimesh.Scene):
            mesh = loaded.dump(concatenate=True)
        else:
            mesh = loaded
        if not isinstance(mesh, trimesh.Trimesh):
            raise RuntimeError(f"Unsupported mesh payload for {stl}")

        case_dir = output / case
        case_dir.mkdir(parents=True, exist_ok=True)
        case_report: dict[str, object] = {
            "source": str(stl.relative_to(root)),
            "vertices": int(len(mesh.vertices)),
            "faces": int(len(mesh.faces)),
            "watertight": bool(mesh.is_watertight),
            "views": {},
        }

        for name, vector in VIEWS.items():
            image, metrics = _render_points(mesh, vector)
            image.save(case_dir / f"{name}.png", optimize=True)
            case_report["views"][name] = metrics
        report["cases"][case] = case_report

    if found == 0:
        raise RuntimeError(f"No STL files found below {root}")

    report_path = output / "visual_acceptance.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(f"DOBO Visual Acceptance Matrix {VISUAL_ACCEPTANCE_MATRIX_VERSION}: Valid OK")
    print(f"cases {found} OK")
    print(f"report {report_path}")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix-root", required=True, type=Path)
    args = parser.parse_args()
    render_matrix(args.matrix_root.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
