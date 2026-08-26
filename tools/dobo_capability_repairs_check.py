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

def program(profile: str, *, text: bool = False):
    family, tag, opening = {
        "cuboid": ("organic", "cuboid", "polygonal"),
        "cylindrical": ("cylindrical", "cylindrical", "circular"),
        "ovoid": ("organic", "ovoid", "elliptical"),
        "triangular_prism": ("hexagonal", "triangular_prism", "polygonal"),
        "spherical": ("spherical", "spherical", "circular"),
    }[profile]
    features = []
    if text:
        features.append(_feature("front_text", "text_dobo", "text", "raised", region="front", horizontal=0.0, vertical=0.52, width=0.38, height=0.16, depth=1.8))
    return _program(
        f"repair_{profile}_{'text' if text else 'plain'}",
        f"Maceta {profile}" + (" con texto DOBO" if text else ""),
        family=family, height=110.0, width=110.0, depth=110.0,
        opening_shape=opening, opening_width=0.58, opening_depth=0.58,
        style_tags=[tag], features=features, relations=[],
    )

def check_neutral_profiles():
    report = {}
    for profile in ("cuboid", "cylindrical", "ovoid", "triangular_prism", "spherical"):
        p = program(profile)
        resolved = GeneralBodyFamilyExpander.requested_profile(p)
        fields, _ = GeneralBodyFamilyExpander._fields_for(resolved, p)
        centers = [round(float(field["center"][2]), 6) for field in fields]
        if len(set(centers)) != 1:
            raise RuntimeError(f"{profile} still contains unsolicited axial sections: {centers}")
        report[profile] = {"profile": resolved, "axial_centers": centers}
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
    out = ROOT / "outputs-ci" / "capability-repairs"
    result = Pipeline().generate_from_semantic(program("cylindrical", text=True), output_root=out)
    result.validate()
    semantic = json.loads(Path(result.semantic_path).read_text(encoding="utf-8"))
    motor = json.loads(Path(result.motor_path).read_text(encoding="utf-8"))
    feature = next(item for item in semantic["features"] if item["form_hint"] == "text")
    if feature["concept"] != "text_dobo":
        raise RuntimeError("Text literal was not preserved semantically.")
    if not result.mesh_result.watertight or not result.mesh_result.winding_consistent:
        raise RuntimeError("Text planter is not physically valid.")
    if not Path(result.stl_path).is_file() or Path(result.stl_path).stat().st_size <= 0:
        raise RuntimeError("Text planter STL was not generated.")
    return {
        "text_concept": feature["concept"],
        "profile": result.trace.body_profile,
        "morphology": motor.get("morphogenesis", {}).get("profile"),
        "watertight": result.mesh_result.watertight,
        "winding_consistent": result.mesh_result.winding_consistent,
        "vertices": result.mesh_result.vertex_count,
        "stl": result.stl_path,
        "three_mf": result.three_mf_path,
    }

def main():
    out = ROOT / "outputs-ci" / "capability-repairs"
    out.mkdir(parents=True, exist_ok=True)
    report = {
        "neutral_profiles": check_neutral_profiles(),
        "voxel_repair": check_voxel_repair(),
        "text_geometry": check_text_geometry(),
    }
    target = out / "REPAIR_VALIDATION.json"
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
