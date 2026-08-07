from __future__ import annotations

import os

import cadquery as cq

from product_generators.surface_mapping.cylinder_mapper import (
    CylinderSurfaceMapper,
)

from .contracts import (
    SurfaceDesignMode,
)
from .designer import (
    SurfaceDesigner,
)


OUTPUT_DIRECTORY = (
    "outputs/product_generators/surface_designer/phase_1"
)

RADIUS = 50.0
HEIGHT = 110.0
OVERLAP = 0.7


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


def _surface(
    mode: SurfaceDesignMode,
):
    mapped_radius = (
        RADIUS - OVERLAP
        if mode is SurfaceDesignMode.EMBOSS
        else RADIUS + OVERLAP
    )

    return CylinderSurfaceMapper(
        radius=mapped_radius,
    )


def _base() -> cq.Shape:
    return cq.Solid.makeCylinder(
        RADIUS,
        HEIGHT,
    ).clean()


def build_gallery():
    designer = SurfaceDesigner()

    outputs = []

    svg_logo = """
    <svg xmlns="http://www.w3.org/2000/svg">
      <path d="M 0 0 L 18 0 L 26 10 L 18 20 L 0 20 L 8 10 Z"/>
    </svg>
    """

    cases = (
        (
            "designer_svg_emboss.step",
            lambda:
            designer.add_svg(
                base_shape=_base(),
                surface=_surface(
                    SurfaceDesignMode.EMBOSS
                ),
                svg=svg_logo,
                mode=SurfaceDesignMode.EMBOSS,
                depth=3.8,
                v_offset=40.0,
            ),
        ),
        (
            "designer_badge_deboss.step",
            lambda:
            designer.add_badge(
                base_shape=_base(),
                surface=_surface(
                    SurfaceDesignMode.DEBOSS
                ),
                width=28.0,
                height=20.0,
                kind="diamond",
                mode=SurfaceDesignMode.DEBOSS,
                depth=3.8,
                v_offset=40.0,
            ),
        ),
        (
            "designer_frame_emboss.step",
            lambda:
            designer.add_frame(
                base_shape=_base(),
                surface=_surface(
                    SurfaceDesignMode.EMBOSS
                ),
                width=34.0,
                height=26.0,
                border=6.0,
                mode=SurfaceDesignMode.EMBOSS,
                depth=3.8,
                v_offset=40.0,
            ),
        ),
        (
            "designer_text_proxy.step",
            lambda:
            designer.add_text(
                base_shape=_base(),
                surface=_surface(
                    SurfaceDesignMode.EMBOSS
                ),
                text="DOBO",
                size=9.0,
                mode=SurfaceDesignMode.EMBOSS,
                depth=3.8,
                v_offset=45.0,
            ),
        ),
    )

    for filename, factory in cases:
        result = factory()
        result.validate()

        path = _export(
            result.shape,
            filename,
        )

        outputs.append(
            (
                path,
                result,
            )
        )

    return tuple(outputs)
