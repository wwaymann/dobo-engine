"""
DOBO Sketch

Line Profile Recognizer Test
"""

from __future__ import annotations

from sketch.entities import (
    LineEntity,
    SketchPoint,
)
from sketch.profiles import (
    LineProfileRecognizer,
    ProfileBuilder,
)
from sketch.sketch import Sketch


def build_rectangle_lines() -> tuple[
    LineEntity,
    ...,
]:
    """
    Creates four unordered rectangle lines.
    """

    return (
        LineEntity(
            id="bottom",
            start=SketchPoint(
                0.0,
                0.0,
            ),
            end=SketchPoint(
                20.0,
                0.0,
            ),
        ),
        LineEntity(
            id="right",
            start=SketchPoint(
                20.0,
                0.0,
            ),
            end=SketchPoint(
                20.0,
                10.0,
            ),
        ),
        LineEntity(
            id="top",
            start=SketchPoint(
                0.0,
                10.0,
            ),
            end=SketchPoint(
                20.0,
                10.0,
            ),
        ),
        LineEntity(
            id="left",
            start=SketchPoint(
                0.0,
                10.0,
            ),
            end=SketchPoint(
                0.0,
                0.0,
            ),
        ),
    )


def main() -> None:
    lines = build_rectangle_lines()

    recognition = (
        LineProfileRecognizer().recognize(
            lines
        )
    )

    if recognition.count != 1:
        raise RuntimeError(
            "Expected one recognized profile."
        )

    recognized_profile = (
        recognition.profiles[0]
    )

    if recognized_profile.area != 200.0:
        raise RuntimeError(
            "Recognized area is incorrect."
        )

    if recognized_profile.perimeter != 60.0:
        raise RuntimeError(
            "Recognized perimeter is incorrect."
        )

    sketch = Sketch(
        name="Independent Line Rectangle",
    )

    for line in lines:
        sketch.add_entity(
            line
        )

    profiles = ProfileBuilder().build(
        sketch
    )

    profiles.validate()

    print()
    print("DOBO Line Profile Recognizer")
    print("----------------------------")
    print(
        "Lines:",
        len(
            lines
        ),
    )
    print(
        "Recognized profiles:",
        recognition.count,
    )
    print(
        "Used lines:",
        recognition.used_entity_ids,
    )
    print(
        "Ignored lines:",
        recognition.ignored_entity_ids,
    )
    print(
        "Profile points:",
        recognized_profile.point_count,
    )
    print(
        "Profile area:",
        recognized_profile.area,
    )
    print(
        "Profile perimeter:",
        recognized_profile.perimeter,
    )
    print(
        "Profile centroid:",
        recognized_profile.centroid,
    )
    print(
        "Builder profiles:",
        profiles.count,
    )
    print("Valid: OK")
    print()


if __name__ == "__main__":
    main()