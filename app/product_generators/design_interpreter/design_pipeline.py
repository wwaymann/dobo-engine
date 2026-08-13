from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from .image_interpreter import ImageModelClient, ImageSemanticInterpreter
from .prompt_interpreter import PromptSemanticInterpreter, SemanticModelClient
from .proposal_repair import SemanticProposalRepairer, SemanticRepairResult
from .semantic_contract import DesignSemanticProgram
from .three_mf_export import ThreeMFExportResult, ThreeMFMeshExporter


PIPELINE_VERSION = "3F.3"
_DISPLACEMENT_FAILURE = (
    "Localized mesh refinement exceeded its displacement limit."
)
_CONNECTIVITY_FAILURE = "Smooth union did not create one connected surface."


@dataclass(frozen=True, slots=True)
class DesignPipelineTrace:
    pipeline_version: str
    source_kind: str
    interpreter_version: str
    model: str
    response_id: str
    semantic_program_id: str
    motor_program_id: str
    repair_actions: int
    vertex_count: int
    face_count: int
    generation_seconds: float
    generation_attempts: int
    mesh_quality_profile: str


@dataclass(frozen=True, slots=True)
class DesignPipelineResult:
    repair: SemanticRepairResult
    mesh_result: Any
    three_mf: ThreeMFExportResult
    semantic_path: str
    motor_path: str
    repair_report_path: str
    manifest_path: str
    trace: DesignPipelineTrace

    @property
    def stl_path(self) -> str:
        return str(self.mesh_result.stl_path)

    @property
    def three_mf_path(self) -> str:
        return self.three_mf.path

    def validate(self) -> None:
        self.repair.report.validate()
        self.mesh_result.validate()
        self.three_mf.validate()
        for path in (
            self.semantic_path,
            self.motor_path,
            self.repair_report_path,
            self.manifest_path,
            self.stl_path,
            self.three_mf_path,
        ):
            target = Path(path)
            if not target.is_file() or target.stat().st_size <= 0:
                raise RuntimeError(f"Pipeline artifact was not created: {target}")
        if self.trace.pipeline_version != PIPELINE_VERSION:
            raise RuntimeError("Unexpected design pipeline version.")


