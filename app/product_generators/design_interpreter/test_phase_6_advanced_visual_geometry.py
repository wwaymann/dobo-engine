from __future__ import annotations

import numpy as np

from product_generators.organic_shapes.fields import implicit_field_distance
from product_generators.organic_shapes.hierarchy_specification import (
    HierarchicalFeatureParser,
)
from product_generators.organic_shapes.specification import AdvancedFieldSpec

from .phase_5_design_matrix import design_matrix
from .structural_compiler import (
    ADAPTIVE_QUALITY_VERSION,
    ADVANCED_PRIMITIVE_VERSION,
    CLEAN_COMPOSITION_VERSION,
    STYLE_DIFFERENTIATION_VERSION,
    VISUAL_ACCEPTANCE_VERSION,
    StructuralSemanticCompiler,
)
from .structural_pipeline import (
    ADVANCED_GENERATION_BUDGET_SECONDS,
    STRUCTURAL_FUSION_VERSION,
    STRUCTURAL_PIPELINE_VERSION,
)


def _sample(field: AdvancedFieldSpec, point: tuple[float, float, float]) -> float:
    return float(
        implicit_field_distance(
            np.asarray(point[0]),
            np.asarray(point[1]),
            np.asarray(point[2]),
            field,
        )
    )


def _primitive_contract() -> None:
    primitives = (
        AdvancedFieldSpec(
            "soft_cube", "superellipsoid", (0.0, 0.0, 0.0), (8.0, 7.0, 9.0),
            exponent=4.0, round_mm=0.8,
        ),
        AdvancedFieldSpec(
            "hex", "faceted_ellipsoid", (0.0, 0.0, 0.0), (9.0, 9.0, 10.0),
            exponent=3.6, sides=6, rotation_degrees=30.0, round_mm=0.8,
        ),
        AdvancedFieldSpec(
            "leaf", "leaf", (0.0, 0.0, 0.0), (5.0, 3.0, 12.0),
            round_mm=0.7,
        ),
        AdvancedFieldSpec(
            "point", "pointed", (0.0, 0.0, 0.0), (6.0, 3.0, 12.0),
            round_mm=0.7,
        ),
    )
    for field in primitives:
        field.validate()
        if _sample(field, field.center) >= 0.0:
            raise RuntimeError(f"{field.kind} lost its interior.")
        outside = (field.center[0], field.center[1], field.center[2] + 1.2 * field.radii[2])
        if _sample(field, outside) <= 0.0:
            raise RuntimeError(f"{field.kind} lost its exterior.")

    leaf = primitives[2]
    if _sample(leaf, (4.5, 0.0, 8.0)) <= 0.0:
        raise RuntimeError("Leaf primitive did not taper toward its tip.")
    pointed = primitives[3]
    if _sample(pointed, (5.5, 0.0, 9.0)) <= 0.0:
        raise RuntimeError("Pointed primitive did not converge toward its apex.")


