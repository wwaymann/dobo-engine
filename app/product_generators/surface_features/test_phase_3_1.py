from __future__ import annotations

from product_generators.vector_geometry.contracts import (
    VectorContour,
    VectorDocument,
)
from product_generators.vector_geometry.svg_parser import (
    SvgVectorParser,
)

from .contracts import (
    TopologyRole,
)
from .topology import (
    SurfaceFeatureTopologyAnalyzer,
)


def main() -> None:
    print()
    print(
        "DOBO Advanced Geometry - Phase 3.1"
    )
    print(
        "Surface Feature Topology"
    )
    print(
        "-----------------------------------"
    )

    analyzer = (
        SurfaceFeatureTopologyAnalyzer()
    )

    nested = VectorDocument(
        id="nested_test",
        contours=(
            VectorContour(
                id="outer",
                points=(
                    (0.0, 0.0),
                    (100.0, 0.0),
                    (100.0, 100.0),
                    (0.0, 100.0),
                ),
            ),
            VectorContour(
                id="hole",
                points=(
                    (20.0, 20.0),
                    (80.0, 20.0),
                    (80.0, 80.0),
                    (20.0, 80.0),
                ),
            ),
            VectorContour(
                id="island",
                points=(
                    (40.0, 40.0),
                    (60.0, 40.0),
                    (60.0, 60.0),
                    (40.0, 60.0),
                ),
            ),
        ),
        source="test",
    )

    topology = analyzer.analyze(
        nested
    )

    assert len(
        topology.outer_loops
    ) == 1

    assert len(
        topology.holes
    ) == 1

    assert len(
        topology.islands
    ) == 1

    assert (
        topology.outer_loops[0].role
        is TopologyRole.OUTER
    )

    assert (
        topology.holes[0].parent_id
        == "outer"
    )

    assert (
        topology.islands[0].parent_id
        == "hole"
    )

    print(
        "Nested outer/hole/island: OK"
    )

    svg = """
    <svg xmlns="http://www.w3.org/2000/svg">
      <rect x="0" y="0" width="100" height="100"/>
      <rect x="20" y="20" width="60" height="60"/>
      <rect x="40" y="40" width="20" height="20"/>
    </svg>
    """

    document = (
        SvgVectorParser()
        .parse_string(
            svg,
            document_id=(
                "svg_topology"
            ),
        )
    )

    svg_topology = (
        analyzer.analyze(
            document
        )
    )

    print(
        "SVG loops:",
        len(
            svg_topology.loops
        ),
        "OK",
    )

    for loop in (
        svg_topology.loops
    ):
        print(
            loop.id,
            "depth",
            loop.depth,
            "role",
            loop.role.value,
            "parent",
            loop.parent_id,
        )

    print(
        "-----------------------------------"
    )
    print(
        "Phase 3.1: Valid OK"
    )
    print()


if __name__ == "__main__":
    main()
