from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .feature_program_specification import FeatureInstruction, FeatureProgramParser
from .specification import _object, _vector3
from .vessel_specification import OrganicVesselParser, OrganicVesselSpecification


@dataclass(frozen=True, slots=True)
class TransformSpec:
    translate: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotate_degrees: tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: tuple[float, float, float] = (1.0, 1.0, 1.0)

    def validate(self) -> None:
        if any(abs(value) <= 1e-9 for value in self.scale):
            raise ValueError("Hierarchy transform scale components must be non-zero.")


@dataclass(frozen=True, slots=True)
class RepeatSpec:
    count: int = 1
    translate_step: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotate_step_degrees: tuple[float, float, float] = (0.0, 0.0, 0.0)

    def validate(self) -> None:
        if not 1 <= self.count <= 32:
            raise ValueError("Hierarchy repeat count must be between 1 and 32.")


@dataclass(frozen=True, slots=True)
class HierarchyNode:
    id: str
    template_ids: tuple[str, ...]
    transform: TransformSpec
    repeat: RepeatSpec
    mirror_axis: str | None
    children: tuple["HierarchyNode", ...]

    def validate(self) -> None:
        if not self.id.strip():
            raise ValueError("Hierarchy node id must not be empty.")
        if self.mirror_axis not in {None, "x", "y", "z"}:
            raise ValueError("Hierarchy mirror_axis must be x, y or z.")
        self.transform.validate()
        self.repeat.validate()
        if not self.template_ids and not self.children:
            raise ValueError(f"Hierarchy node '{self.id}' is empty.")
        child_ids: set[str] = set()
        for child in self.children:
            child.validate()
            if child.id in child_ids:
                raise ValueError(
                    f"Duplicate child id '{child.id}' under hierarchy node '{self.id}'."
                )
            child_ids.add(child.id)


@dataclass(frozen=True, slots=True)
class HierarchicalFeatureSpecification:
    vessel_specification: OrganicVesselSpecification
    templates: tuple[FeatureInstruction, ...]
    roots: tuple[HierarchyNode, ...]

    def __getattr__(self, name: str):
        return getattr(self.vessel_specification, name)

    def validate(self) -> None:
        self.vessel_specification.validate()
        if not self.templates or not self.roots:
            raise ValueError("Hierarchy requires templates and root nodes.")
        template_ids: set[str] = set()
        for template in self.templates:
            template.validate()
            if template.id in template_ids:
                raise ValueError(f"Duplicate hierarchy template id '{template.id}'.")
            template_ids.add(template.id)

        def validate_references(node: HierarchyNode) -> None:
            missing = set(node.template_ids) - template_ids
            if missing:
                raise ValueError(
                    f"Hierarchy node '{node.id}' references unknown templates {sorted(missing)}."
                )
            for child in node.children:
                validate_references(child)

        root_ids: set[str] = set()
        for root in self.roots:
            root.validate()
            if root.id in root_ids:
                raise ValueError(f"Duplicate hierarchy root id '{root.id}'.")
            root_ids.add(root.id)
            validate_references(root)


class HierarchicalFeatureParser:
    def parse_file(self, path: str | Path) -> HierarchicalFeatureSpecification:
        source = Path(path).resolve()
        return self.parse_dict(json.loads(source.read_text(encoding="utf-8")))

    def parse_dict(self, data: dict[str, Any]) -> HierarchicalFeatureSpecification:
        vessel = OrganicVesselParser().parse_dict(data)
        program = _object(data, "hierarchy_program")
        raw_templates = program.get("templates")
        raw_roots = program.get("roots")
        if not isinstance(raw_templates, list) or not all(
            isinstance(item, dict) for item in raw_templates
        ):
            raise TypeError("hierarchy_program.templates must be an array of objects.")
        if not isinstance(raw_roots, list) or not all(
            isinstance(item, dict) for item in raw_roots
        ):
            raise TypeError("hierarchy_program.roots must be an array of objects.")
        specification = HierarchicalFeatureSpecification(
            vessel_specification=vessel,
            templates=tuple(
                FeatureProgramParser._feature(item) for item in raw_templates
            ),
            roots=tuple(self._node(item) for item in raw_roots),
        )
        specification.validate()
        return specification

    @classmethod
    def _node(cls, data: dict[str, Any]) -> HierarchyNode:
        raw_transform = data.get("transform", {})
        raw_repeat = data.get("repeat", {})
        raw_children = data.get("children", [])
        template_ids = data.get("template_ids", [])
        if not isinstance(raw_transform, dict) or not isinstance(raw_repeat, dict):
            raise TypeError("Hierarchy transform and repeat values must be objects.")
        if not isinstance(raw_children, list) or not all(
            isinstance(item, dict) for item in raw_children
        ):
            raise TypeError("Hierarchy node children must be an array of objects.")
        if not isinstance(template_ids, list) or not all(
            isinstance(item, str) for item in template_ids
        ):
            raise TypeError("Hierarchy template_ids must be an array of strings.")
        return HierarchyNode(
            id=str(data["id"]),
            template_ids=tuple(template_ids),
            transform=TransformSpec(
                translate=_vector3(
                    raw_transform.get("translate", [0.0, 0.0, 0.0]),
                    "hierarchy.transform.translate",
                ),
                rotate_degrees=_vector3(
                    raw_transform.get("rotate_degrees", [0.0, 0.0, 0.0]),
                    "hierarchy.transform.rotate_degrees",
                ),
                scale=_vector3(
                    raw_transform.get("scale", [1.0, 1.0, 1.0]),
                    "hierarchy.transform.scale",
                ),
            ),
            repeat=RepeatSpec(
                count=int(raw_repeat.get("count", 1)),
                translate_step=_vector3(
                    raw_repeat.get("translate_step", [0.0, 0.0, 0.0]),
                    "hierarchy.repeat.translate_step",
                ),
                rotate_step_degrees=_vector3(
                    raw_repeat.get("rotate_step_degrees", [0.0, 0.0, 0.0]),
                    "hierarchy.repeat.rotate_step_degrees",
                ),
            ),
            mirror_axis=(
                str(data["mirror_axis"]) if data.get("mirror_axis") is not None else None
            ),
            children=tuple(cls._node(item) for item in raw_children),
        )
