from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


VIEWS = {
    "front": Vector((0.0, -1.0, 0.0)),
    "side": Vector((1.0, 0.0, 0.0)),
    "top": Vector((0.0, 0.0, 1.0)),
    "iso": Vector((1.0, -1.0, 0.82)),
}
BACKGROUND = (0.055, 0.060, 0.065)
OBJECT_COLOR = (0.82, 0.83, 0.82, 1.0)


def _arguments() -> argparse.Namespace:
    argv = sys.argv
    argv = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser(
        description="Render one DOBO acceptance STL from normalized review views."
    )
    parser.add_argument("--stl", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--resolution", type=int, default=512)
    return parser.parse_args(argv)


def _clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def _import_stl(path: Path):
    before = set(bpy.data.objects)
    if hasattr(bpy.ops.wm, "stl_import"):
        bpy.ops.wm.stl_import(filepath=str(path))
    elif hasattr(bpy.ops.import_mesh, "stl"):
        bpy.ops.import_mesh.stl(filepath=str(path))
    else:
        raise RuntimeError("This Blender build does not expose an STL import operator.")
    created = [obj for obj in bpy.data.objects if obj not in before and obj.type == "MESH"]
    if len(created) != 1:
        raise RuntimeError(f"Expected one imported mesh; found {len(created)}.")
    obj = created[0]
    obj.color = OBJECT_COLOR
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    material = bpy.data.materials.new(name="DOBO_acceptance_matte")
    material.diffuse_color = OBJECT_COLOR
    obj.data.materials.append(material)
    return obj


def _bounds(obj) -> tuple[Vector, Vector]:
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    minimum = Vector((
        min(point.x for point in corners),
        min(point.y for point in corners),
        min(point.z for point in corners),
    ))
    maximum = Vector((
        max(point.x for point in corners),
        max(point.y for point in corners),
        max(point.z for point in corners),
    ))
    return minimum, maximum


def _scene(resolution: int):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.world.color = BACKGROUND
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "MATERIAL"
    shading.show_shadows = True
    shading.show_cavity = True
    if hasattr(shading, "cavity_type"):
        shading.cavity_type = "BOTH"
    return scene


def _camera(center: Vector, maximum_extent: float):
    camera_data = bpy.data.cameras.new("DOBO_Acceptance_Camera")
    camera = bpy.data.objects.new("DOBO_Acceptance_Camera", camera_data)
    bpy.context.collection.objects.link(camera)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = maximum_extent * 1.28
    camera.data.clip_start = max(0.01, maximum_extent * 0.001)
    camera.data.clip_end = max(1000.0, maximum_extent * 20.0)
    bpy.context.scene.camera = camera
    return camera


def main() -> None:
    args = _arguments()
    stl = Path(args.stl).resolve()
    output_root = Path(args.output_root).resolve()
    if not stl.is_file():
        raise FileNotFoundError(stl)
    output_root.mkdir(parents=True, exist_ok=True)

    _clear_scene()
    obj = _import_stl(stl)
    scene = _scene(args.resolution)
    minimum, maximum = _bounds(obj)
    center = (minimum + maximum) * 0.5
    dimensions = maximum - minimum
    maximum_extent = max(dimensions.x, dimensions.y, dimensions.z)
    if maximum_extent <= 0.0:
        raise RuntimeError("Acceptance mesh has zero extent.")
    camera = _camera(center, maximum_extent)

    for view_name, axis in VIEWS.items():
        unit = axis.normalized()
        camera.location = center + unit * (maximum_extent * 3.2)
        camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
        target = output_root / f"{args.label}_{view_name}.png"
        scene.render.filepath = str(target)
        bpy.ops.render.render(write_still=True)
        if not target.exists():
            raise RuntimeError(f"Blender did not write {target}.")
        print(args.label, view_name, target, "OK")


if __name__ == "__main__":
    main()
