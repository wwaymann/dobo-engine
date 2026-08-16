from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class GeometryRepresentation(str, Enum):
    BREP = "brep"
    MESH = "mesh"
    DOCUMENT = "document"
    POST_GEOMETRY = "post_geometry"


class Capability(str, Enum):
    MORPHOLOGY = "morphology"
    TEXT = "text"
    SURFACE_RELIEF = "surface_relief"
    DECORATION = "decoration"
    BOOLEAN = "boolean"
    EXTRUDE = "extrude"
    REVOLVE = "revolve"
    LOFT = "loft"
    SWEEP = "sweep"
    SHELL = "shell"
    NEGATIVE_VOLUME = "negative_volume"
    DRAINAGE = "drainage"
    MULTICOLOR = "multicolor"
    MANUFACTURABILITY = "manufacturability"
    STL = "stl"
    THREE_MF = "3mf"
    RENDER = "render"


@dataclass(frozen=True, slots=True)
class CapabilityProvider:
    name: str
    module: str
    representation: GeometryRepresentation
    capabilities: frozenset[Capability]
    active: bool = True
    historical: bool = False


@dataclass(frozen=True, slots=True)
class CompositionPlan:
    requested: frozenset[Capability]
    providers: tuple[CapabilityProvider, ...]
    covered: frozenset[Capability]
    missing: frozenset[Capability]
    geometry_representations: frozenset[GeometryRepresentation]
    bridge_required: bool

    @property
    def complete(self) -> bool:
        return not self.missing

    @property
    def executable_without_bridge(self) -> bool:
        return self.complete and not self.bridge_required

    def validate_coverage(self) -> None:
        if self.missing:
            names = ", ".join(sorted(cap.value for cap in self.missing))
            raise RuntimeError(f"DOBO capability loss detected: {names}")


DEFAULT_PROVIDERS: tuple[CapabilityProvider, ...] = (
    CapabilityProvider(
        name="morphological-engine",
        module="product_generators.organic_shapes.hierarchy_engine",
        representation=GeometryRepresentation.MESH,
        capabilities=frozenset(
            {
                Capability.MORPHOLOGY,
                Capability.NEGATIVE_VOLUME,
                Capability.DRAINAGE,
                Capability.STL,
            }
        ),
    ),
    CapabilityProvider(
        name="cad-kernel-v2",
        module="kernel.geometry",
        representation=GeometryRepresentation.BREP,
        capabilities=frozenset(
            {
                Capability.BOOLEAN,
                Capability.EXTRUDE,
                Capability.REVOLVE,
                Capability.LOFT,
                Capability.SWEEP,
                Capability.SHELL,
            }
        ),
    ),
    CapabilityProvider(
        name="surface-designer",
        module="product_generators.surface_designer",
        representation=GeometryRepresentation.BREP,
        capabilities=frozenset(
            {
                Capability.TEXT,
                Capability.SURFACE_RELIEF,
                Capability.DECORATION,
                Capability.BOOLEAN,
                Capability.MULTICOLOR,
                Capability.THREE_MF,
            }
        ),
    ),
    CapabilityProvider(
        name="legacy-parametric-engine",
        module="engine",
        representation=GeometryRepresentation.BREP,
        capabilities=frozenset(
            {
                Capability.TEXT,
                Capability.DECORATION,
                Capability.DRAINAGE,
                Capability.STL,
            }
        ),
        historical=True,
    ),
    CapabilityProvider(
        name="manufacturability-engine",
        module="product_generators.manufacturability",
        representation=GeometryRepresentation.POST_GEOMETRY,
        capabilities=frozenset({Capability.MANUFACTURABILITY}),
    ),
    CapabilityProvider(
        name="production-package",
        module="product_generators.production_package",
        representation=GeometryRepresentation.POST_GEOMETRY,
        capabilities=frozenset(
            {Capability.RENDER, Capability.STL, Capability.THREE_MF}
        ),
    ),
)


class GeometryComposer:
    """Plan composition across all accumulated DOBO geometry capabilities.

    C0 deliberately starts by making capability loss impossible to hide.  A
    request is never silently downgraded because the currently selected body
    engine lacks a tool.  The planner resolves every requested capability to
    an existing provider and explicitly marks the BRep/mesh boundary that must
    be bridged for hybrid products.
    """

    GEOMETRY_REPRESENTATIONS = frozenset(
        {GeometryRepresentation.BREP, GeometryRepresentation.MESH}
    )

    def __init__(
        self, providers: Iterable[CapabilityProvider] = DEFAULT_PROVIDERS
    ) -> None:
        self.providers = tuple(provider for provider in providers if provider.active)

    def plan(self, requested: Iterable[Capability]) -> CompositionPlan:
        request = frozenset(requested)
        chosen: list[CapabilityProvider] = []
        covered: set[Capability] = set()

        # Prefer non-historical providers. Legacy providers are retained as
        # capability evidence/fallback until parity is proven elsewhere.
        ordered = sorted(self.providers, key=lambda item: item.historical)
        for provider in ordered:
            contribution = provider.capabilities & (request - covered)
            if contribution:
                chosen.append(provider)
                covered.update(contribution)

        missing = request - covered
        reps = frozenset(
            provider.representation
            for provider in chosen
            if provider.representation in self.GEOMETRY_REPRESENTATIONS
        )
        return CompositionPlan(
            requested=request,
            providers=tuple(chosen),
            covered=frozenset(covered),
            missing=frozenset(missing),
            geometry_representations=reps,
            bridge_required=len(reps) > 1,
        )


def c0_accumulation_request() -> frozenset[Capability]:
    """Capabilities that a modern DOBO planter must accumulate, not replace."""

    return frozenset(
        {
            Capability.MORPHOLOGY,
            Capability.TEXT,
            Capability.SURFACE_RELIEF,
            Capability.DECORATION,
            Capability.BOOLEAN,
            Capability.NEGATIVE_VOLUME,
            Capability.DRAINAGE,
            Capability.MULTICOLOR,
            Capability.MANUFACTURABILITY,
            Capability.STL,
            Capability.THREE_MF,
            Capability.RENDER,
        }
    )
