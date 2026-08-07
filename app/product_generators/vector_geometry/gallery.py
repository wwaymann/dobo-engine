from __future__ import annotations
import os
import cadquery as cq
from kernel.contracts.geometry_operation_type import GeometryOperationType
from kernel.contracts.geometry_request import GeometryRequest
from kernel.contracts.operations import GeometryOperation
from kernel.core.execution_context import KernelExecutionContext
from testing import build_dispatcher
from .kernel_adapter import VectorGeometryKernelAdapter
from .svg_parser import SvgVectorParser
from .text_generator import TextGeometryGenerator

OUT="outputs/product_generators/vector_geometry"
SVGS={
"svg_shapes":"""<svg xmlns="http://www.w3.org/2000/svg"><rect x="5" y="5" width="30" height="18" rx="3"/><circle cx="55" cy="14" r="9"/><polygon points="75,5 90,14 75,23 60,14"/></svg>""",
"svg_bezier":"""<svg xmlns="http://www.w3.org/2000/svg"><path d="M 5 20 C 20 0,40 0,55 20 C 40 40,20 40,5 20 Z"/></svg>"""
}
def _export(shape,name):
    os.makedirs(OUT,exist_ok=True); p=os.path.join(OUT,name); cq.exporters.export(shape,p); return p
def build_svg_gallery():
    parser=SvgVectorParser(); adapter=VectorGeometryKernelAdapter(); dispatcher=build_dispatcher(include_geometry=True,include_boolean=False,include_shell=False,include_modeling=False,include_export=False); paths=[]
    for gid,svg in SVGS.items():
        geom=adapter.to_geometry_definition_set(parser.parse_string(svg,document_id=gid))
        req=GeometryRequest(id=f"{gid}:request",geometry=geom,operation=GeometryOperationType.EXTRUDE,parameters={"distance":3.0,"direction":(0.0,0.0,1.0),"symmetric":False,"draft_angle":0.0},output_id=f"{gid}:solid"); req.validate()
        op=GeometryOperation(id=f"{gid}:operation",name=f"{gid} Extrusion",request=req,output_id=req.output_id); op.validate()
        ctx=KernelExecutionContext(); dispatcher.dispatch(op,ctx); solid=ctx.solids.get(req.output_id); paths.append(_export(solid.geometry,f"{gid}.step"))
    return tuple(paths)
def build_text_gallery():
    result=TextGeometryGenerator().generate("DOBO",size=22.0,depth=3.0)
    return _export(result.shape,"text_dobo.step")
