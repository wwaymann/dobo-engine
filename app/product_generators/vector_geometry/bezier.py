from __future__ import annotations
Point2D=tuple[float,float]
def quadratic(p0:Point2D,p1:Point2D,p2:Point2D,*,segments:int=12)->tuple[Point2D,...]:
    return tuple((((1-t)**2)*p0[0]+2*(1-t)*t*p1[0]+t*t*p2[0],((1-t)**2)*p0[1]+2*(1-t)*t*p1[1]+t*t*p2[1]) for t in (i/segments for i in range(1,segments+1)))
def cubic(p0:Point2D,p1:Point2D,p2:Point2D,p3:Point2D,*,segments:int=16)->tuple[Point2D,...]:
    return tuple((((1-t)**3)*p0[0]+3*((1-t)**2)*t*p1[0]+3*(1-t)*(t**2)*p2[0]+(t**3)*p3[0],((1-t)**3)*p0[1]+3*((1-t)**2)*t*p1[1]+3*(1-t)*(t**2)*p2[1]+(t**3)*p3[1]) for t in (i/segments for i in range(1,segments+1)))
