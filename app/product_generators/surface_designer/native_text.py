from __future__ import annotations

from dataclasses import dataclass
import math

import cadquery as cq

from cadquery.func import (
    offset,
    text,
)

from kernel.geometry.solid_factory import SolidFactory

from product_generators.surface_mapping.cylinder_mapper import CylinderSurfaceMapper
from product_generators.surface_mapping.cone_mapper import ConeSurfaceMapper


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
            raise RuntimeError("Native surface text final shape is invalid.")
        if not isinstance(self.projected_shape, cq.Shape):
            raise TypeError("projected_shape must be a CadQuery Shape.")
        if not isinstance(self.text_tool, cq.Shape):
            raise TypeError("text_tool must be a CadQuery Shape.")
        if self.base_volume <= 0.0:
            raise ValueError("base_volume must be positive.")
        if self.final_volume <= 0.0:
            raise ValueError("final_volume must be positive.")
        if self.solid_count != 1:
            raise RuntimeError("Native text result must contain exactly one body.")


class NativeSurfaceTextBuilder:
    """Native CadQuery surface-text implementation."""

    def apply(self, *, base_shape: cq.Shape, surface, text_value: str, size: float,
              depth: float, mode: str, font: str = "Arial", kind: str = "regular",
              u_offset: float = 0.0, v_offset: float = 0.0) -> NativeSurfaceTextResult:
        if not isinstance(base_shape, cq.Shape) or not base_shape.isValid():
            raise ValueError("base_shape must be a valid CadQuery Shape.")
        if not isinstance(text_value, str) or not text_value.strip():
            raise ValueError("text_value cannot be empty.")
        size, depth = float(size), float(depth)
        if size <= 0.0 or depth <= 0.0:
            raise ValueError("size and depth must be positive.")
        if mode not in {"emboss", "deboss"}:
            raise ValueError("mode must be 'emboss' or 'deboss'.")

        if isinstance(surface, CylinderSurfaceMapper):
            projected, tool = self._cylinder_text(
                base_shape=base_shape, surface=surface, text_value=text_value,
                size=size, depth=depth, mode=mode, font=font, kind=kind,
                u_offset=float(u_offset), v_offset=float(v_offset),
            )
        elif isinstance(surface, ConeSurfaceMapper):
            raise NotImplementedError("Native text Phase 2 currently validates cylindrical surfaces only. Cone support is next.")
        else:
            raise NotImplementedError("Native text Phase 2 currently validates cylindrical surfaces only.")

        base_contract = SolidFactory.from_shape(
            geometry=base_shape.clean(), source="surface_designer:native_text_base",
            metadata={"text": text_value, "mode": mode},
        )
        try:
            if mode == "emboss":
                current = base_shape
                tool_solids = tuple(tool.Solids())
                if not tool_solids:
                    raise RuntimeError("Native text emboss tool contains no solids.")
                for glyph_index, glyph in enumerate(tool_solids):
                    before = float(current.Volume())
                    joined = current.fuse(glyph, tol=0.01).clean()
                    solids = tuple(joined.Solids())
                    if len(solids) != 1:
                        raise RuntimeError(f"Native text emboss glyph {glyph_index} did not join the vessel body.")
                    after = float(solids[0].Volume())
                    if after <= before + 1e-8:
                        raise RuntimeError(f"Native text emboss glyph {glyph_index} produced no measurable joined volume.")
                    current = solids[0]
                raw = current
            else:
                raw = base_shape.cut(tool, tol=0.01)
        except RuntimeError:
            raise
        except Exception as error:
            raise RuntimeError("Native surface text Boolean failed.") from error

        final_shape = self._single_primary_solid(raw.clean())
        final_contract = SolidFactory.from_shape(
            geometry=final_shape, source="surface_designer:native_text_final",
            metadata={"text": text_value, "mode": mode},
        )
        result = NativeSurfaceTextResult(
            shape=final_contract.geometry, projected_shape=projected, text_tool=tool,
            base_volume=float(base_contract.volume), final_volume=float(final_contract.volume),
            mode=mode, solid_count=len(final_contract.geometry.Solids()),
        )
        result.validate()
        delta = result.final_volume - result.base_volume if mode == "emboss" else result.base_volume - result.final_volume
        if delta <= 1e-8:
            raise RuntimeError(f"Native text {mode} produced no measurable volume change.")
        return result

    @staticmethod
    def _frontal_arc(radius: float, z: float, text_value: str, size: float) -> cq.Edge:
        """Return the known-good bounded projection arc on the +Y reference meridian."""
        glyph_count = max(1, len(text_value.strip()))
        estimated_width = max(size, glyph_count * size * 0.72)
        arc_length = min(estimated_width * 1.18, math.pi * radius * 0.82)
        half_angle = max(math.radians(3.0), min(0.5 * arc_length / radius, math.radians(73.0)))

        def point(angle: float) -> cq.Vector:
            return cq.Vector(radius * math.sin(angle), radius * math.cos(angle), z)

        left = point(-half_angle)
        middle = point(0.0)
        right = point(half_angle)
        arc = cq.Edge.makeThreePointArc(right, middle, left)
        if not arc.isValid():
            raise RuntimeError("Native frontal text arc is invalid.")
        return arc

    @staticmethod
    def _projection_size_limit(radius: float, text_value: str, requested_size: float) -> float:
        """Keep a line inside the same frontal arc without globally shrinking the block."""
        glyph_count = max(1, len(text_value.strip()))
        usable_arc = math.pi * radius * 0.82 * 0.92
        width_per_size = max(1.0, glyph_count * 0.72) * 1.18
        safe_size = usable_arc / width_per_size
        return min(float(requested_size), safe_size)

    @staticmethod
    def _angular_bounds_center(shape: cq.Shape, reference_angle: float) -> float:
        """Measure the visual angular midpoint of projected glyph geometry.

        CadQuery's path text can be centered parametrically on a spine while the
        resulting glyph outlines are not centered on the same cylindrical meridian.
        Use the actual projected vertices, unwrap them around the known +Y reference,
        and return the midpoint of their angular extent. This centers the visible
        text block, not merely the path used to create it.
        """
        angles: list[float] = []
        for vertex in shape.Vertices():
            point = vertex.toTuple()
            angle = math.atan2(float(point[1]), float(point[0]))
            while angle - reference_angle > math.pi:
                angle -= 2.0 * math.pi
            while angle - reference_angle < -math.pi:
                angle += 2.0 * math.pi
            angles.append(angle)
        if not angles:
            center = shape.Center()
            return math.atan2(float(center.y), float(center.x))
        return 0.5 * (min(angles) + max(angles))

    def _cylinder_text(self, *, base_shape: cq.Shape, surface: CylinderSurfaceMapper,
                       text_value: str, size: float, depth: float, mode: str,
                       font: str, kind: str, u_offset: float,
                       v_offset: float) -> tuple[cq.Shape, cq.Shape]:
        cylindrical_faces = [face for face in base_shape.Faces() if face.geomType() == "CYLINDER"]
        if not cylindrical_faces:
            raise RuntimeError("Base shape contains no cylindrical face.")
        lateral_face = max(cylindrical_faces, key=lambda face: float(face.Area()))

        projection_size = self._projection_size_limit(
            float(surface.radius), text_value, size
        )
        spine = self._frontal_arc(
            float(surface.radius), float(v_offset), text_value, projection_size
        )

        try:
            projected = text(
                text_value, projection_size, spine, lateral_face, font=font, kind=kind,
                halign="center", valign="center",
            )
        except ValueError as error:
            if "Null TopoDS_Shape" not in str(error):
                raise
            projection_size *= 0.94
            spine = self._frontal_arc(
                float(surface.radius), float(v_offset), text_value, projection_size
            )
            try:
                projected = text(
                    text_value, projection_size, spine, lateral_face,
                    font=font, kind=kind, halign="center", valign="center",
                )
            except ValueError as retry_error:
                raise RuntimeError(
                    f"Native cylindrical text projection failed for {text_value!r} "
                    f"at safe size {projection_size:.3f} mm."
                ) from retry_error
        if not projected.isValid():
            raise RuntimeError("Native projected text is invalid.")

        try:
            if mode == "emboss":
                outward_depth = min(depth, 1.50)
                anchor_depth = min(0.16, max(0.06, 0.10 * outward_depth))
                outward_tool = offset(projected, -outward_depth, cap=True)
                inward_anchor = offset(projected, anchor_depth, cap=True)
                tool = outward_tool.fuse(inward_anchor, tol=0.01).clean()
            else:
                tool = offset(projected, depth, cap=True)
        except Exception as error:
            raise RuntimeError(f"Native text {mode} offset failed.") from error
        if not tool.isValid():
            raise RuntimeError(f"Native text {mode} offset tool is invalid.")

        # Measure where the generated glyphs actually landed before moving them.
        # The Lab/DOBO front is -Y (angle -90°). Center the measured angular bounds
        # there, then apply the semantic circumferential offset as an additional
        # rigid rotation. Size, relief, line spacing and vertical placement are
        # untouched.
        measured_center = self._angular_bounds_center(projected, math.pi / 2.0)
        target_center = -math.pi / 2.0
        semantic_offset = float(u_offset) / float(surface.radius)
        angle_deg = math.degrees(target_center - measured_center + semantic_offset)

        projected = projected.rotate(
            (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), angle_deg
        )
        tool = tool.rotate(
            (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), angle_deg
        )
        return projected, tool

    @staticmethod
    def _single_primary_solid(shape: cq.Shape) -> cq.Shape:
        solids = tuple(shape.Solids())
        if not solids:
            raise RuntimeError("Native text Boolean produced no solids.")
        if len(solids) != 1:
            raise RuntimeError(f"Native text Boolean produced {len(solids)} disconnected solids.")
        primary = solids[0].clean()
        if not primary.isValid():
            raise RuntimeError("Native text primary body is invalid.")
        return primary
