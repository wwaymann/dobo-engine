from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from .prompt_interpreter import (
    OpenAIResponsesSemanticClient,
    PromptSemanticInterpreter,
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Interpret a DOBO design prompt as Semantic Program 3A.1."
    )
    parser.add_argument("prompt", help="Natural-language planter design prompt.")
    parser.add_argument(
        "--model",
        default=os.environ.get("DOBO_OPENAI_MODEL"),
        help="OpenAI model name; defaults to DOBO_OPENAI_MODEL.",
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
    client = OpenAIResponsesSemanticClient(model=arguments.model)
    result = PromptSemanticInterpreter(client).interpret(arguments.prompt)
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
        result.trace.prompt_sha256,
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
