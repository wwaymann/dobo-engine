from __future__ import annotations

from product_generators.vector_geometry.contracts import (
    VectorDocument,
)

from .contour_classifier import (
    ContourRoleClassifier,
)
from .contracts import (
    TopologyDocument,
    TopologyLoop,
)
from .nesting_detector import (
    ContourNestingDetector,
)
from .winding import (
    signed_area,
)


class SurfaceFeatureTopologyAnalyzer:
    """
    Converts VectorDocument contours into
    explicit nested topology.
    """

    def __init__(
        self,
    ) -> None:
        self._nesting = (
            ContourNestingDetector()
        )

        self._classifier = (
            ContourRoleClassifier()
        )

    def analyze(
        self,
        document: VectorDocument,
    ) -> TopologyDocument:
        document.validate()

        closed = tuple(
            contour
            for contour in document.contours
            if contour.closed
        )

        if not closed:
            raise ValueError(
                "Topology analysis requires "
                "at least one closed contour."
            )

        relations = (
            self._nesting.detect(
                closed
            )
        )

        relation_by_id = {
            relation.child_id: relation
            for relation in relations
        }

        loops: list[
            TopologyLoop
        ] = []

        for contour in closed:
            relation = (
                relation_by_id[
                    contour.id
                ]
            )

            loop = TopologyLoop(
                id=contour.id,
                points=contour.points,
                signed_area=signed_area(
                    contour.points
                ),
                depth=relation.depth,
                role=(
                    self._classifier
                    .classify(
                        relation.depth
                    )
                ),
                parent_id=(
                    relation.parent_id
                ),
            )

            loop.validate()

            loops.append(
                loop
            )

        result = TopologyDocument(
            id=(
                f"{document.id}:topology"
            ),
            loops=tuple(
                loops
            ),
        )

        result.validate()

        return result
