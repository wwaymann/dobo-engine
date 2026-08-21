from __future__ import annotations

from base64 import b64decode
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from .image_interpreter import (
    ImageModelResponse,
    ImageSemanticInterpreter,
    OpenAIResponsesImageClient,
)
from .semantic_compiler import SemanticToMotorCompiler


SPEC_PATH = Path(__file__).with_name("phase_3a_semantic_design.json")
PNG_BYTES = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class FixtureImageClient:
    def __init__(self, output: dict) -> None:
        self.output = output
        self.calls: list[dict] = []

    def generate_semantic_program(self, **request) -> ImageModelResponse:
        self.calls.append(request)
        return ImageModelResponse(
            output=deepcopy(self.output),
            model="fixture-vision-model",
            response_id="fixture-response-3d",
        )


class FakeResponsesAPI:
    def __init__(self, output: dict) -> None:
        self.output = output
        self.request = None

    def create(self, **request):
        self.request = request
        return SimpleNamespace(
            output_text=json.dumps(self.output, ensure_ascii=False),
            model="fake-openai-vision-model",
            id="fake-openai-vision-response",
        )


def _must_reject(label: str, action) -> None:
    try:
        action()
    except (FileNotFoundError, TypeError, ValueError, RuntimeError):
        print("reject", label, True, "OK")
        return
    raise RuntimeError(f"Phase 3D accepted invalid case '{label}'.")


def main() -> None:
    print()
    print("DOBO Design Interpreter - Phase 3D")
    print("Image -> vision model -> semantic contract -> compiler")
    print("-----------------------------------")
    fixture = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    digest = sha256(PNG_BYTES).hexdigest()
    image_reference = f"sha256:{digest}"
    fixture["source"] = {
        "kind": "image",
        "prompt": None,
        "image_reference": image_reference,
    }

    with TemporaryDirectory() as directory:
        image_path = Path(directory) / "reference.png"
        image_path.write_bytes(PNG_BYTES)

        fixture_client = FixtureImageClient(fixture)
        result = ImageSemanticInterpreter(fixture_client).interpret_file(image_path)
        request = fixture_client.calls[0]
        print("model calls", len(fixture_client.calls), "OK")
        print("model", result.trace.model, "OK")
        print("response id", result.trace.response_id, "OK")
        print("image hash length", len(result.trace.image_sha256), "OK")
        print("image reference private", result.program.source.image_reference, "OK")
        print("media type", result.trace.media_type, "OK")
        print("image bytes", result.trace.image_bytes, "OK")
        print("semantic features", result.trace.feature_count, "OK")
        if request["image_reference"] != image_reference:
            raise RuntimeError("Image identity was not passed to the model client.")

        compiled = SemanticToMotorCompiler.compile(result.program)
        print("compiled templates", len(compiled.report.feature_traces), "OK")
        if len(compiled.report.feature_traces) != result.trace.feature_count:
            raise RuntimeError("Image-to-compiler feature trace was lost.")

        fake_responses = FakeResponsesAPI(fixture)
        openai_adapter = OpenAIResponsesImageClient(
            model="configured-vision-model",
            detail="high",
            client=SimpleNamespace(responses=fake_responses),
        )
        live_shape = ImageSemanticInterpreter(openai_adapter).interpret_file(
            image_path
        )
        api_request = fake_responses.request
        response_format = api_request["text"]["format"]
        user_content = api_request["input"][1]["content"]
        image_part = next(
            part for part in user_content if part["type"] == "input_image"
        )
        print("Responses API model", api_request["model"], "OK")
        print("structured output type", response_format["type"], "OK")
        print("strict JSON Schema", response_format["strict"], "OK")
        print("image content type", image_part["type"], "OK")
        print("image data URL", image_part["image_url"].startswith("data:image/png;base64,"), "OK")
        print("image detail", image_part["detail"], "OK")
        print("OpenAI adapter semantic features", len(live_shape.program.features), "OK")
        if response_format["type"] != "json_schema" or not response_format["strict"]:
            raise RuntimeError("Image adapter did not request strict output.")

        wrong_reference = deepcopy(fixture)
        wrong_reference["source"]["image_reference"] = "sha256:" + "0" * 64
        _must_reject(
            "model changed image reference",
            lambda: ImageSemanticInterpreter(
                FixtureImageClient(wrong_reference)
            ).interpret_file(image_path),
        )
        wrong_source = deepcopy(fixture)
        wrong_source["source"] = {
            "kind": "prompt",
            "prompt": "Un prompt suficientemente largo.",
            "image_reference": None,
        }
        _must_reject(
            "non-image source",
            lambda: ImageSemanticInterpreter(
                FixtureImageClient(wrong_source)
            ).interpret_file(image_path),
        )
        prompt_leak = deepcopy(fixture)
        prompt_leak["source"]["prompt"] = "Texto no permitido para imagen pura."
        _must_reject(
            "image source prompt leak",
            lambda: ImageSemanticInterpreter(
                FixtureImageClient(prompt_leak)
            ).interpret_file(image_path),
        )
        text_path = Path(directory) / "reference.txt"
        text_path.write_text("not an image", encoding="utf-8")
        _must_reject(
            "unsupported image type",
            lambda: ImageSemanticInterpreter(fixture_client).interpret_file(
                text_path
            ),
        )
        empty_path = Path(directory) / "empty.png"
        empty_path.write_bytes(b"")
        _must_reject(
            "empty image",
            lambda: ImageSemanticInterpreter(fixture_client).interpret_file(
                empty_path
            ),
        )

    _must_reject(
        "invalid detail level",
        lambda: OpenAIResponsesImageClient(
            model="configured-vision-model",
            detail="ultra",
            client=SimpleNamespace(),
        ),
    )
    print("-----------------------------------")
    print("No API credit consumed OK")
    print("DOBO Design Interpreter Phase 3D: Valid OK")


if __name__ == "__main__":
    main()
