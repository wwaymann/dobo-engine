from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Protocol

from .semantic_contract import DesignSemanticProgram
from .semantic_parser import SemanticProgramParser


PROMPT_INTERPRETER_VERSION = "3C.4"
DEFAULT_SCHEMA_PATH = Path(__file__).with_name("semantic_program.schema.json")

# Structured Outputs accepts a strict subset of JSON Schema. Keep the canonical
# 3A.1 schema unchanged for local validation and remove only constraints that
# the Responses API cannot accept from the copy sent to OpenAI.
_OPENAI_UNSUPPORTED_SCHEMA_KEYWORDS = frozenset({"uniqueItems"})

SYSTEM_INSTRUCTIONS = """You are the semantic design interpreter for DOBO.
Convert the user's planter description into exactly one Design Semantic Program 3A.1.

Rules:
- Interpret meaning only. Never emit SDFs, meshes, CAD commands or Motor primitives.
- Preserve the user's prompt exactly in source.prompt.
- Set source.kind to prompt and source.image_reference to null.
- Use only values permitted by the supplied JSON Schema.
- Express visible parts as features and spatial structure as relations.
- Use normalized anchors and real millimetres only where the schema requests them.
- Record every inferred value as an assumption.
- Record uncertainty as a non-blocking ambiguity when a safe default exists.
- Use a blocking ambiguity when no safe interpretation exists.
- Required features cannot be omittable.
- Manufacturing values must remain internally safe.
- manufacturing.maximum_relief_depth_mm MUST be strictly smaller than
  manufacturing.minimum_wall_mm. Prefer a conservative relief depth no greater
  than half the wall thickness when the user does not provide exact values.
"""


def _json_schema_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    raise TypeError(f"Unsupported JSON Schema literal type: {type(value).__name__}.")


def _openai_compatible_schema(value: Any) -> Any:
    if isinstance(value, dict):
        projected = {
            key: _openai_compatible_schema(item)
            for key, item in value.items()
            if key not in _OPENAI_UNSUPPORTED_SCHEMA_KEYWORDS
        }
        if "type" not in projected and "const" in projected:
            projected["type"] = _json_schema_type(projected["const"])
        if "type" not in projected and "enum" in projected:
            inferred_types = list(
                dict.fromkeys(_json_schema_type(item) for item in projected["enum"])
            )
            if not inferred_types:
                raise ValueError("OpenAI enum schemas must contain at least one value.")
            projected["type"] = (
                inferred_types[0] if len(inferred_types) == 1 else inferred_types
            )
        return projected
    if isinstance(value, list):
        return [_openai_compatible_schema(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class SemanticModelResponse:
    output: dict[str, Any]
    model: str
    response_id: str


class SemanticModelClient(Protocol):
    def generate_semantic_program(
        self,
        *,
        prompt: str,
        system_instructions: str,
        schema: dict[str, Any],
    ) -> SemanticModelResponse: ...


@dataclass(frozen=True, slots=True)
class PromptInterpretationTrace:
    interpreter_version: str
    model: str
    response_id: str
    prompt_sha256: str
    feature_count: int
    relation_count: int
    assumption_count: int
    ambiguity_count: int


@dataclass(frozen=True, slots=True)
class PromptInterpretationResult:
    program: DesignSemanticProgram
    trace: PromptInterpretationTrace


class PromptSemanticInterpreter:
    def __init__(
        self,
        client: SemanticModelClient,
        *,
        schema_path: str | Path = DEFAULT_SCHEMA_PATH,
    ) -> None:
        self.client = client
        path = Path(schema_path).resolve()
        self.schema = json.loads(path.read_text(encoding="utf-8"))
        if self.schema.get("title") != "DOBO Design Semantic Program 3A.1":
            raise ValueError("Prompt interpreter requires the 3A.1 semantic schema.")

    def interpret(self, prompt: str) -> PromptInterpretationResult:
        normalized = prompt.strip()
        if not 10 <= len(normalized) <= 4000:
            raise ValueError("Design prompt must contain between 10 and 4000 characters.")
        response = self.client.generate_semantic_program(
            prompt=normalized,
            system_instructions=SYSTEM_INSTRUCTIONS,
            schema=self.schema,
        )
        if not isinstance(response.output, dict):
            raise TypeError("Semantic model output must be a JSON object.")
        program = SemanticProgramParser().parse_dict(response.output)
        if program.source.kind != "prompt":
            raise ValueError("Prompt interpretation must set source.kind to prompt.")
        if program.source.prompt != normalized:
            raise ValueError("Semantic model did not preserve the exact source prompt.")
        if program.source.image_reference is not None:
            raise ValueError("Prompt-only interpretation cannot include an image reference.")
        trace = PromptInterpretationTrace(
            interpreter_version=PROMPT_INTERPRETER_VERSION,
            model=response.model,
            response_id=response.response_id,
            prompt_sha256=sha256(normalized.encode("utf-8")).hexdigest(),
            feature_count=len(program.features),
            relation_count=len(program.relations),
            assumption_count=len(program.assumptions),
            ambiguity_count=len(program.ambiguities),
        )
        return PromptInterpretationResult(program=program, trace=trace)


class OpenAIResponsesSemanticClient:
    """OpenAI Responses API adapter with strict JSON Schema output."""

    def __init__(self, *, model: str, client: Any | None = None) -> None:
        if not model.strip():
            raise ValueError("OpenAI model name must not be empty.")
        self.model = model.strip()
        if client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise RuntimeError(
                    "OpenAI Python SDK is required for live prompt interpretation."
                ) from exc
            client = OpenAI()
        self.client = client

    def generate_semantic_program(
        self,
        *,
        prompt: str,
        system_instructions: str,
        schema: dict[str, Any],
    ) -> SemanticModelResponse:
        api_schema = _openai_compatible_schema(schema)
        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": prompt},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "dobo_semantic_program_3a_1",
                    "schema": api_schema,
                    "strict": True,
                }
            },
        )
        output_text = getattr(response, "output_text", None)
        if not isinstance(output_text, str) or not output_text.strip():
            raise RuntimeError("OpenAI response did not contain semantic JSON output.")
        try:
            output = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise RuntimeError("OpenAI semantic output was not valid JSON.") from exc
        return SemanticModelResponse(
            output=output,
            model=str(getattr(response, "model", self.model)),
            response_id=str(getattr(response, "id", "unavailable")),
        )
