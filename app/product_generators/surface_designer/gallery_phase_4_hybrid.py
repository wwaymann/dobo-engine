from __future__ import annotations

import math
import os

import cadquery as cq

from cadquery.func import torus

from .contracts import (
    SurfaceDesignMode,
)
from .designer import (
    SurfaceDesigner,
)
from .face_selector import (
    SurfaceFaceSelector,
)


OUTPUT_DIRECTORY = (
    "outputs/product_generators/"
    "surface_designer/phase_4_hybrid"
)

SVG_MARK = """
<svg xmlns="http://www.w3.org/2000/svg">
  <path d="
    M 0 12
    L 10 0
    L 20 12
    L 30 0
    L 40 12
    L 30 24
    L 20 12
    L 10 24
    Z
  "/>
</svg>
"""


def _organic_core() -> cq.Shape:
    """
    Smooth freeform loft: one B-Spline-like lateral skin,
    deliberately asymmetric and non-primitive.
    """
    sections = (
        (0.0,   38.0,  0.0,  0.0),
        (18.0,  46.0,  4.0, -1.5),
        (38.0,  42.0, -2.5,  2.5),
        (60.0,  52.0,  5.0,  0.0),
        (82.0,  45.0, -3.0, -2.0),
        (105.0, 49.0,  1.5,  1.0),
    )

    wires = tuple(
        cq.Wire.makeCircle(
            radius,
            cq.Vector(
                x_shift,
                y_shift,
                z,
            ),
            cq.Vector(
                0.0,
                0.0,
                1.0,
            ),
        )
        for z, radius, x_shift, y_shift
        in sections
    )

    shape = cq.Solid.makeLoft(
        wires,
        ruled=False,
    ).clean()

    if not shape.isValid():
        raise RuntimeError(
            "Organic core is invalid."
        )

    return shape


def _hybridize(
    organic: cq.Shape,
) -> cq.Shape:
    """
    Mix the organic loft with primitive geometry.

    - cylindrical pedestal
    - toroidal/ring-like top collar made from revolved circle
    - spherical side nodes
    """
    pedestal = cq.Solid.makeCylinder(
        40.0,
        9.0,
        cq.Vector(0.0, 0.0, -9.0),
        cq.Vector(0.0, 0.0, 1.0),
    )

    # Primitive toroidal collar.
    # Use cadquery.func.torus(), which is already validated in this
    # CadQuery installation and avoids version-specific Solid.revolve()
    # overload differences.
    collar = torus(
        50.0,
        3.5,
    ).translate(
        (
            0.0,
            0.0,
            105.0,
        )
    )

    if not collar.isValid():
        raise RuntimeError(
            "Toroidal collar is invalid."
        )

    left_node = cq.Solid.makeSphere(
        8.0,
        cq.Vector(-43.0, 0.0, 56.0),
    )

    right_node = cq.Solid.makeSphere(
        8.0,
        cq.Vector(47.0, 0.0, 56.0),
    )

    result = organic

    for tool in (
        pedestal,
        collar,
        left_node,
        right_node,
    ):
        result = result.fuse(
            tool,
            tol=0.005,
        ).clean()

        if not result.isValid():
            raise RuntimeError(
                "Hybrid primitive fusion became invalid."
            )

    return _primary_solid(result)


def _boolean_details(
    shape: cq.Shape,
) -> cq.Shape:
    """
    Explicit subtractive Boolean features:
    - front circular port
    - rear circular port
    - vertical slot
    """
    front_port = cq.Solid.makeCylinder(
        7.0,
        30.0,
        cq.Vector(0.0, -70.0, 56.0),
        cq.Vector(0.0, 1.0, 0.0),
    )

    rear_port = cq.Solid.makeCylinder(
        5.0,
        30.0,
        cq.Vector(0.0, 70.0, 76.0),
        cq.Vector(0.0, -1.0, 0.0),
    )

    slot = (
        cq.Workplane("YZ")
        .center(0.0, 31.0)
        .rect(7.0, 26.0)
        .extrude(90.0, both=True)
        .val()
    )

    result = shape

    for tool in (
        front_port,
        rear_port,
        slot,
    ):
        result = result.cut(
            tool,
            tol=0.005,
        ).clean()

        if not result.isValid():
            raise RuntimeError(
                "Subtractive Boolean became invalid."
            )

    return _primary_solid(result)


