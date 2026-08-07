from __future__ import annotations

import os

import cadquery as cq

from product_generators.surface_mapping.cylinder_mapper import (
    CylinderSurfaceMapper,
)

from .contracts import SurfaceDesignMode
from .designer import SurfaceDesigner


OUTPUT_DIRECTORY = (
    "outputs/product_generators/surface_designer/phase_2_native"
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
            f"{filename}: export failed."
        )

    return path


def main() -> None:
    print()
    print("DOBO Surface Designer - Phase 2 Native")
    print("Real Text on Cylinder")
    print("-----------------------------------")

    designer = SurfaceDesigner()

    cases = (
        (
            "native_dobo_emboss.step",
            "DOBO",
            SurfaceDesignMode.EMBOSS,
            "regular",
        ),
        (
            "native_open_deboss.step",
            "OPEN",
            SurfaceDesignMode.DEBOSS,
            "regular",
        ),
        (
            "native_b8_bold_emboss.step",
            "B8",
            SurfaceDesignMode.EMBOSS,
            "bold",
        ),
    )

    for filename, text_value, mode, kind in cases:
        base = cq.Solid.makeCylinder(
            50.0,
            110.0,
        ).clean()

        base_volume = float(
            base.Volume()
        )

        surface = CylinderSurfaceMapper(
            radius=50.0,
        )

        result = designer.add_text(
            base_shape=base,
            surface=surface,
            text=text_value,
            size=10.0,
            mode=mode,
            depth=1.3,
            font="Arial",
            kind=kind,
            u_offset=0.0,
            v_offset=55.0,
        )

        result.validate()

        solids = tuple(
            result.shape.Solids()
        )

        if len(solids) != 1:
            raise RuntimeError(
                f"{filename}: expected one connected body."
            )

        final_volume = float(
            result.shape.Volume()
        )

        delta = (
            final_volume - base_volume
            if mode is SurfaceDesignMode.EMBOSS
            else base_volume - final_volume
        )

        if delta <= 1e-8:
            raise RuntimeError(
                f"{filename}: expected positive volume delta."
            )

        path = _export(
            result.shape,
            filename,
        )

        print(
            filename,
            text_value,
            mode.value,
            "delta",
            round(delta, 6),
            "solids",
            len(solids),
            os.path.getsize(path),
            "bytes",
            "OK",
        )

    print("-----------------------------------")
    print("Models: 3")
    print("Surface Designer Phase 2 Native: Valid OK")
    print()


if __name__ == "__main__":
    main()
