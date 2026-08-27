"""Semantic design interpretation contracts for the DOBO platform."""

from importlib.util import find_spec as _find_spec

from .semantic_contract import (
    Ambiguity,
    Assumption,
    BodyIntent,
    DesignSemanticProgram,
    FeatureIntent,
    FeatureSizeIntent,
    ManufacturingIntent,
    SemanticAnchor,
    SemanticRelation,
    SourceIntent,
)
from .semantic_parser import SemanticProgramParser
from .prompt_interpreter import (
    OpenAIResponsesSemanticClient,
    PromptInterpretationResult,
    PromptInterpretationTrace,
    PromptSemanticInterpreter,
    SemanticModelClient,
    SemanticModelResponse,
)
from .semantic_compiler import (
    CompilationTrace,
    SemanticCompilationReport,
    SemanticCompilationResult,
    SemanticToMotorCompiler,
)
from .image_interpreter import (
    ImageInterpretationResult,
    ImageInterpretationTrace,
    ImageModelClient,
    ImageModelResponse,
    ImageSemanticInterpreter,
    OpenAIResponsesImageClient,
)
from .proposal_repair import (
    ProposalValidationSnapshot,
    SemanticProposalRepairer,
    SemanticRepairAction,
    SemanticRepairReport,
    SemanticRepairResult,
)
from .design_pipeline import (
    DesignPipelineResult,
    DesignPipelineTrace,
    DoboDesignPipeline,
)

# Keep lightweight semantic imports lightweight. The promoted reconnection uses
# the geometry stack it actually imports. Shapely is intentionally not a gate:
# the canonical text/retry reconnection does not depend on it, and requiring it
# made local DOBO Lab runs silently fall back to the old rounded-box plaque.
_CORE_GEOMETRY_DEPENDENCIES = (
    "numpy",
    "scipy",
    "trimesh",
    "skimage",
    "cadquery",
)
_CORE_GEOMETRY_READY = all(
    _find_spec(module_name) is not None
    for module_name in _CORE_GEOMETRY_DEPENDENCIES
)

if _CORE_GEOMETRY_READY:
    from .core_capability_reconnection import (
        CORE_CAPABILITY_RECONNECTION_VERSION,
        install_core_capability_reconnection,
    )
    from .core_retry_reconnection import (
        CORE_RETRY_RECONNECTION_VERSION,
        install_core_retry_reconnection,
    )

    install_core_capability_reconnection()
    install_core_retry_reconnection()
else:
    CORE_CAPABILITY_RECONNECTION_VERSION = "C0R.1-deferred"
    CORE_RETRY_RECONNECTION_VERSION = "3F.R1-deferred"

    def install_core_capability_reconnection() -> str:
        return CORE_CAPABILITY_RECONNECTION_VERSION

    def install_core_retry_reconnection() -> str:
        return CORE_RETRY_RECONNECTION_VERSION

from .three_mf_export import ThreeMFExportResult, ThreeMFMeshExporter
from .structural_vocabulary import (
    StructuralAnchor,
    StructuralDesignProgram,
    StructuralFeature,
    StructuralVisualGroup,
    StructuralVocabularyResolver,
)
from .design_grammar import (
    ACCEPTANCE_MATRIX_VERSION,
    BODY_GRAMMAR_VERSION,
    COMPONENT_GRAMMAR_VERSION,
    COMPOSITION_GRAMMAR_VERSION,
    STYLE_GRAMMAR_VERSION,
    DesignGrammarPlan,
    DesignGrammarResolver,
    GrammarFeaturePlan,
    GrammarStyleProfile,
)
from .structural_compiler import (
    ADAPTIVE_QUALITY_VERSION,
    ADVANCED_PRIMITIVE_VERSION,
    CLEAN_COMPOSITION_VERSION,
    STYLE_DIFFERENTIATION_VERSION,
    VISUAL_ACCEPTANCE_VERSION,
    STRUCTURAL_COMPILER_VERSION,
    STRUCTURAL_HIERARCHY_VERSION,
    STRUCTURAL_TEMPLATE_VERSION,
    StructuralCompilationReport,
    StructuralCompilationResult,
    StructuralSemanticCompiler,
)
from .structural_pipeline import (
    STRUCTURAL_FUSION_VERSION,
    STRUCTURAL_PIPELINE_VERSION,
    DoboStructuralPipeline,
    StructuralPipelineResult,
    StructuralPipelineTrace,
)
from .structural_morphogenesis import (
    MORPHOLOGY_ACCEPTANCE_VERSION,
    SECTION_PROFILE_VERSION,
    STRUCTURAL_SYNTHESIS_VERSION,
    TOPOLOGY_GRAPH_VERSION,
    StructuralBodySynthesizer,
    StructuralMorphogenesisResolver,
    StructuralMorphologyPlan,
    front_surface_y,
)
from .morphological_integration import (
    ADVANCED_MORPHOLOGICAL_INTEGRATION_VERSION,
    AdvancedMorphologicalIntegration,
    ChildExposurePolicy,
    ParentLocalAnchor,
    SpanInterfacePolicy,
)
from .continuous_morphological_fusion import (
    CONTINUOUS_MORPHOLOGICAL_FUSION_VERSION,
    AttachmentSpreadPolicy,
    ContinuousMorphologicalFusion,
    SpanContinuityPolicy,
    TransitionMassPolicy,
)
from .complex_composition import (
    COMPLEX_ACCEPTANCE_VERSION,
    COMPLEX_TOPOLOGY_VERSION,
    MULTILEVEL_HIERARCHY_VERSION,
    NEGATIVE_VOLUME_VERSION,
    STRUCTURAL_SPAN_VERSION,
    ComplexCompositionCompiler,
    ComplexCompositionPlan,
    ComplexCompositionResolver,
    ComplexTopologyEdge,
    ComplexTopologyNode,
)
from .intelligent_surfaces import (
    ADAPTIVE_MAPPING_VERSION,
    COLOR_ZONE_VERSION,
    RELIEF_SYNTHESIS_VERSION,
    SURFACE_ACCEPTANCE_VERSION,
    SURFACE_INTENT_VERSION,
    IntelligentSurfaceCompiler,
    IntelligentSurfaceProgram,
    IntelligentSurfaceReport,
    ResolvedSurfaceLayer,
    SurfaceLayerIntent,
    SurfaceMaterialMapper,
)

