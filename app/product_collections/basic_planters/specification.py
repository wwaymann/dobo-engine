from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class BasicPlanterSpecification:
    id: str
    name: str
    profile: str
    width: float
    depth: float
    height: float
    wall_thickness: float = 4.0
    top_scale: float = 1.0
    corner_radius: float = 0.0
    shell: bool = True
    export_filename: str = ""

    def validate(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip(): raise ValueError("id cannot be empty")
        if not isinstance(self.name, str) or not self.name.strip(): raise ValueError("name cannot be empty")
        if self.profile not in {"rectangle","rounded_rectangle","circle","ellipse","hexagon"}: raise ValueError(f"Unsupported profile '{self.profile}'.")
        for field_name, value in (("width",self.width),("depth",self.depth),("height",self.height),("wall_thickness",self.wall_thickness),("top_scale",self.top_scale),("corner_radius",self.corner_radius)):
            if isinstance(value, bool) or not isinstance(value,(int,float)): raise TypeError(f"{field_name} must be numeric")
        if self.width <= 0 or self.depth <= 0 or self.height <= 0: raise ValueError("width, depth and height must be greater than zero")
        if self.wall_thickness <= 0: raise ValueError("wall_thickness must be greater than zero")
        if self.top_scale <= 0: raise ValueError("top_scale must be greater than zero")
        if self.corner_radius < 0: raise ValueError("corner_radius cannot be negative")

    @property
    def resolved_export_filename(self) -> str:
        return self.export_filename or f"{self.id}.step"
