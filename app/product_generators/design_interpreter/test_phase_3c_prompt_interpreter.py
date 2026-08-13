from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

from .prompt_interpreter import (
    OpenAIResponsesSemanticClient,
    PromptSemanticInterpreter,
    SemanticModelResponse,
)
from .semantic_compiler import SemanticToMotorCompiler


SPEC_PATH = Path(__file__).with_name("phase_3a_semantic_design.json")


class FixtureSemanticClient:
    def __init__(self, output: dict) -> None:
        self.output = output
        self.calls: list[dict] = []

    def generate_semantic_program(self, **request) -> SemanticModelResponse:
        self.calls.append(request)
        return SemanticModelResponse(
            output=deepcopy(self.output),
            model="fixture-semantic-model",
            response_id="fixture-response-3c",
        )


class FakeResponsesAPI:
    def __init__(self, output: dict) -> None:
        self.output = output
        self.request = None

    def create(self, **request):
        self.request = request
        return SimpleNamespace(
            output_text=json.dumps(self.output, ensure_ascii=False),
            model="fake-openai-model",
            id="fake-openai-response",
        )


def _must_reject(label: str, action) -> None:
    try:
        action()
    except (TypeError, ValueError, RuntimeError):
        print("reject", label, True, "OK")
        return
    raise RuntimeError(f"Phase 3C accepted invalid case '{label}'.")


def main() -> None:
    print()
    print("DOBO Design Interpreter - Phase 3C")
    print("Prompt -> structured model output -> semantic contract -> compiler")
    print("-----------------------------------")
    fixture = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    prompt = fixture["source"]["prompt"]
    fixture_client = FixtureSemanticClient(fixture)
    result = PromptSemanticInterpreter(fixture_client).interpret(prompt)
    print("model calls", len(fixture_client.calls), "OK")
    print("model", result.trace.model, "OK")
    print("response id", result.trace.response_id, "OK")
    print("prompt hash length", len(result.trace.prompt_sha256), "OK")
    print("semantic features", result.trace.feature_count, "OK")
    print("semantic relations", result.trace.relation_count, "OK")
    print("assumptions", result.trace.assumption_count, "OK")
    print("ambiguities", result.trace.ambiguity_count, "OK")
    if len(fixture_client.calls) != 1 or len(result.trace.prompt_sha256) != 64:
        raise RuntimeError("Prompt interpretation trace is incomplete.")

    compiled = SemanticToMotorCompiler.compile(result.program)
    print("compiled templates", len(compiled.report.feature_traces), "OK")
    print("compiled relations", compiled.report.compiled_relations, "OK")
    if len(compiled.report.feature_traces) != result.trace.feature_count:
        raise RuntimeError("Prompt-to-compiler feature trace was lost.")

    fake_responses = FakeResponsesAPI(fixture)
    openai_adapter = OpenAIResponsesSemanticClient(
        model="configured-model",
        client=SimpleNamespace(responses=fake_responses),
    )
    live_shape = PromptSemanticInterpreter(openai_adapter).interpret(prompt)
    request = fake_responses.request
    response_format = request["text"]["format"]
    print("Responses API model", request["model"], "OK")
    print("structured output type", response_format["type"], "OK")
    print("strict JSON Schema", response_format["strict"], "OK")
    print("OpenAI adapter semantic features", len(live_shape.program.features), "OK")
    if response_format["type"] != "json_schema" or not response_format["strict"]:
        raise RuntimeError("OpenAI adapter did not request strict Structured Outputs.")

    wrong_prompt = deepcopy(fixture)
    wrong_prompt["source"]["prompt"] = "Otro prompt distinto y suficientemente largo."
    _must_reject(
        "model changed source prompt",
        lambda: PromptSemanticInterpreter(FixtureSemanticClient(wrong_prompt)).interpret(
            prompt
        ),
    )
    wrong_source = deepcopy(fixture)
    wrong_source["source"] = {
        "kind": "image",
        "prompt": None,
        "image_reference": "image://fixture",
    }
    _must_reject(
        "non-prompt source",
        lambda: PromptSemanticInterpreter(FixtureSemanticClient(wrong_source)).interpret(
            prompt
        ),
    )
    blocking = deepcopy(fixture)
    blocking["ambiguities"][0]["blocking"] = True
    _must_reject(
        "blocking ambiguity",
        lambda: PromptSemanticInterpreter(FixtureSemanticClient(blocking)).interpret(
            prompt
        ),
    )
    _must_reject(
        "empty prompt",
        lambda: PromptSemanticInterpreter(FixtureSemanticClient(fixture)).interpret(""),
    )
    print("-----------------------------------")
    print("No API credit consumed OK")
    print("DOBO Design Interpreter Phase 3C: Valid OK")


if __name__ == "__main__":
    main()
