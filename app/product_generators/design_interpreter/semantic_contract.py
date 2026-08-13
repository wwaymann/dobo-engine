from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
import re
from typing import Any


SCHEMA_VERSION = "3A.1"
_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{1,63}$")

SOURCE_KINDS = frozenset({"prompt", "image", "prompt_and_image"})
PRODUCT_KINDS = frozenset({"planter"})
BODY_FAMILIES = frozenset(
    {"organic", "cylindrical", "tapered", "hexagonal", "character"}
)
OPENING_SHAPES = frozenset({"circular", "elliptical", "polygonal"})
SURFACE_REGIONS = frozenset(
    {"front", "back", "left", "right", "upper", "lower", "all_around"}
)
FORM_HINTS = frozenset(
    {
        "arch",
        "badge",
        "capsule",
        "disc",
        "leaf",
        "oval",
        "point",
        "ridge",
        "slit",
        "text",
        "unspecified",
    }
)
SURFACE_EFFECTS = frozenset({"raised", "recessed", "cutout", "marking"})
PRIORITIES = frozenset({"required", "preferred", "optional"})
RELATION_KINDS = frozenset(
    {
        "above",
        "aligned_with",
        "below",
        "centered_on",
        "grouped_with",
        "mirror_of",
        "repeated_from",
    }
)


def _identifier(value: str, label: str) -> None:
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError(
            f"{label} must use lower_snake_case and contain 2-64 characters."
        )


def _finite(value: float, label: str) -> None:
    if not isfinite(value):
        raise ValueError(f"{label} must be finite.")


def _choice(value: str, choices: frozenset[str], label: str) -> None:
    if value not in choices:
        raise ValueError(f"{label} must be one of {sorted(choices)}.")


def _confidence(value: float, label: str) -> None:
    _finite(value, label)
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{label} must be between 0 and 1.")


@dataclass(frozen=True, slots=True)
class SourceIntent:
    kind: str
    prompt: str | None
    image_reference: str | None

    def validate(self) -> None:
        _choice(self.kind, SOURCE_KINDS, "source.kind")
        if self.kind in {"prompt", "prompt_and_image"} and not (
            self.prompt and self.prompt.strip()
        ):
            raise ValueError("Prompt source requires non-empty source.prompt.")
        if self.kind in {"image", "prompt_and_image"} and not (
            self.image_reference and self.image_reference.strip()
        ):
            raise ValueError(
                "Image source requires non-empty source.image_reference."
            )


@dataclass(frozen=True, slots=True)
class BodyIntent:
    family: str
    height_mm: float
    width_mm: float
    depth_mm: float
    opening_shape: str
    opening_width_ratio: float
    opening_depth_ratio: float
    style_tags: tuple[str, ...]

    def validate(self) -> None:
        _choice(self.family, BODY_FAMILIES, "body.family")
        _choice(self.opening_shape, OPENING_SHAPES, "body.opening_shape")
        for label, value in (
            ("body.height_mm", self.height_mm),
            ("body.width_mm", self.width_mm),
            ("body.depth_mm", self.depth_mm),
        ):
            _finite(value, label)
            if not 30.0 <= value <= 500.0:
                raise ValueError(f"{label} must be between 30 and 500 mm.")
        for label, value in (
            ("body.opening_width_ratio", self.opening_width_ratio),
            ("body.opening_depth_ratio", self.opening_depth_ratio),
        ):
            _finite(value, label)
            if not 0.15 <= value <= 0.95:
                raise ValueError(f"{label} must be between 0.15 and 0.95.")
        if not self.style_tags:
            raise ValueError("body.style_tags must contain at least one tag.")
        if len(set(self.style_tags)) != len(self.style_tags):
            raise ValueError("body.style_tags must be unique.")
        for tag in self.style_tags:
            _identifier(tag, "body style tag")


@dataclass(frozen=True, slots=True)
class SemanticAnchor:
    region: str
    horizontal: float
    vertical: float
    roll_degrees: float = 0.0

    def validate(self) -> None:
        _choice(self.region, SURFACE_REGIONS, "feature.anchor.region")
        for label, value, low, high in (
            ("feature.anchor.horizontal", self.horizontal, -1.0, 1.0),
            ("feature.anchor.vertical", self.vertical, 0.0, 1.0),
            ("feature.anchor.roll_degrees", self.roll_degrees, -180.0, 180.0),
        ):
            _finite(value, label)
            if not low <= value <= high:
                raise ValueError(f"{label} must be between {low} and {high}.")


@dataclass(frozen=True, slots=True)
class FeatureSizeIntent:
    width_ratio: float
    height_ratio: float
    depth_mm: float

    def validate(self) -> None:
        for label, value in (
            ("feature.size.width_ratio", self.width_ratio),
            ("feature.size.height_ratio", self.height_ratio),
        ):
            _finite(value, label)
            if not 0.01 <= value <= 1.0:
                raise ValueError(f"{label} must be between 0.01 and 1.0.")
        _finite(self.depth_mm, "feature.size.depth_mm")
        if not 0.1 <= self.depth_mm <= 20.0:
            raise ValueError("feature.size.depth_mm must be between 0.1 and 20 mm.")


