from __future__ import annotations
import math
from kernel.contracts.contour_definition import ContourDefinition
Point2D = tuple[float, float]

def rectangle_points(width: float, depth: float) -> tuple[Point2D, ...]:
    return ((0.0,0.0),(float(width),0.0),(float(width),float(depth)),(0.0,float(depth)))

def circle_points(diameter: float, samples: int = 96) -> tuple[Point2D, ...]:
    r=float(diameter)/2.0
    return tuple((r+r*math.cos(2*math.pi*i/samples), r+r*math.sin(2*math.pi*i/samples)) for i in range(samples))

def ellipse_points(width: float, depth: float, samples: int = 96) -> tuple[Point2D, ...]:
    rx=float(width)/2.0; ry=float(depth)/2.0
    return tuple((rx+rx*math.cos(2*math.pi*i/samples), ry+ry*math.sin(2*math.pi*i/samples)) for i in range(samples))

def hexagon_points(width: float, depth: float) -> tuple[Point2D, ...]:
    rx=float(width)/2.0; ry=float(depth)/2.0
    return tuple((rx+rx*math.cos(math.radians(60*i)), ry+ry*math.sin(math.radians(60*i))) for i in range(6))

def rounded_rectangle_points(width: float, depth: float, radius: float, arc_samples: int = 8) -> tuple[Point2D, ...]:
    width=float(width); depth=float(depth); radius=min(float(radius),width/2,depth/2)
    if radius <= 0: return rectangle_points(width, depth)
    corners=((width-radius,radius,-90,0),(width-radius,depth-radius,0,90),(radius,depth-radius,90,180),(radius,radius,180,270))
    points=[]
    for cx,cy,start,end in corners:
        for step in range(arc_samples):
            t=step/(arc_samples-1); a=math.radians(start+(end-start)*t); p=(cx+radius*math.cos(a),cy+radius*math.sin(a))
            if not points or p != points[-1]: points.append(p)
    return tuple(points)

def build_contour(profile: str, width: float, depth: float, *, corner_radius: float=0.0, scale: float=1.0, contour_id: str) -> ContourDefinition:
    w=float(width)*float(scale); d=float(depth)*float(scale)
    if profile=="rectangle": points=rectangle_points(w,d)
    elif profile=="rounded_rectangle": points=rounded_rectangle_points(w,d,float(corner_radius)*float(scale))
    elif profile=="circle": points=circle_points(w)
    elif profile=="ellipse": points=ellipse_points(w,d)
    elif profile=="hexagon": points=hexagon_points(w,d)
    else: raise ValueError(f"Unsupported profile '{profile}'.")
    contour=ContourDefinition(id=contour_id,points=points,closed=True,source="basic_planters",metadata={"profile":profile,"width":w,"depth":d,"scale":scale})
    contour.validate(); return contour
