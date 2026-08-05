from sketch import (
    CircleEntity,
    LineEntity,
    Sketch,
    SketchPoint,
)


def main() -> None:
    sketch = Sketch(
        name="DOBO Sketch Test",
        metadata={
            "test": True,
        },
    )

    sketch.add_entity(
        LineEntity(
            id="line_1",
            start=SketchPoint(
                0.0,
                0.0,
            ),
            end=SketchPoint(
                20.0,
                0.0,
            ),
        )
    )

    sketch.add_entity(
        LineEntity(
            id="line_2",
            start=SketchPoint(
                20.0,
                0.0,
            ),
            end=SketchPoint(
                20.0,
                10.0,
            ),
        )
    )

    sketch.add_entity(
        CircleEntity(
            id="circle_1",
            center=SketchPoint(
                5.0,
                5.0,
            ),
            radius=3.0,
        )
    )

    sketch.validate()

    first_line = sketch.get_entity(
        "line_1"
    )

    if not isinstance(
        first_line,
        LineEntity,
    ):
        raise RuntimeError(
            "Expected LineEntity."
        )

    print()
    print("DOBO Sketch")
    print("-----------")
    print(
        "Name:",
        sketch.name,
    )
    print(
        "Entities:",
        sketch.count,
    )
    print(
        "Lines:",
        sketch.line_count,
    )
    print(
        "Circles:",
        sketch.circle_count,
    )
    print(
        "First line length:",
        first_line.length,
    )
    print(
        "Bounds:",
        sketch.bounds,
    )
    print("Valid: OK")
    print()


if __name__ == "__main__":
    main()