@dataclass(frozen=True, slots=True)
class FeatureIntent:
    id: str
    concept: str
    form_hint: str
    surface_effect: str
    anchor: SemanticAnchor
    size: FeatureSizeIntent
    priority: str
    can_omit: bool
    confidence: float

    def validate(self) -> None:
        _identifier(self.id, "feature.id")
        _identifier(self.concept, "feature.concept")
        _choice(self.form_hint, FORM_HINTS, "feature.form_hint")
        _choice(self.surface_effect, SURFACE_EFFECTS, "feature.surface_effect")
        _choice(self.priority, PRIORITIES, "feature.priority")
        _confidence(self.confidence, "feature.confidence")
        if self.priority == "required" and self.can_omit:
            raise ValueError(f"Required feature '{self.id}' cannot be omittable.")
        self.anchor.validate()
        self.size.validate()


@dataclass(frozen=True, slots=True)
class SemanticRelation:
    kind: str
    subject_id: str
    object_id: str
    confidence: float

    def validate(self) -> None:
        _choice(self.kind, RELATION_KINDS, "relation.kind")
        _identifier(self.subject_id, "relation.subject_id")
        _identifier(self.object_id, "relation.object_id")
        if self.subject_id == self.object_id:
            raise ValueError("Semantic relation cannot reference the same feature twice.")
        _confidence(self.confidence, "relation.confidence")


@dataclass(frozen=True, slots=True)
class ManufacturingIntent:
    minimum_wall_mm: float
    minimum_feature_mm: float
    maximum_relief_depth_mm: float
    drainage_required: bool
    multicolor_requested: bool

    def validate(self) -> None:
        for label, value in (
            ("manufacturing.minimum_wall_mm", self.minimum_wall_mm),
            ("manufacturing.minimum_feature_mm", self.minimum_feature_mm),
            (
                "manufacturing.maximum_relief_depth_mm",
                self.maximum_relief_depth_mm,
            ),
        ):
            _finite(value, label)
            if value <= 0.0:
                raise ValueError(f"{label} must be positive.")
        if self.maximum_relief_depth_mm >= self.minimum_wall_mm:
            raise ValueError(
                "Maximum relief depth must be smaller than minimum wall thickness."
            )


@dataclass(frozen=True, slots=True)
class Assumption:
    field_path: str
    selected_value: str
    reason: str
    confidence: float
    requires_confirmation: bool

    def validate(self) -> None:
        if not all(
            value.strip()
            for value in (self.field_path, self.selected_value, self.reason)
        ):
            raise ValueError("Assumption text values must not be empty.")
        _confidence(self.confidence, "assumption.confidence")


@dataclass(frozen=True, slots=True)
class Ambiguity:
    field_path: str
    candidates: tuple[str, ...]
    question: str
    blocking: bool

    def validate(self) -> None:
        if not self.field_path.strip() or not self.question.strip():
            raise ValueError("Ambiguity field path and question must not be empty.")
        if len(self.candidates) < 2 or len(set(self.candidates)) != len(
            self.candidates
        ):
            raise ValueError("Ambiguity must contain at least two unique candidates.")
        if any(not candidate.strip() for candidate in self.candidates):
            raise ValueError("Ambiguity candidates must not be empty.")


@dataclass(frozen=True, slots=True)
class DesignSemanticProgram:
    schema_version: str
    id: str
    product_kind: str
    source: SourceIntent
    body: BodyIntent
    features: tuple[FeatureIntent, ...]
    relations: tuple[SemanticRelation, ...]
    manufacturing: ManufacturingIntent
    assumptions: tuple[Assumption, ...]
    ambiguities: tuple[Ambiguity, ...]

    def validate(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"schema_version must be '{SCHEMA_VERSION}', got "
                f"'{self.schema_version}'."
            )
        _identifier(self.id, "program.id")
        _choice(self.product_kind, PRODUCT_KINDS, "program.product_kind")
        self.source.validate()
        self.body.validate()
        self.manufacturing.validate()
        if not self.features:
            raise ValueError("Semantic program requires at least one feature.")
        feature_ids: set[str] = set()
        for feature in self.features:
            feature.validate()
            if feature.id in feature_ids:
                raise ValueError(f"Duplicate feature id '{feature.id}'.")
            feature_ids.add(feature.id)
        relation_keys: set[tuple[str, str, str]] = set()
        for relation in self.relations:
            relation.validate()
            missing = {relation.subject_id, relation.object_id} - feature_ids
            if missing:
                raise ValueError(
                    f"Relation references unknown feature ids {sorted(missing)}."
                )
            key = (relation.kind, relation.subject_id, relation.object_id)
            if key in relation_keys:
                raise ValueError(f"Duplicate semantic relation {key}.")
            relation_keys.add(key)
        for assumption in self.assumptions:
            assumption.validate()
        for ambiguity in self.ambiguities:
            ambiguity.validate()
        if any(ambiguity.blocking for ambiguity in self.ambiguities):
            raise ValueError("Semantic program contains unresolved blocking ambiguity.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
