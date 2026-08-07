from __future__ import annotations

import cadquery as cq

from .native_face_decorator import (
    NativeFaceDecorationResult,
    NativeFaceDecorator,
)
from .svg_planar import (
    SvgPlanarFaceBuilder,
)


class NativeSvgFaceDecorator:
    def __init__(self) -> None:
        self._planar = SvgPlanarFaceBuilder()
        self._decorator = NativeFaceDecorator()

    def decorate(
        self,
        *,
        base_shape: cq.Shape,
        target_face: cq.Face,
        svg: str,
        mode: str,
        depth: float,
        width_fraction: float = 0.28,
        height_fraction: float = 0.22,
        u_center: float = 0.5,
        v_center: float = 0.5,
        document_id: str = "native_surface_svg",
    ) -> NativeFaceDecorationResult:
        planar = self._planar.build(
            svg,
            document_id=document_id,
        )

        return self._decorator.decorate(
            base_shape=base_shape,
            target_face=target_face,
            planar_shape=planar,
            mode=mode,
            depth=depth,
            width_fraction=width_fraction,
            height_fraction=height_fraction,
            u_center=u_center,
            v_center=v_center,
        )