__all__ = (
    "Ambiguity",
    "Assumption",
    "BodyIntent",
    "DesignSemanticProgram",
    "FeatureIntent",
    "FeatureSizeIntent",
    "ManufacturingIntent",
    "SemanticAnchor",
    "OpenAIResponsesSemanticClient",
    "PromptInterpretationResult",
    "PromptInterpretationTrace",
    "PromptSemanticInterpreter",
    "SemanticModelClient",
    "SemanticModelResponse",
    "CompilationTrace",
    "SemanticCompilationReport",
    "SemanticCompilationResult",
    "SemanticToMotorCompiler",
    "ImageInterpretationResult",
    "ImageInterpretationTrace",
    "ImageModelClient",
    "ImageModelResponse",
    "ImageSemanticInterpreter",
    "OpenAIResponsesImageClient",
    "ProposalValidationSnapshot",
    "SemanticProposalRepairer",
    "SemanticRepairAction",
    "SemanticRepairReport",
    "SemanticRepairResult",
    "DesignPipelineResult",
    "DesignPipelineTrace",
    "DoboDesignPipeline",
    "CORE_CAPABILITY_RECONNECTION_VERSION",
    "install_core_capability_reconnection",
    "CORE_RETRY_RECONNECTION_VERSION",
    "install_core_retry_reconnection",
    "ThreeMFExportResult",
    "ThreeMFMeshExporter",
    "StructuralAnchor",
    "StructuralDesignProgram",
    "StructuralFeature",
    "StructuralVisualGroup",
    "StructuralVocabularyResolver",
    "DesignGrammarPlan",
    "DesignGrammarResolver",
    "GrammarFeaturePlan",
    "GrammarStyleProfile",
    "BODY_GRAMMAR_VERSION",
    "COMPONENT_GRAMMAR_VERSION",
    "COMPOSITION_GRAMMAR_VERSION",
    "STYLE_GRAMMAR_VERSION",
    "ACCEPTANCE_MATRIX_VERSION",
    "StructuralCompilationReport",
    "StructuralCompilationResult",
    "StructuralSemanticCompiler",
    "STRUCTURAL_COMPILER_VERSION",
    "ADVANCED_PRIMITIVE_VERSION",
    "CLEAN_COMPOSITION_VERSION",
    "STYLE_DIFFERENTIATION_VERSION",
    "ADAPTIVE_QUALITY_VERSION",
    "VISUAL_ACCEPTANCE_VERSION",
    "STRUCTURAL_TEMPLATE_VERSION",
    "STRUCTURAL_HIERARCHY_VERSION",
    "STRUCTURAL_FUSION_VERSION",
    "STRUCTURAL_PIPELINE_VERSION",
    "DoboStructuralPipeline",
    "StructuralPipelineResult",
    "StructuralPipelineTrace",
    "TOPOLOGY_GRAPH_VERSION",
    "SECTION_PROFILE_VERSION",
    "STRUCTURAL_SYNTHESIS_VERSION",
    "MORPHOLOGY_ACCEPTANCE_VERSION",
    "StructuralMorphologyPlan",
    "StructuralMorphogenesisResolver",
    "StructuralBodySynthesizer",
    "front_surface_y",
    "ADVANCED_MORPHOLOGICAL_INTEGRATION_VERSION",
    "ParentLocalAnchor",
    "ChildExposurePolicy",
    "SpanInterfacePolicy",
    "AdvancedMorphologicalIntegration",
    "CONTINUOUS_MORPHOLOGICAL_FUSION_VERSION",
    "AttachmentSpreadPolicy",
    "TransitionMassPolicy",
    "SpanContinuityPolicy",
    "ContinuousMorphologicalFusion",
    "COMPLEX_TOPOLOGY_VERSION",
    "STRUCTURAL_SPAN_VERSION",
    "NEGATIVE_VOLUME_VERSION",
    "MULTILEVEL_HIERARCHY_VERSION",
    "COMPLEX_ACCEPTANCE_VERSION",
    "ComplexTopologyNode",
    "ComplexTopologyEdge",
    "ComplexCompositionPlan",
    "ComplexCompositionResolver",
    "ComplexCompositionCompiler",
    "SURFACE_INTENT_VERSION",
    "ADAPTIVE_MAPPING_VERSION",
    "RELIEF_SYNTHESIS_VERSION",
    "COLOR_ZONE_VERSION",
    "SURFACE_ACCEPTANCE_VERSION",
    "SurfaceLayerIntent",
    "ResolvedSurfaceLayer",
    "IntelligentSurfaceProgram",
    "IntelligentSurfaceReport",
    "IntelligentSurfaceCompiler",
    "SurfaceMaterialMapper",
    "SemanticProgramParser",
    "SemanticRelation",
    "SourceIntent",
)
