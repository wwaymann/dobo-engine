from __future__ import annotations

from dataclasses import dataclass

import cadquery as cq


@dataclass(frozen=True, slots=True)
class UVPlacement:
    u_offset: float
    v_offset: float
    scale_u: float
    scale_v: float

    def validate(self) -> None:
        if self.scale_u <= 0.0:
            raise ValueError("scale_u must be positive.")
        if self.scale_v <= 0.0:
            raise ValueError("scale_v must be positive.")


class UVPlacementResolver:
    """
    Places planar geometry inside the native UV domain of a target face.

    Width/height are expressed as fractions of the available UV domain.
    This deliberately avoids introducing a new surface abstraction.
    """

    def centered(
        self,
        *,
        target_face: cq.Face,
        planar_shape: cq.Shape,
        width_fraction: float = 0.28,
        height_fraction: float = 0.22,
        u_center: float = 0.5,
        v_center: float = 0.5,
    ) -> UVPlacement:
        if not isinstance(target_face, cq.Face):
            raise TypeError("target_face must be a CadQuery Face.")

        if not target_face.isValid():
            raise ValueError("target_face must be valid.")

        if not isinstance(planar_shape, cq.Shape):
            raise TypeError("planar_shape must be a CadQuery Shape.")

        if not planar_shape.isValid():
            raise ValueError("planar_shape must be valid.")

        for name, value in (
            ("width_fraction", width_fraction),
            ("height_fraction", height_fraction),
            ("u_center", u_center),
            ("v_center", v_center),
        ):
            value = float(value)
            if name.endswith("_fraction"):
                if value <= 0.0 or value >= 1.0:
                    raise ValueError(f"{name} must be between 0 and 1.")
            else:
                if value <= 0.0 or value >= 1.0:
                    raise ValueError(f"{name} must be between 0 and 1.")

        u_min, u_max, v_min, v_max = target_face.uvBounds()

        u_span = float(u_max - u_min)
        v_span = float(v_max - v_min)

        if u_span <= 0.0 or v_span <= 0.0:
            raise RuntimeError("Target face has invalid UV bounds.")

        box = planar_shape.BoundingBox()

        source_w = float(box.xmax - box.xmin)
        source_h = float(box.ymax - box.ymin)

        if source_w <= 0.0 or source_h <= 0.0:
            raise RuntimeError("Planar geometry has invalid bounds.")

        target_w = u_span * float(width_fraction)
        target_h = v_span * float(height_fraction)

        scale_u = target_w / source_w
        scale_v = target_h / source_h

        u_mid = u_min + u_span * float(u_center)
        v_mid = v_min + v_span * float(v_center)

        source_mid_x = (float(box.xmin) + float(box.xmax)) / 2.0
        source_mid_y = (float(box.ymin) + float(box.ymax)) / 2.0

        u_offset = u_mid - source_mid_x * scale_u
        v_offset = v_mid - source_mid_y * scale_v

        result = UVPlacement(
            u_offset=u_offset,
            v_offset=v_offset,
            scale_u=scale_u,
            scale_v=scale_v,
        )
        result.validate()
        return result
