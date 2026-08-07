from __future__ import annotations
from kernel.contracts.contour_definition import ContourDefinition
from kernel.contracts.geometry_definition import GeometryDefinition
from kernel.contracts.geometry_definition_set import GeometryDefinitionSet
from .contracts import VectorDocument

class VectorGeometryKernelAdapter:
    @staticmethod
    def to_geometry_definition_set(document:VectorDocument,*,geometry_id:str|None=None)->GeometryDefinitionSet:
        document.validate(); defs=[]
        for i,c in enumerate(document.contours):
            if not c.closed: continue
            contour=ContourDefinition(id=f"{document.id}:kernel-contour:{i}",points=c.points,closed=True,source=document.source or "vector_geometry"); contour.validate()
            d=GeometryDefinition(id=f"{document.id}:kernel-definition:{i}",outer_contour=contour,source=document.source or "vector_geometry"); d.validate(); defs.append(d)
        if not defs: raise ValueError("No closed vector contours.")
        result=GeometryDefinitionSet(id=geometry_id or f"{document.id}:geometry",definitions=tuple(defs),source=document.source or "vector_geometry"); result.validate(); return result
