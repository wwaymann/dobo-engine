from __future__ import annotations
from dataclasses import dataclass
Vector3=tuple[float,float,float]

@dataclass(frozen=True,slots=True)
class SurfaceFrame:
    origin:Vector3
    tangent_u:Vector3
    tangent_v:Vector3
    normal:Vector3
    def validate(self)->None:
        for name,value in (("origin",self.origin),("tangent_u",self.tangent_u),("tangent_v",self.tangent_v),("normal",self.normal)):
            if not isinstance(value,tuple) or len(value)!=3: raise TypeError(f"{name} must be a 3-value tuple.")

@dataclass(frozen=True,slots=True)
class SurfaceSample:
    u:float
    v:float
    point:Vector3
    frame:SurfaceFrame
    def validate(self)->None:
        if isinstance(self.u,bool) or not isinstance(self.u,(int,float)): raise TypeError("u must be numeric.")
        if isinstance(self.v,bool) or not isinstance(self.v,(int,float)): raise TypeError("v must be numeric.")
        self.frame.validate()

@dataclass(frozen=True,slots=True)
class MappedContour:
    id:str
    samples:tuple[SurfaceSample,...]
    closed:bool=True
    def validate(self)->None:
        if not isinstance(self.id,str) or not self.id.strip(): raise ValueError("MappedContour id cannot be empty.")
        if not isinstance(self.samples,tuple): raise TypeError("samples must be a tuple.")
        if len(self.samples)<(3 if self.closed else 2): raise ValueError("MappedContour has too few samples.")
        for s in self.samples:
            if not isinstance(s,SurfaceSample): raise TypeError("samples must contain SurfaceSample values.")
            s.validate()
