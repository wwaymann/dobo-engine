from __future__ import annotations

from dataclasses import dataclass
import unicodedata

from .semantic_contract import DesignSemanticProgram, FeatureIntent
from .structural_vocabulary import StructuralDesignProgram


BODY_GRAMMAR_VERSION = "5A.1"
COMPONENT_GRAMMAR_VERSION = "5B.1"
COMPOSITION_GRAMMAR_VERSION = "5C.1"
STYLE_GRAMMAR_VERSION = "5D.1"
ACCEPTANCE_MATRIX_VERSION = "5E.1"


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.strip().lower())
    return "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )


def _tokens(feature: FeatureIntent) -> set[str]:
    tokens: set[str] = set()
    for value in (feature.id, feature.concept, feature.form_hint):
        normalized = _normalized(value).replace("-", "_")
        tokens.add(normalized)
        tokens.update(part for part in normalized.split("_") if part)
    return tokens


@dataclass(frozen=True, slots=True)
class GrammarStyleProfile:
    name: str
    silhouette_scale: float
    depth_scale: float
    fusion_mm: float

    def validate(self) -> None:
        if self.name not in {"childlike", "organic", "minimal", "geometric"}:
            raise ValueError("Unknown design grammar style profile.")
        if not 0.7 <= self.silhouette_scale <= 1.3:
            raise ValueError("Style silhouette scale is outside its safe range.")
        if not 0.7 <= self.depth_scale <= 1.3:
            raise ValueError("Style depth scale is outside its safe range.")
        if not 2.5 <= self.fusion_mm <= 4.2:
            raise ValueError("Style fusion is outside its safe range.")


@dataclass(frozen=True, slots=True)
class GrammarFeaturePlan:
    semantic_feature_id: str
    component_kind: str
    mass_strategy: str
    shape_profile: str
    group_ids: tuple[str, ...]

    def validate(self) -> None:
        if self.component_kind not in {
            "silhouette_lobe",
            "botanical_lobe",
            "compound_parent",
            "compound_child",
            "structural_frame",
            "surface_feature",
        }:
            raise ValueError("Unknown grammar component kind.")
        if self.mass_strategy not in {
            "surface",
            "silhouette_mass",
            "compound_mass",
            "compound_child_mass",
        }:
            raise ValueError("Unknown grammar mass strategy.")
        if self.shape_profile not in {
            "round",
            "pointed",
            "elongated",
            "leaf",
            "tapered",
            "arch",
            "relief",
        }:
            raise ValueError("Unknown grammar shape profile.")


@dataclass(frozen=True, slots=True)
class DesignGrammarPlan:
    body_version: str
    component_version: str
    composition_version: str
    style_version: str
    source_program_id: str
    body_profile: str
    style: GrammarStyleProfile
    features: tuple[GrammarFeaturePlan, ...]
    mirror_groups: int
    repetition_groups: int
    compound_groups: int
    signature: str

    def validate(self, expected_features: int) -> None:
        if self.body_version != BODY_GRAMMAR_VERSION:
            raise ValueError("Unexpected body grammar version.")
        if self.component_version != COMPONENT_GRAMMAR_VERSION:
            raise ValueError("Unexpected component grammar version.")
        if self.composition_version != COMPOSITION_GRAMMAR_VERSION:
            raise ValueError("Unexpected composition grammar version.")
        if self.style_version != STYLE_GRAMMAR_VERSION:
            raise ValueError("Unexpected style grammar version.")
        if self.body_profile not in {
            "character",
            "organic",
            "column",
            "tapered",
            "faceted_proxy",
            "spherical",
        }:
            raise ValueError("Unknown body grammar profile.")
        if len(self.features) != expected_features:
            raise ValueError("Design grammar lost semantic features.")
        ids = {feature.semantic_feature_id for feature in self.features}
        if len(ids) != len(self.features):
            raise ValueError("Design grammar feature ids must be unique.")
        for feature in self.features:
            feature.validate()
        self.style.validate()
        if not self.signature.strip():
            raise ValueError("Design grammar signature must not be empty.")


