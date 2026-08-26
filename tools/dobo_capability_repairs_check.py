from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
TOOLS = ROOT / "tools"
for path in (APP, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from dobo_capability_repairs import install
from product_generators.design_interpreter.phase_5_design_matrix import _feature, _program
from product_generators.design_interpreter.semantic_compiler import SemanticToMotorCompiler
from product_generators.design_interpreter.body_family_expansion import GeneralBodyFamilyExpander
from product_generators.organic_shapes.vessel_specification import OrganicVesselParser

Pipeline = install()

def program(profile: str, *, text_literal: str | None = None):
    family, tag, opening, dims = {
        "cuboid": ("organic", "cuboid", "polygonal", (110.0, 110.0, 110.0)),
        "rectangular_prism": ("organic", "rectangular_prism", "polygonal", (105.0, 145.0, 95.0)),
        "cylindrical": ("cylindrical", "cylindrical", "circular", (115.0, 110.0, 110.0)),
        "tapered_revolution": ("tapered", "tapered_revolution", "circular", (120.0, 120.0, 120.0)),
        "ovoid": ("organic", "ovoid", "elliptical", (125.0, 112.0, 106.0)),
        "triangular_prism": ("hexagonal", "triangular_prism", "polygonal", (112.0, 120.0, 120.0)),
        "spherical": ("spherical", "spherical", "circular", (112.0, 122.0, 122.0)),
    }[profile]
    height, width, depth = dims
    features = []
    if text_literal:
        features.append(_feature("front_text", f"text_{text_literal.lower()}", "text", "raised", region="front", horizontal=0.0, vertical=0.52, width=0.38, height=0.16, depth=1.8))
    return _program(
        f"repair_{profile}_{text_literal.lower() if text_literal else 'plain'}",
        f"Maceta {profile}" + (f" con texto {text_literal}" if text_literal else ""),
        family=family, height=height, width=width, depth=depth,
        opening_shape=opening, opening_width=0.58, opening_depth=0.58,
        style_tags=[tag], features=features, relations=[],
    )

def check_neutral_profiles():
    report = {}
    for profile in ("cuboid", "rectangular_prism", "cylindrical", "tapered_revolution", "ovoid", "triangular_prism", "spherical"):
        p = program(profile)
        resolved = GeneralBodyFamilyExpander.requested_profile(p)
        fields, _ = GeneralBodyFamilyExpander._fields_for(resolved, p)
        centers = [round(float(field["center"][2]), 6) for field in fields]
        if profile != "tapered_revolution" and len(set(centers)) != 1:
            raise RuntimeError(f"{profile} still contains unsolicited axial sections: {centers}")
        report[profile] = {"profile": resolved, "axial_centers": centers}
    return report

def check_primitive_geometry():
    out = ROOT / "outputs-ci" / "capability-repairs" / "primitives"
    report = {}
    for profile in ("cuboid", "rectangular_prism", "cylindrical", "tapered_revolution", "spherical", "ovoid", "triangular_prism"):
        print(f"GENERATING_PRIMITIVE={profile}", flush=True)
        result = Pipeline().generate_from_semantic(program(profile), output_root=out / profile)
        result.validate()
        mesh = result.mesh_result
        if not mesh.watertight or not mesh.winding_consistent or mesh.component_count != 1:
            raise RuntimeError(
                f"Primitive {profile} topology invalid: watertight={mesh.watertight}, winding={mesh.winding_consistent}, components={mesh.component_count}"
            )
        report[profile] = {
            "watertight": mesh.watertight,
            "winding_consistent": mesh.winding_consistent,
            "components": mesh.component_count,
            "vertices": mesh.vertex_count,
            "faces": mesh.face_count,
            "stl": result.stl_path,
        }
    return report

def check_voxel_repair():
    p = program("cylindrical")
    motor = SemanticToMotorCompiler.compile(p).motor_program
    motor["grid"]["voxel_mm"] = 2.0
    before = motor["grid"]["voxel_mm"]
    parsed = OrganicVesselParser().parse_dict(motor)
    after = parsed.grid.voxel_mm
    if after * 3.0 > parsed.vessel.wall_mm + 1e-9:
        raise RuntimeError("Voxel repair did not preserve a three-voxel vessel wall.")
    return {"before_voxel_mm": before, "after_voxel_mm": after, "wall_mm": parsed.vessel.wall_mm}

def check_text_geometry():
    out = ROOT / "outputs-ci" / "capability-repairs" / "text"
    report = {}
    for literal in ("DOBO", "WALTER"):
        print(f"GENERATING_TEXT={literal}", flush=True)
        result = Pipeline().generate_from_semantic(program("cylindrical", text_literal=literal), output_root=out / literal.lower())
        result.validate()
        semantic = json.loads(Path(result.semantic_path).read_text(encoding="utf-8"))
        motor = json.loads(Path(result.motor_path).read_text(encoding="utf-8"))
        feature = next(item for item in semantic["features"] if item["form_hint"] == "text")
        expected = f"text_{literal.lower()}"
        if feature["concept"] != expected:
            raise RuntimeError(f"Text literal was not preserved semantically: {feature['concept']} != {expected}")
        mesh = result.mesh_result
        if not mesh.watertight or not mesh.winding_consistent or mesh.component_count != 1:
            raise RuntimeError(
                f"Text {literal} topology invalid: watertight={mesh.watertight}, winding={mesh.winding_consistent}, components={mesh.component_count}"
            )
        if not Path(result.stl_path).is_file() or Path(result.stl_path).stat().st_size <= 0:
            raise RuntimeError(f"Text planter STL was not generated for {literal}.")
        report[literal] = {
            "text_concept": feature["concept"],
            "profile": result.trace.body_profile,
            "morphology": motor.get("morphogenesis", {}).get("profile"),
            "watertight": mesh.watertight,
            "winding_consistent": mesh.winding_consistent,
            "components": mesh.component_count,
            "vertices": mesh.vertex_count,
            "stl": result.stl_path,
            "three_mf": result.three_mf_path,
        }
    return report

def main():
    out = ROOT / "outputs-ci" / "capability-repairs"
    out.mkdir(parents=True, exist_ok=True)
    report = {
        "neutral_profiles": check_neutral_profiles(),
        "primitive_geometry": check_primitive_geometry(),
        "voxel_repair": check_voxel_repair(),
        "text_geometry": check_text_geometry(),
    }
    target = out / "REPAIR_VALIDATION.json"
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
