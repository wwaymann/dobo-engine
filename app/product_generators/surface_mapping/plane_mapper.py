from __future__ import annotations

from .contracts import SurfaceFrame, SurfaceSample


class PlaneSurfaceMapper:
    """Metric mapper for a bounded planar surface.

    ``u`` and ``v`` are expressed in millimetres along the supplied tangent
    directions.  The normal points out of the product surface.
    """

    def __init__(
        self,
        *,
        origin: tuple[float, float, float],
        tangent_u: tuple[float, float, float],
        tangent_v: tuple[float, float, float],
        normal: tuple[float, float, float],
        width: float,
        height: float,
    ) -> None:
        if width <= 0.0 or height <= 0.0:
            raise ValueError("Planar surface width and height must be positive.")
        self.origin = tuple(float(value) for value in origin)
        self.tangent_u = tuple(float(value) for value in tangent_u)
        self.tangent_v = tuple(float(value) for value in tangent_v)
        self.normal = tuple(float(value) for value in normal)
        self.width = float(width)
        self.height = float(height)

    def sample(self, u: float, v: float) -> SurfaceSample:
        u = float(u)
        v = float(v)
        point = tuple(
            self.origin[index]
            + u * self.tangent_u[index]
            + v * self.tangent_v[index]
            for index in range(3)
        )
        frame = SurfaceFrame(
            origin=point,
            tangent_u=self.tangent_u,
            tangent_v=self.tangent_v,
            normal=self.normal,
        )
        result = SurfaceSample(u=u, v=v, point=point, frame=frame)
        result.validate()
        return result
