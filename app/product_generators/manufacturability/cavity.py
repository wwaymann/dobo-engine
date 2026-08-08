from __future__ import annotations

from dataclasses import dataclass

import cadquery as cq


@dataclass(frozen=True, slots=True)
class InternalVolumeResult:
    available: bool
    volume: float | None
    valid: bool | None


@dataclass(frozen=True, slots=True)
class DrainageResult:
    available: bool
    path_count: int | None
    all_connected: bool | None
    connected_indices: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class ClosedCavityResult:
    available: bool
    undeclared_count: int | None
    declared_count: int | None = None


class InternalVolumeAnalyzer:
    def analyze(
        self,
        cavity: cq.Shape | None,
    ) -> InternalVolumeResult:
        if cavity is None:
            return InternalVolumeResult(
                available=False,
                volume=None,
                valid=None,
            )

        valid = bool(
            cavity.isValid()
            and len(cavity.Solids()) >= 1
            and float(cavity.Volume()) > 0.0
        )

        return InternalVolumeResult(
            available=True,
            volume=float(cavity.Volume()),
            valid=valid,
        )


class DrainageAnalyzer:
    """
    Validate explicit drainage tools.

    A drainage tool is considered connected when:
      1. it intersects the declared internal cavity,
      2. it intersects the structural body material,
      3. it extends outside the structural body's bounding box at the lower
         side OR reaches the body's minimum Z plane.

    This is semantic validation of an explicitly declared drain path, not an
    attempt to discover drains from arbitrary B-Rep topology.
    """

    def analyze(
        self,
        *,
        structural_body: cq.Shape,
        internal_cavity: cq.Shape | None,
        drainage_tools: tuple[cq.Shape, ...],
        z_tolerance: float = 0.05,
    ) -> DrainageResult:
        if (
            internal_cavity is None
            or not drainage_tools
        ):
            return DrainageResult(
                available=False,
                path_count=None,
                all_connected=None,
                connected_indices=(),
            )

        body_box = structural_body.BoundingBox()
        connected: list[int] = []

        for index, tool in enumerate(
            drainage_tools,
            start=1,
        ):
            try:
                cavity_overlap = float(
                    tool.intersect(
                        internal_cavity
                    ).Volume()
                )

                body_overlap = float(
                    tool.intersect(
                        structural_body
                    ).Volume()
                )

                tool_box = tool.BoundingBox()

                reaches_exterior = (
                    tool_box.zmin
                    <= body_box.zmin
                    + z_tolerance
                )

                if (
                    cavity_overlap > 0.0
                    and body_overlap > 0.0
                    and reaches_exterior
                ):
                    connected.append(index)

            except Exception:
                continue

        return DrainageResult(
            available=True,
            path_count=len(connected),
            all_connected=(
                len(connected)
                == len(drainage_tools)
            ),
            connected_indices=tuple(
                connected
            ),
        )


class ClosedCavityAnalyzer:
    """
    Validate explicitly declared sealed-cavity semantics.

    Discovery of arbitrary undeclared voids from an unbounded complement is a
    separate topology problem and is deliberately not guessed here.

    If semantic cavity information exists, this analyzer can account for
    declared sealed cavities and report zero undeclared cavities at this
    semantic layer.
    """

    def analyze(
        self,
        *,
        internal_cavity: cq.Shape | None,
        declared_closed_cavities: tuple[cq.Shape, ...] = (),
    ) -> ClosedCavityResult:
        if internal_cavity is None:
            return ClosedCavityResult(
                available=False,
                undeclared_count=None,
                declared_count=None,
            )

        return ClosedCavityResult(
            available=True,
            undeclared_count=0,
            declared_count=len(
                declared_closed_cavities
            ),
        )
