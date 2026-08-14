from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from .design_pipeline import DoboDesignPipeline
from .image_interpreter import ImageModelClient, ImageSemanticInterpreter
from .prompt_interpreter import PromptSemanticInterpreter, SemanticModelClient
from .proposal_repair import SemanticProposalRepairer, SemanticRepairResult
from .semantic_contract import DesignSemanticProgram
from .structural_compiler import (
    StructuralCompilationResult,
    StructuralSemanticCompiler,
)
from .structural_vocabulary import StructuralVocabularyResolver
from .three_mf_export import ThreeMFExportResult, ThreeMFMeshExporter


STRUCTURAL_PIPELINE_VERSION = "5.9"
STRUCTURAL_FUSION_VERSION = "5C.1"
STRUCTURAL_GENERATION_BUDGET_SECONDS = 45.0


@dataclass(frozen=True, slots=True)
class StructuralPipelineTrace:
    pipeline_version: str
    fusion_version: str
    source_kind: str
    interpreter_version: str
    model: str
    response_id: str
    semantic_program_id: str
    motor_program_id: str
    body_profile: str
    style_profile: str
    grammar_signature: str
    silhouette_features: int
    compound_children: int
    repair_actions: int
    generation_attempts: int
    mesh_quality_profile: str
    vertex_count: int
    face_count: int
    generation_seconds: float


@dataclass(frozen=True, slots=True)
class StructuralPipelineResult:
    repair: SemanticRepairResult
    compilation: StructuralCompilationResult
    mesh_result: Any
    three_mf: ThreeMFExportResult
    semantic_path: str
    structural_path: str
    motor_path: str
    repair_report_path: str
    manifest_path: str
    trace: StructuralPipelineTrace

    @property
    def stl_path(self) -> str:
        return str(self.mesh_result.stl_path)

    @property
    def three_mf_path(self) -> str:
        return self.three_mf.path

    def validate(self) -> None:
        self.repair.report.validate()
        self.compilation.report.validate(len(self.repair.program.features))
        self.mesh_result.validate()
        self.three_mf.validate()
        if self.trace.pipeline_version != STRUCTURAL_PIPELINE_VERSION:
            raise RuntimeError("Unexpected structural pipeline version.")
        if self.trace.fusion_version != STRUCTURAL_FUSION_VERSION:
            raise RuntimeError("Unexpected structural fusion version.")
        if (
            self.mesh_result.generation_seconds
            > self.mesh_result.max_generation_seconds
        ):
            raise RuntimeError("Structural pipeline exceeded its generation budget.")
        for path in (
            self.semantic_path,
            self.structural_path,
            self.motor_path,
            self.repair_report_path,
            self.manifest_path,
            self.stl_path,
            self.three_mf_path,
        ):
            target = Path(path)
            if not target.is_file() or target.stat().st_size <= 0:
                raise RuntimeError(f"Structural pipeline artifact is missing: {target}")


