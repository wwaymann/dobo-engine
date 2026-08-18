from pathlib import Path

path = Path("app/product_generators/design_interpreter/prompt_interpreter.py")
text = path.read_text(encoding="utf-8")
old = '''        program = SemanticProgramParser().parse_dict(response.output)\n'''
new = '''        semantic_output = response.output\n        features = semantic_output.get("features")\n        relations = semantic_output.get("relations")\n        if isinstance(features, list) and isinstance(relations, list):\n            feature_ids = {\n                feature.get("id")\n                for feature in features\n                if isinstance(feature, dict) and isinstance(feature.get("id"), str)\n            }\n            program_id = semantic_output.get("id")\n            body_aliases = {"body"}\n            if isinstance(program_id, str) and program_id:\n                # Live models sometimes use the semantic program id as shorthand\n                # for the vessel as a whole. The 3A.1 relation contract only\n                # permits feature-to-feature endpoints, while body attachment is\n                # already represented by each feature's surface anchor.\n                body_aliases.add(program_id)\n            normalized_relations = []\n            for relation in relations:\n                if not isinstance(relation, dict):\n                    normalized_relations.append(relation)\n                    continue\n                subject = relation.get("subject_id")\n                object_id = relation.get("object_id")\n                if subject in body_aliases or object_id in body_aliases:\n                    other = object_id if subject in body_aliases else subject\n                    if other in feature_ids:\n                        # Redundant feature-to-vessel shorthand. Do not relax\n                        # arbitrary unknown-id validation; only explicit vessel\n                        # aliases are normalized away.\n                        continue\n                normalized_relations.append(relation)\n            if len(normalized_relations) != len(relations):\n                semantic_output = dict(semantic_output)\n                semantic_output["relations"] = normalized_relations\n        program = SemanticProgramParser().parse_dict(semantic_output)\n'''
if old not in text:
    raise SystemExit("prompt interpreter parse insertion point not found")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print(path)

# Keep the live-model acceptance gate on the existing manufacturability contract,
# but normalize its minimum-feature interpretation: lateral printable size and
# relief depth are independent checks in the contract.
minimum_feature_patch = Path("patches/c0_normalize_minimum_feature_validation.py")
exec(compile(minimum_feature_patch.read_text(encoding="utf-8"), str(minimum_feature_patch), "exec"))
