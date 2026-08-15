from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import unicodedata
from typing import Any

from .semantic_contract import DesignSemanticProgram


COMPLEX_TOPOLOGY_VERSION = "7A.1"
STRUCTURAL_SPAN_VERSION = "7B.1"
NEGATIVE_VOLUME_VERSION = "7C.1"
MULTILEVEL_HIERARCHY_VERSION = "7D.1"
COMPLEX_ACCEPTANCE_VERSION = "7E.1"
VISUAL_INTEGRATION_VERSION = "7E.2"


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.strip().lower())
    return "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )


def _tokens(*values: str) -> set[str]:
    result: set[str] = set()
    for value in values:
        normalized = _normalized(value).replace("-", "_")
        result.add(normalized)
        result.update(part for part in normalized.split("_") if part)
    return result


@dataclass(frozen=True, slots=True)
class ComplexTopologyNode:
    id: str
    role: str
    operation: str
    parent_id: str | None
    level: int

    def validate(self) -> None:
        if not self.id.strip():
            raise ValueError("Complex topology node id must not be empty.")
        if self.role not in {
            "body_attachment",
            "span",
            "branch",
            "terminal",
            "negative_volume",
            "surface_layer",
        }:
            raise ValueError(f"Unsupported complex topology role '{self.role}'.")
        if self.operation not in {"add", "subtract", "mark"}:
            raise ValueError("Complex topology operation is invalid.")
        if self.level < 0:
            raise ValueError("Complex topology level must not be negative.")
        if self.parent_id is None and self.level != 0:
            raise ValueError("Root topology nodes must use level zero.")
        if self.parent_id is not None and self.level < 1:
            raise ValueError("Child topology nodes must use a positive level.")


@dataclass(frozen=True, slots=True)
class ComplexTopologyEdge:
    subject_id: str
    object_id: str
    kind: str

    def validate(self) -> None:
        if self.subject_id == self.object_id:
            raise ValueError("Complex topology edge cannot be self-referential.")
        if self.kind not in {
            "attached_to",
            "contains",
            "bridges",
            "branches_from",
            "mirrors",
            "repeats",
        }:
            raise ValueError(f"Unsupported complex topology edge '{self.kind}'.")


@dataclass(frozen=True, slots=True)
class ComplexCompositionPlan:
    topology_version: str
    span_version: str
    negative_volume_version: str
    hierarchy_version: str
    acceptance_version: str
    source_program_id: str
    profile: str
    nodes: tuple[ComplexTopologyNode, ...]
    edges: tuple[ComplexTopologyEdge, ...]
    maximum_depth: int
    span_count: int
    branch_count: int
    negative_volume_count: int

    def validate(self) -> None:
        versions = (
            (self.topology_version, COMPLEX_TOPOLOGY_VERSION),
            (self.span_version, STRUCTURAL_SPAN_VERSION),
            (self.negative_volume_version, NEGATIVE_VOLUME_VERSION),
            (self.hierarchy_version, MULTILEVEL_HIERARCHY_VERSION),
            (self.acceptance_version, COMPLEX_ACCEPTANCE_VERSION),
        )
        if any(actual != expected for actual, expected in versions):
            raise ValueError("Unexpected complex-composition version.")
        if self.profile not in {
            "surface_only",
            "spanning_frame",
            "branching_network",
            "nested_negative",
            "hybrid_complex",
        }:
            raise ValueError("Unknown complex-composition profile.")
        identifiers = {node.id for node in self.nodes}
        if len(identifiers) != len(self.nodes):
            raise ValueError("Complex topology node ids must be unique.")
        for node in self.nodes:
            node.validate()
            if node.parent_id not in identifiers | {None}:
                raise ValueError("Complex topology node references an unknown parent.")
        for edge in self.edges:
            edge.validate()
            if {edge.subject_id, edge.object_id} - identifiers:
                raise ValueError("Complex topology edge references unknown nodes.")
        measured_depth = max((node.level for node in self.nodes), default=0)
        if measured_depth != self.maximum_depth:
            raise ValueError("Complex topology depth report is inconsistent.")
        if self.span_count != sum(node.role == "span" for node in self.nodes):
            raise ValueError("Complex topology span count is inconsistent.")
        if self.branch_count != sum(node.role == "branch" for node in self.nodes):
            raise ValueError("Complex topology branch count is inconsistent.")
        if self.negative_volume_count != sum(
            node.role == "negative_volume" for node in self.nodes
        ):
            raise ValueError("Complex topology negative-volume count is inconsistent.")

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


