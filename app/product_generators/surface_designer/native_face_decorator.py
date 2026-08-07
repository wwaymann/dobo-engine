from __future__ import annotations

from dataclasses import dataclass

import cadquery as cq

from cadquery.func import (
    faceOn,
    offset,
)

from kernel.geometry.solid_factory import SolidFactory

from .uv_placement import (
    UVPlacement,
    UVPlacementResolver,
)


@dataclass(frozen=True, slots=True)
class NativeFaceDecorationResult:
    shape: cq.Shape
    mapped_faces: cq.Shape
    tool: cq.Shape
    base_volume: float
    final_volume: float
    mode: str
    solids: int

    def validate(self) -> None:
        if not isinstance(self.shape, cq.Shape):
            raise TypeError("shape must be CadQuery Shape.")

        if not self.shape.isValid():
            raise RuntimeError(
                "Final decorated shape is invalid."
            )

        if self.solids != 1:
            raise RuntimeError(
                "Decoration must leave one connected product body."
            )

        if self.base_volume <= 0.0:
            raise ValueError("base_volume must be positive.")

        if self.final_volume <= 0.0:
            raise ValueError("final_volume must be positive.")


class NativeFaceDecorator:
    """
    Maps planar B-Rep faces onto an arbitrary target cq.Face using OCC.

    No analytical surface mapper is required here.

        planar face(s)
            -> UV placement
            -> faceOn(target_face, ...)
            -> offset()
            -> fuse/cut
            -> one final solid
    """

    def __init__(
        self,
        *,
        boolean_tolerance: float = 0.005,
    ) -> None:
        if boolean_tolerance <= 0.0:
            raise ValueError(
                "boolean_tolerance must be positive."
            )

        self._boolean_tolerance = float(
            boolean_tolerance
        )

        self._placement = UVPlacementResolver()

    def decorate(
        self,
        *,
        base_shape: cq.Shape,
        target_face: cq.Face,
        planar_shape: cq.Shape,
        mode: str,
        depth: float,
        placement: UVPlacement | None = None,
        width_fraction: float = 0.28,
        height_fraction: float = 0.22,
        u_center: float = 0.5,
        v_center: float = 0.5,
    ) -> NativeFaceDecorationResult:
        if mode not in {"emboss", "deboss"}:
            raise ValueError(
                "mode must be 'emboss' or 'deboss'."
            )

        depth = float(depth)

        if depth <= 0.0:
            raise ValueError(
                "depth must be positive."
            )

        if not isinstance(base_shape, cq.Shape):
            raise TypeError(
                "base_shape must be CadQuery Shape."
            )

        if not base_shape.isValid():
            raise ValueError(
                "base_shape must be valid."
            )

        if not isinstance(target_face, cq.Face):
            raise TypeError(
                "target_face must be CadQuery Face."
            )

        if not target_face.isValid():
            raise ValueError(
                "target_face must be valid."
            )

        if placement is None:
            placement = self._placement.centered(
                target_face=target_face,
                planar_shape=planar_shape,
                width_fraction=width_fraction,
                height_fraction=height_fraction,
                u_center=u_center,
                v_center=v_center,
            )

        placement.validate()

        placed = self._transform_planar(
            planar_shape,
            placement,
        )

        mapped = faceOn(
            target_face,
            placed,
        )

        if not isinstance(mapped, cq.Shape):
            raise RuntimeError(
                "faceOn did not return a CadQuery Shape."
            )

        if not mapped.isValid():
            raise RuntimeError(
                "Mapped decoration faces are invalid."
            )

        signed_depth = (
            depth
            if mode == "emboss"
            else -depth
        )

        try:
            tool = offset(
                mapped,
                signed_depth,
                cap=True,
            )
        except Exception as error:
            raise RuntimeError(
                f"Could not offset mapped decoration for {mode}."
            ) from error

        if not tool.isValid():
            raise RuntimeError(
                "Mapped decoration tool is invalid."
            )

        base_contract = SolidFactory.from_shape(
            geometry=base_shape.clean(),
            source="surface_designer:native_face_base",
            metadata={
                "mode": mode,
            },
        )

        try:
            if mode == "emboss":
                raw = base_shape.fuse(
                    tool,
                    tol=self._boolean_tolerance,
                )
            else:
                raw = base_shape.cut(
                    tool,
                    tol=self._boolean_tolerance,
                )
        except Exception as error:
            raise RuntimeError(
                f"Native face {mode} Boolean failed."
            ) from error

        cleaned = raw.clean()

        final_shape = self._primary_solid(
            cleaned
        )

        final_contract = SolidFactory.from_shape(
            geometry=final_shape,
            source="surface_designer:native_face_final",
            metadata={
                "mode": mode,
            },
        )

        result = NativeFaceDecorationResult(
            shape=final_contract.geometry,
            mapped_faces=mapped,
            tool=tool,
            base_volume=float(
                base_contract.volume
            ),
            final_volume=float(
                final_contract.volume
            ),
            mode=mode,
            solids=len(
                final_contract.geometry.Solids()
            ),
        )
        result.validate()

        delta = (
            result.final_volume
            - result.base_volume
            if mode == "emboss"
            else result.base_volume
            - result.final_volume
        )

        if delta <= 1e-8:
            raise RuntimeError(
                f"{mode} produced no measurable volume change."
            )

        return result

    @staticmethod
    def _transform_planar(
        shape: cq.Shape,
        placement: UVPlacement,
    ) -> cq.Shape:
        """
        Apply non-uniform UV scaling plus translation.

        CadQuery Shape.scale() is uniform-only in the installed API.
        UV placement needs independent U and V scale factors, so use
        a general affine Matrix and transformGeometry().
        """
        matrix = cq.Matrix(
            [
                [
                    placement.scale_u,
                    0.0,
                    0.0,
                    placement.u_offset,
                ],
                [
                    0.0,
                    placement.scale_v,
                    0.0,
                    placement.v_offset,
                ],
                [
                    0.0,
                    0.0,
                    1.0,
                    0.0,
                ],
            ]
        )

        transformed = shape.transformGeometry(
            matrix
        )

        if not isinstance(transformed, cq.Shape):
            raise RuntimeError(
                "UV affine transform did not return a CadQuery Shape."
            )

        if not transformed.isValid():
            raise RuntimeError(
                "Placed planar decoration is invalid."
            )

        return transformed

    @staticmethod
    def _primary_solid(
        shape: cq.Shape,
    ) -> cq.Shape:
        solids = tuple(
            shape.Solids()
        )

        if not solids:
            raise RuntimeError(
                "Decoration Boolean produced no solids."
            )

        primary = max(
            solids,
            key=lambda solid: float(
                solid.Volume()
            ),
        ).clean()

        if not primary.isValid():
            raise RuntimeError(
                "Primary decorated product body is invalid."
            )

        return primary
