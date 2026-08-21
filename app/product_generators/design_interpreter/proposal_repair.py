from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
from typing import Any

from .semantic_compiler import (
    SemanticCompilationResult,
    SemanticToMotorCompiler,
)
from .semantic_contract import DesignSemanticProgram, FeatureIntent
from .semantic_parser import SemanticProgramParser


REPAIR_VERSION = "3E.1"


@dataclass(frozen=True, slots=True)
class ProposalValidationSnapshot:
    surface_anchor_failures: tuple[str, ...]
    layout_failures: tuple[str, ...]
    manufacturability_failures: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not (
            self.surface_anchor_failures
            or self.layout_failures
            or self.manufacturability_failures
        )

    @property
    def failures(self) -> tuple[str, ...]:
        return (
            *self.surface_anchor_failures,
            *self.layout_failures,
            *self.manufacturability_failures,
        )


@dataclass(frozen=True, slots=True)
class SemanticRepairAction:
    field_path: str
    before: str
    after: str
    reason: str


@dataclass(frozen=True, slots=True)
class SemanticRepairReport:
    repair_version: str
    attempts: int
    actions: tuple[SemanticRepairAction, ...]
    before: ProposalValidationSnapshot
    after: ProposalValidationSnapshot
    confirmation_fields: tuple[str, ...]
    ambiguity_questions: tuple[str, ...]

    @property
    def changed(self) -> bool:
        return bool(self.actions)

    @property
    def ready_for_compilation(self) -> bool:
        return self.after.valid

    def validate(self) -> None:
        if self.repair_version != REPAIR_VERSION:
            raise RuntimeError("Unexpected semantic repair version.")
        if not self.after.valid:
            raise RuntimeError(
                f"Semantic proposal repair failed: {list(self.after.failures)}"
            )


