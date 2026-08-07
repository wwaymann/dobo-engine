from __future__ import annotations
import math
Vector3=tuple[float,float,float]
def normalize(v:Vector3)->Vector3:
    l=math.sqrt(sum(c*c for c in v))
    if l<=1e-12: raise ValueError("Cannot normalize zero vector.")
    return (v[0]/l,v[1]/l,v[2]/l)
def cross(a:Vector3,b:Vector3)->Vector3:
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
