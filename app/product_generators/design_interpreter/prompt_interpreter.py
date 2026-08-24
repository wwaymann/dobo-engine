from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Protocol
import unicodedata

from .semantic_contract import DesignSemanticProgram
from .semantic_parser import SemanticProgramParser


PROMPT_INTERPRETER_VERSION = "3C.8"
DEFAULT_SCHEMA_PATH = Path(__file__).with_name("semantic_program.schema.json")

_OPENAI_UNSUPPORTED_SCHEMA_KEYWORDS = frozenset({"uniqueItems"})

SYSTEM_INSTRUCTIONS = """You are the semantic design interpreter for DOBO.
Convert the user's planter description into exactly one Design Semantic Program 3A.1.

Rules:
- Interpret meaning only. Never emit SDFs, meshes, CAD commands or Motor primitives.
- Preserve the user's prompt exactly in source.prompt.
- Set source.kind to prompt and source.image_reference to null.
- Use only values permitted by the supplied JSON Schema.
- Preserve explicit body geometry. When the user names a primitive or body family, that body intent MUST survive in body.family and/or body.style_tags rather than being replaced by a generic cylindrical or organic body.
- For a cube/cubic body use a style tag such as cuboid or cube. For a rectangular prism use rectangular_prism. For a cylinder/cylindrical body keep body.family=cylindrical and include cylindrical when useful. For a cone/truncated cone use body.family=tapered and a conical/tapered tag. For a sphere use body.family=spherical. For an ovoid/ellipsoid use body.family=organic with style tag ovoid. For a triangular prism use a triangular_prism style tag and a polygonal opening when appropriate.
- Do not reinterpret an explicitly requested primitive as sculptural, flowing, helical, organic-asymmetric or another expressive family unless the user asks for that style.
- Express visible decorative parts as features and spatial structure as relations. A plain planter may have an empty features array.
- Functional vessel drainage is NOT a decorative visible feature. If the user merely asks for a normal drainage hole or drainage at the bottom, set manufacturing.drainage_required=true and do not create a drainage feature. Create a drainage-related feature only when the user explicitly asks for a special visible drainage geometry or decorative drainage pattern beyond the normal vessel drain.
- Preserve literal user-requested lettering as semantic content, not merely as a generic text feature.
- Every requested word, name, number or short phrase that must appear on the planter MUST be represented by a required feature with form_hint=text, and feature.concept MUST include the normalized literal content as identifier tokens (for example, literal HELLO -> concept text_hello; never use only concept=text).
- Preserve the requested text surface treatment exactly: emboss, raised, sobrerrelieve or equivalent wording -> surface_effect=raised; deboss, recessed, bajorrelieve or equivalent wording -> surface_effect=recessed.
- Preserve explicit placement wording in feature.anchor.region. Front, frontal or al frente -> front; back -> back; left -> left; right -> right; upper/top -> upper; lower/bottom -> lower; all-around -> all_around.
- Interpret normalized anchor coordinates consistently: horizontal=-1 is left, horizontal=0 is centered, horizontal=1 is right; vertical=0 is bottom, vertical=0.5 is vertically centered, vertical=1 is top. If the user explicitly asks for centered placement, use horizontal=0.
- Relations may reference feature ids only; never use the body itself as subject_id or object_id.
- Never create a relation whose subject_id and object_id are the same feature.
- If the design has only one visible feature and no second feature is needed, return an empty relations array.
- Use each feature's anchor to express attachment or placement on the planter body; do not invent a relation just to say that a feature is on the body.
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


def _plain_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.lower())
    return "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )


def _normalize_functional_prompt_output(prompt: str, output: dict[str, Any]) -> dict[str, Any]:
    """Preserve explicit primitive intent and keep normal drainage in the vessel contract."""
    data = deepcopy(output)
    text = _plain_text(prompt)
    body = data.get("body")
    if isinstance(body, dict):
        raw_tags = body.get("style_tags", [])
        tags = [str(tag) for tag in raw_tags] if isinstance(raw_tags, list) else []
        shape_tags = {
            "cuboid", "cube", "cubic", "rectangular", "rectangular_prism",
            "cylindrical", "cylinder", "tapered", "tapered_revolution", "conical",
            "truncated_cone", "frustum", "spherical", "sphere", "ovoid", "ellipsoidal",
            "triangular", "triangular_prism", "triangle_prism",
        }
        tags = [tag for tag in tags if tag not in shape_tags]
        if "prisma triangular" in text or "triangular prism" in text:
            body["family"] = "organic"
            body["opening_shape"] = "polygonal"
            tags.append("triangular_prism")
        elif "prisma rectangular" in text or "rectangular prism" in text or "jardinera rectangular" in text:
            body["family"] = "organic"
            body["opening_shape"] = "polygonal"
            tags.append("rectangular_prism")
        elif any(token in text for token in ("troncocon", "tronco de cono", "truncated cone", "frustum")) or ("cono" in text and "cono" not in "icono"):
            body["family"] = "tapered"
            tags.append("tapered_revolution")
        elif any(token in text for token in ("cilindrica", "cilindrico", "cilindro", "cylindrical", "cylinder")):
            body["family"] = "cylindrical"
            tags.append("cylindrical")
        elif any(token in text for token in ("esferica", "esferico", "esfera", "spherical", "sphere")):
            body["family"] = "spherical"
            tags.append("spherical")
        elif any(token in text for token in ("ovoide", "ovoidal", "elipsoidal", "ovoid", "ellipsoid")):
            body["family"] = "organic"
            tags.append("ovoid")
        elif any(token in text for token in ("cubo", "cubica", "cubico", "cube", "cubic")):
            body["family"] = "organic"
            body["opening_shape"] = "polygonal"
            tags.append("cuboid")
        body["style_tags"] = list(dict.fromkeys(tags or ["functional"]))

    manufacturing = data.get("manufacturing")
    ordinary_drainage = isinstance(manufacturing, dict) and bool(manufacturing.get("drainage_required"))
    custom_drainage = any(
        phrase in text
        for phrase in (
            "patron de drenaje", "patron drenaje", "decoracion de drenaje",
            "decorative drainage", "drainage pattern", "multiple drainage",
        )
    )
    features = data.get("features")
    if ordinary_drainage and not custom_drainage and isinstance(features, list):
        kept: list[dict[str, Any]] = []
        removed_ids: set[str] = set()
        for feature in features:
            if not isinstance(feature, dict):
                continue
            identity = " ".join((str(feature.get("id", "")), str(feature.get("concept", "")))).lower()
            if "drain" in identity or "dren" in identity:
                removed_ids.add(str(feature.get("id", "")))
            else:
                kept.append(feature)
        data["features"] = kept
        if removed_ids:
            relations = data.get("relations")
            if isinstance(relations, list):
                data["relations"] = [
                    relation for relation in relations
                    if isinstance(relation, dict)
                    and str(relation.get("subject_id", "")) not in removed_ids
                    and str(relation.get("object_id", "")) not in removed_ids
                ]
    return data


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
        normalized_output = _normalize_functional_prompt_output(normalized, response.output)
        program = SemanticProgramParser().parse_dict(normalized_output)
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
