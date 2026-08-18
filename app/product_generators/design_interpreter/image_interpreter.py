from __future__ import annotations

from base64 import b64encode
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Protocol

from .prompt_interpreter import DEFAULT_SCHEMA_PATH, _openai_compatible_schema
from .semantic_contract import DesignSemanticProgram
from .semantic_parser import SemanticProgramParser


IMAGE_INTERPRETER_VERSION = "3D.1"
SUPPORTED_IMAGE_TYPES = {
    ".gif": "image/gif",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpg",
    ".png": "image/png",
    ".webp": "image/webp",
}
SUPPORTED_DETAIL_LEVELS = frozenset({"low", "high", "original", "auto"})

SYSTEM_INSTRUCTIONS = """You are the visual semantic design interpreter for DOBO.
Convert the supplied planter reference image into exactly one Design Semantic
Program 3A.1.

Rules:
- Interpret visible design meaning only. Never emit SDFs, meshes, CAD commands
  or Motor primitives.
- Set source.kind to image, source.prompt to null and preserve the supplied
  source.image_reference exactly.
- Describe the planter itself, not its background, plant, tools, packaging,
  shadows, camera or photographic environment.
- The main vessel body, base, rim/opening and cavity belong to the top-level
  body/manufacturing semantics. Do not duplicate them as feature entries such
  as rounded_body, planter_body, plant_opening, pot_opening, rim or cavity.
- Use features only for secondary visible geometry that is distinct from the
  canonical vessel body, such as ears, leaves, ribs, facial parts, applied
  ornaments, cutouts or relief details.
- Express visible geometric parts as features and spatial structure as relations.
- Use normalized anchors as semantic estimates; do not claim pixel precision.
- Use only values permitted by the supplied JSON Schema.
- Record every inferred dimension or hidden property as an assumption.
- Record uncertain visual interpretations as non-blocking ambiguities when a
  safe default exists; use a blocking ambiguity when no safe interpretation exists.
- Required features cannot be omittable.
- Manufacturing values must remain internally safe.
- manufacturing.maximum_relief_depth_mm MUST be strictly smaller than
  manufacturing.minimum_wall_mm. Prefer a conservative relief depth no greater
  than half the wall thickness when exact dimensions are not visible.
"""


@dataclass(frozen=True, slots=True)
class ImageModelResponse:
    output: dict[str, Any]
    model: str
    response_id: str


class ImageModelClient(Protocol):
    def generate_semantic_program(
        self,
        *,
        image_data_url: str,
        image_reference: str,
        system_instructions: str,
        schema: dict[str, Any],
    ) -> ImageModelResponse: ...


@dataclass(frozen=True, slots=True)
class ImageInterpretationTrace:
    interpreter_version: str
    model: str
    response_id: str
    image_sha256: str
    media_type: str
    image_bytes: int
    feature_count: int
    relation_count: int
    assumption_count: int
    ambiguity_count: int


@dataclass(frozen=True, slots=True)
class ImageInterpretationResult:
    program: DesignSemanticProgram
    trace: ImageInterpretationTrace


class ImageSemanticInterpreter:
    def __init__(
        self,
        client: ImageModelClient,
        *,
        schema_path: str | Path = DEFAULT_SCHEMA_PATH,
    ) -> None:
        self.client = client
        path = Path(schema_path).resolve()
        self.schema = json.loads(path.read_text(encoding="utf-8"))
        if self.schema.get("title") != "DOBO Design Semantic Program 3A.1":
            raise ValueError("Image interpreter requires the 3A.1 semantic schema.")

    def interpret_file(self, image_path: str | Path) -> ImageInterpretationResult:
        source = Path(image_path).resolve()
        if not source.is_file():
            raise FileNotFoundError(f"Image input does not exist: {source}")
        media_type = SUPPORTED_IMAGE_TYPES.get(source.suffix.lower())
        if media_type is None:
            raise ValueError(
                "Image input must be PNG, JPEG, WEBP or non-animated GIF."
            )
        content = source.read_bytes()
        if not content:
            raise ValueError("Image input must not be empty.")
        digest = sha256(content).hexdigest()
        image_reference = f"sha256:{digest}"
        image_data_url = (
            f"data:{media_type};base64,{b64encode(content).decode('ascii')}"
        )
        response = self.client.generate_semantic_program(
            image_data_url=image_data_url,
            image_reference=image_reference,
            system_instructions=SYSTEM_INSTRUCTIONS,
            schema=self.schema,
        )
        if not isinstance(response.output, dict):
            raise TypeError("Visual semantic model output must be a JSON object.")
        program = SemanticProgramParser().parse_dict(response.output)
        if program.source.kind != "image":
            raise ValueError("Image interpretation must set source.kind to image.")
        if program.source.prompt is not None:
            raise ValueError("Image-only interpretation must set source.prompt to null.")
        if program.source.image_reference != image_reference:
            raise ValueError("Visual model did not preserve the exact image reference.")
        trace = ImageInterpretationTrace(
            interpreter_version=IMAGE_INTERPRETER_VERSION,
            model=response.model,
            response_id=response.response_id,
            image_sha256=digest,
            media_type=media_type,
            image_bytes=len(content),
            feature_count=len(program.features),
            relation_count=len(program.relations),
            assumption_count=len(program.assumptions),
            ambiguity_count=len(program.ambiguities),
        )
        return ImageInterpretationResult(program=program, trace=trace)


class OpenAIResponsesImageClient:
    """OpenAI Responses API adapter for one image and strict semantic JSON."""

    def __init__(
        self,
        *,
        model: str,
        detail: str = "high",
        client: Any | None = None,
    ) -> None:
        if not model.strip():
            raise ValueError("OpenAI model name must not be empty.")
        if detail not in SUPPORTED_DETAIL_LEVELS:
            raise ValueError(
                f"Image detail must be one of {sorted(SUPPORTED_DETAIL_LEVELS)}."
            )
        self.model = model.strip()
        self.detail = detail
        if client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise RuntimeError(
                    "OpenAI Python SDK is required for live image interpretation."
                ) from exc
            client = OpenAI()
        self.client = client

    def generate_semantic_program(
        self,
        *,
        image_data_url: str,
        image_reference: str,
        system_instructions: str,
        schema: dict[str, Any],
    ) -> ImageModelResponse:
        api_schema = _openai_compatible_schema(schema)
        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": system_instructions},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Interpret this planter reference image. Set "
                                "source.image_reference exactly to "
                                f"'{image_reference}'."
                            ),
                        },
                        {
                            "type": "input_image",
                            "image_url": image_data_url,
                            "detail": self.detail,
                        },
                    ],
                },
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
            raise RuntimeError("OpenAI response did not contain visual semantic JSON.")
        try:
            output = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise RuntimeError("OpenAI visual semantic output was not valid JSON.") from exc
        return ImageModelResponse(
            output=output,
            model=str(getattr(response, "model", self.model)),
            response_id=str(getattr(response, "id", "unavailable")),
        )
