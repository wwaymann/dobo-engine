from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from .image_interpreter import (
    OpenAIResponsesImageClient,
    ImageSemanticInterpreter,
    SUPPORTED_DETAIL_LEVELS,
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Interpret a DOBO reference image as Semantic Program 3A.1."
    )
    parser.add_argument("image", type=Path, help="Local planter reference image.")
    parser.add_argument(
        "--model",
        default=os.environ.get("DOBO_OPENAI_MODEL"),
        help="OpenAI vision-capable model; defaults to DOBO_OPENAI_MODEL.",
    )
    parser.add_argument(
        "--detail",
        choices=sorted(SUPPORTED_DETAIL_LEVELS),
        default="high",
        help="Image understanding detail level; defaults to high.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional destination JSON path; stdout is used when omitted.",
    )
    arguments = parser.parse_args()
    if not arguments.model:
        parser.error("--model or DOBO_OPENAI_MODEL is required")
    return arguments


def main() -> None:
    arguments = _arguments()
    client = OpenAIResponsesImageClient(
        model=arguments.model,
        detail=arguments.detail,
    )
    result = ImageSemanticInterpreter(client).interpret_file(arguments.image)
    encoded = json.dumps(
        result.program.to_dict(),
        indent=2,
        ensure_ascii=False,
    ) + "\n"
    if arguments.output is None:
        print(encoded, end="")
    else:
        target = arguments.output.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(encoded, encoding="utf-8")
        print(target)
    print(
        "trace",
        result.trace.model,
        result.trace.response_id,
        result.trace.image_sha256,
        result.trace.media_type,
        result.trace.image_bytes,
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
