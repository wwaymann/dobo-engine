from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from .body_family_expansion import GeneralBodyFamilyExpander
from .design_pipeline import DoboDesignPipeline
from .image_interpreter import ImageModelClient, ImageSemanticInterpreter
from .intelligent_surfaces import (
    IntelligentSurfaceCompiler,
    IntelligentSurfaceProgram,
    IntelligentSurfaceReport,
    SurfaceLayerIntent,
)
from .native_foundational_cad_adapter import install_native_foundational_cad_adapter
from .native_profiled_cad_adapter import install_native_profiled_cad_adapter
from .native_profiled_text_adapter import (
    decorate_profiled_mesh_result_with_native_text,
    uses_native_profiled_text,
)
from .native_ovoid_text_adapter import (
    decorate_ovoid_mesh_result_with_native_text,
    uses_native_ovoid_text,
)
from .native_radial_cad_adapter import install_native_radial_cad_adapter
from .native_radial_text_adapter import (
    decorate_radial_mesh_result_with_native_text,
    uses_native_radial_text,
)
from .native_text_pipeline_adapter import (
    decorate_mesh_result_with_native_text,
    strip_text_from_motor,
    uses_native_cylindrical_text,
)
from .native_tapered_cad_adapter import install_native_tapered_cad_adapter
from .native_tapered_text_adapter import (
    decorate_tapered_mesh_result_with_native_text,
    uses_native_tapered_text,
)
from .profiled_multicolor_adapter import (
    export_profiled_compound_multicolor,
    uses_profiled_compound_multicolor,
)
from .prompt_interpreter import PromptSemanticInterpreter, SemanticModelClient
from .proposal_repair import SemanticProposalRepairer, SemanticRepairResult
from .semantic_contract import DesignSemanticProgram
from .structural_compiler import StructuralCompilationResult, StructuralSemanticCompiler
from .structural_vocabulary import StructuralVocabularyResolver
from .three_mf_export import ThreeMFExportResult, ThreeMFMeshExporter

# Install promoted primitive routes as wrappers around the already consolidated
# retry chain. The foundational router is installed last so canonical cylinder
# and triangular-prism requests cannot silently fall back to voxel geometry.
install_native_tapered_cad_adapter()
install_native_radial_cad_adapter()
install_native_foundational_cad_adapter()
install_native_profiled_cad_adapter()

STRUCTURAL_PIPELINE_VERSION = "8.12-expanded-profile-catalog"
STRUCTURAL_FUSION_VERSION = "7C.3"
STRUCTURAL_GENERATION_BUDGET_SECONDS = 45.0
ADVANCED_GENERATION_BUDGET_SECONDS = 30.0


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
    complex_profile: str
    hierarchy_depth: int
    negative_volumes: int
    surface_layers: int
    color_zones: int


