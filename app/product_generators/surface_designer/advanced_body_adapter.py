from __future__ import annotations

from pathlib import Path

import cadquery as cq
from OCP.StlAPI import StlAPI_Reader
from OCP.TopoDS import TopoDS_Shape


def load_advanced_stl_as_cadquery_shape(path: str | Path) -> cq.Shape:
    """Load an existing advanced STL into the OCC/CadQuery shape contract.

    This is an interface adapter only: it does not synthesize, simplify,
    remodel, or otherwise replace the source morphology.
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
    return shape
