from __future__ import annotations

from dataclasses import dataclass

import cadquery as cq

from cadquery.func import (
    offset,
    text,
)

from kernel.geometry.solid_factory import SolidFactory

from product_generators.surface_mapping.cylinder_mapper import (
    CylinderSurfaceMapper,
)
from product_generators.surface_mapping.cone_mapper import (
    ConeSurfaceMapper,
)


@dataclass(frozen=True, slots=True)
class NativeSurfaceTextResult:
    shape: cq.Shape
    projected_shape: cq.Shape
    text_tool: cq.Shape
    base_volume: float
    final_volume: float
    mode: str
    solid_count: int

    def validate(self) -> None:
        if not isinstance(self.shape, cq.Shape):
            raise TypeError("shape must be a CadQuery Shape.")

        if not self.shape.isValid():
            raise RuntimeError(
                "Native surface text final shape is invalid."
            )

        if not isinstance(self.projected_shape, cq.Shape):
            raise TypeError(
                "projected_shape must be a CadQuery Shape."
            )

        if not isinstance(self.text_tool, cq.Shape):
            raise TypeError(
                "text_tool must be a CadQuery Shape."
            )

        if self.base_volume <= 0.0:
            raise ValueError("base_volume must be positive.")

        if self.final_volume <= 0.0:
            raise ValueError("final_volume must be positive.")

        if self.solid_count != 1:
            raise RuntimeError(
                "Native text result must contain exactly one body."
            )


class NativeSurfaceTextBuilder:
    """
    Native CadQuery surface-text implementation.

    Cylinder text uses:
        cadquery.func.text(..., spine, base_surface)
        cadquery.func.offset(...)

    Offset direction:
        emboss -> positive / outward
        deboss -> negative / inward
    """

    def apply(
        self,
        *,
        base_shape: cq.Shape,
        surface,
        text_value: str,
        size: float,
        depth: float,
        mode: str,
        font: str = "Arial",
        kind: str = "regular",
        u_offset: float = 0.0,
        v_offset: float = 0.0,
    ) -> NativeSurfaceTextResult:
        if not isinstance(base_shape, cq.Shape) or not base_shape.isValid():
            raise ValueError(
                "base_shape must be a valid CadQuery Shape."
            )

        if not isinstance(text_value, str) or not text_value.strip():
            raise ValueError("text_value cannot be empty.")

        size = float(size)
        depth = float(depth)

        if size <= 0.0 or depth <= 0.0:
            raise ValueError("size and depth must be positive.")

        if mode not in {"emboss", "deboss"}:
            raise ValueError(
                "mode must be 'emboss' or 'deboss'."
            )

        if isinstance(surface, CylinderSurfaceMapper):
            projected, tool = self._cylinder_text(
                base_shape=base_shape,
                surface=surface,
                text_value=text_value,
                size=size,
                depth=depth,
                mode=mode,
                font=font,
                kind=kind,
                u_offset=float(u_offset),
                v_offset=float(v_offset),
            )
        elif isinstance(surface, ConeSurfaceMapper):
            raise NotImplementedError(
                "Native text Phase 2 currently validates "
                "cylindrical surfaces only. Cone support is next."
            )
        else:
            raise NotImplementedError(
                "Native text Phase 2 currently validates "
                "cylindrical surfaces only."
            )

        base_contract = SolidFactory.from_shape(
            geometry=base_shape.clean(),
            source="surface_designer:native_text_base",
            metadata={
                "text": text_value,
                "mode": mode,
            },
        )

        try:
            if mode == "emboss":
                raw = base_shape.fuse(
                    tool,
                    tol=0.01,
                )
            else:
                raw = base_shape.cut(
                    tool,
                    tol=0.01,
                )
        except Exception as error:
            raise RuntimeError(
                "Native surface text Boolean failed."
            ) from error

        cleaned = raw.clean()

        final_shape = self._single_primary_solid(
            cleaned
        )

        final_contract = SolidFactory.from_shape(
            geometry=final_shape,
            source="surface_designer:native_text_final",
            metadata={
                "text": text_value,
                "mode": mode,
            },
        )

        result = NativeSurfaceTextResult(
            shape=final_contract.geometry,
            projected_shape=projected,
            text_tool=tool,
            base_volume=float(base_contract.volume),
            final_volume=float(final_contract.volume),
            mode=mode,
            solid_count=len(
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
                f"Native text {mode} produced no measurable "
                f"volume change."
            )

        return result

    def _cylinder_text(
        self,
        *,
        base_shape: cq.Shape,
        surface: CylinderSurfaceMapper,
        text_value: str,
        size: float,
        depth: float,
        mode: str,
        font: str,
        kind: str,
        u_offset: float,
        v_offset: float,
    ) -> tuple[cq.Shape, cq.Shape]:
        cylindrical_faces = [
            face
            for face in base_shape.Faces()
            if face.geomType() == "CYLINDER"
        ]

        if not cylindrical_faces:
            raise RuntimeError(
                "Base shape contains no cylindrical face."
            )

        lateral_face = max(
            cylindrical_faces,
            key=lambda face: float(face.Area()),
        )

        circular_edges = [
            edge
            for edge in base_shape.Edges()
            if edge.geomType() == "CIRCLE"
        ]

        if not circular_edges:
            raise RuntimeError(
                "Cylinder contains no circular edge for text spine."
            )

        reference_edge = min(
            circular_edges,
            key=lambda edge: abs(
                float(edge.Center().z)
                - float(v_offset)
            ),
        )

        dz = (
            float(v_offset)
            - float(reference_edge.Center().z)
        )

        spine = reference_edge.translate(
            (0.0, 0.0, dz)
        )

        if not spine.isValid():
            raise RuntimeError(
                "Native text spine is invalid."
            )

        projected = text(
            text_value,
            size,
            spine,
            lateral_face,
            font=font,
            kind=kind,
            halign="center",
            valign="center",
        )

        if not projected.isValid():
            raise RuntimeError(
                "Native projected text is invalid."
            )

        # Critical correction:
        # lateral cylinder normals point outward.
        # emboss needs outward thickness; deboss must penetrate inward.
        signed_depth = (
            depth
            if mode == "emboss"
            else -depth
        )

        try:
            tool = offset(
                projected,
                signed_depth,
                cap=True,
            )
        except Exception as error:
            raise RuntimeError(
                f"Native text {mode} offset failed."
            ) from error

        if not tool.isValid():
            raise RuntimeError(
                f"Native text {mode} offset tool is invalid."
            )

        if abs(u_offset) > 1e-12:
            angle_deg = (
                float(u_offset)
                / float(surface.radius)
                * 180.0
                / 3.141592653589793
            )

            projected = projected.rotate(
                (0.0, 0.0, 0.0),
                (0.0, 0.0, 1.0),
                angle_deg,
            )

            tool = tool.rotate(
                (0.0, 0.0, 0.0),
                (0.0, 0.0, 1.0),
                angle_deg,
            )

        return projected, tool

    @staticmethod
    def _single_primary_solid(
        shape: cq.Shape,
    ) -> cq.Shape:
        solids = tuple(
            shape.Solids()
        )

        if not solids:
            raise RuntimeError(
                "Native text Boolean produced no solids."
            )

        primary = max(
            solids,
            key=lambda solid: float(solid.Volume()),
        ).clean()

        if not primary.isValid():
            raise RuntimeError(
                "Native text primary body is invalid."
            )

        return primary
