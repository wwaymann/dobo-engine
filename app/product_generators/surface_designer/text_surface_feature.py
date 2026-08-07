from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

import cadquery as cq

from kernel.geometry.solid_factory import SolidFactory


class TextSurfaceMode(str, Enum):
    EMBOSS = "emboss"
    DEBOSS = "deboss"


class SurfaceSampler(Protocol):
    def sample(self, u: float, v: float):
        ...


@dataclass(frozen=True, slots=True)
class TextSurfaceFeatureResult:
    shape: cq.Shape
    base_volume: float
    final_volume: float
    glyph_face_count: int
    triangle_count: int
    boolean_count: int
    discarded_fragment_count: int
    discarded_fragment_volume: float

    def validate(self) -> None:
        if not isinstance(self.shape, cq.Shape):
            raise TypeError("shape must be a CadQuery Shape.")

        if not self.shape.isValid():
            raise RuntimeError(
                "Text surface feature result is invalid."
            )

        if self.base_volume <= 0.0 or self.final_volume <= 0.0:
            raise ValueError("Volumes must be positive.")

        if self.glyph_face_count < 1:
            raise ValueError("glyph_face_count must be positive.")

        if self.triangle_count < 1:
            raise ValueError("triangle_count must be positive.")

        if self.boolean_count < 1:
            raise ValueError("boolean_count must be positive.")


