from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

import cadquery as cq

from kernel.contracts.boolean_request import (
    BooleanOperation,
    BooleanRequest,
)
from kernel.contracts.model_state import (
    ModelState,
)
from kernel.geometry.solid_factory import (
    SolidFactory,
)
from kernel.services.boolean_engine import (
    BooleanEngine,
)

from product_generators.surface_mapping.document_mapper import (
    VectorSurfaceMapper,
)
from product_generators.vector_geometry.svg_parser import (
    SvgVectorParser,
)

from .closed_feature_solid import (
    ClosedSurfaceFeatureSolidBuilder,
)
from .topology import (
    SurfaceFeatureTopologyAnalyzer,
)


class SurfaceFeatureMode(str, Enum):
    EMBOSS = "emboss"
    DEBOSS = "deboss"


class SurfaceSampler(Protocol):
    def sample(self, u: float, v: float):
        ...


@dataclass(frozen=True, slots=True)
class SurfaceFeaturePipelineResult:
    mode: SurfaceFeatureMode
    base_volume: float
    final_volume: float
    feature_solid_count: int
    shape: cq.Shape

    def validate(self) -> None:
        if not isinstance(self.mode, SurfaceFeatureMode):
            raise TypeError("mode must be SurfaceFeatureMode.")

        if self.base_volume <= 0.0:
            raise ValueError("base_volume must be positive.")

        if self.final_volume <= 0.0:
            raise ValueError("final_volume must be positive.")

        if self.feature_solid_count < 1:
            raise ValueError(
                "feature_solid_count must be positive."
            )

        if not isinstance(self.shape, cq.Shape):
            raise TypeError("shape must be a CadQuery Shape.")

        if not self.shape.isValid():
            raise RuntimeError(
                "Surface feature pipeline produced invalid geometry."
            )

        if self.mode is SurfaceFeatureMode.EMBOSS:
            if self.final_volume <= self.base_volume:
                raise RuntimeError(
                    "Emboss must increase model volume."
                )

        if self.mode is SurfaceFeatureMode.DEBOSS:
            if self.final_volume >= self.base_volume:
                raise RuntimeError(
                    "Deboss must decrease model volume."
                )


class SurfaceFeaturePipeline:
    """
    Integration pipeline:

    SVG
      -> VectorDocument
      -> TopologyDocument
      -> mapped contour
      -> closed feature prisms
      -> Kernel BooleanEngine
      -> final CAD shape

    Phase 3.3.1 supports one outer loop intentionally.
    Hole/island boolean composition is the next integration step.
    """

    def __init__(self) -> None:
        self._svg = SvgVectorParser()
        self._topology = SurfaceFeatureTopologyAnalyzer()
        self._mapper = VectorSurfaceMapper()
        self._feature_builder = ClosedSurfaceFeatureSolidBuilder()
        self._boolean = BooleanEngine()

    def apply_svg(
        self,
        *,
        svg: str,
        document_id: str,
        surface: SurfaceSampler,
        base_shape: cq.Shape,
        mode: SurfaceFeatureMode,
        depth: float,
        u_offset: float = 0.0,
        v_offset: float = 0.0,
    ) -> SurfaceFeaturePipelineResult:
        if not isinstance(mode, SurfaceFeatureMode):
            raise TypeError("mode must be SurfaceFeatureMode.")

        if depth <= 0.0:
            raise ValueError("depth must be positive.")

        if not isinstance(base_shape, cq.Shape):
            raise TypeError("base_shape must be a CadQuery Shape.")

        if not base_shape.isValid():
            raise ValueError("base_shape must be valid.")

        document = self._svg.parse_string(
            svg,
            document_id=document_id,
        )

        topology = self._topology.analyze(
            document
        )

        if len(topology.outer_loops) != 1:
            raise ValueError(
                "Phase 3.3.1 pipeline requires exactly one outer loop."
            )

        if topology.holes or topology.islands:
            raise ValueError(
                "Phase 3.3.1 does not yet compose holes/islands."
            )

        mapped = self._mapper.map_document(
            document,
            surface,
            u_offset=u_offset,
            v_offset=v_offset,
        )

        if len(mapped) != 1:
            raise RuntimeError(
                "Expected exactly one mapped contour."
            )

        feature_result = self._feature_builder.build(
            mapped[0],
            depth=float(depth),
            inward=(
                mode
                is SurfaceFeatureMode.DEBOSS
            ),
        )

        feature_result.validate()

        feature_solids = tuple(
            feature_result.shape.Solids()
        )

        if not feature_solids:
            raise RuntimeError(
                "Closed feature produced no solids."
            )

        base_solid = SolidFactory.from_shape(
            geometry=base_shape.clean(),
            source="surface_feature_pipeline:base",
            metadata={
                "document_id": document_id,
            },
        )

        state = ModelState(
            solid=base_solid,
            metadata={
                "pipeline": "surface_feature",
                "document_id": document_id,
            },
        )
        state.validate()

        base_volume = float(
            base_solid.volume
        )

        operation = (
            BooleanOperation.UNION
            if mode is SurfaceFeatureMode.EMBOSS
            else BooleanOperation.CUT
        )

        applied_count = 0

        for index, geometry in enumerate(
            feature_solids
        ):
            if not geometry.isValid():
                raise RuntimeError(
                    f"Feature solid {index} is invalid."
                )

            operand = SolidFactory.from_shape(
                geometry=geometry.clean(),
                source="surface_feature_pipeline:feature",
                metadata={
                    "document_id": document_id,
                    "feature_index": index,
                    "mode": mode.value,
                },
            )

            request = BooleanRequest(
                id=(
                    f"{document_id}:"
                    f"{mode.value}:{index}"
                ),
                operation=operation,
                operand=operand,
                tolerance=0.01,
                metadata={
                    "surface_feature": True,
                    "mode": mode.value,
                    "feature_index": index,
                },
            )
            request.validate()

            state = self._boolean.apply(
                state,
                request,
            )

            applied_count += 1

        if state.solid is None:
            raise RuntimeError(
                "Surface feature pipeline lost the model solid."
            )

        state.solid.validate()

        result = SurfaceFeaturePipelineResult(
            mode=mode,
            base_volume=base_volume,
            final_volume=float(
                state.solid.volume
            ),
            feature_solid_count=applied_count,
            shape=state.solid.geometry,
        )
        result.validate()
        return result
