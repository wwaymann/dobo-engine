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
    "SemanticProgramParser",
    "SemanticRelation",
    "SourceIntent",
)
