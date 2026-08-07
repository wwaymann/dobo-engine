from __future__ import annotations
import math
from .contracts import SurfaceFrame,SurfaceSample
from .math3d import normalize,cross

class ConeSurfaceMapper:
    def __init__(self,*,base_radius:float,top_radius:float,height:float,angle_offset_degrees:float=0.0,center:tuple[float,float,float]=(0.0,0.0,0.0))->None:
        if base_radius<=0 or top_radius<=0 or height<=0: raise ValueError("Cone dimensions must be positive.")
        self.base_radius=float(base_radius); self.top_radius=float(top_radius); self.height=float(height); self.angle_offset=math.radians(float(angle_offset_degrees)); self.center=center
    def radius_at(self,v:float)->float:
        return self.base_radius+(self.top_radius-self.base_radius)*(float(v)/self.height)
    def sample(self,u:float,v:float)->SurfaceSample:
        v=float(v); r=self.radius_at(v)
        if r<=0: raise ValueError("Mapped radius must remain positive.")
        a=self.angle_offset+float(u)/r; c=math.cos(a); s=math.sin(a)
        p=(self.center[0]+r*c,self.center[1]+r*s,self.center[2]+v)
        tu=normalize((-s,c,0.0)); slope=(self.top_radius-self.base_radius)/self.height; tv=normalize((slope*c,slope*s,1.0)); n=normalize(cross(tu,tv))
        f=SurfaceFrame(origin=p,tangent_u=tu,tangent_v=tv,normal=n)
        out=SurfaceSample(u=float(u),v=v,point=p,frame=f); out.validate(); return out
