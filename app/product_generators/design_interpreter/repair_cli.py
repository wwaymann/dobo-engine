from __future__ import annotations

import argparse

from .proposal_repair import SemanticProposalRepairer


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and deterministically repair a DOBO Semantic Program 3A.1."
        )
    )
    parser.add_argument("input", help="Input Semantic Program JSON.")
    parser.add_argument(
        "--output",
        required=True,
        help="Destination for the repaired Semantic Program JSON.",
    )
    parser.add_argument(
        "--report",
        help="Optional destination for the machine-readable repair report.",
    )
    return parser.parse_args()


def main() -> None:
    arguments = _arguments()
    result = SemanticProposalRepairer().repair_file(arguments.input)
    output = result.write_program(arguments.output)
    print(output)
    if arguments.report:
        print(result.write_report(arguments.report))
    print(
        "repair",
        result.report.repair_version,
        "changed",
        result.report.changed,
        "actions",
        len(result.report.actions),
        "attempts",
        result.report.attempts,
    )
    print("ready for compilation", result.report.ready_for_compilation, "OK")


if __name__ == "__main__":
    main()