class DoboStructuralPipeline:
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
        self, prompt: str, *, output_root: str | Path
    ) -> StructuralPipelineResult:
        if self.prompt_client is None:
            raise RuntimeError("Structural prompt pipeline requires a model client.")
        interpreted = PromptSemanticInterpreter(self.prompt_client).interpret(prompt)
        return self.generate_from_semantic(
            interpreted.program,
            output_root=output_root,
            interpreter_version=interpreted.trace.interpreter_version,
            model=interpreted.trace.model,
            response_id=interpreted.trace.response_id,
        )

    def generate_from_image(
        self, image_path: str | Path, *, output_root: str | Path
    ) -> StructuralPipelineResult:
        if self.image_client is None:
            raise RuntimeError("Structural image pipeline requires a vision client.")
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
        output_root: str | Path,
        interpreter_version: str = "semantic-input",
        model: str = "not-used",
        response_id: str = "not-used",
    ) -> StructuralPipelineResult:
        from product_generators.organic_shapes.hierarchy_engine import (
            HierarchicalFeatureVesselEngine,
        )
        from product_generators.organic_shapes.hierarchy_specification import (
            HierarchicalFeatureParser,
        )

        repair = self.repairer.repair(program)
        structural = StructuralVocabularyResolver.resolve(repair.program)
        compilation = StructuralSemanticCompiler.compile(
            repair.program, structural
        )
        motor = compilation.motor_program
        motor["output"]["max_generation_seconds"] = max(
            float(motor["output"]["max_generation_seconds"]),
            STRUCTURAL_GENERATION_BUDGET_SECONDS,
        )
        motor_id = str(motor["id"])
        output_directory = Path(output_root).resolve() / motor_id
        motor["output"]["directory"] = str(output_directory)
        motor["output"]["basename"] = motor_id
        output_directory.mkdir(parents=True, exist_ok=True)

        semantic_path = output_directory / f"{motor_id}.semantic.json"
        structural_path = output_directory / f"{motor_id}.structural.json"
        motor_path = output_directory / f"{motor_id}.motor.json"
        repair_path = output_directory / f"{motor_id}.repair.json"
        semantic_path.write_text(
            json.dumps(repair.program.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        structural.write_json(structural_path)
        motor_path.write_text(
            json.dumps(motor, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        repair.write_report(repair_path)

        parser = HierarchicalFeatureParser()
        specification = parser.parse_dict(motor)
        anchors = HierarchicalFeatureVesselEngine.surface_anchor_checks(specification)
        layout = HierarchicalFeatureVesselEngine.layout_report(specification)
        manufacturing = (
            HierarchicalFeatureVesselEngine.feature_manufacturability_report(
                specification
            )
        )
        if not all(anchors.values()):
            failed = [name for name, passed in anchors.items() if not passed]
            raise RuntimeError(f"Structural anchor preflight failed: {failed}")
        layout.validate()
        manufacturing.validate()

        engine = self.engine or HierarchicalFeatureVesselEngine()
        mesh_result, selected_motor, attempts, profile = (
            DoboDesignPipeline._generate_with_retry(
                motor,
                parser=parser,
                engine=engine,
            )
        )
        motor_path.write_text(
            json.dumps(selected_motor, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        three_mf = ThreeMFMeshExporter.export(
            mesh_result.mesh,
            output_directory / f"{motor_id}.3mf",
            name=motor_id,
        )
        trace = StructuralPipelineTrace(
            pipeline_version=STRUCTURAL_PIPELINE_VERSION,
            fusion_version=STRUCTURAL_FUSION_VERSION,
            source_kind=repair.program.source.kind,
            interpreter_version=interpreter_version,
            model=model,
            response_id=response_id,
            semantic_program_id=repair.program.id,
            motor_program_id=motor_id,
            body_profile=compilation.report.body_profile,
            style_profile=compilation.report.style_profile,
            grammar_signature=compilation.report.grammar_signature,
            silhouette_features=compilation.report.silhouette_features,
            compound_children=compilation.report.compound_children,
            repair_actions=len(repair.report.actions),
            generation_attempts=attempts,
            mesh_quality_profile=profile,
            vertex_count=mesh_result.vertex_count,
            face_count=mesh_result.face_count,
            generation_seconds=mesh_result.generation_seconds,
        )
        manifest_path = output_directory / f"{motor_id}.manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "trace": asdict(trace),
                    "artifacts": {
                        "semantic": str(semantic_path),
                        "structural": str(structural_path),
                        "motor": str(motor_path),
                        "repair_report": str(repair_path),
                        "stl": str(mesh_result.stl_path),
                        "three_mf": three_mf.path,
                    },
                    "validation": {
                        "watertight": mesh_result.watertight,
                        "winding_consistent": mesh_result.winding_consistent,
                        "component_count": mesh_result.component_count,
                        "surface_anchor_checks": len(anchors),
                        "layout_checks": len(layout.checks),
                        "manufacturability_checks": len(manufacturing.checks),
                    },
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        result = StructuralPipelineResult(
            repair=repair,
            compilation=compilation,
            mesh_result=mesh_result,
            three_mf=three_mf,
            semantic_path=str(semantic_path),
            structural_path=str(structural_path),
            motor_path=str(motor_path),
            repair_report_path=str(repair_path),
            manifest_path=str(manifest_path),
            trace=trace,
        )
        result.validate()
        return result
