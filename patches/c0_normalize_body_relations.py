from pathlib import Path


def patch_interpreter(path_string: str) -> None:
    path = Path(path_string)
    text = path.read_text(encoding="utf-8")
    old = '''        program = SemanticProgramParser().parse_dict(response.output)\n'''
    new = '''        semantic_output = response.output\n        features = semantic_output.get("features")\n        relations = semantic_output.get("relations")\n        if isinstance(features, list) and isinstance(relations, list):\n            feature_ids = {\n                feature.get("id")\n                for feature in features\n                if isinstance(feature, dict) and isinstance(feature.get("id"), str)\n            }\n            program_id = semantic_output.get("id")\n            # The semantic relation contract is feature-to-feature only, while\n            # attachment to the vessel is already encoded by surface_anchor.\n            # Live interpreters can still name that vessel endpoint with common\n            # body aliases; normalize only these explicit whole-vessel shorthands.\n            body_aliases = {\n                "body",\n                "planter_body",\n                "pot_body",\n                "vessel_body",\n                "main_body",\n            }\n            if isinstance(program_id, str) and program_id:\n                # Live models sometimes use the semantic program id as shorthand\n                # for the vessel as a whole.\n                body_aliases.add(program_id)\n            normalized_relations = []\n            for relation in relations:\n                if not isinstance(relation, dict):\n                    normalized_relations.append(relation)\n                    continue\n                subject = relation.get("subject_id")\n                object_id = relation.get("object_id")\n                if subject in body_aliases or object_id in body_aliases:\n                    other = object_id if subject in body_aliases else subject\n                    if other in feature_ids:\n                        # Redundant feature-to-vessel shorthand. Do not relax\n                        # arbitrary unknown-id validation; only explicit vessel\n                        # aliases are normalized away.\n                        continue\n                normalized_relations.append(relation)\n            if len(normalized_relations) != len(relations):\n                semantic_output = dict(semantic_output)\n                semantic_output["relations"] = normalized_relations\n        program = SemanticProgramParser().parse_dict(semantic_output)\n'''
    if old not in text:
        raise SystemExit(f"interpreter parse insertion point not found: {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(path)


patch_interpreter("app/product_generators/design_interpreter/prompt_interpreter.py")
patch_interpreter("app/product_generators/design_interpreter/image_interpreter.py")

# Keep the live-model acceptance gate on the existing manufacturability contract,
# but normalize its minimum-feature interpretation: lateral printable size and
# relief depth are independent checks in the contract.
minimum_feature_patch = Path("patches/c0_normalize_minimum_feature_validation.py")
exec(compile(minimum_feature_patch.read_text(encoding="utf-8"), str(minimum_feature_patch), "exec"))

# The deterministic repair previously targeted half of maximum relief depth.
# That can remain below the compiler's minimum-depth gate (up to 0.8 mm), so a
# valid shallow feature could be selected for repair forever without ever
# reaching a satisfiable value. Raise only failing depth features to the exact
# bounded contract floor, with a 1% numerical margin, and keep the existing
# maximum-relief ceiling intact.
repair_path = Path("app/product_generators/design_interpreter/proposal_repair.py")
repair_text = repair_path.read_text(encoding="utf-8")
old_repair = '''            if operations.get("increase_depth"):\n                depth = max(\n                    size.depth_mm,\n                    min(\n                        0.8,\n                        0.5 * program.manufacturing.maximum_relief_depth_mm,\n                    ),\n                )\n'''
new_repair = '''            if operations.get("increase_depth"):\n                required_depth = min(\n                    0.8, program.manufacturing.maximum_relief_depth_mm\n                )\n                target_depth = min(\n                    program.manufacturing.maximum_relief_depth_mm,\n                    1.01 * required_depth,\n                )\n                depth = max(size.depth_mm, target_depth)\n'''
if new_repair in repair_text:
    print(f"already normalized: {repair_path}")
elif old_repair in repair_text:
    repair_path.write_text(
        repair_text.replace(old_repair, new_repair, 1), encoding="utf-8"
    )
    print(repair_path)
else:
    raise SystemExit("proposal-repair minimum-depth block no longer matches expected source")
