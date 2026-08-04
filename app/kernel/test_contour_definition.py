from kernel.contracts.contour_definition import (
    ContourDefinition,
)
from kernel.contracts.contour_definition_set import (
    ContourDefinitionSet,
)


def main() -> None:

    contour = ContourDefinition(
        points=(
            (0.0, 0.0),
            (20.0, 0.0),
            (20.0, 10.0),
            (0.0, 10.0),
        ),
        closed=True,
        source="unit-test",
    )

    contour.validate()

    contour_set = ContourDefinitionSet(
        contours=(contour,),
        source="unit-test",
    )

    contour_set.validate()

    print()
    print("DOBO ContourDefinition")
    print("----------------------")
    print("Contours:", contour_set.count)
    print("Points:", contour_set.point_count)
    print("Bounds:", contour_set.bounds)
    print("Valid: OK")
    print()


if __name__ == "__main__":
    main()