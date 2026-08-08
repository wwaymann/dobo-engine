from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
import json

import cadquery as cq

from .local_thickness import (
    LocalThicknessResult,
    ThicknessSample,
)


@dataclass(frozen=True, slots=True)
class ThinSpotDiagnosticResult:
    csv_path: str
    json_path: str
    marker_step_path: str
    exported_spots: int


class ThinSpotDiagnostics:
    """
    Export local-thickness samples for visual inspection.

    The marker STEP contains small spheres centered at the thinnest sampled
    points. It does not modify the product and is only a diagnostic artifact.
    """

    def export(
        self,
        *,
        result: LocalThicknessResult,
        output_directory: str | Path,
        limit: int = 20,
        marker_radius: float = 1.25,
    ) -> ThinSpotDiagnosticResult:
        if limit < 1:
            raise ValueError(
                "Diagnostic limit must be >= 1."
            )

        if marker_radius <= 0.0:
            raise ValueError(
                "marker_radius must be positive."
            )

        if not result.samples:
            raise RuntimeError(
                "No local-thickness samples available."
            )

        output_directory = Path(
            output_directory
        )

        output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        selected = tuple(
            sorted(
                result.samples,
                key=lambda item: item.thickness,
            )[:limit]
        )

        csv_path = (
            output_directory
            / "thin_spots.csv"
        )

        with csv_path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as stream:
            writer = csv.writer(
                stream
            )

            writer.writerow(
                (
                    "rank",
                    "face_index",
                    "x_mm",
                    "y_mm",
                    "z_mm",
                    "thickness_mm",
                )
            )

            for rank, sample in enumerate(
                selected,
                start=1,
            ):
                writer.writerow(
                    (
                        rank,
                        sample.face_index,
                        f"{sample.point.x:.6f}",
                        f"{sample.point.y:.6f}",
                        f"{sample.point.z:.6f}",
                        f"{sample.thickness:.6f}",
                    )
                )

        json_path = (
            output_directory
            / "thin_spots.json"
        )

        payload = [
            {
                "rank": rank,
                "face_index": (
                    sample.face_index
                ),
                "point_mm": {
                    "x": sample.point.x,
                    "y": sample.point.y,
                    "z": sample.point.z,
                },
                "thickness_mm": (
                    sample.thickness
                ),
            }
            for rank, sample in enumerate(
                selected,
                start=1,
            )
        ]

        json_path.write_text(
            json.dumps(
                payload,
                indent=2,
            ),
            encoding="utf-8",
        )

        marker_step_path = (
            output_directory
            / "thin_spot_markers.step"
        )

        markers: list[cq.Shape] = []

        for sample in selected:
            markers.append(
                cq.Solid.makeSphere(
                    marker_radius,
                    sample.point,
                )
            )

        compound = cq.Compound.makeCompound(
            markers
        )

        cq.exporters.export(
            compound,
            str(
                marker_step_path
            ),
        )

        return ThinSpotDiagnosticResult(
            csv_path=str(
                csv_path
            ),
            json_path=str(
                json_path
            ),
            marker_step_path=str(
                marker_step_path
            ),
            exported_spots=len(
                selected
            ),
        )
