from __future__ import annotations

from dataclasses import dataclass

import cadquery as cq


@dataclass(frozen=True, slots=True)
class FinalProductValidationResult:
    cad_valid: bool
    connected: bool
    degenerate_geometry_ok: bool
    clearance_available: bool
    overhang_available: bool
    solid_count: int
    face_count: int
    volume: float


class FinalProductAnalyzer:
    """
    Core final-product checks that can be performed directly on the B-Rep.

    Implemented:
      CAD_VALID
      CONNECTED_FINAL_PRODUCT
      NO_DEGENERATE_GEOMETRY

    Source-dependent / intentionally not guessed here:
      CLEARANCE
      OVERHANG

    Clearance requires explicit moving/assembly relationships or intended
    separation semantics. Overhang is orientation + process dependent and is
    better evaluated from meshed/print-oriented geometry.
    """

    def analyze(
        self,
        *,
        shape: cq.Shape,
        minimum_face_area: float = 1.0e-6,
        minimum_edge_length: float = 1.0e-6,
    ) -> FinalProductValidationResult:
        cad_valid = bool(shape.isValid())
        solids = tuple(shape.Solids())
        faces = tuple(shape.Faces())
        edges = tuple(shape.Edges())

        connected = len(solids) == 1

        volume = float(shape.Volume())

        face_ok = True
        for face in faces:
            try:
                if float(face.Area()) <= minimum_face_area:
                    face_ok = False
                    break
            except Exception:
                face_ok = False
                break

        edge_ok = True
        for edge in edges:
            try:
                if float(edge.Length()) <= minimum_edge_length:
                    edge_ok = False
                    break
            except Exception:
                edge_ok = False
                break

        degenerate_ok = bool(
            cad_valid
            and volume > 0.0
            and face_ok
            and edge_ok
        )

        return FinalProductValidationResult(
            cad_valid=cad_valid,
            connected=connected,
            degenerate_geometry_ok=degenerate_ok,
            clearance_available=False,
            overhang_available=False,
            solid_count=len(solids),
            face_count=len(faces),
            volume=volume,
        )
