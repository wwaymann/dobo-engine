"""
DOBO Advanced Geometry Pack
Phase 3.1 - Surface Feature Topology
"""

from .contracts import (
    TopologyDocument,
    TopologyLoop,
    TopologyRole,
)
from .topology import (
    SurfaceFeatureTopologyAnalyzer,
)

__all__ = [
    "TopologyDocument",
    "TopologyLoop",
    "TopologyRole",
    "SurfaceFeatureTopologyAnalyzer",
]
