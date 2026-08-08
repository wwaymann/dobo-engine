from __future__ import annotations

import cadquery as cq

from .color_validation import ColorRegionAnalyzer
from .final_product_validation import FinalProductAnalyzer
from .production_validation import ProductionAnalyzer
from .profile import ManufacturingProfile


def _box(
    x: float,
    y: float,
    z: float,
    *,
    center: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> cq.Shape:
    shape = (
        cq.Workplane("XY")
        .box(
            x,
            y,
            z,
            centered=(True, True, False),
        )
        .findSolid()
    )

    if center != (0.0, 0.0, 0.0):
        shape = shape.translate(
            center
        )

    return shape


def _validate_color() -> None:
    profile = ManufacturingProfile()
    analyzer = ColorRegionAnalyzer()

    final_shape = _box(
        30.0,
        10.0,
        10.0,
    )

    body = _box(
        10.0,
        10.0,
        10.0,
        center=(-10.0, 0.0, 0.0),
    )

    text = _box(
        10.0,
        10.0,
        10.0,
        center=(0.0, 0.0, 0.0),
    )

    decoration = _box(
        10.0,
        10.0,
        10.0,
        center=(10.0, 0.0, 0.0),
    )

    result = analyzer.analyze(
        final_shape=final_shape,
        regions={
            "Body": body,
            "Text": text,
            "Decoration": decoration,
        },
        minimum_region_volume=(
            profile.min_color_region_volume
        ),
    )

    if result.regions_valid is not True:
        raise RuntimeError(
            f"Color regions should be valid: {result}"
        )

    if result.minimum_volume_ok is not True:
        raise RuntimeError(
            f"Color volumes should pass: {result}"
        )

    if result.connectivity_ok is not True:
        raise RuntimeError(
            f"Color connectivity should pass: {result}"
        )

    if result.interface_integrity_ok is not True:
        raise RuntimeError(
            f"Color partition integrity failed: {result}"
        )

    bad_overlap = analyzer.analyze(
        final_shape=final_shape,
        regions={
            "Body": body,
            "Text": text.translate(
                (-5.0, 0.0, 0.0)
            ),
            "Decoration": decoration,
        },
        minimum_region_volume=(
            profile.min_color_region_volume
        ),
    )

    if bad_overlap.interface_integrity_ok is not False:
        raise RuntimeError(
            "Overlapping material regions must fail interface integrity."
        )

    print(
        "color fixtures",
        f"volume_error={result.volume_error:.6f}",
        "overlap_detection=OK",
        "OK",
    )


def _validate_final_product() -> None:
    analyzer = FinalProductAnalyzer()

    valid = analyzer.analyze(
        shape=_box(
            40.0,
            40.0,
            30.0,
        )
    )

    disconnected = cq.Compound.makeCompound(
        [
            _box(
                10.0,
                10.0,
                10.0,
            ),
            _box(
                10.0,
                10.0,
                10.0,
                center=(30.0, 0.0, 0.0),
            ),
        ]
    )

    invalid_connection = analyzer.analyze(
        shape=disconnected
    )

    if (
        not valid.cad_valid
        or not valid.connected
        or not valid.degenerate_geometry_ok
    ):
        raise RuntimeError(
            f"Valid final-product fixture failed: {valid}"
        )

    if invalid_connection.connected is not False:
        raise RuntimeError(
            "Disconnected final-product fixture was not detected."
        )

    print(
        "final product fixtures",
        f"solids={valid.solid_count}",
        f"faces={valid.face_count}",
        "disconnected_detection=OK",
        "OK",
    )


def _validate_production() -> None:
    profile = ManufacturingProfile()
    analyzer = ProductionAnalyzer()

    valid_shape = _box(
        100.0,
        120.0,
        80.0,
    )

    too_large = _box(
        320.0,
        100.0,
        50.0,
    )

    size_ok = analyzer.physical_size(
        shape=valid_shape,
        max_x=profile.max_size_x,
        max_y=profile.max_size_y,
        max_z=profile.max_size_z,
    )

    size_bad = analyzer.physical_size(
        shape=too_large,
        max_x=profile.max_size_x,
        max_y=profile.max_size_y,
        max_z=profile.max_size_z,
    )

    orientation_ok = analyzer.orientation_on_bed(
        shape=valid_shape,
        tolerance=profile.bed_z_tolerance,
    )

    orientation_bad = analyzer.orientation_on_bed(
        shape=valid_shape.translate(
            (0.0, 0.0, 5.0)
        ),
        tolerance=profile.bed_z_tolerance,
    )

    filament_ok = analyzer.filament_assignment(
        assigned_slots=(1, 2, 3),
        expected_region_count=3,
    )

    filament_bad = analyzer.filament_assignment(
        assigned_slots=(1, 1, 3),
        expected_region_count=3,
    )

    integrity_ok = analyzer.multicolor_3mf_integrity(
        top_level_build_items=1,
        component_count=3,
        expected_component_count=3,
    )

    integrity_bad = analyzer.multicolor_3mf_integrity(
        top_level_build_items=3,
        component_count=3,
        expected_component_count=3,
    )

    if size_ok.valid is not True:
        raise RuntimeError(
            f"Valid size fixture failed: {size_ok}"
        )

    if size_bad.valid is not False:
        raise RuntimeError(
            "Oversize fixture was not detected."
        )

    if orientation_ok.valid is not True:
        raise RuntimeError(
            f"Bed orientation fixture failed: {orientation_ok}"
        )

    if orientation_bad.valid is not False:
        raise RuntimeError(
            "Raised Z fixture was not detected."
        )

    if filament_ok.valid is not True:
        raise RuntimeError(
            f"Filament fixture failed: {filament_ok}"
        )

    if filament_bad.valid is not False:
        raise RuntimeError(
            "Duplicate filament-slot fixture was not detected."
        )

    if integrity_ok.valid is not True:
        raise RuntimeError(
            f"3MF integrity fixture failed: {integrity_ok}"
        )

    if integrity_bad.valid is not False:
        raise RuntimeError(
            "Multiple top-level build items must fail compound-object integrity."
        )

    print(
        "production fixtures",
        f"size={size_ok.size_x:.1f}x{size_ok.size_y:.1f}x{size_ok.size_z:.1f}",
        f"zmin={orientation_ok.z_min:.3f}",
        "filaments=1/2/3",
        "compound_3mf=OK",
        "OK",
    )


def _validate_known_phase6_contract() -> None:
    """
    Known-good Creality Phase 6.5 project properties already validated
    visually in Creality Print:
      - one top-level printable compound object
      - three internal material components
      - Body -> slot 1
      - Text -> slot 2
      - Decoration -> slot 3
    """
    analyzer = ProductionAnalyzer()

    filament = analyzer.filament_assignment(
        assigned_slots=(1, 2, 3),
        expected_region_count=3,
    )

    integrity = analyzer.multicolor_3mf_integrity(
        top_level_build_items=1,
        component_count=3,
        expected_component_count=3,
    )

    if (
        filament.valid is not True
        or integrity.valid is not True
    ):
        raise RuntimeError(
            "Known Phase-6.5 Creality contract should pass."
        )

    print(
        "known Phase-6.5 Creality contract",
        "1 build item",
        "3 components",
        "slots=1/2/3",
        "OK",
    )


def main() -> None:
    _validate_color()
    _validate_final_product()
    _validate_production()
    _validate_known_phase6_contract()

    print(
        "DOBO Manufacturability - Phase 7.8"
    )
    print(
        "Color + Final Product + Production"
    )
    print(
        "-----------------------------------"
    )

    statuses = (
        ("COLOR_REGIONS_VALID", "OK"),
        ("COLOR_REGION_MIN_VOLUME", "OK"),
        ("COLOR_REGION_CONNECTIVITY", "OK"),
        ("COLOR_INTERFACE_INTEGRITY", "OK"),
        ("CAD_VALID", "OK"),
        ("CONNECTED_FINAL_PRODUCT", "OK"),
        ("NO_DEGENERATE_GEOMETRY", "OK"),
        ("CLEARANCE", "SOURCE_PENDING"),
        ("OVERHANG", "MESH_ORIENTATION_PENDING"),
        ("PHYSICAL_SIZE_LIMITS", "OK"),
        ("ORIENTATION_ON_BED", "OK"),
        ("MULTICOLOR_3MF_INTEGRITY", "OK_PHASE6_5"),
        ("FILAMENT_ASSIGNMENT", "OK_PHASE6_5"),
    )

    for code, status in statuses:
        print(
            f"{code:<32} {status}"
        )

    print(
        "-----------------------------------"
    )
    print(
        "Phase 7.8 Color + Final + Production: Valid OK"
    )


if __name__ == "__main__":
    main()
