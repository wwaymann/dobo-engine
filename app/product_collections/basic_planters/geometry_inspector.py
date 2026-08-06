from __future__ import annotations
import cadquery as cq

class BasicPlanterGeometryInspector:
    @staticmethod
    def top_face_index(solid) -> int:
        solid.validate()
        geometry = solid.geometry
        if not isinstance(geometry, cq.Shape):
            raise TypeError('Expected CadQuery Shape geometry.')
        faces = list(geometry.Faces())
        if not faces:
            raise RuntimeError('Geometry contains no faces.')
        return max(range(len(faces)), key=lambda i: float(faces[i].Center().z))

    @staticmethod
    def bottom_face_index(solid) -> int:
        solid.validate()
        geometry = solid.geometry
        if not isinstance(geometry, cq.Shape):
            raise TypeError('Expected CadQuery Shape geometry.')
        faces = list(geometry.Faces())
        if not faces:
            raise RuntimeError('Geometry contains no faces.')
        return min(range(len(faces)), key=lambda i: float(faces[i].Center().z))
