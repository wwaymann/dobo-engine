from __future__ import annotations

import argparse
import os

from .design_pipeline import DoboDesignPipeline
from .image_interpreter import OpenAIResponsesImageClient
from .prompt_interpreter import OpenAIResponsesSemanticClient
from .semantic_parser import SemanticProgramParser


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate validated DOBO STL and 3MF from a prompt or image."
    )
    subparsers = parser.add_subparsers(dest="source_kind", required=True)

    prompt = subparsers.add_parser("prompt", help="Generate from natural language.")
    prompt.add_argument("source", help="Natural-language planter design prompt.")
    prompt.add_argument("--model", default=os.environ.get("DOBO_OPENAI_MODEL"))
    prompt.add_argument("--output-root", default="outputs/design_interpreter")

    image = subparsers.add_parser("image", help="Generate from a reference image.")
    image.add_argument("source", help="Local planter reference image.")
    image.add_argument("--model", default=os.environ.get("DOBO_OPENAI_MODEL"))
    image.add_argument(
        "--detail",
        choices=("auto", "high", "low", "original"),
        default="high",
    )
    image.add_argument("--output-root", default="outputs/design_interpreter")
    semantic = subparsers.add_parser(
        "semantic",
        help="Generate from an existing Semantic Program JSON without AI.",
    )
    semantic.add_argument("source", help="Semantic Program 3A.1 JSON path.")
    semantic.add_argument("--output-root", default="outputs/design_interpreter")
    arguments = parser.parse_args()
    if arguments.source_kind in {"prompt", "image"} and not arguments.model:
        parser.error("--model or DOBO_OPENAI_MODEL is required.")
    return arguments


def main() -> None:
    arguments = _arguments()
    if arguments.source_kind == "prompt":
        pipeline = DoboDesignPipeline(
            prompt_client=OpenAIResponsesSemanticClient(model=arguments.model)
        )
        result = pipeline.generate_from_prompt(
            arguments.source,
            output_root=arguments.output_root,
        )
    elif arguments.source_kind == "image":
        pipeline = DoboDesignPipeline(
            image_client=OpenAIResponsesImageClient(
                model=arguments.model,
                detail=arguments.detail,
            )
        )
        result = pipeline.generate_from_image(
            arguments.source,
            output_root=arguments.output_root,
        )
    else:
        program = SemanticProgramParser().parse_file(arguments.source)
        result = DoboDesignPipeline().generate_from_semantic(
            program,
            output_root=arguments.output_root,
        )
    print("pipeline", result.trace.pipeline_version, "OK")
    print("source", result.trace.source_kind, "OK")
    print("repair actions", result.trace.repair_actions, "OK")
    print("vertices", result.trace.vertex_count)
    print("faces", result.trace.face_count)
    print("generation seconds", f"{result.trace.generation_seconds:.3f}")
    print("generation attempts", result.trace.generation_attempts)
    print("mesh quality profile", result.trace.mesh_quality_profile)
    print("semantic JSON", result.semantic_path)
    print("Motor JSON", result.motor_path)
    print("repair report", result.repair_report_path)
    print("STL", result.stl_path)
    print("3MF", result.three_mf_path)
    print("manifest", result.manifest_path)
    print("DOBO Design Interpreter Phase 3F: Valid OK")


if __name__ == "__main__":
    main()
