from kernel.contracts.offset_contour import (
    OffsetContour,
)
from kernel.contracts.offset_contour_set import (
    OffsetContourSet,
)
from kernel.contracts.offset_point import (
    OffsetPoint,
)
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
    projected_contour = ProjectedContour(
        points=(
            ProjectedPoint(
                0.0,
                0.0,
                0.0,
            ),
            ProjectedPoint(
                10.0,
                0.0,
                0.0,
            ),
            ProjectedPoint(
                10.0,
                10.0,
                0.0,
            ),
            ProjectedPoint(
                0.0,
                10.0,
                0.0,
            ),
        ),
        normals=(
            (
                0.0,
                0.0,
                1.0,
            ),
            (
                0.0,
                0.0,
                1.0,
            ),
            (
                0.0,
                0.0,
                1.0,
            ),
            (
                0.0,
                0.0,
                1.0,
            ),
        ),
    )

    projected_set = ProjectedContourSet(
        contours=(projected_contour,),
    )

    offset_contour = OffsetContour(
        points=tuple(
            OffsetPoint(
                source=point,
                normal=normal,
                inner=point,
                outer=ProjectedPoint(
                    point.x,
                    point.y,
                    point.z + 2.0,
                ),
                distance=2.0,
            )
            for point, normal in zip(
                projected_contour.points,
                projected_contour.normals,
                strict=True,
            )
        ),
    )

    offset_set = OffsetContourSet(
        contours=(offset_contour,),
        source=projected_set,
    )

    offset_set.validate()

    print()
    print("DOBO Offset Contracts")
    print("---------------------")
    print(
        "Contours:",
        offset_set.count,
    )
    print(
        "Points:",
        offset_set.point_count,
    )
    print(
        "First inner:",
        offset_contour.inner_points[0],
    )
    print(
        "First outer:",
        offset_contour.outer_points[0],
    )
    print("Valid: OK")
    print()


if __name__ == "__main__":
    main()
