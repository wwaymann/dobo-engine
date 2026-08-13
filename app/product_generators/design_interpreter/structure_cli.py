from __future__ import annotations

import argparse

from .semantic_parser import SemanticProgramParser
from .structural_vocabulary import StructuralVocabularyResolver


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Resolve Semantic Program 3A.1 into structural vocabulary 4A.1."
    )
    parser.add_argument("input", help="Input Semantic Program JSON.")
    parser.add_argument("--output", required=True, help="Structural JSON output.")
    arguments = parser.parse_args()
    semantic = SemanticProgramParser().parse_file(arguments.input)
    structural = StructuralVocabularyResolver.resolve(semantic)
    output = structural.write_json(arguments.output)
    print(output)
    print("vocabulary", structural.vocabulary_version, "OK")
    print("features", len(structural.features), "OK")
    print("groups", len(structural.groups), "OK")


if __name__ == "__main__":
    main()
