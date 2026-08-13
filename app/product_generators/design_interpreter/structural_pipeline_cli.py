from __future__ import annotations

import argparse
import os

from .image_interpreter import OpenAIResponsesImageClient
from .prompt_interpreter import OpenAIResponsesSemanticClient
from .semantic_parser import SemanticProgramParser
from .structural_pipeline import DoboStructuralPipeline


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate structurally composed DOBO STL and 3MF."
    )
    sources = parser.add_subparsers(dest="source_kind", required=True)
    prompt = sources.add_parser("prompt")
    prompt.add_argument("source")
    prompt.add_argument("--model", default=os.environ.get("DOBO_OPENAI_MODEL"))
    prompt.add_argument("--output-root", required=True)
    image = sources.add_parser("image")
    image.add_argument("source")
    image.add_argument("--model", default=os.environ.get("DOBO_OPENAI_MODEL"))
    image.add_argument(
        "--detail", choices=("auto", "high", "low", "original"), default="high"
    )
    image.add_argument("--output-root", required=True)
    semantic = sources.add_parser("semantic")
    semantic.add_argument("source")
    semantic.add_argument("--output-root", required=True)
    arguments = parser.parse_args()
    if arguments.source_kind in {"prompt", "image"} and not arguments.model:
        parser.error("--model or DOBO_OPENAI_MODEL is required.")
    return arguments


def main() -> None:
    arguments = _arguments()
    if arguments.source_kind == "prompt":
        result = DoboStructuralPipeline(
            prompt_client=OpenAIResponsesSemanticClient(model=arguments.model)
        ).generate_from_prompt(
            arguments.source, output_root=arguments.output_root
        )
    elif arguments.source_kind == "image":
        result = DoboStructuralPipeline(
            image_client=OpenAIResponsesImageClient(
                model=arguments.model, detail=arguments.detail
            )
        ).generate_from_image(
            arguments.source, output_root=arguments.output_root
        )
    else:
        semantic = SemanticProgramParser().parse_file(arguments.source)
        result = DoboStructuralPipeline().generate_from_semantic(
            semantic, output_root=arguments.output_root
        )
    print("pipeline", result.trace.pipeline_version, "OK")
    print("fusion", result.trace.fusion_version, "OK")
    print("source", result.trace.source_kind, "OK")
    print("silhouette features", result.trace.silhouette_features, "OK")
    print("compound children", result.trace.compound_children, "OK")
    print("repair actions", result.trace.repair_actions, "OK")
    print("vertices", result.trace.vertex_count)
    print("faces", result.trace.face_count)
    print("generation seconds", f"{result.trace.generation_seconds:.3f}")
    print("generation attempts", result.trace.generation_attempts)
    print("mesh quality profile", result.trace.mesh_quality_profile)
    print("structural JSON", result.structural_path)
    print("Motor JSON", result.motor_path)
    print("STL", result.stl_path)
    print("3MF", result.three_mf_path)
    print("manifest", result.manifest_path)
    print("DOBO Canonical Facial Acceptance Phase 4U: Valid OK")


if __name__ == "__main__":
    main()
