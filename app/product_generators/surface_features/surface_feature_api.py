from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

import cadquery as cq

from kernel.contracts.boolean_request import (
    BooleanOperation,
    BooleanRequest,
)
from kernel.contracts.model_state import ModelState
from kernel.geometry.solid_factory import SolidFactory
from kernel.services.boolean_engine import BooleanEngine

from product_generators.surface_mapping.document_mapper import (
    VectorSurfaceMapper,
)
from product_generators.vector_geometry.contracts import (
    VectorContour,
    VectorDocument,
)
from product_generators.vector_geometry.svg_parser import (
    SvgVectorParser,
)

from .closed_feature_solid import (
    ClosedSurfaceFeatureSolidBuilder,
)
from .contracts import (
    TopologyLoop,
    TopologyRole,
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
class SurfaceFeatureApplicationResult:
    mode: SurfaceFeatureMode
    shape: cq.Shape
    base_volume: float
    final_volume: float
    loop_count: int
    boolean_count: int

    def validate(self) -> None:
        if not isinstance(self.mode, SurfaceFeatureMode):
            raise TypeError("mode must be SurfaceFeatureMode.")

        if not isinstance(self.shape, cq.Shape):
            raise TypeError("shape must be a CadQuery Shape.")

        if not self.shape.isValid():
            raise RuntimeError(
                "Surface feature result contains invalid geometry."
            )

        if self.base_volume <= 0.0 or self.final_volume <= 0.0:
            raise ValueError("Volumes must be positive.")

        if self.loop_count < 1:
            raise ValueError("loop_count must be positive.")

        if self.boolean_count < 1:
            raise ValueError("boolean_count must be positive.")


class SurfaceFeatureAPI:
    """
    Reusable surface-decoration API.

    Important topology rule:

    Topology is composed into ONE feature tool first:

        outer - hole + island - nested_hole ...

    Only after that tool is valid do we apply it to the model:

        EMBOSS -> UNION
        DEBOSS -> CUT

    This prevents hole/island operations from modifying the base body
    directly and avoids invalid intermediate model states.
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
        base_shape: cq.Shape,
        surface: SurfaceSampler,
        mode: SurfaceFeatureMode,
        depth: float,
        document_id: str = "surface_feature",
        u_offset: float = 0.0,
        v_offset: float = 0.0,
        scale_u: float = 1.0,
        scale_v: float = 1.0,
    ) -> SurfaceFeatureApplicationResult:
        document = self._svg.parse_string(
            svg,
            document_id=document_id,
        )

        return self.apply_document(
            document=document,
            base_shape=base_shape,
            surface=surface,
            mode=mode,
            depth=depth,
            u_offset=u_offset,
            v_offset=v_offset,
            scale_u=scale_u,
            scale_v=scale_v,
        )

    def apply_document(
        self,
        *,
        document: VectorDocument,
        base_shape: cq.Shape,
        surface: SurfaceSampler,
        mode: SurfaceFeatureMode,
        depth: float,
        u_offset: float = 0.0,
        v_offset: float = 0.0,
        scale_u: float = 1.0,
        scale_v: float = 1.0,
    ) -> SurfaceFeatureApplicationResult:
        document.validate()

        if not isinstance(base_shape, cq.Shape):
            raise TypeError("base_shape must be a CadQuery Shape.")

        if not base_shape.isValid():
            raise ValueError("base_shape must be valid.")

        if not isinstance(mode, SurfaceFeatureMode):
            raise TypeError("mode must be SurfaceFeatureMode.")

        depth = float(depth)

        if depth <= 0.0:
            raise ValueError("depth must be positive.")

        topology = self._topology.analyze(document)

        contour_by_id = {
            contour.id: contour
            for contour in document.contours
        }

        # Every topology loop must point in the same physical direction.
        # Holes are removed from the feature TOOL, not from the base model.
        inward = (
            mode is SurfaceFeatureMode.DEBOSS
        )

        loop_shapes: dict[str, cq.Shape] = {}

        ordered_loops = tuple(
            sorted(
                topology.loops,
                key=lambda loop: (
                    loop.depth,
                    -abs(loop.signed_area),
                ),
            )
        )

        for loop in ordered_loops:
            contour = contour_by_id.get(loop.id)

            if contour is None:
                raise RuntimeError(
                    f"Missing VectorContour for topology loop '{loop.id}'."
                )

            mapped_contour = self._map_single_contour(
                contour=contour,
                surface=surface,
                u_offset=u_offset,
                v_offset=v_offset,
                scale_u=scale_u,
                scale_v=scale_v,
            )

            feature = self._feature_builder.build(
                mapped_contour,
                depth=depth,
                inward=inward,
            )
            feature.validate()

            loop_shapes[loop.id] = self._merge_triangle_solids(
                feature.shape,
                loop_id=loop.id,
            )

        tool_shape = self._compose_topology_tool(
            loops=ordered_loops,
            loop_shapes=loop_shapes,
        )

        if not tool_shape.isValid():
            raise RuntimeError(
                "Composed surface-feature tool is invalid."
            )

        tool_volume = float(tool_shape.Volume())

        if tool_volume <= 0.0:
            raise RuntimeError(
                "Composed surface-feature tool has zero volume."
            )

        base_solid = SolidFactory.from_shape(
            geometry=base_shape.clean(),
            source="surface_feature_api:base",
            metadata={
                "document_id": document.id,
            },
        )

        tool_solid = SolidFactory.from_shape(
            geometry=tool_shape.clean(),
            source="surface_feature_api:tool",
            metadata={
                "document_id": document.id,
                "loop_count": len(topology.loops),
            },
        )

        state = ModelState(
            solid=base_solid,
            metadata={
                "surface_feature_api": True,
                "document_id": document.id,
            },
        )
        state.validate()

        operation = (
            BooleanOperation.UNION
            if mode is SurfaceFeatureMode.EMBOSS
            else BooleanOperation.CUT
        )

        request = BooleanRequest(
            id=f"{document.id}:{mode.value}:final",
            operation=operation,
            operand=tool_solid,
            tolerance=0.01,
            metadata={
                "surface_feature_api": True,
                "mode": mode.value,
                "loop_count": len(topology.loops),
            },
        )
        request.validate()

        final_state = self._boolean.apply(
            state,
            request,
        )

        if final_state.solid is None:
            raise RuntimeError(
                "SurfaceFeatureAPI produced no final solid."
            )

        final_state.solid.validate()

        result = SurfaceFeatureApplicationResult(
            mode=mode,
            shape=final_state.solid.geometry,
            base_volume=float(base_solid.volume),
            final_volume=float(final_state.solid.volume),
            loop_count=len(topology.loops),
            boolean_count=1,
        )
        result.validate()
        return result

    def _map_single_contour(
        self,
        *,
        contour: VectorContour,
        surface: SurfaceSampler,
        u_offset: float,
        v_offset: float,
        scale_u: float,
        scale_v: float,
    ):
        document = VectorDocument(
            id=f"{contour.id}:single",
            contours=(contour,),
            source="surface_feature_api",
        )
        document.validate()

        return self._mapper.map_document(
            document,
            surface,
            u_offset=u_offset,
            v_offset=v_offset,
            scale_u=scale_u,
            scale_v=scale_v,
        )[0]

    @staticmethod
    def _merge_triangle_solids(
        shape: cq.Shape,
        *,
        loop_id: str,
    ) -> cq.Shape:
        solids = tuple(
            shape.Solids()
        )

        if not solids:
            raise RuntimeError(
                f"Loop '{loop_id}' produced no solids."
            )

        merged: cq.Shape = solids[0]

        for index, solid in enumerate(
            solids[1:],
            start=1,
        ):
            try:
                merged = merged.fuse(
                    solid,
                    tol=0.001,
                ).clean()
            except Exception as error:
                raise RuntimeError(
                    f"Could not merge triangle solid {index} "
                    f"for loop '{loop_id}'."
                ) from error

            if not merged.isValid():
                raise RuntimeError(
                    f"Merged loop '{loop_id}' became invalid "
                    f"at triangle {index}."
                )

        return merged.clean()

    @staticmethod
    def _compose_topology_tool(
        *,
        loops: tuple[TopologyLoop, ...],
        loop_shapes: dict[str, cq.Shape],
    ) -> cq.Shape:
        root_loops = tuple(
            loop
            for loop in loops
            if loop.depth == 0
        )

        if not root_loops:
            raise RuntimeError(
                "Topology contains no outer loops."
            )

        root_shapes: list[cq.Shape] = []

        for root in root_loops:
            shape = loop_shapes[root.id]

            descendants = tuple(
                loop
                for loop in loops
                if SurfaceFeatureAPI._belongs_to_root(
                    loop=loop,
                    root_id=root.id,
                    loops=loops,
                )
                and loop.id != root.id
            )

            for loop in sorted(
                descendants,
                key=lambda item: item.depth,
            ):
                child_shape = loop_shapes[
                    loop.id
                ]

                try:
                    if loop.depth % 2 == 1:
                        shape = shape.cut(
                            child_shape,
                            tol=0.001,
                        ).clean()
                    else:
                        shape = shape.fuse(
                            child_shape,
                            tol=0.001,
                        ).clean()
                except Exception as error:
                    raise RuntimeError(
                        f"Could not compose topology loop "
                        f"'{loop.id}' at depth {loop.depth}."
                    ) from error

                if not shape.isValid():
                    raise RuntimeError(
                        f"Topology composition became invalid "
                        f"after loop '{loop.id}'."
                    )

            root_shapes.append(
                shape
            )

        tool = root_shapes[0]

        for index, shape in enumerate(
            root_shapes[1:],
            start=1,
        ):
            try:
                tool = tool.fuse(
                    shape,
                    tol=0.001,
                ).clean()
            except Exception as error:
                raise RuntimeError(
                    f"Could not merge root feature {index}."
                ) from error

            if not tool.isValid():
                raise RuntimeError(
                    "Merged topology tool became invalid."
                )

        return tool.clean()

    @staticmethod
    def _belongs_to_root(
        *,
        loop: TopologyLoop,
        root_id: str,
        loops: tuple[TopologyLoop, ...],
    ) -> bool:
        by_id = {
            item.id: item
            for item in loops
        }

        current = loop

        while current.parent_id is not None:
            parent = by_id.get(
                current.parent_id
            )

            if parent is None:
                raise RuntimeError(
                    f"Missing topology parent "
                    f"'{current.parent_id}'."
                )

            if parent.id == root_id:
                return True

            current = parent

        return loop.id == root_id
