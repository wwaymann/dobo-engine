from __future__ import annotations

import cadquery as cq

from product_generators.surface_mapping.plane_mapper import PlaneSurfaceMapper


class NativePlanarTextBuilder:
    """Reusable CadQuery text Boolean for any bounded planar product surface."""

    @staticmethod
    def _safe_size(surface: PlaneSurfaceMapper, text_value: str, requested: float) -> float:
        glyph_count = max(1, len(text_value.strip()))
        estimated_width_per_size = max(1.0, 0.68 * glyph_count)
        usable_width = 0.90 * surface.width
        return min(float(requested), usable_width / estimated_width_per_size)

    @staticmethod
    def _plane(
        surface: PlaneSurfaceMapper,
        *,
        u_offset: float,
        v_offset: float,
        normal_offset: float,
    ) -> cq.Plane:
        sample = surface.sample(float(u_offset), float(v_offset))
        origin = tuple(
            sample.point[index] + normal_offset * surface.normal[index]
            for index in range(3)
        )
        return cq.Plane(
            origin=cq.Vector(*origin),
            xDir=cq.Vector(*surface.tangent_u),
            normal=cq.Vector(*surface.normal),
        )

    def apply(
        self,
        *,
        base_shape: cq.Shape,
        surface: PlaneSurfaceMapper,
        text_value: str,
        size: float,
        depth: float,
        mode: str,
        font: str = "Arial",
        kind: str = "regular",
        u_offset: float = 0.0,
        v_offset: float = 0.0,
    ) -> cq.Shape:
        if not isinstance(base_shape, cq.Shape) or not base_shape.isValid():
            raise ValueError("base_shape must be a valid CadQuery Shape.")
        if not text_value or not text_value.strip():
            raise ValueError("text_value cannot be empty.")
        if mode not in {"emboss", "deboss"}:
            raise ValueError("mode must be emboss or deboss.")
        size = self._safe_size(surface, text_value, float(size))
        depth = float(depth)
        if size <= 0.0 or depth <= 0.0:
            raise ValueError("size and depth must be positive.")

        before = float(base_shape.Volume())
        if mode == "emboss":
            outward = min(depth, 1.50)
            anchor = min(0.16, max(0.06, 0.10 * outward))
            # Start just inside the wall and extrude along the outward normal so
            # every glyph is physically anchored to the vessel body.
            plane = self._plane(
                surface,
                u_offset=u_offset,
                v_offset=v_offset,
                normal_offset=-anchor,
            )
            tool = cq.Workplane(plane).text(
                text_value,
                size,
                outward + anchor,
                font=font,
                kind=kind,
                halign="center",
                valign="center",
                combine=False,
            ).val()
            current = base_shape
            solids = tuple(tool.Solids())
            if not solids:
                raise RuntimeError("Planar emboss text produced no glyph solids.")
            for index, glyph in enumerate(solids):
                fused = current.fuse(glyph, tol=0.01).clean()
                joined = tuple(fused.Solids())
                if len(joined) != 1:
                    raise RuntimeError(
                        f"Planar emboss glyph {index} did not join the vessel body."
                    )
                current = joined[0]
            final = current.clean()
        else:
            epsilon = 0.05
            # Begin just outside the face and extrude opposite the outward normal
            # so the cutter enters the wall without floating tolerances.
            plane = self._plane(
                surface,
                u_offset=u_offset,
                v_offset=v_offset,
                normal_offset=epsilon,
            )
            tool = cq.Workplane(plane).text(
                text_value,
                size,
                -(depth + epsilon),
                font=font,
                kind=kind,
                halign="center",
                valign="center",
                combine=False,
            ).val()
            final = base_shape.cut(tool, tol=0.01).clean()

        if not final.isValid() or len(tuple(final.Solids())) != 1:
            raise RuntimeError("Native planar text must leave one valid CAD solid.")
        after = float(final.Volume())
        delta = after - before if mode == "emboss" else before - after
        if delta <= 1e-8:
            raise RuntimeError(f"Native planar text {mode} produced no volume change.")
        return final
