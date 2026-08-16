from __future__ import annotations

from dataclasses import dataclass

import cadquery as cq
import trimesh


@dataclass(frozen=True, slots=True)
class MeshBRepConversionResult:
    shape: cq.Shape
    input_vertices: int
    input_faces: int
    brep_faces: int
    solids: int

    def validate(self) -> None:
        if not isinstance(self.shape, cq.Shape):
            raise TypeError("Converted geometry must be a CadQuery Shape.")
        if not self.shape.isValid():
            raise RuntimeError("Converted BRep is invalid.")
        if self.input_vertices <= 0 or self.input_faces <= 0:
            raise RuntimeError("Input mesh is empty.")
        if self.brep_faces <= 0:
            raise RuntimeError("Converted BRep has no faces.")
        if self.solids != 1:
            raise RuntimeError(
                f"Converted BRep must contain one solid, got {self.solids}."
            )


def trimesh_to_brep(mesh: trimesh.Trimesh) -> MeshBRepConversionResult:
    """Convert one watertight Trimesh body to a faceted CadQuery BRep.

    This is intentionally a representation conversion only. It does not
    regenerate, smooth, reinterpret, or redesign the source morphology.
    Each source triangle becomes one BRep face; the closed face set is sewn
    into one shell and promoted to one solid.
    """

    if not isinstance(mesh, trimesh.Trimesh):
        raise TypeError("mesh must be trimesh.Trimesh.")
    if len(mesh.vertices) == 0 or len(mesh.faces) == 0:
        raise ValueError("mesh cannot be empty.")
    if not mesh.is_watertight:
        raise ValueError("mesh must be watertight before BRep conversion.")

    faces: list[cq.Face] = []
    vertices = mesh.vertices
    for indices in mesh.faces:
        points = [cq.Vector(*map(float, vertices[int(index)])) for index in indices]
        wire = cq.Wire.makePolygon(points, close=True)
        face = cq.Face.makeFromWires(wire)
        if not face.isValid():
            raise RuntimeError("Triangle to BRep face conversion produced invalid geometry.")
        faces.append(face)

    shell = cq.Shell.makeShell(faces)
    if not shell.isValid():
        raise RuntimeError("Converted triangle faces did not form a valid shell.")

    solid = cq.Solid.makeSolid(shell).clean()
    result = MeshBRepConversionResult(
        shape=solid,
        input_vertices=int(len(mesh.vertices)),
        input_faces=int(len(mesh.faces)),
        brep_faces=int(len(solid.Faces())),
        solids=int(len(solid.Solids())),
    )
    result.validate()
    return result
