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

__all__ = [
    "Vector3",
    "ExtrudeFeatureDefinition",
    "RevolveFeatureDefinition",
    "LoftFeatureDefinition",
    "SweepFeatureDefinition",
    "ShellFeatureDefinition",
]