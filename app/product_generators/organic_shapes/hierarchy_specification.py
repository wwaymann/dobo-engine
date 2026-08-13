from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .adaptive_refinement import AdaptiveFeatureRefinementContract
from .feature_program_specification import FeatureInstruction, FeatureProgramParser
from .specification import _object, _vector3
from .surface_anchoring import SurfaceAnchorSpec
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
    surface_anchor: SurfaceAnchorSpec | None = None

    def validate(self) -> None:
        if not self.id.strip():
            raise ValueError("Hierarchy node id must not be empty.")
        if self.mirror_axis not in {None, "x", "y", "z"}:
            raise ValueError("Hierarchy mirror_axis must be x, y or z.")
        self.transform.validate()
        self.repeat.validate()
        if self.surface_anchor is not None:
            self.surface_anchor.validate()
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
    adaptive_refinement: AdaptiveFeatureRefinementContract | None = None

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
        if self.adaptive_refinement is not None:
            self.adaptive_refinement.validate()


class HierarchicalFeatureParser:
    def parse_file(self, path: str | Path) -> HierarchicalFeatureSpecification:
        source = Path(path).resolve()
        return self.parse_dict(json.loads(source.read_text(encoding="utf-8")))

    def parse_dict(self, data: dict[str, Any]) -> HierarchicalFeatureSpecification:
        vessel = OrganicVesselParser().parse_dict(data)
        program = _object(data, "hierarchy_program")
        raw_templates = program.get("templates")
        raw_roots = program.get("roots")
        raw_adaptive = program.get("adaptive_refinement")
        if not isinstance(raw_templates, list) or not all(
            isinstance(item, dict) for item in raw_templates
        ):
            raise TypeError("hierarchy_program.templates must be an array of objects.")
        if not isinstance(raw_roots, list) or not all(
            isinstance(item, dict) for item in raw_roots
        ):
            raise TypeError("hierarchy_program.roots must be an array of objects.")
        if raw_adaptive is not None and not isinstance(raw_adaptive, dict):
            raise TypeError("hierarchy_program.adaptive_refinement must be an object.")
        specification = HierarchicalFeatureSpecification(
            vessel_specification=vessel,
            templates=tuple(
                FeatureProgramParser._feature(item) for item in raw_templates
            ),
            roots=tuple(self._node(item) for item in raw_roots),
            adaptive_refinement=(
                AdaptiveFeatureRefinementContract(
                    surface_band_mm=float(raw_adaptive["surface_band_mm"]),
                    size_band_ratio=float(raw_adaptive["size_band_ratio"]),
                    maximum_band_mm=float(raw_adaptive["maximum_band_mm"]),
                    small_feature_threshold_mm=float(
                        raw_adaptive["small_feature_threshold_mm"]
                    ),
                    detail_subdivision_passes=int(
                        raw_adaptive["detail_subdivision_passes"]
                    ),
                )
                if raw_adaptive is not None
                else None
            ),
        )
        specification.validate()
        return specification

    @classmethod
    def _node(cls, data: dict[str, Any]) -> HierarchyNode:
        raw_transform = data.get("transform", {})
        raw_repeat = data.get("repeat", {})
        raw_children = data.get("children", [])
        raw_anchor = data.get("surface_anchor")
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
        if raw_anchor is not None and not isinstance(raw_anchor, dict):
            raise TypeError("Hierarchy surface_anchor must be an object.")
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
            surface_anchor=(
                SurfaceAnchorSpec(
                    azimuth_degrees=float(raw_anchor["azimuth_degrees"]),
                    height_ratio=float(raw_anchor["height_ratio"]),
                    offset_mm=float(raw_anchor.get("offset_mm", 0.0)),
                    roll_degrees=float(raw_anchor.get("roll_degrees", 0.0)),
                )
                if raw_anchor is not None
                else None
            ),
            children=tuple(cls._node(item) for item in raw_children),
        )
