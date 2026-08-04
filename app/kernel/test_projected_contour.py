from kernel.contracts.projected_contour import (
    ProjectedContour,
)
from kernel.contracts.projected_contour_set import (
    ProjectedContourSet,
)
from kernel.contracts.projected_point import (
    ProjectedPoint,
)


def main() -> None:

    contour = ProjectedContour(
        points=(
            ProjectedPoint(
                0,
                0,
                0,
            ),
            ProjectedPoint(
                20,
                0,
                0,
            ),
            ProjectedPoint(
                20,
                20,
                0,
            ),
            ProjectedPoint(
                0,
                20,
                0,
            ),
        )
    )

    contour.validate()

    contour_set = ProjectedContourSet(
        contours=(
            contour,
        )
    )

    contour_set.validate()

    print()
    print("DOBO Projected Contour")
    print("----------------------")
    print("Contours:", contour_set.count)
    print("Points:", contour_set.point_count)
    print("Valid: OK")
    print()


if __name__ == "__main__":
    main()