from __future__ import annotations

from pathlib import Path

import cadquery as cq
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

    # StlAPI_Reader can return a compound containing many triangular shells even
    # for one watertight mesh. Sew those existing faces back into their shared
    # closed boundary, then promote that boundary to a Solid.
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
    """Load an existing advanced STL into the OCC/CadQuery shape contract.

    This is an interface adapter only: it does not synthesize, simplify,
    remodel, or otherwise replace the source morphology. Watertight imported
    triangular boundaries are normalized to a CadQuery Solid only so the
    existing SurfaceDesigner Boolean path can operate on that same body.
    """
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
