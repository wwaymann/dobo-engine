from __future__ import annotations

import cadquery as cq


class SurfaceFaceSelector:
    """
    Finds a useful external decoration face from an existing solid.

    Preference:
    1. explicitly requested geometry type
    2. non-planar faces
    3. largest available face

    This is product-side selection logic, not a new geometry layer.
    """

    def largest_external(
        self,
        shape: cq.Shape,
        *,
        geom_type: str | None = None,
    ) -> cq.Face:
        if not isinstance(shape, cq.Shape):
            raise TypeError("shape must be a CadQuery Shape.")

        if not shape.isValid():
            raise ValueError("shape must be valid.")

        faces = tuple(shape.Faces())

        if not faces:
            raise RuntimeError("Shape contains no faces.")

        candidates = faces

        if geom_type:
            filtered = tuple(
                face
                for face in faces
                if face.geomType().upper() == geom_type.upper()
            )
            if filtered:
                candidates = filtered
        else:
            curved = tuple(
                face
                for face in faces
                if face.geomType().upper() != "PLANE"
            )
            if curved:
                candidates = curved

        result = max(
            candidates,
            key=lambda face: float(face.Area()),
        )

        if not result.isValid():
            raise RuntimeError("Selected face is invalid.")

        return result
