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
from dobo_retry_repairs import install_retry_repairs
from product_generators.design_interpreter.semantic_parser import SemanticProgramParser

install_retry_repairs()
Pipeline = install()

SEMANTIC = {
    "schema_version": "3A.1",
    "id": "planter_cyl_walter_001",
    "product_kind": "planter",
    "source": {"kind": "prompt", "prompt": "Crea una maceta cilíndrica con el texto WALTER en sobrerrelieve al frente y drenaje inferior.", "image_reference": None},
    "body": {"family": "cylindrical", "height_mm": 140.0, "width_mm": 140.0, "depth_mm": 140.0, "opening_shape": "circular", "opening_width_ratio": 0.9, "opening_depth_ratio": 0.95, "style_tags": ["cylindrical"]},
    "features": [{"id": "feat_text_walter", "concept": "text_walter", "form_hint": "text", "surface_effect": "raised", "anchor": {"region": "front", "horizontal": 0.0, "vertical": 0.5, "roll_degrees": 0.0}, "size": {"width_ratio": 0.6, "height_ratio": 0.18, "depth_mm": 0.6}, "priority": "required", "can_omit": False, "confidence": 0.9}],
    "relations": [],
    "manufacturing": {"minimum_wall_mm": 2.0, "minimum_feature_mm": 0.5, "maximum_relief_depth_mm": 0.8, "drainage_required": True, "multicolor_requested": False},
    "assumptions": [], "ambiguities": [],
}


def main() -> None:
    program = SemanticProgramParser().parse_dict(SEMANTIC)
    out = ROOT / "outputs-ci" / "exact-walter"
    result = Pipeline().generate_from_semantic(
        program,
        output_root=out,
        generation_budget_seconds=120.0,
    )
    result.validate()
    motor = json.loads(Path(result.motor_path).read_text(encoding="utf-8"))
    templates = motor["hierarchy_program"]["templates"]
    text_template = next(item for item in templates if item["id"] == "feat_text_walter_template")
    if text_template.get("semantic_kind") != "text_stroke":
        raise RuntimeError("Motor JSON did not preserve semantic text kind.")
    if text_template.get("text_literal") != "WALTER":
        raise RuntimeError("Motor JSON did not preserve WALTER literal.")
    mesh = result.mesh_result
    if not mesh.watertight or not mesh.winding_consistent or mesh.component_count != 1:
        raise RuntimeError(f"Exact WALTER topology invalid: watertight={mesh.watertight}, winding={mesh.winding_consistent}, components={mesh.component_count}")
    if not Path(result.stl_path).is_file() or Path(result.stl_path).stat().st_size <= 0:
        raise RuntimeError("Exact WALTER STL missing.")
    if not Path(result.three_mf_path).is_file() or Path(result.three_mf_path).stat().st_size <= 0:
        raise RuntimeError("Exact WALTER 3MF missing.")
    report = {
        "semantic_id": program.id,
        "text_literal": text_template["text_literal"],
        "semantic_kind": text_template["semantic_kind"],
        "body_profile": result.trace.body_profile,
        "mesh_quality_profile": result.trace.mesh_quality_profile,
        "generation_attempts": result.trace.generation_attempts,
        "generation_seconds": mesh.generation_seconds,
        "max_generation_seconds": mesh.max_generation_seconds,
        "watertight": mesh.watertight,
        "winding_consistent": mesh.winding_consistent,
        "components": mesh.component_count,
        "vertices": mesh.vertex_count,
        "faces": mesh.face_count,
        "stl": result.stl_path,
        "three_mf": result.three_mf_path,
    }
    target = out / "EXACT_WALTER_VALIDATION.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
