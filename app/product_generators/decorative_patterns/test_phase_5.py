from __future__ import annotations

from .generator import DecorativePatternGenerator
from .specification import PatternSpecification


CASES = (
    PatternSpecification(
        id="grid_test",
        pattern="grid",
        width=100.0,
        height=100.0,
        element_width=10.0,
        element_height=10.0,
        spacing_x=4.0,
        spacing_y=4.0,
        rows=4,
        columns=5,
    ),
    PatternSpecification(
        id="brick_test",
        pattern="brick",
        width=100.0,
        height=100.0,
        element_width=14.0,
        element_height=8.0,
        spacing_x=3.0,
        spacing_y=3.0,
        rows=4,
        columns=5,
    ),
    PatternSpecification(
        id="diamond_test",
        pattern="diamond",
        width=100.0,
        height=100.0,
        element_width=12.0,
        element_height=12.0,
        spacing_x=4.0,
        spacing_y=4.0,
        rows=4,
        columns=5,
    ),
    PatternSpecification(
        id="chevron_test",
        pattern="chevron",
        width=100.0,
        height=100.0,
        element_width=16.0,
        element_height=12.0,
        spacing_x=4.0,
        spacing_y=4.0,
        rows=3,
        columns=4,
    ),
    PatternSpecification(
        id="hex_test",
        pattern="hex",
        width=100.0,
        height=100.0,
        element_width=14.0,
        element_height=12.0,
        spacing_x=3.0,
        spacing_y=3.0,
        rows=4,
        columns=5,
    ),
    PatternSpecification(
        id="wave_test",
        pattern="wave_band",
        width=100.0,
        height=60.0,
        element_width=10.0,
        element_height=12.0,
        spacing_x=4.0,
        spacing_y=10.0,
        rows=3,
        columns=3,
    ),
)


def main() -> None:
    generator = DecorativePatternGenerator()

    print()
    print("DOBO Decorative Patterns - Phase 5")
    print("---------------------------------")

    completed = 0

    for specification in CASES:
        definitions = generator.generate(
            specification
        )

        if not definitions:
            raise RuntimeError(
                f"{specification.pattern}: no definitions."
            )

        for definition in definitions:
            definition.validate()

        print(
            specification.pattern,
            len(definitions),
            "elements",
            "OK",
        )

        completed += 1

    print("---------------------------------")
    print("Patterns:", completed)
    print("Phase 5: Valid OK")
    print()


if __name__ == "__main__":
    main()
