"""Semantic design interpretation contracts for the DOBO platform."""

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
from .semantic_compiler import (
    CompilationTrace,
    SemanticCompilationReport,
    SemanticCompilationResult,
    SemanticToMotorCompiler,
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
    "CompilationTrace",
    "SemanticCompilationReport",
    "SemanticCompilationResult",
    "SemanticToMotorCompiler",
    "SemanticProgramParser",
    "SemanticRelation",
    "SourceIntent",
)
