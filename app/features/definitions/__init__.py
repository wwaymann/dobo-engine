"""
DOBO Features

Declarative Feature Definitions public API.
"""

from .extrude_feature_definition import (
    ExtrudeFeatureDefinition,
    Vector3,
)
from .revolve_feature_definition import RevolveFeatureDefinition
from .loft_feature_definition import LoftFeatureDefinition
from .sweep_feature_definition import SweepFeatureDefinition
from .shell_feature_definition import ShellFeatureDefinition
from .move_feature_definition import MoveFeatureDefinition
from .rotate_feature_definition import RotateFeatureDefinition
from .scale_feature_definition import ScaleFeatureDefinition
from .mirror_feature_definition import MirrorFeatureDefinition
from .fillet_feature_definition import FilletFeatureDefinition
from .chamfer_feature_definition import ChamferFeatureDefinition
from .draft_feature_definition import DraftFeatureDefinition
from .linear_pattern_feature_definition import (
    LinearPatternFeatureDefinition,
)
from .circular_pattern_feature_definition import (
    CircularPatternFeatureDefinition,
)

__all__ = [
    "Vector3",
    "ExtrudeFeatureDefinition",
    "RevolveFeatureDefinition",
    "LoftFeatureDefinition",
    "SweepFeatureDefinition",
    "ShellFeatureDefinition",
    "MoveFeatureDefinition",
    "RotateFeatureDefinition",
    "ScaleFeatureDefinition",
    "MirrorFeatureDefinition",
    "FilletFeatureDefinition",
    "ChamferFeatureDefinition",
    "DraftFeatureDefinition",
    "LinearPatternFeatureDefinition",
    "CircularPatternFeatureDefinition",
]