class DirectOCCTextSurfaceFeatureBuilder:
    """
    Direct OCC glyph-face text mapping.

    Text Boolean operations are performed above the Kernel because OCC
    can return a geometrically correct but temporarily invalid B-Rep
    containing removable splitter/sliver topology.

    The route is:

        current valid body
        -> OCC fuse/cut
        -> clean()
        -> keep connected primary body
        -> SolidFactory validation
        -> next glyph

    This does not modify Kernel architecture.
    """

    def __init__(
        self,
        *,
        mesh_tolerance: float = 0.08,
        angular_tolerance: float = 0.1,
        boolean_tolerance: float = 0.01,
    ) -> None:
        if mesh_tolerance <= 0.0:
            raise ValueError("mesh_tolerance must be positive.")

        if angular_tolerance <= 0.0:
            raise ValueError("angular_tolerance must be positive.")

        if boolean_tolerance <= 0.0:
            raise ValueError("boolean_tolerance must be positive.")

        self._mesh_tolerance = float(mesh_tolerance)
        self._angular_tolerance = float(angular_tolerance)
        self._boolean_tolerance = float(boolean_tolerance)

    def apply(
        self,
        *,
        base_shape: cq.Shape,
        surface: SurfaceSampler,
        text: str,
        size: float,
        depth: float,
        mode: TextSurfaceMode,
        font: str = "Arial",
        kind: str = "regular",
        u_offset: float = 0.0,
        v_offset: float = 0.0,
        scale_u: float = 1.0,
        scale_v: float = 1.0,
    ) -> TextSurfaceFeatureResult:
        if not isinstance(base_shape, cq.Shape) or not base_shape.isValid():
            raise ValueError(
                "base_shape must be a valid CadQuery Shape."
            )

        if not isinstance(mode, TextSurfaceMode):
            raise TypeError("mode must be TextSurfaceMode.")

        if not isinstance(text, str) or not text.strip():
            raise ValueError("text cannot be empty.")

        size = float(size)
        depth = float(depth)

        if size <= 0.0 or depth <= 0.0:
            raise ValueError("size and depth must be positive.")

        text_shape = self._make_text(
            text=text,
            size=size,
            font=font,
            kind=kind,
        )

        faces = self._bottom_faces(text_shape)

        if not faces:
            raise RuntimeError(
                "Could not locate glyph footprint faces."
            )

        base_contract = SolidFactory.from_shape(
            geometry=base_shape.clean(),
            source="surface_designer:text_base",
            metadata={
                "text": text,
                "font": font,
                "kind": kind,
            },
        )

        current_shape = base_contract.geometry
        base_volume = float(base_contract.volume)

        inward = mode is TextSurfaceMode.DEBOSS
        triangle_total = 0
        boolean_count = 0
        discarded_count_total = 0
        discarded_volume_total = 0.0

        for face_index, face in enumerate(faces):
            glyph_shape, triangle_count = self._mapped_face_tool(
                face=face,
                surface=surface,
                depth=depth,
                inward=inward,
                u_offset=float(u_offset),
                v_offset=float(v_offset),
                scale_u=float(scale_u),
                scale_v=float(scale_v),
            )

            triangle_total += triangle_count

            # Validate the tool before using it.
            SolidFactory.from_shape(
                geometry=glyph_shape.clean(),
                source="surface_designer:text_glyph",
                metadata={
                    "glyph_face_index": face_index,
                    "text": text,
                },
            )

            current_shape = self._apply_clean_boolean(
                base=current_shape,
                tool=glyph_shape,
                mode=mode,
                face_index=face_index,
            )

            (
                current_shape,
                discarded_count,
                discarded_volume,
            ) = self._normalize_single_body(
                current_shape
            )

            discarded_count_total += discarded_count
            discarded_volume_total += discarded_volume

            # Re-enter the existing public Solid contract after every glyph.
            current_contract = SolidFactory.from_shape(
                geometry=current_shape.clean(),
                source="surface_designer:text_boolean_cleaned",
                metadata={
                    "text": text,
                    "glyph_face_index": face_index,
                    "mode": mode.value,
                },
            )

            current_shape = current_contract.geometry
            boolean_count += 1

        final_contract = SolidFactory.from_shape(
            geometry=current_shape.clean(),
            source="surface_designer:text_final",
            metadata={
                "text": text,
                "font": font,
                "kind": kind,
                "mode": mode.value,
            },
        )

        result = TextSurfaceFeatureResult(
            shape=final_contract.geometry,
            base_volume=base_volume,
            final_volume=float(final_contract.volume),
            glyph_face_count=len(faces),
            triangle_count=triangle_total,
            boolean_count=boolean_count,
            discarded_fragment_count=discarded_count_total,
            discarded_fragment_volume=discarded_volume_total,
        )
        result.validate()

        if mode is TextSurfaceMode.EMBOSS:
            if result.final_volume <= result.base_volume:
                raise RuntimeError(
                    "Text emboss did not increase model volume."
                )
        else:
            if result.final_volume >= result.base_volume:
                raise RuntimeError(
                    "Text deboss did not decrease model volume."
                )

        return result

    def _apply_clean_boolean(
        self,
        *,
        base: cq.Shape,
        tool: cq.Shape,
        mode: TextSurfaceMode,
        face_index: int,
    ) -> cq.Shape:
        try:
            if mode is TextSurfaceMode.EMBOSS:
                raw = base.fuse(
                    tool,
                    tol=self._boolean_tolerance,
                )
            else:
                raw = base.cut(
                    tool,
                    tol=self._boolean_tolerance,
                )
        except Exception as error:
            raise RuntimeError(
                f"Text Boolean failed for glyph face {face_index}."
            ) from error

        if not isinstance(raw, cq.Shape):
            raise RuntimeError(
                f"Glyph face {face_index} Boolean returned no Shape."
            )

        # OCC cleanup is intentionally performed before public validation.
        try:
            cleaned = raw.clean()
        except Exception as error:
            raise RuntimeError(
                f"Could not clean Boolean result for glyph face "
                f"{face_index}."
            ) from error

        if cleaned.isValid():
            return cleaned

        # Some OCC results become valid after selecting the principal solid
        # from an otherwise invalid/disconnected compound.
        solids = tuple(cleaned.Solids())

        if solids:
            ordered = sorted(
                solids,
                key=lambda solid: float(solid.Volume()),
                reverse=True,
            )

            primary = ordered[0].clean()

            if primary.isValid():
                return primary

        raise RuntimeError(
            f"Text Boolean result remains invalid after cleanup "
            f"for glyph face {face_index}."
        )

    @staticmethod
    def _make_text(
        *,
        text: str,
        size: float,
        font: str,
        kind: str,
    ) -> cq.Shape:
        try:
            shape = cq.Compound.makeText(
                text,
                size,
                1.0,
                font=font,
                kind=kind,
                halign="left",
                valign="bottom",
            )
        except Exception as error:
            raise RuntimeError(
                f"Could not generate text with font '{font}'."
            ) from error

        if not isinstance(shape, cq.Shape) or not shape.isValid():
            raise RuntimeError(
                "CadQuery generated invalid text geometry."
            )

        return shape

    @staticmethod
    def _bottom_faces(
        shape: cq.Shape,
        *,
        tolerance: float = 1e-6,
    ) -> tuple[cq.Face, ...]:
        z_min = float(shape.BoundingBox().zmin)

        return tuple(
            face
            for face in shape.Faces()
            if (
                abs(
                    float(face.BoundingBox().zmax)
                    - float(face.BoundingBox().zmin)
                )
                <= tolerance
                and abs(
                    float(face.BoundingBox().zmin)
                    - z_min
                )
                <= tolerance
            )
        )

    def _mapped_face_tool(
        self,
        *,
        face: cq.Face,
        surface: SurfaceSampler,
        depth: float,
        inward: bool,
        u_offset: float,
        v_offset: float,
        scale_u: float,
        scale_v: float,
    ) -> tuple[cq.Shape, int]:
        try:
            vertices, triangles = face.tessellate(
                self._mesh_tolerance,
                self._angular_tolerance,
            )
        except Exception as error:
            raise RuntimeError(
                "OCC could not tessellate original glyph face."
            ) from error

        if not triangles:
            raise RuntimeError(
                "Glyph face tessellation produced no triangles."
            )

        samples = tuple(
            surface.sample(
                u_offset + float(vertex.x) * scale_u,
                v_offset + float(vertex.y) * scale_v,
            )
            for vertex in vertices
        )

        solids: list[cq.Shape] = []

        for triangle in triangles:
            a_index = int(triangle[0])
            b_index = int(triangle[1])
            c_index = int(triangle[2])

            solid = self._triangle_prism(
                (
                    samples[a_index],
                    samples[b_index],
                    samples[c_index],
                ),
                depth=depth,
                inward=inward,
            )

            if not solid.isValid():
                raise RuntimeError(
                    "Mapped glyph triangle prism is invalid."
                )

            solids.append(solid)

        # Merge tessellation cells into one coherent glyph tool.
        merged: cq.Shape = solids[0]

        for solid in solids[1:]:
            try:
                merged = merged.fuse(
                    solid,
                    tol=0.001,
                ).clean()
            except Exception as error:
                raise RuntimeError(
                    "Could not merge mapped glyph tessellation cells."
                ) from error

            if not merged.isValid():
                raise RuntimeError(
                    "Mapped glyph tool became invalid while merging cells."
                )

        return merged.clean(), len(triangles)

    @staticmethod
    def _triangle_prism(
        samples,
        *,
        depth: float,
        inward: bool,
    ) -> cq.Shape:
        sign = -1.0 if inward else 1.0

        base: list[cq.Vector] = []
        top: list[cq.Vector] = []

        for sample in samples:
            sample.validate()

            base.append(cq.Vector(*sample.point))

            top.append(
                cq.Vector(
                    sample.point[0]
                    + sample.frame.normal[0] * depth * sign,
                    sample.point[1]
                    + sample.frame.normal[1] * depth * sign,
                    sample.point[2]
                    + sample.frame.normal[2] * depth * sign,
                )
            )

        faces = [
            DirectOCCTextSurfaceFeatureBuilder._triangle_face(
                base[0], base[1], base[2]
            ),
            DirectOCCTextSurfaceFeatureBuilder._triangle_face(
                top[2], top[1], top[0]
            ),
        ]

        for a, b in ((0, 1), (1, 2), (2, 0)):
            faces.append(
                DirectOCCTextSurfaceFeatureBuilder._triangle_face(
                    base[a], base[b], top[b]
                )
            )
            faces.append(
                DirectOCCTextSurfaceFeatureBuilder._triangle_face(
                    base[a], top[b], top[a]
                )
            )

        shell = cq.Shell.makeShell(faces)

        if not shell.isValid():
            raise RuntimeError(
                "Glyph triangle prism shell is invalid."
            )

        return cq.Solid.makeSolid(shell).clean()

    @staticmethod
    def _triangle_face(
        a: cq.Vector,
        b: cq.Vector,
        c: cq.Vector,
    ) -> cq.Face:
        wire = cq.Wire.makePolygon(
            (a, b, c),
            close=True,
        )

        face = cq.Face.makeFromWires(wire)

        if not face.isValid():
            raise RuntimeError(
                "Glyph triangle face is invalid."
            )

        return face

    @staticmethod
    def _normalize_single_body(
        shape: cq.Shape,
    ) -> tuple[cq.Shape, int, float]:
        solids = tuple(shape.Solids())

        if not solids:
            raise RuntimeError(
                "Text Boolean result contains no solids."
            )

        ordered = sorted(
            solids,
            key=lambda solid: float(solid.Volume()),
            reverse=True,
        )

        primary = ordered[0].clean()
        discarded = ordered[1:]

        return (
            primary,
            len(discarded),
            sum(float(solid.Volume()) for solid in discarded),
        )
