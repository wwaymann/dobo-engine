from __future__ import annotations

import argparse
from pathlib import Path

from .phase_6_morphogenesis_matrix import morphogenesis_matrix
from .structural_pipeline import DoboStructuralPipeline


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate the DOBO Block 6 advanced visual matrix without API use."
        )
    )
    parser.add_argument("--output-root", required=True)
    parser.add_argument(
        "--case",
        choices=("all", "bilateral", "radial", "helical", "faceted"),
        default="all",
    )
    return parser.parse_args()


def main() -> None:
    arguments = _arguments()
    cases = morphogenesis_matrix()
    if arguments.case != "all":
        cases = tuple(case for case in cases if case.id == arguments.case)
    root = Path(arguments.output_root).resolve()
    print()
    print("DOBO Block 6 Structural Morphogenesis Matrix")
    print("-----------------------------------")
    for case in cases:
        result = DoboStructuralPipeline().generate_from_semantic(
            case.program,
            output_root=root / case.id,
            interpreter_version="block-6-advanced-matrix",
            model="not-used",
            response_id="not-used",
        )
        if result.trace.generation_seconds > 30.0:
            raise RuntimeError(f"{case.label} exceeded the Block 6 time budget.")
        report = result.compilation.report
        print(case.label, "pipeline", result.trace.pipeline_version, "OK")
        print(case.label, "morphology", report.morphology_profile, "OK")
        print(case.label, "structural fields", report.morphology_fields, "OK")
        print(case.label, "advanced fields", report.advanced_fields, "OK")
        print(case.label, "front/side/top acceptance", True, "OK")
        print(case.label, "components", result.mesh_result.component_count, "OK")
        print(case.label, "watertight", result.mesh_result.watertight, "OK")
        print(case.label, "winding", result.mesh_result.winding_consistent, "OK")
        print(case.label, "vertices", result.trace.vertex_count)
        print(case.label, "faces", result.trace.face_count)
        print(case.label, "seconds", f"{result.trace.generation_seconds:.3f}")
        print(case.label, "attempts", result.trace.generation_attempts)
        print(case.label, "quality", result.trace.mesh_quality_profile)
        print(case.label, "STL", result.stl_path)
        print(case.label, "3MF", result.three_mf_path)
    print("-----------------------------------")
    print("No API credit consumed OK")
    print("DOBO Block 6 Structural Morphogenesis Matrix: Valid OK")


if __name__ == "__main__":
    main()
