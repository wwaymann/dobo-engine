from __future__ import annotations

import argparse
import json
from pathlib import Path

import cadquery as cq

from product_generators.surface_designer.face_selector import SurfaceFaceSelector
from product_generators.surface_designer.native_text_face import NativeTextFaceDecorator


def args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build a DOBO text planter from existing primitive + surface text capabilities.")
    p.add_argument("--shape", choices=("cone", "cylinder", "sphere"), required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--output-root", required=True)
    p.add_argument("--size", type=float, default=15.0)
    p.add_argument("--depth", type=float, default=1.8)
    return p.parse_args()


def planter(shape: str):
    wall = 4.0
    if shape == "cone":
        height, bottom_r, top_r = 140.0, 56.0, 65.0
        outer = cq.Solid.makeCone(bottom_r, top_r, height)
        inner = cq.Solid.makeCone(bottom_r-wall, top_r-wall, height-3.0, cq.Vector(0, 0, 4.0))
        return outer.cut(inner, tol=0.005).clean(), "CONE", {
            "height_mm": height, "bottom_radius_mm": bottom_r, "top_radius_mm": top_r, "wall_mm": wall
        }
    if shape == "cylinder":
        height, radius = 140.0, 62.0
        outer = cq.Solid.makeCylinder(radius, height)
        inner = cq.Solid.makeCylinder(radius-wall, height-4.0, cq.Vector(0, 0, 4.0))
        return outer.cut(inner, tol=0.005).clean(), "CYLINDER", {
            "height_mm": height, "radius_mm": radius, "wall_mm": wall
        }
    radius, opening_radius, opening_z = 65.0, 25.0, 55.0
    outer = cq.Solid.makeSphere(radius)
    inner = cq.Solid.makeSphere(radius-wall)
    shell = outer.cut(inner, tol=0.005).clean()
    opening = cq.Solid.makeCylinder(opening_radius, radius, cq.Vector(0, 0, opening_z))
    return shell.cut(opening, tol=0.005).clean(), "SPHERE", {
        "radius_mm": radius, "wall_mm": wall, "opening_radius_mm": opening_radius, "opening_start_z_mm": opening_z
    }


def main() -> None:
    a = args()
    out = Path(a.output_root)
    out.mkdir(parents=True, exist_ok=True)

    base, geom_type, body = planter(a.shape)
    if not base.isValid() or len(base.Solids()) != 1:
        raise RuntimeError(f"{a.shape} planter base invalid")

    face = SurfaceFaceSelector().largest_external(base, geom_type=geom_type)
    decorated = NativeTextFaceDecorator().decorate(
        base_shape=base,
        target_face=face,
        text_value=a.text,
        size=a.size,
        depth=a.depth,
        mode="emboss",
        font="Arial",
        kind="bold",
        width_fraction=0.30,
        height_fraction=0.16,
        u_center=0.25 if a.shape in ("cone", "cylinder", "sphere") else 0.5,
        v_center=0.52,
    )
    decorated.validate()
    final = decorated.shape.clean()
    if not final.isValid() or len(final.Solids()) != 1:
        raise RuntimeError("Decorated planter is not one valid solid")

    stem = f"dobo_{a.shape}_{''.join(c if c.isalnum() else '_' for c in a.text)[:32]}"
    step = out / f"{stem}.step"
    stl = out / f"{stem}.stl"
    cq.exporters.export(final, str(step))
    cq.exporters.export(final, str(stl), tolerance=0.03, angularTolerance=0.08)

    manifest = {
        "schema": "dobo.parametric_text_planter.1",
        "creates_new_engine_behavior": False,
        "creates_new_geometry_capability": False,
        "shape": a.shape,
        "body": body,
        "text": {"content": a.text, "mode": "emboss", "size_mm": a.size, "depth_mm": a.depth},
        "outputs": {"step": step.name, "stl": stl.name},
    }
    (out / "EXECUTED_SPECIFICATION.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
