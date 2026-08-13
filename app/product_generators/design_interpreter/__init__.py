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
from .image_interpreter import (
    ImageInterpretationResult,
    ImageInterpretationTrace,
    ImageModelClient,
    ImageModelResponse,
    ImageSemanticInterpreter,
    OpenAIResponsesImageClient,
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
    "SemanticProgramParser",
    "SemanticRelation",
    "SourceIntent",
)
