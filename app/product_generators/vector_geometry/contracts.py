from __future__ import annotations
from dataclasses import dataclass
Point2D = tuple[float,float]

@dataclass(frozen=True, slots=True)
class VectorContour:
    id: str
    points: tuple[Point2D,...]
    closed: bool = True
    def validate(self)->None:
        if not isinstance(self.id,str) or not self.id.strip(): raise ValueError("VectorContour id cannot be empty.")
        if not isinstance(self.points,tuple): raise TypeError("VectorContour points must be a tuple.")
        minimum=3 if self.closed else 2
        if len(self.points)<minimum: raise ValueError(f"VectorContour requires at least {minimum} points.")
        for p in self.points:
            if not isinstance(p,tuple) or len(p)!=2: raise TypeError("VectorContour points must be 2-value tuples.")
            for v in p:
                if isinstance(v,bool) or not isinstance(v,(int,float)): raise TypeError("VectorContour coordinates must be numeric.")

@dataclass(frozen=True, slots=True)
class VectorDocument:
    id: str
    contours: tuple[VectorContour,...]
    source: str = ""
    def validate(self)->None:
        if not isinstance(self.id,str) or not self.id.strip(): raise ValueError("VectorDocument id cannot be empty.")
        if not isinstance(self.contours,tuple) or not self.contours: raise ValueError("VectorDocument must contain contours.")
        for c in self.contours:
            if not isinstance(c,VectorContour): raise TypeError("VectorDocument accepts VectorContour values only.")
            c.validate()