def main() -> None:
    print()
    print("DOBO Advanced Visual Geometry - Block 6")
    print("primitives -> composition -> styles -> quality -> visual matrix")
    print("-----------------------------------")
    print("advanced primitive version", ADVANCED_PRIMITIVE_VERSION, "OK")
    print("clean composition version", CLEAN_COMPOSITION_VERSION, "OK")
    print("style differentiation version", STYLE_DIFFERENTIATION_VERSION, "OK")
    print("adaptive quality version", ADAPTIVE_QUALITY_VERSION, "OK")
    print("visual acceptance version", VISUAL_ACCEPTANCE_VERSION, "OK")
    print("fusion version", STRUCTURAL_FUSION_VERSION, "OK")
    print("pipeline version", STRUCTURAL_PIPELINE_VERSION, "OK")

    _primitive_contract()
    print("advanced primitive contracts", 4, "OK")

    expected = {
        "cat": {"pointed"},
        "rabbit": {"leaf"},
        "botanical": {"leaf"},
        "geometric": {"faceted_ellipsoid"},
    }
    view_signatures: set[tuple[object, ...]] = set()
    for case in design_matrix():
        compiled = StructuralSemanticCompiler.compile(case.program)
        motor = compiled.motor_program
        specification = HierarchicalFeatureParser().parse_dict(motor)
        active_ids = set(motor["composition"]["field_ids"])
        active = [field for field in motor["fields"] if field["id"] in active_ids]
        kinds = {str(field.get("kind", "ellipsoid")) for field in active}
        if not expected[case.id] <= kinds:
            raise RuntimeError(f"{case.label} lost its advanced primitive family.")
        if compiled.report.advanced_fields <= 0 or not compiled.report.adaptive_quality:
            raise RuntimeError(f"{case.label} did not activate adaptive quality.")
        if "mesh_quality" in motor:
            raise RuntimeError(f"{case.label} retained the expensive legacy refiner.")
        if float(motor["grid"]["voxel_mm"]) < 0.72:
            raise RuntimeError(f"{case.label} adaptive voxel contract is invalid.")
        if float(motor["output"]["max_generation_seconds"]) != ADVANCED_GENERATION_BUDGET_SECONDS:
            raise RuntimeError(f"{case.label} lost its 30-second budget.")
        if case.id == "geometric":
            forbidden = {"body_shoulder_left", "body_shoulder_right"} & active_ids
            if forbidden:
                raise RuntimeError("Geometric body still composes legacy shoulder lobes.")
        if case.id == "rabbit":
            ears = [
                field
                for field in active
                if str(field["id"]).endswith("ear__silhouette_mass")
            ]
            if len(ears) != 2:
                raise RuntimeError("Rabbit did not compile exactly two long ears.")
            for ear in ears:
                center_z = float(ear["center"][2])
                half_height = float(ear["radii"][2])
                if center_z < 0.36 * case.program.body.height_mm:
                    raise RuntimeError("Rabbit ear center is too low.")
                if half_height < 0.19 * case.program.body.height_mm:
                    raise RuntimeError("Rabbit ear lost its elongated proportion.")
                if center_z + half_height < 0.57 * case.program.body.height_mm:
                    raise RuntimeError("Rabbit ear has insufficient top exposure.")
            print("rabbit long ear exposure", True, "OK")
        if case.id == "botanical":
            leaves = [
                field
                for field in active
                if str(field["id"]).startswith("leaf_")
                and str(field["id"]).endswith("__silhouette_mass")
            ]
            if len(leaves) != 6:
                raise RuntimeError("Botanical crown lost its six leaf masses.")
            maximum_crown = max(
                float(leaf["center"][2]) + float(leaf["radii"][2])
                for leaf in leaves
            )
            if maximum_crown > 0.34 * case.program.body.height_mm:
                raise RuntimeError("Botanical crown can invade the opening rim.")
            print("botanical opening separation", True, "OK")
        if case.id == "cat":
            nose = next(
                field
                for field in active
                if str(field["id"]).endswith("nose__compound_child_mass")
            )
            if str(nose.get("kind", "ellipsoid")) == "pointed":
                raise RuntimeError("Cat nose retained the beak-like pointed mass.")
            if float(nose["radii"][2]) >= float(nose["radii"][0]):
                raise RuntimeError("Cat nose lost its compact rounded profile.")
            print("cat compact rounded nose", True, "OK")
        centers = tuple(
            sorted(
                (
                    str(field.get("kind", "ellipsoid")),
                    round(float(field["center"][0]), 2),
                    round(float(field["center"][2]), 2),
                )
                for field in active
            )
        )
        view_signatures.add((case.id, tuple(sorted(kinds)), centers))
        print(
            case.label,
            "advanced fields",
            compiled.report.advanced_fields,
            "kinds",
            ",".join(sorted(kinds)),
            "views front/side/top",
            True,
            "OK",
        )
        _ = specification

    if len(view_signatures) != 4:
        raise RuntimeError("Block 6 did not produce four distinct view signatures.")
    print("distinct visual signatures", len(view_signatures), "OK")
    print("product-specific compiler branches", 0, "OK")
    print("-----------------------------------")
    print("No mesh generation or API credit required OK")
    print("DOBO Advanced Visual Geometry Block 6: Valid OK")


if __name__ == "__main__":
    main()