@dataclass(frozen=True, slots=True)
class StructuralPipelineResult:
    repair: SemanticRepairResult
    compilation: StructuralCompilationResult
    mesh_result: Any
    three_mf: ThreeMFExportResult
    surface_program: IntelligentSurfaceProgram
    surface_report: IntelligentSurfaceReport
    semantic_path: str
    structural_path: str
    surface_path: str
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
        if self.mesh_result.generation_seconds > self.mesh_result.max_generation_seconds:
            raise RuntimeError("Structural pipeline exceeded its generation budget.")
        for path in (
            self.semantic_path,
            self.structural_path,
            self.surface_path,
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
        self,
        prompt: str,
        *,
        output_root: str | Path,
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
        self,
        image_path: str | Path,
        *,
        output_root: str | Path,
    ) -> StructuralPipelineResult:
        if self.image_client is None:
            raise RuntimeError("Structural image pipeline requires a vision client.")
        interpreted = ImageSemanticInterpreter(self.image_client).interpret_file(image_path)
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
        surface_intents: tuple[SurfaceLayerIntent, ...] = (),
        base_color: str = "#E8E1D5",
        generation_budget_seconds: float | None = None,
    ) -> StructuralPipelineResult:
        from product_generators.organic_shapes.hierarchy_engine import (
            HierarchicalFeatureVesselEngine,
        )
        from product_generators.organic_shapes.hierarchy_specification import (
            HierarchicalFeatureParser,
        )

        repair = self.repairer.repair(program)
        structural = StructuralVocabularyResolver.resolve(repair.program)
        compilation = StructuralSemanticCompiler.compile(repair.program, structural)
        motor = compilation.motor_program

        # Normalize the body first, then remove native text from the volumetric
        # hierarchy. Cylinders, tapered vessels and promoted radial bodies keep
        # their CAD bodies; glyphs are applied only after body/cavity/drain pass.
        GeneralBodyFamilyExpander.apply(motor, repair.program)
        native_cylindrical_text = uses_native_cylindrical_text(repair.program)
        native_profiled_text = uses_native_profiled_text(repair.program)
        native_tapered_text = (
            uses_native_tapered_text(repair.program) and not native_profiled_text
        )
        native_radial_text = uses_native_radial_text(repair.program)
        native_ovoid_text = uses_native_ovoid_text(repair.program)
        native_foundational_text = bool(
            motor.get("_native_foundational_text", {}).get("entries", [])
            if isinstance(motor.get("_native_foundational_text"), dict)
            else False
        )
        native_cad_text = (
            native_cylindrical_text
            or native_profiled_text
            or native_tapered_text
            or native_radial_text
            or native_foundational_text
        )
        if (
            native_cylindrical_text
            or native_profiled_text
            or native_tapered_text
            or native_radial_text
        ):
            strip_text_from_motor(motor, repair.program)

        if compilation.report.complex_profile != "surface_only":
            motor["output"]["max_generation_seconds"] = max(
                float(motor["output"]["max_generation_seconds"]),
                STRUCTURAL_GENERATION_BUDGET_SECONDS,
            )
        elif compilation.report.adaptive_quality:
            motor["output"]["max_generation_seconds"] = ADVANCED_GENERATION_BUDGET_SECONDS
        else:
            motor["output"]["max_generation_seconds"] = max(
                float(motor["output"]["max_generation_seconds"]),
                STRUCTURAL_GENERATION_BUDGET_SECONDS,
            )
        if generation_budget_seconds is not None:
            requested_budget = float(generation_budget_seconds)
            if requested_budget <= 0.0:
                raise ValueError("generation_budget_seconds must be positive.")
            motor["output"]["max_generation_seconds"] = requested_budget

        motor_id = str(motor["id"])
        output_directory = Path(output_root).resolve() / motor_id
        motor["output"]["directory"] = str(output_directory)
        motor["output"]["basename"] = motor_id
        output_directory.mkdir(parents=True, exist_ok=True)
        surface_program, surface_report = IntelligentSurfaceCompiler.compile(
            repair.program,
            motor,
            surface_intents,
            base_color=base_color,
        )

        semantic_path = output_directory / f"{motor_id}.semantic.json"
        structural_path = output_directory / f"{motor_id}.structural.json"
        surface_path = output_directory / f"{motor_id}.surface.json"
        motor_path = output_directory / f"{motor_id}.motor.json"
        repair_path = output_directory / f"{motor_id}.repair.json"
        semantic_path.write_text(
            json.dumps(repair.program.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        structural.write_json(structural_path)
        surface_program.write_json(surface_path)
        motor_path.write_text(
            json.dumps(motor, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        repair.write_report(repair_path)

        parser = HierarchicalFeatureParser()
        specification = parser.parse_dict(motor)
        anchors = HierarchicalFeatureVesselEngine.surface_anchor_checks(specification)
        layout = HierarchicalFeatureVesselEngine.layout_report(specification)
        manufacturing = HierarchicalFeatureVesselEngine.feature_manufacturability_report(
            specification
        )
        if not all(anchors.values()):
            failed = [name for name, passed in anchors.items() if not passed]
            raise RuntimeError(f"Structural anchor preflight failed: {failed}")
        layout.validate()
        manufacturing.validate()

        engine = self.engine or HierarchicalFeatureVesselEngine()
        mesh_result, selected_motor, attempts, profile = DoboDesignPipeline._generate_with_retry(
            motor,
            parser=parser,
            engine=engine,
        )

        # Reconnect text only after the promoted CAD body is proven. No native
        # text route is allowed to deform the planter body through voxel fallback.
        # Foundational cylinder/triangle text is already applied inside its CAD
        # route, so no second decoration pass is needed here.
        if native_profiled_text:
            mesh_result = decorate_profiled_mesh_result_with_native_text(
                mesh_result,
                selected_motor,
                repair.program,
            )
        elif native_cylindrical_text:
            mesh_result = decorate_mesh_result_with_native_text(
                mesh_result,
                selected_motor,
                repair.program,
            )
        elif native_tapered_text:
            mesh_result = decorate_tapered_mesh_result_with_native_text(
                mesh_result,
                selected_motor,
                repair.program,
            )
        elif native_ovoid_text:
            mesh_result = decorate_ovoid_mesh_result_with_native_text(
                mesh_result,
                selected_motor,
                repair.program,
            )
        elif native_radial_text:
            mesh_result = decorate_radial_mesh_result_with_native_text(
                mesh_result,
                selected_motor,
                repair.program,
            )

        motor_path.write_text(
            json.dumps(selected_motor, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        profiled_compound_multicolor = uses_profiled_compound_multicolor(
            repair.program,
            surface_program,
        )
        if profiled_compound_multicolor:
            three_mf = export_profiled_compound_multicolor(
                motor=selected_motor,
                program=repair.program,
                surface_program=surface_program,
                path=output_directory / f"{motor_id}.3mf",
            )
        else:
            three_mf = ThreeMFMeshExporter.export(
                mesh_result.mesh,
                output_directory / f"{motor_id}.3mf",
                name=motor_id,
                surface_program=surface_program,
            )

        # Multicolor CAD partitioning records its physical-region contract on
        # the selected motor, so persist motor metadata after 3MF export too.
        motor_path.write_text(
            json.dumps(selected_motor, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
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
            complex_profile=compilation.report.complex_profile,
            hierarchy_depth=compilation.report.hierarchy_depth,
            negative_volumes=compilation.report.negative_volumes,
            surface_layers=surface_report.layer_count,
            color_zones=surface_report.color_zones,
        )
        manifest_path = output_directory / f"{motor_id}.manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "trace": asdict(trace),
                    "artifacts": {
                        "semantic": str(semantic_path),
                        "structural": str(structural_path),
                        "surface": str(surface_path),
                        "motor": str(motor_path),
                        "repair_report": str(repair_path),
                        "stl": str(mesh_result.stl_path),
                        "three_mf": three_mf.path,
                        "profiled_saucer": (
                            selected_motor.get("_profiled_saucer", {}).get("stl_path")
                            if isinstance(selected_motor.get("_profiled_saucer"), dict)
                            else None
                        ),
                    },
                    "validation": {
                        "watertight": mesh_result.watertight,
                        "winding_consistent": mesh_result.winding_consistent,
                        "component_count": mesh_result.component_count,
                        "surface_anchor_checks": len(anchors),
                        "layout_checks": len(layout.checks),
                        "manufacturability_checks": len(manufacturing.checks),
                        "complex_topology_nodes": compilation.report.complex_nodes,
                        "complex_topology_edges": compilation.report.complex_edges,
                        "hierarchy_depth": compilation.report.hierarchy_depth,
                        "negative_volumes": compilation.report.negative_volumes,
                        "surface_layers": surface_report.layer_count,
                        "color_zones": surface_report.color_zones,
                        "painted_triangles": three_mf.painted_triangle_count,
                        "native_cad_text": native_cad_text,
                        "native_profiled_text": native_profiled_text,
                        "profiled_compound_multicolor": profiled_compound_multicolor,
                        "profiled_text_zone": (
                            selected_motor.get("_profiled_revolution", {}).get("text_zone")
                            if isinstance(selected_motor.get("_profiled_revolution"), dict)
                            else None
                        ),
                        "profiled_saucer_generated": bool(
                            selected_motor.get("_profiled_saucer", {}).get("stl_path")
                            if isinstance(selected_motor.get("_profiled_saucer"), dict)
                            else False
                        ),
                        "native_foundational_text": native_foundational_text,
                        "native_tapered_text": native_tapered_text,
                        "native_radial_text": native_radial_text,
                        "native_ovoid_text": native_ovoid_text,
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
            surface_program=surface_program,
            surface_report=surface_report,
            semantic_path=str(semantic_path),
            structural_path=str(structural_path),
            surface_path=str(surface_path),
            motor_path=str(motor_path),
            repair_report_path=str(repair_path),
            manifest_path=str(manifest_path),
            trace=trace,
        )
        result.validate()
        return result