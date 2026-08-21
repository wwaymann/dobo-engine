from __future__ import annotations

from pathlib import Path

from .vessel_engine import OrganicVesselEngine
from .vessel_specification import OrganicVesselParser


SPEC_PATH = Path(__file__).with_name("phase_2c_localized_mesh_quality.json")


def main() -> None:
    print()
    print("DOBO Organic Shape Engine - Phase 2C")
    print("SDF vessel -> localized Taubin refinement -> protected features -> STL")
    print("-----------------------------------")
    specification = OrganicVesselParser().parse_file(SPEC_PATH)
    result = OrganicVesselEngine().generate(specification)
    quality = result.mesh_quality
    if quality is None:
        raise RuntimeError("Phase 2C did not execute mesh refinement.")

    print("components", result.component_count, "OK")
    print("watertight", result.watertight, "OK")
    print("winding consistent", result.winding_consistent, "OK")
    print("input faces", quality.input_face_count)
    print("refined faces", quality.refined_face_count, "OK")
    print("active rim vertices", quality.active_vertex_count, "OK")
    print("protected functional vertices", quality.protected_vertex_count, "OK")
    print("iterations applied", quality.iterations_applied, "OK")
    print("roughness before mm", round(quality.roughness_before_mm, 6))
    print("roughness after mm", round(quality.roughness_after_mm, 6))
    print(
        "roughness improvement percent",
        round(quality.roughness_improvement_percent, 3),
        "OK",
    )
    print("volume drift percent", round(quality.volume_drift_percent, 5), "OK")
    print(
        "total volume drift from input percent",
        round(quality.total_volume_drift_percent, 5),
        "OK",
    )
    print("maximum displacement mm", round(quality.maximum_displacement_mm, 5), "OK")
    print(
        "protected displacement mm",
        round(quality.protected_displacement_mm, 9),
        "OK",
    )
    print("mean SDF surface error mm", round(quality.mean_surface_error_mm, 7))
    print(
        "maximum SDF surface error mm",
        round(quality.maximum_surface_error_mm, 7),
        "OK",
    )
    print(
        "maximum base plane error mm",
        round(quality.maximum_base_plane_error_mm, 7),
        "OK",
    )
    print(
        "maximum base perimeter error mm",
        round(quality.maximum_base_perimeter_error_mm, 7),
        "OK",
    )
    print(
        "maximum base transition error mm",
        round(quality.maximum_base_transition_error_mm, 7),
        "OK",
    )
    print(
        "maximum drain radius error mm",
        round(quality.maximum_drain_radius_error_mm, 7),
        "OK",
    )
    print("flat base vertices", result.flat_base_vertex_count, "OK")
    for name, valid in result.semantic_checks.items():
        print("semantic", name, valid, "OK" if valid else "ERROR")
    print("vertices", result.vertex_count)
    print("faces", result.face_count)
    print("volume mm3", round(result.volume_mm3, 3))
    print("stage timings")
    for name, seconds in result.stage_seconds.items():
        print(f"  {name} {seconds:.3f}s")
    print(f"generation seconds {result.generation_seconds:.3f}")
    print(f"generation target {result.max_generation_seconds:.1f} seconds")
    print("STL", result.stl_path)
    print("-----------------------------------")
    if result.generation_seconds > result.max_generation_seconds:
        raise RuntimeError("Organic vessel generation exceeded the Phase 2C budget.")
    print("generation budget OK")
    print("DOBO Organic Shape Engine Phase 2C: Valid OK")


if __name__ == "__main__":
    main()
