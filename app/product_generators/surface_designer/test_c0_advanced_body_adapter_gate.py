from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import trimesh

from product_generators.design_interpreter.macroblock_a4_matrix_cli import main as a4_matrix_main
from product_generators.surface_designer.advanced_body_adapter import (
    load_advanced_stl_as_cadquery_shape,
    local_surface_mapping_proxy,
)
from product_generators.surface_designer.contracts import SurfaceDesignMode
from product_generators.surface_designer.designer import SurfaceDesigner


def test_advanced_branching_body_reaches_surface_designer_without_morphology_replacement(monkeypatch):
    with TemporaryDirectory() as directory:
        output_root = Path(directory) / "c0-adapter"
        monkeypatch.setattr(
            "sys.argv",
            [
                "macroblock_a4_matrix_cli",
                "--output-root",
                str(output_root),
                "--case",
                "branching",
            ],
        )
        a4_matrix_main()

        stl = next(output_root.rglob("*.stl"))
        mesh = trimesh.load_mesh(stl, process=False)
        shape = load_advanced_stl_as_cadquery_shape(stl)

        bb = shape.BoundingBox()
        mesh_ext = mesh.bounds
        occ_ext = ((bb.xmin, bb.ymin, bb.zmin), (bb.xmax, bb.ymax, bb.zmax))
        max_delta = max(
            abs(float(mesh_ext[i][j]) - float(occ_ext[i][j]))
            for i in range(2)
            for j in range(3)
        )
        assert max_delta <= 1e-3
        assert shape.Solids()

        # The STL boundary is intentionally triangulated, so one OCC face is
        # only one tiny triangle. Use an interface-only local mapping proxy
        # derived from that exact mesh; every Boolean still operates on `shape`
        # or on the directly decorated result of that same advanced body.
        target_face = local_surface_mapping_proxy(
            stl,
            width_mm=34.0,
            height_mm=22.0,
            inset_mm=0.45,
        )
        designer = SurfaceDesigner()

        base_volume = float(shape.Volume())
        text_result = designer.add_text(
            base_shape=shape,
            target_face=target_face,
            text="DOBO",
            size=12.0,
            mode=SurfaceDesignMode.EMBOSS,
            depth=1.8,
            width_fraction=0.62,
            height_fraction=0.36,
            u_center=0.5,
            v_center=0.69,
            font="Arial",
            kind="bold",
        )
        text_volume = float(text_result.shape.Volume())
        assert text_volume > base_volume + 1e-8
        assert len(text_result.shape.Solids()) == 1

        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 24">'
            '<path d="M 0 12 L 10 0 L 20 12 L 30 0 L 40 12 '
            'L 30 24 L 20 12 L 10 24 Z"/>'
            '</svg>'
        )
        svg_result = designer.add_svg(
            base_shape=text_result.shape,
            target_face=target_face,
            svg=svg,
            mode=SurfaceDesignMode.DEBOSS,
            depth=1.4,
            width_fraction=0.42,
            height_fraction=0.28,
            u_center=0.5,
            v_center=0.28,
            document_id="c0_advanced_branching_svg",
        )
        svg_volume = float(svg_result.shape.Volume())
        assert svg_volume < text_volume - 1e-8
        assert len(svg_result.shape.Solids()) == 1