class DesignGrammarResolver:
    """Resolve reusable geometry rules without product-specific branches."""

    _MUZZLE = frozenset({"hocico", "morro", "muzzle", "snout"})
    _NOSE = frozenset({"nariz", "nose"})
    _BOTANICAL = frozenset({"hoja", "leaf", "petal", "petalo"})
    _EAR = frozenset({"ear", "oreja"})
    _TAPERED = frozenset({"antler", "asta", "horn", "cuerno"})
    _FRAME = frozenset({"handle", "asa", "bridge", "puente", "arch", "arco"})

    @classmethod
    def resolve(
        cls,
        program: DesignSemanticProgram,
        structural: StructuralDesignProgram,
    ) -> DesignGrammarPlan:
        program.validate()
        structural.validate(expected_features=len(program.features))
        semantic_by_id = {feature.id: feature for feature in program.features}
        plans = tuple(
            cls._feature(
                semantic_by_id[resolved.semantic_feature_id],
                structural_role=resolved.structural_role,
                operation=resolved.geometric_operation,
                group_ids=resolved.group_ids,
            )
            for resolved in structural.features
        )
        style = cls._style(program.body.style_tags)
        body_profile = {
            "character": "character",
            "organic": "organic",
            "cylindrical": "column",
            "tapered": "tapered",
            "hexagonal": "faceted_proxy",
            "spherical": "spherical",
        }[program.body.family]
        group_kinds = [group.kind for group in structural.groups]
        component_signature = ",".join(
            sorted(
                f"{feature.component_kind}:{feature.shape_profile}:"
                f"{feature.mass_strategy}"
                for feature in plans
            )
        )
        signature = f"{body_profile}|{style.name}|{component_signature}"
        result = DesignGrammarPlan(
            body_version=BODY_GRAMMAR_VERSION,
            component_version=COMPONENT_GRAMMAR_VERSION,
            composition_version=COMPOSITION_GRAMMAR_VERSION,
            style_version=STYLE_GRAMMAR_VERSION,
            source_program_id=program.id,
            body_profile=body_profile,
            style=style,
            features=plans,
            mirror_groups=group_kinds.count("mirror_pair"),
            repetition_groups=group_kinds.count("repetition"),
            compound_groups=group_kinds.count("compound"),
            signature=signature,
        )
        result.validate(len(program.features))
        return result

    @classmethod
    def _feature(
        cls,
        feature: FeatureIntent,
        *,
        structural_role: str,
        operation: str,
        group_ids: tuple[str, ...],
    ) -> GrammarFeaturePlan:
        tokens = _tokens(feature)
        if tokens & cls._FRAME and feature.form_hint == "arch":
            return GrammarFeaturePlan(
                feature.id,
                "structural_frame",
                "surface",
                "arch",
                group_ids,
            )
        if structural_role == "compound_child" and tokens & cls._NOSE:
            return GrammarFeaturePlan(
                feature.id,
                "compound_child",
                "compound_child_mass",
                cls._profile(feature, tokens),
                group_ids,
            )
        if tokens & cls._MUZZLE and operation == "add":
            return GrammarFeaturePlan(
                feature.id,
                "compound_parent",
                "compound_mass",
                cls._profile(feature, tokens),
                group_ids,
            )
        if structural_role == "silhouette" and operation == "add":
            botanical = _normalized(feature.concept) in cls._BOTANICAL
            return GrammarFeaturePlan(
                feature.id,
                "botanical_lobe" if botanical else "silhouette_lobe",
                "silhouette_mass",
                cls._profile(feature, tokens),
                group_ids,
            )
        return GrammarFeaturePlan(
            feature.id,
            "surface_feature",
            "surface",
            "relief",
            group_ids,
        )

    @classmethod
    def _profile(cls, feature: FeatureIntent, tokens: set[str]) -> str:
        aspect = feature.size.height_ratio / max(feature.size.width_ratio, 1e-6)
        if tokens & cls._EAR:
            if feature.form_hint == "point":
                return "pointed"
            if aspect >= 1.45 or feature.form_hint == "leaf":
                return "elongated"
            return "round"
        if tokens & cls._BOTANICAL:
            return "leaf"
        if tokens & cls._TAPERED:
            return "tapered"
        if feature.form_hint == "point":
            return "pointed"
        if feature.form_hint == "leaf":
            return "elongated"
        return "round"

    @staticmethod
    def _style(tags: tuple[str, ...]) -> GrammarStyleProfile:
        normalized = {_normalized(tag) for tag in tags}
        if normalized & {"geometric", "geometrico", "faceted", "facetado"}:
            return GrammarStyleProfile("geometric", 0.95, 0.90, 2.8)
        if normalized & {"minimal", "minimalist", "minimalista"}:
            return GrammarStyleProfile("minimal", 1.00, 1.00, 3.6)
        if normalized & {"organic", "organico", "botanical", "botanico"}:
            return GrammarStyleProfile("organic", 1.00, 1.00, 3.8)
        return GrammarStyleProfile("childlike", 1.08, 1.10, 3.6)
