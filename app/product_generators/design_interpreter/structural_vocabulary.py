from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any
import unicodedata

from .semantic_contract import DesignSemanticProgram, FeatureIntent


STRUCTURAL_VOCABULARY_VERSION = "4A.1"
STRUCTURAL_ROLES = frozenset(
    {"silhouette", "surface", "texture", "compound_child"}
)
ATTACHMENT_MODES = frozenset(
    {"body_silhouette", "body_surface", "feature_surface"}
)
GEOMETRIC_OPERATIONS = frozenset({"add", "subtract", "mark"})
VISUAL_ZONES = frozenset(
    {
        "crown",
        "upper_face",
        "mid_face",
        "lower_face",
        "side",
        "body",
        "all_around",
    }
)

_SILHOUETTE_CONCEPTS = frozenset(
    {
        "antler",
        "asa",
        "ear",
        "handle",
        "hoja",
        "horn",
        "leaf",
        "oreja",
        "asta",
        "cuerno",
    }
)
_EYE_CONCEPTS = frozenset({"eye", "ojo", "pupil", "pupila"})
_MUZZLE_CONCEPTS = frozenset({"hocico", "morro", "muzzle", "snout"})
_NOSE_CONCEPTS = frozenset({"nariz", "nose"})
_MOUTH_CONCEPTS = frozenset({"boca", "mouth"})
_TEXTURE_CONCEPTS = frozenset(
    {"finish", "roughness", "surface_texture", "textura", "texture"}
)


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.strip().lower())
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def _tokens(feature: FeatureIntent) -> set[str]:
    values = (feature.id, feature.concept)
    tokens: set[str] = set()
    for value in values:
        normalized = _normalized(value).replace("-", "_")
        tokens.add(normalized)
        tokens.update(part for part in normalized.split("_") if part)
    return tokens


@dataclass(frozen=True, slots=True)
class StructuralAnchor:
    coordinate_space: str
    region: str
    horizontal: float
    vertical: float
    roll_degrees: float

    def validate(self) -> None:
        if self.coordinate_space not in {"body", "parent_feature"}:
            raise ValueError("Structural anchor coordinate space is invalid.")
        if not -1.0 <= self.horizontal <= 1.0:
            raise ValueError("Structural anchor horizontal value is invalid.")
        if not 0.0 <= self.vertical <= 1.0:
            raise ValueError("Structural anchor vertical value is invalid.")
        if not -180.0 <= self.roll_degrees <= 180.0:
            raise ValueError("Structural anchor roll is invalid.")


@dataclass(frozen=True, slots=True)
class StructuralFeature:
    semantic_feature_id: str
    concept: str
    structural_role: str
    attachment_mode: str
    geometric_operation: str
    visual_zone: str
    parent_feature_id: str | None
    group_ids: tuple[str, ...]
    anchor: StructuralAnchor
    priority: str
    can_omit: bool
    confidence: float

    def validate(self) -> None:
        if self.structural_role not in STRUCTURAL_ROLES:
            raise ValueError("Unknown structural role.")
        if self.attachment_mode not in ATTACHMENT_MODES:
            raise ValueError("Unknown attachment mode.")
        if self.geometric_operation not in GEOMETRIC_OPERATIONS:
            raise ValueError("Unknown structural geometric operation.")
        if self.visual_zone not in VISUAL_ZONES:
            raise ValueError("Unknown visual zone.")
        if self.structural_role == "compound_child":
            if self.attachment_mode != "feature_surface" or not self.parent_feature_id:
                raise ValueError("Compound child requires a parent feature attachment.")
            if self.anchor.coordinate_space != "parent_feature":
                raise ValueError("Compound child anchor must be parent-relative.")
        elif self.parent_feature_id is not None:
            raise ValueError("Only compound children can name a parent feature.")
        if self.priority == "required" and self.can_omit:
            raise ValueError("Required structural feature cannot be omitted.")
        if len(set(self.group_ids)) != len(self.group_ids):
            raise ValueError("Structural feature group ids must be unique.")
        self.anchor.validate()


