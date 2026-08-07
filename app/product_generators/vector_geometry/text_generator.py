from __future__ import annotations
from dataclasses import dataclass
import cadquery as cq

@dataclass(frozen=True,slots=True)
class TextGeometryResult:
    text:str
    shape:cq.Shape
    def validate(self)->None:
        if not self.text: raise ValueError("text cannot be empty.")
        if not isinstance(self.shape,cq.Shape) or not self.shape.isValid(): raise RuntimeError("Invalid text geometry.")

class TextGeometryGenerator:
    def generate(self,text:str,*,size:float=20.0,depth:float=2.0,font:str="Arial",kind:str="regular",halign:str="center",valign:str="center")->TextGeometryResult:
        try:
            shape=cq.Workplane("XY").text(text,float(size),float(depth),font=font,kind=kind,halign=halign,valign=valign,combine=True,clean=True).val()
        except Exception as error:
            raise RuntimeError(f"Could not generate text with font '{font}'.") from error
        result=TextGeometryResult(text=text,shape=shape.clean()); result.validate(); return result