class ComplexCompositionResolver:
    """Build a product-agnostic topology graph from semantic relationships."""

    _SPAN = frozenset({"arch", "arco", "bridge", "puente", "handle", "asa"})
    _BRANCH = frozenset(
        {"branch", "rama", "stem", "tallo", "trunk", "tronco", "arm"}
    )
    _TERMINAL = frozenset(
        {"bud", "brote", "flower", "flor", "tip", "punta", "node", "nodo"}
    )
    _SURFACE = frozenset(
        {"text", "texto", "logo", "svg", "image", "imagen", "relief", "relieve"}
    )

    @classmethod
    def resolve(cls, program: DesignSemanticProgram) -> ComplexCompositionPlan:
        program.validate()
        feature_by_id = {feature.id: feature for feature in program.features}
        parents = cls._parent_map(program)
        levels = cls._levels(feature_by_id, parents)
        nodes: list[ComplexTopologyNode] = []
        for feature in program.features:
            tokens = _tokens(feature.id, feature.concept, feature.form_hint)
            operation = (
                "subtract"
                if feature.surface_effect in {"recessed", "cutout"}
                else "mark"
                if feature.surface_effect == "marking"
                else "add"
            )
            if operation == "subtract":
                role = "negative_volume"
            elif tokens & cls._SPAN or feature.form_hint == "arch":
                role = "span"
            elif tokens & cls._BRANCH:
                role = "branch"
            elif tokens & cls._TERMINAL:
                role = "terminal"
            elif tokens & cls._SURFACE or feature.form_hint == "text":
                role = "surface_layer"
            else:
                role = "body_attachment"
            nodes.append(
                ComplexTopologyNode(
                    id=feature.id,
                    role=role,
                    operation=operation,
                    parent_id=parents.get(feature.id),
                    level=levels[feature.id],
                )
            )

        edges: list[ComplexTopologyEdge] = []
        node_roles = {node.id: node.role for node in nodes}
        for child_id, parent_id in parents.items():
            if node_roles[child_id] == "negative_volume":
                kind = "contains"
            elif node_roles[child_id] in {"branch", "terminal"}:
                kind = "branches_from"
            elif node_roles[child_id] == "span":
                kind = "bridges"
            else:
                kind = "attached_to"
            edges.append(ComplexTopologyEdge(child_id, parent_id, kind))
        for relation in program.relations:
            if relation.kind == "mirror_of":
                edges.append(
                    ComplexTopologyEdge(
                        relation.subject_id, relation.object_id, "mirrors"
                    )
                )
            elif relation.kind == "repeated_from":
                edges.append(
                    ComplexTopologyEdge(
                        relation.subject_id, relation.object_id, "repeats"
                    )
                )

        span_count = sum(node.role == "span" for node in nodes)
        branch_count = sum(node.role == "branch" for node in nodes)
        negative_count = sum(node.role == "negative_volume" for node in nodes)
        maximum_depth = max(levels.values(), default=0)
        if branch_count and maximum_depth >= 2:
            profile = "branching_network"
        elif negative_count and maximum_depth >= 2:
            profile = "nested_negative"
        elif span_count and negative_count and maximum_depth >= 1:
            profile = "spanning_frame"
        elif span_count or branch_count or negative_count:
            profile = "hybrid_complex"
        else:
            profile = "surface_only"
        result = ComplexCompositionPlan(
            topology_version=COMPLEX_TOPOLOGY_VERSION,
            span_version=STRUCTURAL_SPAN_VERSION,
            negative_volume_version=NEGATIVE_VOLUME_VERSION,
            hierarchy_version=MULTILEVEL_HIERARCHY_VERSION,
            acceptance_version=COMPLEX_ACCEPTANCE_VERSION,
            source_program_id=program.id,
            profile=profile,
            nodes=tuple(nodes),
            edges=tuple(edges),
            maximum_depth=maximum_depth,
            span_count=span_count,
            branch_count=branch_count,
            negative_volume_count=negative_count,
        )
        result.validate()
        return result

    @staticmethod
    def _parent_map(program: DesignSemanticProgram) -> dict[str, str]:
        by_id = {feature.id: feature for feature in program.features}
        parents: dict[str, str] = {}
        for relation in program.relations:
            if relation.kind not in {"centered_on", "attached_to", "contained_by"}:
                continue
            subject = by_id[relation.subject_id]
            target = by_id[relation.object_id]
            if relation.kind == "centered_on":
                subject_area = subject.size.width_ratio * subject.size.height_ratio
                target_area = target.size.width_ratio * target.size.height_ratio
                if subject_area >= target_area:
                    continue
            parents[subject.id] = target.id
        return parents

    @staticmethod
    def _levels(
        feature_by_id: dict[str, Any], parents: dict[str, str]
    ) -> dict[str, int]:
        levels: dict[str, int] = {}

        def level(feature_id: str, visiting: set[str]) -> int:
            if feature_id in levels:
                return levels[feature_id]
            if feature_id in visiting:
                raise ValueError("Complex topology contains a parent cycle.")
            parent = parents.get(feature_id)
            if parent is None:
                value = 0
            else:
                if parent not in feature_by_id:
                    raise ValueError("Complex topology references an unknown parent.")
                value = 1 + level(parent, visiting | {feature_id})
            levels[feature_id] = value
            return value

        for feature_id in feature_by_id:
            level(feature_id, set())
        return levels


class ComplexCompositionCompiler:
    """Attach the accepted topology contract to Motor DOBO JSON."""

    @staticmethod
    def apply(
        motor_program: dict[str, Any], plan: ComplexCompositionPlan
    ) -> None:
        plan.validate()
        motor_program["complex_composition"] = plan.to_dict()
        if plan.profile != "surface_only":
            voxel = float(motor_program["grid"]["voxel_mm"])
            reserve = max(8.0, 10.0 * voxel)
            for axis in (0, 1):
                motor_program["grid"]["minimum"][axis] = (
                    float(motor_program["grid"]["minimum"][axis]) - reserve
                )
                motor_program["grid"]["maximum"][axis] = (
                    float(motor_program["grid"]["maximum"][axis]) + reserve
                )
            motor_program["grid"]["maximum"][2] = (
                float(motor_program["grid"]["maximum"][2]) + reserve
            )
