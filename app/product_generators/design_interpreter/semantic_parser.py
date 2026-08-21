from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .semantic_contract import (
    Ambiguity,
    Assumption,
    BodyIntent,
    DesignSemanticProgram,
    FeatureIntent,
    FeatureSizeIntent,
    ManufacturingIntent,
    SemanticAnchor,
    SemanticRelation,
    SourceIntent,
)


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be an object.")
    return value


def _objects(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise TypeError(f"{label} must be an array of objects.")
    return value


def _strings(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise TypeError(f"{label} must be an array of strings.")
    return tuple(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a string.")
    return value


def _nullable_string(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _string(value, label)


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be a number.")
    return float(value)


def _boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{label} must be a boolean.")
    return value


def _only(data: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = set(data) - allowed
    missing = allowed - set(data)
    if unknown:
        raise ValueError(f"{label} contains unknown fields {sorted(unknown)}.")
    if missing:
        raise ValueError(f"{label} is missing fields {sorted(missing)}.")


class SemanticProgramParser:
    def parse_file(self, path: str | Path) -> DesignSemanticProgram:
        source = Path(path).resolve()
        return self.parse_dict(json.loads(source.read_text(encoding="utf-8")))

    def parse_dict(self, value: dict[str, Any]) -> DesignSemanticProgram:
        data = _object(value, "semantic program")
        _only(
            data,
            {
                "schema_version",
                "id",
                "product_kind",
                "source",
                "body",
                "features",
                "relations",
                "manufacturing",
                "assumptions",
                "ambiguities",
            },
            "semantic program",
        )
        source = _object(data["source"], "source")
        _only(source, {"kind", "prompt", "image_reference"}, "source")
        body = _object(data["body"], "body")
        _only(
            body,
            {
                "family",
                "height_mm",
                "width_mm",
                "depth_mm",
                "opening_shape",
                "opening_width_ratio",
                "opening_depth_ratio",
                "style_tags",
            },
            "body",
        )
        manufacturing = _object(data["manufacturing"], "manufacturing")
        _only(
            manufacturing,
            {
                "minimum_wall_mm",
                "minimum_feature_mm",
                "maximum_relief_depth_mm",
                "drainage_required",
                "multicolor_requested",
            },
            "manufacturing",
        )
        program = DesignSemanticProgram(
            schema_version=_string(data["schema_version"], "schema_version"),
            id=_string(data["id"], "id"),
            product_kind=_string(data["product_kind"], "product_kind"),
            source=SourceIntent(
                kind=_string(source["kind"], "source.kind"),
                prompt=_nullable_string(source["prompt"], "source.prompt"),
                image_reference=_nullable_string(
                    source["image_reference"], "source.image_reference"
                ),
            ),
            body=BodyIntent(
                family=_string(body["family"], "body.family"),
                height_mm=_number(body["height_mm"], "body.height_mm"),
                width_mm=_number(body["width_mm"], "body.width_mm"),
                depth_mm=_number(body["depth_mm"], "body.depth_mm"),
                opening_shape=_string(
                    body["opening_shape"], "body.opening_shape"
                ),
                opening_width_ratio=_number(
                    body["opening_width_ratio"], "body.opening_width_ratio"
                ),
                opening_depth_ratio=_number(
                    body["opening_depth_ratio"], "body.opening_depth_ratio"
                ),
                style_tags=_strings(body["style_tags"], "body.style_tags"),
            ),
            features=tuple(self._feature(item) for item in _objects(data["features"], "features")),
            relations=tuple(self._relation(item) for item in _objects(data["relations"], "relations")),
            manufacturing=ManufacturingIntent(
                minimum_wall_mm=_number(
                    manufacturing["minimum_wall_mm"],
                    "manufacturing.minimum_wall_mm",
                ),
                minimum_feature_mm=_number(
                    manufacturing["minimum_feature_mm"],
                    "manufacturing.minimum_feature_mm",
                ),
                maximum_relief_depth_mm=_number(
                    manufacturing["maximum_relief_depth_mm"],
                    "manufacturing.maximum_relief_depth_mm",
                ),
                drainage_required=_boolean(
                    manufacturing["drainage_required"],
                    "manufacturing.drainage_required",
                ),
                multicolor_requested=_boolean(
                    manufacturing["multicolor_requested"],
                    "manufacturing.multicolor_requested",
                ),
            ),
            assumptions=tuple(self._assumption(item) for item in _objects(data["assumptions"], "assumptions")),
            ambiguities=tuple(self._ambiguity(item) for item in _objects(data["ambiguities"], "ambiguities")),
        )
        program.validate()
        return program

    @staticmethod
    def _feature(data: dict[str, Any]) -> FeatureIntent:
        _only(
            data,
            {"id", "concept", "form_hint", "surface_effect", "anchor", "size", "priority", "can_omit", "confidence"},
            "feature",
        )
        anchor = _object(data["anchor"], "feature.anchor")
        size = _object(data["size"], "feature.size")
        _only(anchor, {"region", "horizontal", "vertical", "roll_degrees"}, "feature.anchor")
        _only(size, {"width_ratio", "height_ratio", "depth_mm"}, "feature.size")
        return FeatureIntent(
            id=_string(data["id"], "feature.id"),
            concept=_string(data["concept"], "feature.concept"),
            form_hint=_string(data["form_hint"], "feature.form_hint"),
            surface_effect=_string(
                data["surface_effect"], "feature.surface_effect"
            ),
            anchor=SemanticAnchor(
                region=_string(anchor["region"], "feature.anchor.region"),
                horizontal=_number(
                    anchor["horizontal"], "feature.anchor.horizontal"
                ),
                vertical=_number(anchor["vertical"], "feature.anchor.vertical"),
                roll_degrees=_number(
                    anchor["roll_degrees"], "feature.anchor.roll_degrees"
                ),
            ),
            size=FeatureSizeIntent(
                width_ratio=_number(
                    size["width_ratio"], "feature.size.width_ratio"
                ),
                height_ratio=_number(
                    size["height_ratio"], "feature.size.height_ratio"
                ),
                depth_mm=_number(size["depth_mm"], "feature.size.depth_mm"),
            ),
            priority=_string(data["priority"], "feature.priority"),
            can_omit=_boolean(data["can_omit"], "feature.can_omit"),
            confidence=_number(data["confidence"], "feature.confidence"),
        )

    @staticmethod
    def _relation(data: dict[str, Any]) -> SemanticRelation:
        _only(data, {"kind", "subject_id", "object_id", "confidence"}, "relation")
        return SemanticRelation(
            kind=_string(data["kind"], "relation.kind"),
            subject_id=_string(data["subject_id"], "relation.subject_id"),
            object_id=_string(data["object_id"], "relation.object_id"),
            confidence=_number(data["confidence"], "relation.confidence"),
        )

    @staticmethod
    def _assumption(data: dict[str, Any]) -> Assumption:
        _only(data, {"field_path", "selected_value", "reason", "confidence", "requires_confirmation"}, "assumption")
        return Assumption(
            field_path=_string(data["field_path"], "assumption.field_path"),
            selected_value=_string(
                data["selected_value"], "assumption.selected_value"
            ),
            reason=_string(data["reason"], "assumption.reason"),
            confidence=_number(data["confidence"], "assumption.confidence"),
            requires_confirmation=_boolean(
                data["requires_confirmation"],
                "assumption.requires_confirmation",
            ),
        )

    @staticmethod
    def _ambiguity(data: dict[str, Any]) -> Ambiguity:
        _only(data, {"field_path", "candidates", "question", "blocking"}, "ambiguity")
        return Ambiguity(
            field_path=_string(data["field_path"], "ambiguity.field_path"),
            candidates=_strings(data["candidates"], "ambiguity.candidates"),
            question=_string(data["question"], "ambiguity.question"),
            blocking=_boolean(data["blocking"], "ambiguity.blocking"),
        )
