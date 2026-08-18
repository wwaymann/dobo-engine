from __future__ import annotations

from pathlib import Path

import cadquery as cq
from OCP.StlAPI import StlAPI_Reader
from OCP.TopoDS import TopoDS_Shape


def load_advanced_stl_as_cadquery_shape(path: str | Path) -> cq.Shape:
    """Load an existing advanced STL into the OCC/CadQuery shape contract.

    This is an interface adapter only: it does not synthesize, simplify,
    remodel, or otherwise replace the source morphology. If the imported
    watertight STL arrives as a closed shell/compound, promote that existing
    shell to a CadQuery Solid so downstream booleans operate on the same body.
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
    faces = shape.Faces()
    if not faces:
        raise RuntimeError("Imported advanced body contains no OCC faces.")

    # StlAPI_Reader may preserve a watertight triangulated body as a shell or
    # compound of shells. SurfaceDesigner performs Boolean operations, so the
    # adapter must expose the same closed boundary as a Solid when possible.
    solids = shape.Solids()
    if solids:
        return solids[0] if len(solids) == 1 else cq.Compound.makeCompound(solids)

    shells = shape.Shells()
    if len(shells) == 1:
        solid = cq.Solid.makeSolid(shells[0])
        if solid.isValid():
            return solid

    return shape