@dataclass(frozen=True, slots=True)
class StructuralVisualGroup:
    id: str
    kind: str
    member_ids: tuple[str, ...]
    parent_feature_id: str | None = None

    def validate(self) -> None:
        if self.kind not in {"compound", "mirror_pair", "repetition"}:
            raise ValueError("Unknown structural visual group kind.")
        if len(self.member_ids) < 2 or len(set(self.member_ids)) != len(
            self.member_ids
        ):
            raise ValueError("Structural group requires unique members.")
        if self.kind == "compound" and self.parent_feature_id is None:
            raise ValueError("Compound group requires a parent feature.")


@dataclass(frozen=True, slots=True)
class StructuralDesignProgram:
    vocabulary_version: str
    source_program_id: str
    features: tuple[StructuralFeature, ...]
    groups: tuple[StructuralVisualGroup, ...]

    def validate(self, expected_features: int | None = None) -> None:
        if self.vocabulary_version != STRUCTURAL_VOCABULARY_VERSION:
            raise ValueError("Unexpected structural vocabulary version.")
        if expected_features is not None and len(self.features) != expected_features:
            raise ValueError("Structural vocabulary lost semantic features.")
        feature_ids = {feature.semantic_feature_id for feature in self.features}
        if len(feature_ids) != len(self.features):
            raise ValueError("Structural features must be unique.")
        group_ids: set[str] = set()
        for group in self.groups:
            group.validate()
            if group.id in group_ids:
                raise ValueError("Structural group ids must be unique.")
            group_ids.add(group.id)
            if set(group.member_ids) - feature_ids:
                raise ValueError("Structural group references unknown features.")
            if group.parent_feature_id not in feature_ids | {None}:
                raise ValueError("Structural group parent is unknown.")
        parents: dict[str, str] = {}
        for feature in self.features:
            feature.validate()
            if feature.parent_feature_id is not None:
                if feature.parent_feature_id not in feature_ids:
                    raise ValueError("Structural feature parent is unknown.")
                if feature.parent_feature_id == feature.semantic_feature_id:
                    raise ValueError("Structural feature cannot parent itself.")
                parents[feature.semantic_feature_id] = feature.parent_feature_id
            if set(feature.group_ids) - group_ids:
                raise ValueError("Structural feature references unknown groups.")
        for start in parents:
            visited = {start}
            current = start
            while current in parents:
                current = parents[current]
                if current in visited:
                    raise ValueError("Structural feature hierarchy contains a cycle.")
                visited.add(current)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def write_json(self, path: str | Path) -> Path:
        target = Path(path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return target


class StructuralVocabularyResolver:
    """Enrich stable 3A.1 meaning with deterministic executable visual roles."""

    @classmethod
    def resolve(cls, program: DesignSemanticProgram) -> StructuralDesignProgram:
        program.validate()
        by_id = {feature.id: feature for feature in program.features}
        parents = cls._parents(program, by_id)
        raw_groups = cls._groups(program, parents)
        groups = tuple(raw_groups)
        memberships: dict[str, list[str]] = {feature.id: [] for feature in program.features}
        for group in groups:
            for member in group.member_ids:
                memberships[member].append(group.id)
        features = tuple(
            cls._feature(
                feature,
                parent_feature_id=parents.get(feature.id),
                group_ids=tuple(sorted(memberships[feature.id])),
            )
            for feature in program.features
        )
        result = StructuralDesignProgram(
            vocabulary_version=STRUCTURAL_VOCABULARY_VERSION,
            source_program_id=program.id,
            features=features,
            groups=groups,
        )
        result.validate(expected_features=len(program.features))
        return result

    @classmethod
    def _feature(
        cls,
        feature: FeatureIntent,
        *,
        parent_feature_id: str | None,
        group_ids: tuple[str, ...],
    ) -> StructuralFeature:
        tokens = _tokens(feature)
        if parent_feature_id is not None:
            role = "compound_child"
            attachment = "feature_surface"
        elif tokens & _SILHOUETTE_CONCEPTS and feature.surface_effect == "raised":
            role = "silhouette"
            attachment = "body_silhouette"
        elif (
            feature.surface_effect == "marking"
            and (feature.anchor.region == "all_around" or tokens & _TEXTURE_CONCEPTS)
        ):
            role = "texture"
            attachment = "body_surface"
        else:
            role = "surface"
            attachment = "body_surface"
        operation = (
            "subtract"
            if feature.surface_effect in {"recessed", "cutout"}
            else "mark"
            if feature.surface_effect == "marking"
            else "add"
        )
        zone, horizontal, vertical = cls._placement(feature, tokens, role)
        coordinate_space = "parent_feature" if parent_feature_id else "body"
        region = "front" if parent_feature_id else feature.anchor.region
        return StructuralFeature(
            semantic_feature_id=feature.id,
            concept=feature.concept,
            structural_role=role,
            attachment_mode=attachment,
            geometric_operation=operation,
            visual_zone=zone,
            parent_feature_id=parent_feature_id,
            group_ids=group_ids,
            anchor=StructuralAnchor(
                coordinate_space=coordinate_space,
                region=region,
                horizontal=horizontal,
                vertical=vertical,
                roll_degrees=feature.anchor.roll_degrees,
            ),
            priority=feature.priority,
            can_omit=feature.can_omit,
            confidence=feature.confidence,
        )

    @staticmethod
    def _placement(
        feature: FeatureIntent,
        tokens: set[str],
        role: str,
    ) -> tuple[str, float, float]:
        horizontal = feature.anchor.horizontal
        vertical = feature.anchor.vertical
        if role == "compound_child":
            return "mid_face", 0.0, 0.58
        if role == "silhouette":
            sign = -1.0 if horizontal < 0.0 or "left" in tokens or "izquierda" in tokens else 1.0
            if not ({"left", "right", "izquierda", "derecha"} & tokens) and abs(horizontal) < 0.1:
                sign = 0.0
            horizontal = sign * max(0.52, abs(horizontal)) if sign else 0.0
            return "crown", horizontal, max(0.86, vertical)
        if tokens & _EYE_CONCEPTS:
            sign = -1.0 if horizontal < 0.0 or "left" in tokens or "izquierdo" in tokens else 1.0
            horizontal = sign * max(0.22, min(0.38, abs(horizontal)))
            return "upper_face", horizontal, 0.62
        if tokens & _MUZZLE_CONCEPTS:
            return "mid_face", 0.0, 0.44
        if tokens & _NOSE_CONCEPTS:
            return "mid_face", 0.0, 0.50
        if tokens & _MOUTH_CONCEPTS:
            return "lower_face", 0.0, 0.34
        if feature.anchor.region in {"left", "right"}:
            return "side", horizontal, vertical
        if feature.anchor.region == "all_around":
            return "all_around", horizontal, vertical
        return "body", horizontal, vertical

    @staticmethod
    def _parents(
        program: DesignSemanticProgram,
        by_id: dict[str, FeatureIntent],
    ) -> dict[str, str]:
        parents: dict[str, str] = {}
        for relation in program.relations:
            if relation.kind != "centered_on":
                continue
            subject = by_id[relation.subject_id]
            target = by_id[relation.object_id]
            subject_area = subject.size.width_ratio * subject.size.height_ratio
            target_area = target.size.width_ratio * target.size.height_ratio
            if subject_area < target_area and target.surface_effect == "raised":
                parents[subject.id] = target.id
        return parents

    @staticmethod
    def _groups(
        program: DesignSemanticProgram,
        parents: dict[str, str],
    ) -> list[StructuralVisualGroup]:
        groups: list[StructuralVisualGroup] = []
        seen_pairs: set[tuple[str, str]] = set()
        for relation in program.relations:
            if relation.kind not in {"mirror_of", "repeated_from"}:
                continue
            pair = tuple(sorted((relation.subject_id, relation.object_id)))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            kind = "mirror_pair" if relation.kind == "mirror_of" else "repetition"
            groups.append(
                StructuralVisualGroup(
                    id=f"{kind}__{pair[0]}__{pair[1]}",
                    kind=kind,
                    member_ids=pair,
                )
            )
        children_by_parent: dict[str, list[str]] = {}
        for child, parent in parents.items():
            children_by_parent.setdefault(parent, []).append(child)
        for parent in sorted(children_by_parent):
            members = (parent, *sorted(children_by_parent[parent]))
            groups.append(
                StructuralVisualGroup(
                    id=f"compound__{parent}",
                    kind="compound",
                    member_ids=members,
                    parent_feature_id=parent,
                )
            )
        return groups
