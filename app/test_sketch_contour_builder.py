from sketch import (
    CircleEntity,
    PolylineEntity,
    Sketch,
    SketchContourBuilder,
    SketchPoint,
)


def main() -> None:
    sketch = Sketch(
        name="Sketch Contour Test",
    )

    sketch.add_entity(
        PolylineEntity(
            id="rectangle",
            points=(
                SketchPoint(
                    0.0,
                    0.0,
                ),
                SketchPoint(
                    20.0,
                    0.0,
                ),
                SketchPoint(
                    20.0,
                    10.0,
                ),
                SketchPoint(
                    0.0,
                    10.0,
                ),
            ),
            closed=True,
        )
    )

    sketch.add_entity(
        CircleEntity(
            id="circle",
            center=SketchPoint(
                30.0,
                5.0,
            ),
            radius=5.0,
        )
    )

    sketch.validate()

    contours = SketchContourBuilder().build(
        sketch,
        circle_samples=64,
    )

    contours.validate()

    rectangle = contours.contours[0]
    circle = contours.contours[1]

    print()
    print("DOBO Sketch Contour Builder")
    print("---------------------------")
    print(
        "Sketch entities:",
        sketch.count,
    )
    print(
        "Polylines:",
        sketch.polyline_count,
    )
    print(
        "Circles:",
        sketch.circle_count,
    )
    print(
        "Contours:",
        contours.count,
    )
    print(
        "Points:",
        contours.point_count,
    )
    print(
        "Rectangle points:",
        len(
            rectangle.points
        ),
    )
    print(
        "Circle points:",
        len(
            circle.points
        ),
    )
    print(
        "Bounds:",
        contours.bounds,
    )
    print("Valid: OK")
    print()


if __name__ == "__main__":
    main()