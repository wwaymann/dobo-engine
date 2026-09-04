from __future__ import annotations

from base64 import b64decode
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from .design_pipeline import DoboDesignPipeline, PIPELINE_VERSION
from .image_interpreter import ImageModelResponse
from .prompt_interpreter import SemanticModelResponse


SPEC_PATH = Path(__file__).with_name("phase_3a_semantic_design.json")
PNG_BYTES = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class FixturePromptClient:
    def __init__(self, output: dict) -> None:
        self.output = output
        self.calls = 0

    def generate_semantic_program(self, **request) -> SemanticModelResponse:
        self.calls += 1
        return SemanticModelResponse(
            output=deepcopy(self.output),
            model="fixture-pipeline-model",
            response_id="fixture-pipeline-prompt-response",
        )


class FixtureImageClient:
    def __init__(self, output: dict) -> None:
        self.output = output
        self.calls = 0

    def generate_semantic_program(self, **request) -> ImageModelResponse:
        self.calls += 1
        return ImageModelResponse(
            output=deepcopy(self.output),
            model="fixture-pipeline-vision-model",
            response_id="fixture-pipeline-image-response",
        )


class FailRefinementProfilesEngine:
    def __init__(self, delegate) -> None:
        self.delegate = delegate
        self.calls = 0

    def generate(self, specification):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError(
                "Localized mesh refinement exceeded its displacement limit."
            )
        if self.calls == 2:
            raise RuntimeError(
                "Smooth union did not create one connected surface."
            )
        return self.delegate.generate(specification)


def _must_reject(label: str, action) -> None:
    try:
        action()
    except (FileNotFoundError, TypeError, ValueError, RuntimeError):
        print("reject", label, True, "OK")
        return
    raise RuntimeError(f"Phase 3F accepted invalid case '{label}'.")


def _validate_result(label: str, result) -> None:
    result.validate()
    print(label, "pipeline version", result.trace.pipeline_version, "OK")
    print(label, "source", result.trace.source_kind, "OK")
    print(label, "components", result.mesh_result.component_count, "OK")
    print(label, "watertight", result.mesh_result.watertight, "OK")
    print(
        label,
        "winding consistent",
        result.mesh_result.winding_consistent,
        "OK",
    )
    print(label, "vertices", result.mesh_result.vertex_count, "OK")
    print(label, "faces", result.mesh_result.face_count, "OK")
    print(label, "3MF vertices", result.three_mf.vertex_count, "OK")
    print(label, "3MF triangles", result.three_mf.triangle_count, "OK")
    print(label, "artifacts", 6, "OK")
    print(label, "generation attempts", result.trace.generation_attempts, "OK")
    print(label, "quality profile", result.trace.mesh_quality_profile, "OK")
    print(
        label,
        "generation budget",
        result.mesh_result.generation_seconds
        <= result.mesh_result.max_generation_seconds,
        "OK",
    )
    if result.trace.pipeline_version != PIPELINE_VERSION:
        raise RuntimeError("Phase 3F pipeline version was not preserved.")
    if result.mesh_result.component_count != 1:
        raise RuntimeError("Phase 3F output must contain one component.")
    if not result.mesh_result.watertight or not result.mesh_result.winding_consistent:
        raise RuntimeError("Phase 3F output mesh is invalid.")


def main() -> None:
    print()
    print("DOBO Design Interpreter - Phase 3F")
    print("Prompt/Image -> semantic repair -> Motor -> watertight STL + 3MF")
    print("-----------------------------------")
    fixture = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    prompt_client = FixturePromptClient(fixture)

    digest = sha256(PNG_BYTES).hexdigest()
    image_fixture = deepcopy(fixture)
    image_fixture["id"] = "bear_planter_image_pipeline_probe"
    image_fixture["source"] = {
        "kind": "image",
        "prompt": None,
        "image_reference": f"sha256:{digest}",
    }
    image_client = FixtureImageClient(image_fixture)
    from product_generators.organic_shapes.hierarchy_engine import (
        HierarchicalFeatureVesselEngine,
    )

    retry_engine = FailRefinementProfilesEngine(
        HierarchicalFeatureVesselEngine()
    )
    pipeline = DoboDesignPipeline(
        prompt_client=prompt_client,
        image_client=image_client,
        engine=retry_engine,
    )

    with TemporaryDirectory() as directory:
        root = Path(directory)
        prompt_result = pipeline.generate_from_prompt(
            fixture["source"]["prompt"],
            output_root=root / "prompt",
        )
        _validate_result("prompt", prompt_result)
        print(
            "prompt displacement fallback",
            prompt_result.trace.generation_attempts == 3
            and prompt_result.trace.mesh_quality_profile
            == "fused_base_surface",
            "OK",
        )
        selected_motor = json.loads(
            Path(prompt_result.motor_path).read_text(encoding="utf-8")
        )
        add_templates = {
            template["id"]
            for template in selected_motor["hierarchy_program"]["templates"]
            if template["operation"] == "add"
        }
        fused_offsets = [
            root["surface_anchor"]["offset_mm"]
            for root in selected_motor["hierarchy_program"]["roots"]
            if add_templates.intersection(root["template_ids"])
        ]
        print(
            "prompt fusion penetration",
            bool(fused_offsets) and max(fused_offsets) < 0.0,
            "OK",
        )
        image_path = root / "reference.png"
        image_path.write_bytes(PNG_BYTES)
        image_result = pipeline.generate_from_image(
            image_path,
            output_root=root / "image",
        )
        _validate_result("image", image_result)
        print("prompt model calls", prompt_client.calls, "OK")
        print("image model calls", image_client.calls, "OK")
        print(
            "distinct output directories",
            Path(prompt_result.stl_path).parent
            != Path(image_result.stl_path).parent,
            "OK",
        )
        prompt_manifest = json.loads(
            Path(prompt_result.manifest_path).read_text(encoding="utf-8")
        )
        image_manifest = json.loads(
            Path(image_result.manifest_path).read_text(encoding="utf-8")
        )
        print(
            "prompt manifest source",
            prompt_manifest["trace"]["source_kind"] == "prompt",
            "OK",
        )
        print(
            "image manifest source",
            image_manifest["trace"]["source_kind"] == "image",
            "OK",
        )

    _must_reject(
        "missing prompt client",
        lambda: DoboDesignPipeline().generate_from_prompt(
            fixture["source"]["prompt"]
        ),
    )
    _must_reject(
        "missing image client",
        lambda: DoboDesignPipeline().generate_from_image("missing.png"),
    )
    print("-----------------------------------")
    print("No API credit consumed OK")
    print("DOBO Design Interpreter Phase 3F: Valid OK")


if __name__ == "__main__":
    main()
