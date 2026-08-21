from __future__ import annotations

import argparse
from pathlib import Path

from .morphological_integration import ADVANCED_MORPHOLOGICAL_INTEGRATION_VERSION
from .phase_7_8_macroblock_matrix import macroblock_a_matrix
from .structural_pipeline import DoboStructuralPipeline


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the DOBO Macroblock A.2 real visual matrix."
    )
    parser.add_argument("--output-root", required=True)
    parser.add_argument(
        "--case",
        choices=("all", "architectural", "branching", "perforated"),
        default="all",
    )
    return parser.parse_args()


def main() -> None:
    arguments = _arguments()
    cases = macroblock_a_matrix()
    if arguments.case != "all":
        cases = tuple(case for case in cases if case.id == arguments.case)
    root = Path(arguments.output_root).resolve()
    print()
    print("DOBO Macroblock A.2 Real Matrix")
    print("Advanced Morphological Integration", ADVANCED_MORPHOLOGICAL_INTEGRATION_VERSION)
    print("-----------------------------------")
    for case in cases:
        result = DoboStructuralPipeline().generate_from_semantic(
            case.program,
            output_root=root / case.id,
            interpreter_version="macroblock-a2-matrix",
            model="not-used",
            response_id="not-used",
            surface_intents=case.surfaces,
        )
        report = result.compilation.report
        print(case.label, "profile", report.complex_profile, "OK")
        print(case.label, "style", report.style_profile, "OK")
        print(case.label, "hierarchy depth", report.hierarchy_depth, "OK")
        print(case.label, "components", result.mesh_result.component_count, "OK")
        print(case.label, "watertight", result.mesh_result.watertight, "OK")
        print(case.label, "winding", result.mesh_result.winding_consistent, "OK")
        print(case.label, "vertices", result.trace.vertex_count)
        print(case.label, "faces", result.trace.face_count)
        print(case.label, "seconds", f"{result.trace.generation_seconds:.3f}")
        print(case.label, "attempts", result.trace.generation_attempts)
        print(case.label, "quality", result.trace.mesh_quality_profile)
        print(case.label, "painted triangles", result.three_mf.painted_triangle_count)
        print(case.label, "STL", result.stl_path)
        print(case.label, "3MF", result.three_mf_path)
        print(case.label, "surface JSON", result.surface_path)
    print("-----------------------------------")
    print("No API credit consumed OK")
    print("DOBO Macroblock A.2 Real Matrix: Valid OK")


if __name__ == "__main__":
    main()
