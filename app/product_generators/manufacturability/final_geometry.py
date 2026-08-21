from __future__ import annotations

from dataclasses import dataclass
import math

import cadquery as cq


@dataclass(frozen=True, slots=True)
class ClearanceResult:
    available: bool
    minimum_clearance: float | None
    valid: bool | None


@dataclass(frozen=True, slots=True)
class OverhangResult:
    available: bool
    maximum_overhang_angle: float | None
    valid: bool | None
    sampled_triangles: int


class FinalGeometryManufacturingAnalyzer:
    """Manufacturing checks derived directly from final printable geometry.

    CLEARANCE is evaluated between disconnected final solids. A single
    connected solid has no inter-solid clearance constraint and therefore
    satisfies this rule by construction.

    OVERHANG is evaluated from the tessellated final exterior surface in the
    same +Z build orientation used by the production contract. Downward-facing
    triangles at the bed plane are ignored because they are supported by the
    print bed. For every other downward-facing triangle, the overhang angle is
    measured from a vertical wall: 0 degrees is vertical and 90 degrees is a
    horizontal unsupported underside.
    """

    def clearance(
        self,
        *,
        shape: cq.Shape | None,
        minimum_required: float,
    ) -> ClearanceResult:
        if shape is None:
            return ClearanceResult(False, None, None)

        try:
            solids = tuple(shape.Solids())
        except Exception:
            return ClearanceResult(True, 0.0, False)

        if not solids:
            return ClearanceResult(True, 0.0, False)

        if len(solids) == 1:
            return ClearanceResult(True, math.inf, True)

        distances: list[float] = []
        for index, first in enumerate(solids):
            for second in solids[index + 1 :]:
                try:
                    distances.append(float(first.distance(second)))
                except Exception:
                    return ClearanceResult(True, 0.0, False)

        if not distances:
            return ClearanceResult(True, math.inf, True)

        minimum = min(distances)
        return ClearanceResult(
            available=True,
            minimum_clearance=minimum,
            valid=minimum >= float(minimum_required),
        )

    def overhang(
        self,
        *,
        shape: cq.Shape | None,
        maximum_allowed_angle: float,
        bed_tolerance: float,
        tessellation_tolerance: float = 0.20,
    ) -> OverhangResult:
        if shape is None:
            return OverhangResult(False, None, None, 0)

        try:
            vertices, triangles = shape.tessellate(float(tessellation_tolerance))
            z_min = float(shape.BoundingBox().zmin)
        except Exception:
            return OverhangResult(True, 90.0, False, 0)

        maximum = 0.0
        sampled = 0
        bed_limit = z_min + float(bed_tolerance)

        for triangle in triangles:
            try:
                a = vertices[triangle[0]]
                b = vertices[triangle[1]]
                c = vertices[triangle[2]]
                ab = (float(b.x - a.x), float(b.y - a.y), float(b.z - a.z))
                ac = (float(c.x - a.x), float(c.y - a.y), float(c.z - a.z))
                nx = ab[1] * ac[2] - ab[2] * ac[1]
                ny = ab[2] * ac[0] - ab[0] * ac[2]
                nz = ab[0] * ac[1] - ab[1] * ac[0]
                norm = math.sqrt(nx * nx + ny * ny + nz * nz)
                if norm <= 1.0e-12:
                    continue
                nz /= norm
                centroid_z = (float(a.z) + float(b.z) + float(c.z)) / 3.0
            except Exception:
                continue

            # Upward/vertical triangles are self-supporting for this rule.
            if nz >= -1.0e-9:
                continue
            # The bottom skin resting on the bed is externally supported.
            if centroid_z <= bed_limit:
                continue

            sampled += 1
            angle = math.degrees(math.asin(min(1.0, max(0.0, -nz))))
            maximum = max(maximum, angle)

        return OverhangResult(
            available=True,
            maximum_overhang_angle=maximum,
            valid=maximum <= float(maximum_allowed_angle),
            sampled_triangles=sampled,
        )
