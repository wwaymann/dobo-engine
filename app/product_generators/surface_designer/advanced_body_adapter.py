from __future__ import annotations

from pathlib import Path

import cadquery as cq
import numpy as np
import trimesh
from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing
from OCP.StlAPI import StlAPI_Reader
from OCP.TopoDS import TopoDS_Shape


def _promote_closed_boundary_to_solid(shape: cq.Shape) -> cq.Shape:
    """Promote the imported STL boundary to a Boolean-capable Solid when possible.

    This is interface normalization only. It reuses the exact imported triangular
    faces; it does not remesh, simplify, approximate, or synthesize replacement
    geometry.
    """
    solids = shape.Solids()
    if solids:
        return solids[0] if len(solids) == 1 else cq.Compound.makeCompound(solids)

    shells = shape.Shells()
    if len(shells) == 1:
        solid = cq.Solid.makeSolid(shells[0])
        if solid.isValid():
            return solid

    sewing = BRepBuilderAPI_Sewing(1.0e-6)
    for face in shape.Faces():
        sewing.Add(face.wrapped)
    sewing.Perform()

    sewed = sewing.SewedShape()
    if sewed.IsNull():
        return shape

    normalized = cq.Shape.cast(sewed)
    normalized_solids = normalized.Solids()
    if normalized_solids:
        return (
            normalized_solids[0]
            if len(normalized_solids) == 1
            else cq.Compound.makeCompound(normalized_solids)
        )

    normalized_shells = normalized.Shells()
    if len(normalized_shells) == 1:
        solid = cq.Solid.makeSolid(normalized_shells[0])
        if solid.isValid():
            return solid

    return shape


def load_advanced_stl_as_cadquery_shape(path: str | Path) -> cq.Shape:
    """Load an existing advanced STL into the OCC/CadQuery shape contract."""
    source = Path(path).resolve()
    if not source.is_file() or source.stat().st_size <= 0:
        raise FileNotFoundError(source)

    ocp_shape = TopoDS_Shape()
    reader = StlAPI_Reader()
    ok = bool(reader.Read(ocp_shape, str(source)))
    if not ok or ocp_shape.IsNull():
        raise RuntimeError(f"OpenCascade could not import STL: {source}")

    shape = cq.Shape.cast(ocp_shape)
    if not shape.Faces():
        raise RuntimeError("Imported advanced body contains no OCC faces.")

    return _promote_closed_boundary_to_solid(shape)


def local_surface_mapping_proxy(
    path: str | Path,
    *,
    width_mm: float = 30.0,
    height_mm: float = 20.0,
    inset_mm: float = 0.35,
) -> cq.Face:
    """Return a local mapping face anchored to the exact imported mesh surface."""
    source = Path(path).resolve()
    if not source.is_file() or source.stat().st_size <= 0:
        raise FileNotFoundError(source)

    width_mm = float(width_mm)
    height_mm = float(height_mm)
    inset_mm = float(inset_mm)
    if width_mm <= 0.0 or height_mm <= 0.0 or inset_mm <= 0.0:
        raise ValueError("Mapping proxy dimensions and inset must be positive.")

    mesh = trimesh.load_mesh(source, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    if not isinstance(mesh, trimesh.Trimesh) or len(mesh.faces) == 0:
        raise RuntimeError("Advanced STL does not contain a usable triangle mesh.")

    centroids = np.asarray(mesh.triangles_center, dtype=np.float64)
    normals = np.asarray(mesh.face_normals, dtype=np.float64)
    areas = np.asarray(mesh.area_faces, dtype=np.float64)

    z_min = float(mesh.bounds[0][2])
    z_max = float(mesh.bounds[1][2])
    z_span = max(z_max - z_min, 1.0e-9)
    z_fraction = (centroids[:, 2] - z_min) / z_span

    radial = centroids[:, :2]
    radial_norm = np.linalg.norm(radial, axis=1)
    radial_unit = np.zeros_like(radial)
    valid_radial = radial_norm > 1.0e-9
    radial_unit[valid_radial] = radial[valid_radial] / radial_norm[valid_radial, None]
    radial_alignment = np.zeros(len(centroids), dtype=np.float64)
    radial_alignment[valid_radial] = np.sum(
        normals[valid_radial, :2] * radial_unit[valid_radial], axis=1
    )

    eligible = (
        (z_fraction >= 0.38)
        & (z_fraction <= 0.68)
        & (radial_alignment >= 0.45)
        & (np.abs(normals[:, 2]) <= 0.65)
    )
    indices = np.flatnonzero(eligible)
    if len(indices) == 0:
        eligible = valid_radial & (radial_alignment > 0.0)
        indices = np.flatnonzero(eligible)
    if len(indices) == 0:
        raise RuntimeError("Could not locate an outward local wall on advanced STL.")

    score = (
        3.0 * radial_alignment[indices]
        - 1.5 * np.abs(z_fraction[indices] - 0.53)
        - 0.5 * np.abs(normals[indices, 2])
        + 0.05 * areas[indices] / max(float(areas.max()), 1.0e-12)
    )
    index = int(indices[int(np.argmax(score))])

    center = centroids[index]
    normal = normals[index]
    normal_norm = float(np.linalg.norm(normal))
    if normal_norm <= 1.0e-12:
        raise RuntimeError("Selected advanced surface triangle has zero normal.")
    normal = normal / normal_norm

    global_z = np.asarray((0.0, 0.0, 1.0), dtype=np.float64)
    tangent_v = global_z - normal * float(np.dot(global_z, normal))
    tangent_v_norm = float(np.linalg.norm(tangent_v))
    if tangent_v_norm <= 1.0e-8:
        tangent_v = np.asarray((1.0, 0.0, 0.0), dtype=np.float64)
        tangent_v = tangent_v - normal * float(np.dot(tangent_v, normal))
        tangent_v_norm = float(np.linalg.norm(tangent_v))
    tangent_v = tangent_v / tangent_v_norm
    tangent_u = np.cross(tangent_v, normal)
    tangent_u = tangent_u / float(np.linalg.norm(tangent_u))

    proxy_center = center - normal * inset_mm
    half_u = 0.5 * width_mm * tangent_u
    half_v = 0.5 * height_mm * tangent_v
    points = (
        proxy_center - half_u - half_v,
        proxy_center + half_u - half_v,
        proxy_center + half_u + half_v,
        proxy_center - half_u + half_v,
    )
    wire = cq.Wire.makePolygon(
        tuple(cq.Vector(float(p[0]), float(p[1]), float(p[2])) for p in points),
        close=True,
    )
    face = cq.Face.makeFromWires(wire)
    if not face.isValid():
        raise RuntimeError("Advanced local mapping proxy face is invalid.")
    return face