@dataclass(frozen=True, slots=True)
class SemanticRepairResult:
    program: DesignSemanticProgram
    compilation: SemanticCompilationResult
    report: SemanticRepairReport

    def write_program(self, path: str | Path) -> Path:
        target = Path(path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.program.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return target

    def write_report(self, path: str | Path) -> Path:
        target = Path(path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(asdict(self.report), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return target


class SemanticProposalRepairer:
    """Validate and deterministically repair a semantic proposal before 3B."""

    def __init__(
        self,
        *,
        maximum_attempts: int = 18,
        vertical_step: float = 0.035,
        size_scale: float = 0.88,
    ) -> None:
        if not 1 <= maximum_attempts <= 64:
            raise ValueError("maximum_attempts must be between 1 and 64.")
        if not 0.0 < vertical_step <= 0.2:
            raise ValueError("vertical_step must be in (0, 0.2].")
        if not 0.5 <= size_scale < 1.0:
            raise ValueError("size_scale must be in [0.5, 1.0).")
        self.maximum_attempts = maximum_attempts
        self.vertical_step = vertical_step
        self.size_scale = size_scale

    def repair_file(self, path: str | Path) -> SemanticRepairResult:
        source = Path(path).resolve()
        return self.repair_dict(json.loads(source.read_text(encoding="utf-8")))

    def repair_dict(self, value: dict[str, Any]) -> SemanticRepairResult:
        normalized, actions = self._normalize_raw(value)
        program = SemanticProgramParser().parse_dict(normalized)
        return self.repair(program, initial_actions=actions)

    def repair(
        self,
        program: DesignSemanticProgram,
        *,
        initial_actions: tuple[SemanticRepairAction, ...] = (),
    ) -> SemanticRepairResult:
        program.validate()
        candidate = program
        actions = list(initial_actions)
        before, compilation = self._evaluate(candidate)
        current = before
        attempts = 0
        for attempts in range(1, self.maximum_attempts + 1):
            if current.valid:
                attempts -= 1
                break
            repaired, new_actions = self._repair_once(candidate, current)
            if not new_actions:
                break
            candidate = repaired
            actions.extend(new_actions)
            current, compilation = self._evaluate(candidate)
        if not current.valid:
            raise RuntimeError(
                "Proposal contains failures that deterministic repair cannot "
                f"resolve: {list(current.failures)}"
            )
        confirmations = tuple(
            sorted(
                {
                    assumption.field_path
                    for assumption in candidate.assumptions
                    if assumption.requires_confirmation
                }
            )
        )
        questions = tuple(
            ambiguity.question for ambiguity in candidate.ambiguities
        )
        report = SemanticRepairReport(
            repair_version=REPAIR_VERSION,
            attempts=attempts,
            actions=tuple(actions),
            before=before,
            after=current,
            confirmation_fields=confirmations,
            ambiguity_questions=questions,
        )
        report.validate()
        return SemanticRepairResult(
            program=candidate,
            compilation=compilation,
            report=report,
        )

    @staticmethod
    def _evaluate(
        program: DesignSemanticProgram,
    ) -> tuple[ProposalValidationSnapshot, SemanticCompilationResult]:
        from product_generators.organic_shapes.hierarchy_engine import (
            HierarchicalFeatureVesselEngine,
        )
        from product_generators.organic_shapes.hierarchy_specification import (
            HierarchicalFeatureParser,
        )

        compilation = SemanticToMotorCompiler.compile(program)
        specification = HierarchicalFeatureParser().parse_dict(
            compilation.motor_program
        )
        anchors = HierarchicalFeatureVesselEngine.surface_anchor_checks(
            specification
        )
        layout = HierarchicalFeatureVesselEngine.layout_report(specification)
        manufacturing = (
            HierarchicalFeatureVesselEngine.feature_manufacturability_report(
                specification
            )
        )
        return (
            ProposalValidationSnapshot(
                surface_anchor_failures=tuple(
                    name for name, passed in anchors.items() if not passed
                ),
                layout_failures=tuple(
                    name for name, passed in layout.checks.items() if not passed
                ),
                manufacturability_failures=tuple(
                    name
                    for name, passed in manufacturing.checks.items()
                    if not passed
                ),
            ),
            compilation,
        )

    def _repair_once(
        self,
        program: DesignSemanticProgram,
        snapshot: ProposalValidationSnapshot,
    ) -> tuple[DesignSemanticProgram, tuple[SemanticRepairAction, ...]]:
        by_id = {feature.id: feature for feature in program.features}
        changes: dict[str, dict[str, bool]] = {}

        def request(feature_id: str, operation: str) -> None:
            if feature_id in by_id:
                changes.setdefault(feature_id, {})[operation] = True

        for failure in snapshot.layout_failures:
            if failure.startswith("pair/"):
                pair = failure.removeprefix("pair/").split("/", 1)[0]
                first, second = pair.split("--", 1)
                request(first, "shrink")
                request(second, "shrink")
                continue
            feature_id = self._failure_feature_id(failure)
            if failure.endswith("/opening_clearance"):
                request(feature_id, "lower")
            elif failure.endswith("/base_clearance"):
                request(feature_id, "raise")
            elif failure.endswith("/inside_grid"):
                request(feature_id, "shrink")

        for failure in snapshot.manufacturability_failures:
            feature_id = self._failure_feature_id(failure)
            if failure.endswith("/maximum_depth") or failure.endswith(
                "/wall_reserve"
            ):
                request(feature_id, "reduce_depth")
            elif failure.endswith("/minimum_depth"):
                request(feature_id, "increase_depth")
            elif failure.endswith("/minimum_feature"):
                request(feature_id, "grow")

        features: list[FeatureIntent] = []
        actions: list[SemanticRepairAction] = []
        for index, feature in enumerate(program.features):
            operations = changes.get(feature.id, {})
            anchor = feature.anchor
            size = feature.size
            if operations.get("lower"):
                value = max(0.0, anchor.vertical - self.vertical_step)
                if value != anchor.vertical:
                    actions.append(
                        self._action(
                            f"features[{index}].anchor.vertical",
                            anchor.vertical,
                            value,
                            "move feature below the vessel opening clearance",
                        )
                    )
                    anchor = replace(anchor, vertical=value)
            if operations.get("raise"):
                value = min(1.0, anchor.vertical + self.vertical_step)
                if value != anchor.vertical:
                    actions.append(
                        self._action(
                            f"features[{index}].anchor.vertical",
                            anchor.vertical,
                            value,
                            "move feature above the vessel base clearance",
                        )
                    )
                    anchor = replace(anchor, vertical=value)
            if operations.get("shrink"):
                minimum_width = min(
                    1.0,
                    1.05
                    * program.manufacturing.minimum_feature_mm
                    / program.body.width_mm,
                )
                minimum_height = min(
                    1.0,
                    1.05
                    * program.manufacturing.minimum_feature_mm
                    / program.body.height_mm,
                )
                width = max(minimum_width, size.width_ratio * self.size_scale)
                height = max(minimum_height, size.height_ratio * self.size_scale)
                if width != size.width_ratio:
                    actions.append(
                        self._action(
                            f"features[{index}].size.width_ratio",
                            size.width_ratio,
                            width,
                            "reduce a conflicting feature footprint",
                        )
                    )
                if height != size.height_ratio:
                    actions.append(
                        self._action(
                            f"features[{index}].size.height_ratio",
                            size.height_ratio,
                            height,
                            "reduce a conflicting feature footprint",
                        )
                    )
                size = replace(size, width_ratio=width, height_ratio=height)
            if operations.get("grow"):
                width = max(
                    size.width_ratio,
                    1.1
                    * program.manufacturing.minimum_feature_mm
                    / program.body.width_mm,
                )
                height = max(
                    size.height_ratio,
                    1.1
                    * program.manufacturing.minimum_feature_mm
                    / program.body.height_mm,
                )
                if width != size.width_ratio:
                    actions.append(
                        self._action(
                            f"features[{index}].size.width_ratio",
                            size.width_ratio,
                            width,
                            "increase feature width to the manufacturing minimum",
                        )
                    )
                if height != size.height_ratio:
                    actions.append(
                        self._action(
                            f"features[{index}].size.height_ratio",
                            size.height_ratio,
                            height,
                            "increase feature height to the manufacturing minimum",
                        )
                    )
                size = replace(size, width_ratio=width, height_ratio=height)
            if operations.get("reduce_depth"):
                depth = min(
                    size.depth_mm,
                    0.95 * program.manufacturing.maximum_relief_depth_mm,
                    0.8 * program.manufacturing.minimum_wall_mm,
                )
                if depth != size.depth_mm:
                    actions.append(
                        self._action(
                            f"features[{index}].size.depth_mm",
                            size.depth_mm,
                            depth,
                            "preserve wall reserve and maximum relief depth",
                        )
                    )
                    size = replace(size, depth_mm=depth)
            if operations.get("increase_depth"):
                depth = max(
                    size.depth_mm,
                    min(
                        0.8,
                        0.5 * program.manufacturing.maximum_relief_depth_mm,
                    ),
                )
                if depth != size.depth_mm:
                    actions.append(
                        self._action(
                            f"features[{index}].size.depth_mm",
                            size.depth_mm,
                            depth,
                            "increase relief depth to the manufacturing minimum",
                        )
                    )
                size = replace(size, depth_mm=depth)
            features.append(replace(feature, anchor=anchor, size=size))
        return replace(program, features=tuple(features)), tuple(actions)

    @staticmethod
    def _failure_feature_id(failure: str) -> str:
        if not failure.startswith("root/"):
            return ""
        node = failure.split("/", 2)[1]
        return node.split("[", 1)[0].split(".mirror_", 1)[0]

    @staticmethod
    def _action(
        path: str, before: Any, after: Any, reason: str
    ) -> SemanticRepairAction:
        return SemanticRepairAction(
            field_path=path,
            before=str(before),
            after=str(after),
            reason=reason,
        )

    @classmethod
    def _normalize_raw(
        cls, value: dict[str, Any]
    ) -> tuple[dict[str, Any], tuple[SemanticRepairAction, ...]]:
        if not isinstance(value, dict):
            raise TypeError("semantic proposal must be an object.")
        data = deepcopy(value)
        actions: list[SemanticRepairAction] = []
        manufacturing = data.get("manufacturing")
        if isinstance(manufacturing, dict):
            wall = manufacturing.get("minimum_wall_mm")
            relief = manufacturing.get("maximum_relief_depth_mm")
            if (
                isinstance(wall, (int, float))
                and not isinstance(wall, bool)
                and wall > 0.0
                and isinstance(relief, (int, float))
                and not isinstance(relief, bool)
                and relief >= wall
            ):
                repaired = max(0.1, min(0.75 * wall, wall - 0.1))
                manufacturing["maximum_relief_depth_mm"] = repaired
                actions.append(
                    cls._action(
                        "manufacturing.maximum_relief_depth_mm",
                        relief,
                        repaired,
                        "keep maximum relief below wall thickness",
                    )
                )
        features = data.get("features")
        maximum_relief = (
            manufacturing.get("maximum_relief_depth_mm")
            if isinstance(manufacturing, dict)
            else None
        )
        if isinstance(features, list):
            for index, feature in enumerate(features):
                if not isinstance(feature, dict):
                    continue
                if feature.get("priority") == "required" and feature.get(
                    "can_omit"
                ) is True:
                    feature["can_omit"] = False
                    actions.append(
                        cls._action(
                            f"features[{index}].can_omit",
                            True,
                            False,
                            "required features cannot be omitted",
                        )
                    )
                size = feature.get("size")
                if (
                    isinstance(size, dict)
                    and isinstance(maximum_relief, (int, float))
                    and not isinstance(maximum_relief, bool)
                    and isinstance(size.get("depth_mm"), (int, float))
                    and not isinstance(size.get("depth_mm"), bool)
                    and size["depth_mm"] > maximum_relief
                ):
                    before = size["depth_mm"]
                    size["depth_mm"] = float(maximum_relief)
                    actions.append(
                        cls._action(
                            f"features[{index}].size.depth_mm",
                            before,
                            maximum_relief,
                            "cap feature depth at the manufacturing relief limit",
                        )
                    )
        return data, tuple(actions)
