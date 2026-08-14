"""Implicit organic shape generation for DOBO products."""

from .adaptive_refinement import AdaptiveFeatureRefinementContract
from .adaptive_layout import (
    FeatureManufacturabilityContract,
    LayoutConstraintContract,
    LayoutReport,
    ManufacturabilityReport,
    ProportionalScaleContract,
)
from .engine import OrganicShapeEngine, OrganicShapeResult
from .feature_program_engine import FeatureProgramVesselEngine
from .feature_program_specification import (
    FeatureProgramParser,
    FeatureProgramSpecification,
)
from .hierarchy_engine import HierarchicalFeatureVesselEngine
from .hierarchy_specification import (
    HierarchicalFeatureParser,
    HierarchicalFeatureSpecification,
)
from .cat_engine import OrganicCatVesselEngine
from .cat_specification import OrganicCatParser, OrganicCatSpecification
from .mesh_quality import (
    LocalizedTaubinRefiner,
    OrganicMeshQualityContract,
    OrganicMeshQualityMetrics,
)
from .specification import (
    ADVANCED_FIELD_KINDS,
    AdvancedFieldSpec,
    OrganicShapeParser,
    OrganicShapeSpecification,
)
from .surface_anchoring import (
    ResolvedSurfaceAnchor,
    SurfaceAnchorResolver,
    SurfaceAnchorSpec,
)
from .structural_engine import StructuralVesselEngine
from .structural_specification import (
    StructuralVesselParser,
    StructuralVesselSpecification,
)
from .vessel_engine import OrganicVesselEngine, OrganicVesselResult
from .vessel_specification import OrganicVesselParser, OrganicVesselSpecification

__all__ = (
    "OrganicShapeEngine",
    "AdaptiveFeatureRefinementContract",
    "FeatureManufacturabilityContract",
    "LayoutConstraintContract",
    "LayoutReport",
    "ManufacturabilityReport",
    "ProportionalScaleContract",
    "FeatureProgramParser",
    "FeatureProgramSpecification",
    "FeatureProgramVesselEngine",
    "HierarchicalFeatureParser",
    "HierarchicalFeatureSpecification",
    "HierarchicalFeatureVesselEngine",
    "OrganicCatParser",
    "OrganicCatSpecification",
    "OrganicCatVesselEngine",
    "OrganicShapeParser",
    "AdvancedFieldSpec",
    "ADVANCED_FIELD_KINDS",
    "OrganicShapeResult",
    "OrganicShapeSpecification",
    "ResolvedSurfaceAnchor",
    "SurfaceAnchorResolver",
    "SurfaceAnchorSpec",
    "LocalizedTaubinRefiner",
    "OrganicMeshQualityContract",
    "OrganicMeshQualityMetrics",
    "OrganicVesselEngine",
    "OrganicVesselParser",
    "OrganicVesselResult",
    "OrganicVesselSpecification",
    "StructuralVesselEngine",
    "StructuralVesselParser",
    "StructuralVesselSpecification",
)
