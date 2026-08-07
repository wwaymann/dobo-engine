from __future__ import annotations
from typing import Protocol
from product_generators.vector_geometry.contracts import VectorDocument
from .contracts import MappedContour,SurfaceSample

class SurfaceSampler(Protocol):
    def sample(self,u:float,v:float)->SurfaceSample: ...

class VectorSurfaceMapper:
    def map_document(self,document:VectorDocument,surface:SurfaceSampler,*,u_offset:float=0.0,v_offset:float=0.0,scale_u:float=1.0,scale_v:float=1.0)->tuple[MappedContour,...]:
        document.validate(); mapped=[]
        for contour in document.contours:
            samples=tuple(surface.sample(u_offset+float(x)*scale_u,v_offset+float(y)*scale_v) for x,y in contour.points)
            out=MappedContour(id=f"{contour.id}:mapped",samples=samples,closed=contour.closed); out.validate(); mapped.append(out)
        return tuple(mapped)
