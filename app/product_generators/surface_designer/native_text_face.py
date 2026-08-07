from __future__ import annotations

import cadquery as cq

from cadquery.func import text

from .native_face_decorator import (
    NativeFaceDecorationResult,
    NativeFaceDecorator,
)


class NativeTextFaceDecorator:
    """
    Maps native planar CadQuery text faces directly onto any target face.

    Important CadQuery API detail:
        text("DOBO", size)
    already produces planar text faces suitable for faceOn().

    The `planar=True` argument belongs to the overload that receives
    a spine. It must not be supplied to this overload.
    """

    def __init__(self) -> None:
        self._decorator = NativeFaceDecorator()

    def decorate(
        self,
        *,
        base_shape: cq.Shape,
        target_face: cq.Face,
        text_value: str,
        size: float,
        mode: str,
        depth: float,
        font: str = "Arial",
        kind: str = "regular",
        width_fraction: float = 0.30,
        height_fraction: float = 0.22,
        u_center: float = 0.5,
        v_center: float = 0.5,
    ) -> NativeFaceDecorationResult:
        if not isinstance(text_value, str) or not text_value.strip():
            raise ValueError(
                "text_value cannot be empty."
            )

        size = float(size)

        if size <= 0.0:
            raise ValueError(
                "size must be positive."
            )

        try:
            planar = text(
                text_value,
                size,
                font=font,
                kind=kind,
                halign="center",
                valign="center",
            )
        except Exception as error:
            raise RuntimeError(
                f"Could not create planar text '{text_value}' "
                f"with font '{font}'."
            ) from error

        if not isinstance(planar, cq.Shape):
            raise RuntimeError(
                "CadQuery planar text did not return a Shape."
            )

        if not planar.isValid():
            raise RuntimeError(
                "Planar text geometry is invalid."
            )

        faces = tuple(
            planar.Faces()
        )

        if not faces:
            raise RuntimeError(
                "Planar text produced no faces for faceOn()."
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
