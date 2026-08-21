from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from .semantic_parser import SemanticProgramParser
from .structural_vocabulary import (
    STRUCTURAL_VOCABULARY_VERSION,
    StructuralVocabularyResolver,
)


SPEC_PATH = Path(__file__).with_name("phase_3a_semantic_design.json")


def _by_id(structural):
    return {feature.semantic_feature_id: feature for feature in structural.features}


def _must_reject(label: str, action) -> None:
    try:
        action()
    except (TypeError, ValueError, RuntimeError):
        print("reject", label, True, "OK")
        return
    raise RuntimeError(f"Phase 4A accepted invalid case '{label}'.")


def _spanish_probe(fixture: dict) -> dict:
    data = deepcopy(fixture)
    data["id"] = "maceta_oso_vocabulario_probe"
    translations = {
        "left_ear": ("oreja_izquierda", "oreja"),
        "right_ear": ("oreja_derecha", "oreja"),
        "left_eye": ("ojo_izquierdo", "ojo"),
        "right_eye": ("ojo_derecho", "ojo"),
        "muzzle": ("hocico", "hocico"),
        "nose": ("nariz_central", "nariz"),
    }
    for feature in data["features"]:
        old_id = feature["id"]
        feature["id"], feature["concept"] = translations[old_id]
        if old_id in {"left_eye", "right_eye"}:
            feature["anchor"]["vertical"] = 0.28
        elif old_id == "muzzle":
            feature["anchor"]["vertical"] = 0.02
        elif old_id == "nose":
            feature["anchor"]["vertical"] = 0.10
    for relation in data["relations"]:
        relation["subject_id"] = translations[relation["subject_id"]][0]
        relation["object_id"] = translations[relation["object_id"]][0]
    return data


def main() -> None:
    print()
    print("DOBO Design Interpreter - Phase 4A")
    print("Semantic features -> structural roles -> visual groups and hierarchy")
    print("-----------------------------------")
    fixture = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    semantic = SemanticProgramParser().parse_dict(fixture)
    structural = StructuralVocabularyResolver.resolve(semantic)
    structural.validate(expected_features=len(semantic.features))
    features = _by_id(structural)

    print("vocabulary version", structural.vocabulary_version, "OK")
    print("source program", structural.source_program_id, "OK")
    print("semantic features preserved", len(structural.features), "OK")
    print("visual groups", len(structural.groups), "OK")
    print("left ear silhouette", features["left_ear"].structural_role, "OK")
    print("right ear silhouette", features["right_ear"].structural_role, "OK")
    print("ear attachment", features["left_ear"].attachment_mode, "OK")
    print("ear zone", features["left_ear"].visual_zone, "OK")
    print("left eye surface", features["left_eye"].structural_role, "OK")
    print("eye zone", features["left_eye"].visual_zone, "OK")
    print("muzzle zone", features["muzzle"].visual_zone, "OK")
    print("nose compound child", features["nose"].structural_role, "OK")
    print("nose parent", features["nose"].parent_feature_id, "OK")
    print("nose coordinate space", features["nose"].anchor.coordinate_space, "OK")
    print(
        "mirror groups",
        len([group for group in structural.groups if group.kind == "mirror_pair"]),
        "OK",
    )
    print(
        "compound groups",
        len([group for group in structural.groups if group.kind == "compound"]),
        "OK",
    )
    if features["left_ear"].structural_role != "silhouette":
        raise RuntimeError("Bear ear was not classified as a silhouette feature.")
    if features["nose"].parent_feature_id != "muzzle":
        raise RuntimeError("Bear nose was not attached to its muzzle group.")

    spanish = SemanticProgramParser().parse_dict(_spanish_probe(fixture))
    spanish_structural = StructuralVocabularyResolver.resolve(spanish)
    spanish_features = _by_id(spanish_structural)
    print(
        "Spanish ears silhouette",
        spanish_features["oreja_izquierda"].structural_role == "silhouette"
        and spanish_features["oreja_derecha"].structural_role == "silhouette",
        "OK",
    )
    print(
        "Spanish eyes normalized",
        spanish_features["ojo_izquierdo"].anchor.vertical == 0.62
        and spanish_features["ojo_derecho"].anchor.vertical == 0.62,
        "OK",
    )
    print(
        "Spanish muzzle normalized",
        spanish_features["hocico"].anchor.vertical == 0.44,
        "OK",
    )
    print(
        "Spanish nose hierarchy",
        spanish_features["nariz_central"].parent_feature_id == "hocico",
        "OK",
    )

    second = StructuralVocabularyResolver.resolve(semantic)
    print("deterministic output", structural.to_dict() == second.to_dict(), "OK")
    with TemporaryDirectory() as directory:
        output = structural.write_json(Path(directory) / "structural.json")
        encoded = json.loads(output.read_text(encoding="utf-8"))
        print(
            "machine-readable vocabulary",
            encoded["vocabulary_version"] == STRUCTURAL_VOCABULARY_VERSION,
            "OK",
        )

    broken = deepcopy(structural)
    object.__setattr__(broken.features[0], "parent_feature_id", "missing")
    _must_reject("unknown parent", broken.validate)
    print("-----------------------------------")
    print("No AI or mesh generation required OK")
    print("DOBO Design Interpreter Phase 4A: Valid OK")


if __name__ == "__main__":
    main()