class DoboDesignPipeline:
    """Run semantic interpretation, repair, compilation and mesh export."""

    def __init__(
        self,
        *,
        prompt_client: SemanticModelClient | None = None,
        image_client: ImageModelClient | None = None,
        repairer: SemanticProposalRepairer | None = None,
        engine: Any | None = None,
    ) -> None:
        self.prompt_client = prompt_client
        self.image_client = image_client
        self.repairer = repairer or SemanticProposalRepairer()
        self.engine = engine

    def generate_from_prompt(
        self,
        prompt: str,
        *,
        output_root: str | Path | None = None,
    ) -> DesignPipelineResult:
        if self.prompt_client is None:
            raise RuntimeError("Prompt pipeline requires a semantic model client.")
        interpreted = PromptSemanticInterpreter(self.prompt_client).interpret(prompt)
        return self.generate_from_semantic(
            interpreted.program,
            output_root=output_root,
            interpreter_version=interpreted.trace.interpreter_version,
            model=interpreted.trace.model,
            response_id=interpreted.trace.response_id,
        )

    def generate_from_image(
        self,
        image_path: str | Path,
        *,
        output_root: str | Path | None = None,
    ) -> DesignPipelineResult:
        if self.image_client is None:
            raise RuntimeError("Image pipeline requires a vision model client.")
        interpreted = ImageSemanticInterpreter(self.image_client).interpret_file(
            image_path
        )
        return self.generate_from_semantic(
            interpreted.program,
            output_root=output_root,
            interpreter_version=interpreted.trace.interpreter_version,
            model=interpreted.trace.model,
            response_id=interpreted.trace.response_id,
        )

    def generate_from_semantic(
        self,
        program: DesignSemanticProgram,
        *,
        output_root: str | Path | None = None,
        interpreter_version: str = "semantic-input",
        model: str = "not-used",
        response_id: str = "not-used",
    ) -> DesignPipelineResult:
        from product_generators.organic_shapes.hierarchy_engine import (
            HierarchicalFeatureVesselEngine,
        )
        from product_generators.organic_shapes.hierarchy_specification import (
            HierarchicalFeatureParser,
        )

        repair = self.repairer.repair(program)
        motor_program = deepcopy(repair.compilation.motor_program)
        motor_id = repair.compilation.report.output_program_id
        if output_root is None:
            output_directory = Path(motor_program["output"]["directory"])
        else:
            output_directory = Path(output_root).resolve() / motor_id
        motor_program["output"]["directory"] = str(output_directory)
        motor_program["output"]["basename"] = motor_id

        semantic_path = output_directory / f"{motor_id}.semantic.json"
        motor_path = output_directory / f"{motor_id}.motor.json"
        report_path = output_directory / f"{motor_id}.repair.json"
        output_directory.mkdir(parents=True, exist_ok=True)
        semantic_path.write_text(
            json.dumps(repair.program.to_dict(), indent=2, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )
        # Persist diagnostic checkpoints before the expensive mesh stage. A
        # generation failure can then be reproduced without another model call.
        motor_path.write_text(
            json.dumps(motor_program, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        repair.write_report(report_path)
        engine = self.engine or HierarchicalFeatureVesselEngine()
        (
            mesh_result,
            selected_motor_program,
            generation_attempts,
            mesh_quality_profile,
        ) = self._generate_with_retry(
            motor_program,
            parser=HierarchicalFeatureParser(),
            engine=engine,
        )
        motor_path.write_text(
            json.dumps(selected_motor_program, indent=2, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )
        three_mf = ThreeMFMeshExporter.export(
            mesh_result.mesh,
            output_directory / f"{motor_id}.3mf",
            name=motor_id,
        )
        trace = DesignPipelineTrace(
            pipeline_version=PIPELINE_VERSION,
            source_kind=repair.program.source.kind,
            interpreter_version=interpreter_version,
            model=model,
            response_id=response_id,
            semantic_program_id=repair.program.id,
            motor_program_id=motor_id,
            repair_actions=len(repair.report.actions),
            vertex_count=mesh_result.vertex_count,
            face_count=mesh_result.face_count,
            generation_seconds=mesh_result.generation_seconds,
            generation_attempts=generation_attempts,
            mesh_quality_profile=mesh_quality_profile,
        )
        manifest_path = output_directory / f"{motor_id}.manifest.json"
        manifest = {
            "trace": asdict(trace),
            "artifacts": {
                "semantic": str(semantic_path),
                "motor": str(motor_path),
                "repair_report": str(report_path),
                "stl": str(mesh_result.stl_path),
                "three_mf": three_mf.path,
            },
            "validation": {
                "watertight": mesh_result.watertight,
                "winding_consistent": mesh_result.winding_consistent,
                "component_count": mesh_result.component_count,
                "generation_budget_ok": (
                    mesh_result.generation_seconds
                    <= mesh_result.max_generation_seconds
                ),
            },
        }
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        result = DesignPipelineResult(
            repair=repair,
            mesh_result=mesh_result,
            three_mf=three_mf,
            semantic_path=str(semantic_path),
            motor_path=str(motor_path),
            repair_report_path=str(report_path),
            manifest_path=str(manifest_path),
            trace=trace,
        )
        result.validate()
        if mesh_result.generation_seconds > mesh_result.max_generation_seconds:
            raise RuntimeError("Full design pipeline exceeded its generation budget.")
        return result

    @classmethod
    def _generate_with_retry(
        cls,
        motor_program: dict[str, Any],
        *,
        parser: Any,
        engine: Any,
    ) -> tuple[Any, dict[str, Any], int, str]:
        last_error: RuntimeError | None = None
        profiles = cls._mesh_quality_profiles(motor_program)
        for attempt, (profile_name, candidate) in enumerate(profiles, start=1):
            specification = parser.parse_dict(candidate)
            try:
                result = engine.generate(specification)
            except RuntimeError as error:
                if str(error) not in {
                    _DISPLACEMENT_FAILURE,
                    _CONNECTIVITY_FAILURE,
                }:
                    raise
                last_error = error
                continue
            return result, candidate, attempt, profile_name
        raise RuntimeError(
            "Mesh generation failed under every approved 3F recovery "
            "profile. The semantic and Motor JSON checkpoints were preserved."
        ) from last_error

    @staticmethod
    def _mesh_quality_profiles(
        motor_program: dict[str, Any],
    ) -> tuple[tuple[str, dict[str, Any]], ...]:
        canonical = deepcopy(motor_program)
        quality = canonical.get("mesh_quality")
        if not isinstance(quality, dict):
            return (("canonical", canonical),)
        voxel_mm = float(canonical["grid"]["voxel_mm"])
        base_surface = deepcopy(canonical)
        base_surface.pop("mesh_quality", None)
        fused = DoboDesignPipeline._fusion_profile(
            canonical,
            penetration_mm=max(0.5, 1.0 * voxel_mm),
            blend_mm=max(0.8, 1.25 * voxel_mm),
        )
        fused.pop("mesh_quality", None)
        strongly_fused = DoboDesignPipeline._fusion_profile(
            canonical,
            penetration_mm=max(1.0, 1.75 * voxel_mm),
            blend_mm=max(1.2, 2.0 * voxel_mm),
        )
        strongly_fused.pop("mesh_quality", None)
        return (
            ("canonical", canonical),
            ("validated_base_surface", base_surface),
            ("fused_base_surface", fused),
            ("strongly_fused_base_surface", strongly_fused),
        )

    @staticmethod
    def _fusion_profile(
        motor_program: dict[str, Any],
        *,
        penetration_mm: float,
        blend_mm: float,
    ) -> dict[str, Any]:
        candidate = deepcopy(motor_program)
        hierarchy = candidate.get("hierarchy_program", {})
        templates = hierarchy.get("templates", [])
        add_templates = {
            str(template.get("id"))
            for template in templates
            if template.get("operation") == "add"
        }
        for template in templates:
            if str(template.get("id")) in add_templates:
                template["blend_mm"] = max(
                    float(template["blend_mm"]), blend_mm
                )

        def visit(node: dict[str, Any]) -> None:
            if add_templates.intersection(node.get("template_ids", [])):
                anchor = node.get("surface_anchor")
                if isinstance(anchor, dict):
                    anchor["offset_mm"] = min(
                        float(anchor.get("offset_mm", 0.0)),
                        -penetration_mm,
                    )
            for child in node.get("children", []):
                if isinstance(child, dict):
                    visit(child)

        for root in hierarchy.get("roots", []):
            if isinstance(root, dict):
                visit(root)
        return candidate