def _geometric_decoration(
    shape: cq.Shape,
) -> cq.Shape:
    """
    Additive geometric decoration independent from text/SVG.

    A ring of small spherical studs around the lower zone.
    """
    result = shape

    count = 10
    radius = 42.0
    z = 22.0

    for index in range(count):
        angle = (
            2.0
            * math.pi
            * index
            / count
        )

        center = cq.Vector(
            radius * math.cos(angle),
            radius * math.sin(angle),
            z,
        )

        stud = cq.Solid.makeSphere(
            3.2,
            center,
        )

        result = result.fuse(
            stud,
            tol=0.005,
        ).clean()

        if not result.isValid():
            raise RuntimeError(
                f"Geometric stud {index} made model invalid."
            )

    return _primary_solid(result)


def _select_organic_face(
    shape: cq.Shape,
) -> cq.Face:
    """
    Prefer the freeform B-Spline face if OCC preserves the type
    after booleans. Fall back to the existing largest curved face
    selector.
    """
    selector = SurfaceFaceSelector()

    bspline_faces = tuple(
        face
        for face in shape.Faces()
        if face.geomType().upper()
        in {
            "BSPLINE",
            "BEZIER",
        }
    )

    if bspline_faces:
        return max(
            bspline_faces,
            key=lambda face: float(
                face.Area()
            ),
        )

    return selector.largest_external(
        shape
    )


def _export(
    shape: cq.Shape,
    filename: str,
) -> str:
    os.makedirs(
        OUTPUT_DIRECTORY,
        exist_ok=True,
    )

    path = os.path.join(
        OUTPUT_DIRECTORY,
        filename,
    )

    cq.exporters.export(
        shape,
        path,
    )

    if not os.path.isfile(path):
        raise RuntimeError(
            "STEP export failed."
        )

    return path


def _primary_solid(
    shape: cq.Shape,
) -> cq.Shape:
    solids = tuple(
        shape.Solids()
    )

    if not solids:
        raise RuntimeError(
            "Operation produced no solids."
        )

    primary = max(
        solids,
        key=lambda solid: float(
            solid.Volume()
        ),
    ).clean()

    if not primary.isValid():
        raise RuntimeError(
            "Primary solid is invalid."
        )

    return primary


def build_hybrid_showcase():
    designer = SurfaceDesigner()

    # 1. Organic geometry.
    model = _organic_core()
    volume_organic = float(model.Volume())

    # 2. Mix with primitive solids.
    model = _hybridize(model)
    volume_hybrid = float(model.Volume())

    # 3. Subtractive booleans.
    model = _boolean_details(model)
    volume_boolean = float(model.Volume())

    # 4. Add geometric decoration.
    model = _geometric_decoration(model)
    volume_geometric = float(
        model.Volume()
    )

    # 5. Native text emboss on the surviving organic/freeform face.
    text_face = _select_organic_face(
        model
    )

    text_result = designer.add_text(
        base_shape=model,
        target_face=text_face,
        text="DOBO",
        size=12.0,
        mode=SurfaceDesignMode.EMBOSS,
        depth=1.8,
        font="Arial",
        kind="bold",
        width_fraction=0.32,
        height_fraction=0.18,
        u_center=0.50,
        v_center=0.64,
    )

    model = text_result.shape
    volume_text = float(
        model.Volume()
    )

    # 6. SVG deboss on the same product, but reselect the target face
    # after text + Boolean topology changes.
    svg_face = _select_organic_face(
        model
    )

    svg_result = designer.add_svg(
        base_shape=model,
        target_face=svg_face,
        svg=SVG_MARK,
        mode=SurfaceDesignMode.DEBOSS,
        depth=1.4,
        width_fraction=0.25,
        height_fraction=0.17,
        u_center=0.50,
        v_center=0.38,
        document_id="hybrid_showcase_svg",
    )

    model = _primary_solid(
        svg_result.shape
    )

    final_volume = float(
        model.Volume()
    )

    if not model.isValid():
        raise RuntimeError(
            "Final hybrid showcase is invalid."
        )

    if len(model.Solids()) != 1:
        raise RuntimeError(
            "Final hybrid showcase must be one solid."
        )

    path = _export(
        model,
        "dobo_hybrid_showcase.step",
    )

    return {
        "shape": model,
        "path": path,
        "volume_organic": volume_organic,
        "volume_hybrid": volume_hybrid,
        "volume_boolean": volume_boolean,
        "volume_geometric": volume_geometric,
        "volume_text": volume_text,
        "final_volume": final_volume,
        "faces": len(model.Faces()),
        "solids": len(model.Solids()),
    }


if __name__ == "__main__":
    build_hybrid_showcase()
