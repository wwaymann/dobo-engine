from __future__ import annotations
import math
from collections.abc import Callable
from .contracts import SurfaceFrame,SurfaceSample
from .math3d import normalize,cross

class RadialProfileSurfaceMapper:
    def __init__(self,*,radius_function:Callable[[float],float],derivative_function:Callable[[float],float],angle_offset_degrees:float=0.0,center:tuple[float,float,float]=(0.0,0.0,0.0))->None:
        if not callable(radius_function) or not callable(derivative_function): raise TypeError("Functions must be callable.")
        self.radius_function=radius_function; self.derivative_function=derivative_function; self.angle_offset=math.radians(float(angle_offset_degrees)); self.center=center
    def sample(self,u:float,v:float)->SurfaceSample:
        v=float(v); r=float(self.radius_function(v))
        if r<=0: raise ValueError("Surface radius must remain positive.")
        d=float(self.derivative_function(v)); a=self.angle_offset+float(u)/r; c=math.cos(a); s=math.sin(a)
        p=(self.center[0]+r*c,self.center[1]+r*s,self.center[2]+v)
        tu=normalize((-s,c,0.0)); tv=normalize((d*c,d*s,1.0)); n=normalize(cross(tu,tv))
        f=SurfaceFrame(origin=p,tangent_u=tu,tangent_v=tv,normal=n)
        out=SurfaceSample(u=float(u),v=v,point=p,frame=f); out.validate(); return out
