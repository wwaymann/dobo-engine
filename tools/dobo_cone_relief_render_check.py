from __future__ import annotations

import json
from pathlib import Path

import cadquery as cq
import matplotlib.pyplot as plt
import numpy as np
import trimesh

from engine.body import build_body
from engine.context import EngineContext
from engine.drain import build_drain
from product_generators.surface_designer.native_text import NativeSurfaceTextBuilder
from product_generators.surface_mapping.cone_mapper import ConeSurfaceMapper


ROOT = Path("outputs-ci/cone-relief-render")
ROOT.mkdir(parents=True, exist_ok=True)

BOTTOM_DIAMETER = 74.4
TOP_DIAMETER = 108.0
HEIGHT = 120.0
WALL = 4.0
BOTTOM = 6.4
DRAIN = 5.6
TEXT = "WALTER"
TEXT_SIZE = 16.0
TEXT_DEPTH = 1.2
TEXT_Z = 62.0


def _base_shape() -> cq.Shape:
    context = EngineContext({
        "top_diameter": TOP_DIAMETER,
        "bottom_diameter": BOTTOM_DIAMETER,
        "height": HEIGHT,
        "wall_thickness": WALL,
        "bottom_thickness": BOTTOM,
        "drain_hole": True,
        "drain_diameter": DRAIN,
    })
    body = build_body(None, context)
    body = build_drain(body, context)
    shape = body.val().clean()
    if not isinstance(shape, cq.Shape) or not shape.isValid():
        raise RuntimeError("Cone base shape is invalid.")
    if len(tuple(shape.Solids())) != 1:
        raise RuntimeError("Cone base must contain one solid.")
    return shape


def _mesh(path: Path) -> trimesh.Trimesh:
    mesh = trimesh.load_mesh(str(path), process=True)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    if not isinstance(mesh, trimesh.Trimesh):
        raise RuntimeError("Export did not produce a triangle mesh.")
    mesh.merge_vertices()
    mesh.remove_unreferenced_vertices()
    return mesh


def _render(mesh: trimesh.Trimesh, path: Path, *, elev: float, azim: float) -> None:
    vertices = np.asarray(mesh.vertices, dtype=float)
    faces = np.asarray(mesh.faces, dtype=np.int64)
    if len(faces) > 90000:
        step = max(1, len(faces) // 90000)
        faces = faces[::step]
    used = np.unique(faces.reshape(-1))
    remap = np.full(len(vertices), -1, dtype=np.int64)
    remap[used] = np.arange(len(used))
    vertices = vertices[used]
    faces = remap[faces]

    center = 0.5 * (vertices.min(axis=0) + vertices.max(axis=0))
    vertices = vertices - center
    scale = float(max(np.ptp(vertices, axis=0)))
    vertices = vertices / max(scale, 1.0)

    fig = plt.figure(figsize=(7.2, 7.2))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_trisurf(
        vertices[:, 0], vertices[:, 1], vertices[:, 2],
        triangles=faces, linewidth=0.015, antialiased=True, shade=True,
    )
    ax.view_init(elev=elev, azim=azim)
    ax.set_xlim(-0.58, 0.58)
    ax.set_ylim(-0.58, 0.58)
    ax.set_zlim(-0.58, 0.58)
    ax.set_box_aspect((1, 1, 1))
    ax.set_axis_off()
    fig.tight_layout(pad=0)
    fig.savefig(path, dpi=220, bbox_inches="tight", pad_inches=0)
    plt.close(fig)


def _export_case(name: str, shape: cq.Shape) -> dict:
    stl = ROOT / f"{name}.stl"
    cq.exporters.export(shape, str(stl), tolerance=0.025, angularTolerance=0.06)
    mesh = _mesh(stl)
    if not mesh.is_watertight:
        raise RuntimeError(f"{name} mesh is not watertight")
    if not mesh.is_winding_consistent:
        raise RuntimeError(f"{name} mesh winding is inconsistent")
    components = tuple(mesh.split(only_watertight=False))
    if len(components) != 1:
        raise RuntimeError(f"{name} mesh has {len(components)} components")
    iso = ROOT / f"{name}_iso.png"
    front = ROOT / f"{name}_front.png"
    _render(mesh, iso, elev=24, azim=-68)
    _render(mesh, front, elev=4, azim=-90)
    return {
        "stl": str(stl),
        "iso": str(iso),
        "front": str(front),
        "volume_mm3": float(abs(mesh.volume)),
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "component_count": len(components),
    }


def _board(records: dict[str, dict]) -> Path:
    labels = [
        ("plain", "CONO SIN TEXTO"),
        ("emboss", "SOBRERRELIEVE · WALTER"),
        ("deboss", "BAJORRELIEVE · WALTER"),
    ]
    fig = plt.figure(figsize=(15, 10))
    for row, suffix in enumerate(("iso", "front")):
        for col, (key, label) in enumerate(labels):
            ax = fig.add_subplot(2, 3, row * 3 + col + 1)
            image = plt.imread(records[key][suffix])
            ax.imshow(image)
            ax.set_axis_off()
            if row == 0:
                ax.set_title(label, fontsize=14)
    fig.tight_layout(pad=1.0)
    target = ROOT / "DOBO_CONE_RELIEF_RENDER_BOARD.png"
    fig.savefig(target, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return target


def run() -> dict:
    base = _base_shape()
    surface = ConeSurfaceMapper(
        base_radius=0.5 * BOTTOM_DIAMETER,
        top_radius=0.5 * TOP_DIAMETER,
        height=HEIGHT,
    )
    builder = NativeSurfaceTextBuilder()

    emboss = builder.apply(
        base_shape=base,
        surface=surface,
        text_value=TEXT,
        size=TEXT_SIZE,
        depth=TEXT_DEPTH,
        mode="emboss",
        font="DejaVu Sans",
        kind="regular",
        u_offset=0.0,
        v_offset=TEXT_Z,
    )
    deboss = builder.apply(
        base_shape=base,
        surface=surface,
        text_value=TEXT,
        size=TEXT_SIZE,
        depth=TEXT_DEPTH,
        mode="deboss",
        font="DejaVu Sans",
        kind="regular",
        u_offset=0.0,
        v_offset=TEXT_Z,
    )

    if emboss.final_volume <= emboss.base_volume:
        raise RuntimeError("Cone emboss did not increase CAD volume.")
    if deboss.final_volume >= deboss.base_volume:
        raise RuntimeError("Cone deboss did not decrease CAD volume.")

    records = {
        "plain": _export_case("cone_plain", base),
        "emboss": _export_case("cone_emboss_walter", emboss.shape),
        "deboss": _export_case("cone_deboss_walter", deboss.shape),
    }
    board = _board(records)
    report = {
        "schema": "dobo.cone.relief.render.1",
        "dimensions": {
            "bottom_diameter_mm": BOTTOM_DIAMETER,
            "top_diameter_mm": TOP_DIAMETER,
            "height_mm": HEIGHT,
            "wall_mm": WALL,
            "bottom_mm": BOTTOM,
            "drain_diameter_mm": DRAIN,
        },
        "text": {
            "literal": TEXT,
            "size_mm": TEXT_SIZE,
            "depth_mm": TEXT_DEPTH,
            "vertical_mm": TEXT_Z,
        },
        "cad_volume_delta_mm3": {
            "emboss": float(emboss.final_volume - emboss.base_volume),
            "deboss": float(deboss.base_volume - deboss.final_volume),
        },
        "cases": records,
        "board": str(board),
    }
    (ROOT / "CONE_RELIEF_AUDIT.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return report


if __name__ == "__main__":
    run()
