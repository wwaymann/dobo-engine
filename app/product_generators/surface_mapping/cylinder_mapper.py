from __future__ import annotations
import math
from .contracts import SurfaceFrame,SurfaceSample

class CylinderSurfaceMapper:
    def __init__(self,*,radius:float,angle_offset_degrees:float=0.0,center:tuple[float,float,float]=(0.0,0.0,0.0))->None:
        if radius<=0: raise ValueError("radius must be positive.")
        self.radius=float(radius); self.angle_offset=math.radians(float(angle_offset_degrees)); self.center=center
    @property
    def circumference(self)->float: return 2*math.pi*self.radius
    def sample(self,u:float,v:float)->SurfaceSample:
        a=self.angle_offset+float(u)/self.radius; c=math.cos(a); s=math.sin(a)
        p=(self.center[0]+self.radius*c,self.center[1]+self.radius*s,self.center[2]+float(v))
        f=SurfaceFrame(origin=p,tangent_u=(-s,c,0.0),tangent_v=(0.0,0.0,1.0),normal=(c,s,0.0))
        r=SurfaceSample(u=float(u),v=float(v),point=p,frame=f); r.validate(); return r
