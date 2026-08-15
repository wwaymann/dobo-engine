from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


CASES = ("architectural", "branching", "perforated")
VIEWS = {
    "front": Vector((0.0, -1.0, 0.0)),
    "side": Vector((1.0, 0.0, 0.0)),
    "top": Vector((0.0, 0.0, 1.0)),
    "iso": Vector((1.0, -1.0, 0.82)),
}


def _arguments() -> argparse.Namespace:
    argv = sys.argv
    argv = argv[argv.index("--") + 1 :] if "--" in argv else []
    parser = argparse.ArgumentParser(
        description="Render normalized A/B DOBO STL views with Blender."
    )
    parser.add_argument("--baseline-root", required=True)
    parser.add_argument("--candidate-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--baseline-label", default="baseline")
    parser.add_argument("--candidate-label", default="candidate")
    parser.add_argument("--resolution", type=int, default=512)
    return parser.parse_args(argv)


def _find_stl(root: Path, case: str) -> Path:
    matches = sorted((root / case).rglob("*.stl"))
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one STL for {case} under {root}; found {len(matches)}."
        )
    return matches[0]


def _clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        # Remove only unused data. This keeps Blender memory stable across cases.
        for block in list(collection):
            if block.users == 0:
                collection.remove(block)


def _import_stl(path: Path, name: str):
    before = set(bpy.data.objects)
    if hasattr(bpy.ops.wm, "stl_import"):
        bpy.ops.wm.stl_import(filepath=str(path))
    elif hasattr(bpy.ops.import_mesh, "stl"):
        bpy.ops.import_mesh.stl(filepath=str(path))
    else:
        raise RuntimeError("This Blender build does not expose an STL import operator.")
    created = [obj for obj in bpy.data.objects if obj not in before and obj.type == "MESH"]
    if not created:
        raise RuntimeError(f"Blender did not import a mesh from {path}.")
    obj = created[0]
    obj.name = name
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def _material(name: str):
    material = bpy.data.materials.new(name=name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        raise RuntimeError("Principled BSDF node not found.")
    bsdf.inputs["Base Color"].default_value = (0.82, 0.83, 0.82, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.72
    if "Metallic" in bsdf.inputs:
        bsdf.inputs["Metallic"].default_value = 0.0
    return material


def _world_bounds(objects) -> tuple[Vector, Vector]:
    corners: list[Vector] = []
    for obj in objects:
        corners.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
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


def _configure_scene(resolution: int):
    scene = bpy.context.scene
    engine_candidates = ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE")
    for engine in engine_candidates:
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.render.image_settings.color_depth = "8"
    scene.render.use_file_extension = True
    scene.render.resolution_percentage = 100
    # Transparent renders are composited later, but a neutral world still drives fill light.
    scene.world.color = (0.055, 0.06, 0.065)
    if scene.world.use_nodes:
        background = scene.world.node_tree.nodes.get("Background")
        if background is not None:
            background.inputs["Color"].default_value = (0.055, 0.06, 0.065, 1.0)
            background.inputs["Strength"].default_value = 0.42
    try:
        scene.view_settings.look = "Medium High Contrast"
    except (TypeError, ValueError):
        pass
    return scene


def _add_camera(center: Vector, maximum_extent: float):
    camera_data = bpy.data.cameras.new("DOBO_Autopilot_Camera")
    camera = bpy.data.objects.new("DOBO_Autopilot_Camera", camera_data)
    bpy.context.collection.objects.link(camera)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = maximum_extent * 1.28
    camera.data.clip_start = max(0.01, maximum_extent * 0.001)
    camera.data.clip_end = max(1000.0, maximum_extent * 20.0)
    bpy.context.scene.camera = camera
    return camera


def _add_sun(name: str, direction: Vector, energy: float, angle_degrees: float):
    light_data = bpy.data.lights.new(name=name, type="SUN")
    light_data.energy = energy
    light_data.angle = math.radians(angle_degrees)
    light = bpy.data.objects.new(name, light_data)
    bpy.context.collection.objects.link(light)
    direction = direction.normalized()
    # A sun emits along local -Z, so track -Z to the desired direction.
    light.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return light


def _set_camera_view(camera, center: Vector, camera_axis: Vector, maximum_extent: float) -> None:
    axis = camera_axis.normalized()
    camera.location = center + axis * (maximum_extent * 3.2)
    look = center - camera.location
    camera.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()


def _render(scene, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True)
    if not output_path.exists():
        raise RuntimeError(f"Blender did not write {output_path}.")


def main() -> None:
    args = _arguments()
    baseline_root = Path(args.baseline_root).resolve()
    candidate_root = Path(args.candidate_root).resolve()
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    print("DOBO normalized visual renderer")
    print("baseline", args.baseline_label, baseline_root)
    print("candidate", args.candidate_label, candidate_root)
    print("resolution", args.resolution)

    for case in CASES:
        _clear_scene()
        scene = _configure_scene(args.resolution)
        baseline = _import_stl(_find_stl(baseline_root, case), f"{case}_{args.baseline_label}")
        candidate = _import_stl(_find_stl(candidate_root, case), f"{case}_{args.candidate_label}")
        material = _material(f"DOBO_{case}_matte")
        baseline.data.materials.clear()
        candidate.data.materials.clear()
        baseline.data.materials.append(material)
        candidate.data.materials.append(material)

        minimum, maximum = _world_bounds((baseline, candidate))
        center = (minimum + maximum) * 0.5
        dimensions = maximum - minimum
        maximum_extent = max(dimensions.x, dimensions.y, dimensions.z)
        if maximum_extent <= 0.0:
            raise RuntimeError(f"Invalid zero-sized mesh pair for {case}.")

        camera = _add_camera(center, maximum_extent)
        _add_sun("DOBO_Key", Vector((-0.65, -0.8, -1.0)), 2.4, 7.0)
        _add_sun("DOBO_Fill", Vector((0.75, 0.45, -0.35)), 0.72, 15.0)
        _add_sun("DOBO_Rim", Vector((-0.15, 0.85, -0.25)), 0.44, 12.0)

        for view_name, axis in VIEWS.items():
            _set_camera_view(camera, center, axis, maximum_extent)
            baseline.hide_render = False
            candidate.hide_render = True
            _render(
                scene,
                output_root / case / f"{args.baseline_label}_{view_name}.png",
            )
            baseline.hide_render = True
            candidate.hide_render = False
            _render(
                scene,
                output_root / case / f"{args.candidate_label}_{view_name}.png",
            )
            print(case, view_name, "OK")

    print("DOBO normalized visual renderer: Valid OK")


if __name__ == "__main__":
    main()
