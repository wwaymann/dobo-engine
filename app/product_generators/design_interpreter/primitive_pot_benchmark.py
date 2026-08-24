from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from zipfile import ZipFile

import matplotlib.pyplot as plt
import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont

from .prompt_interpreter import OpenAIResponsesSemanticClient, PromptSemanticInterpreter
from .semantic_surface_bridge import SemanticSurfaceIntentBridge
from .structural_pipeline import DoboStructuralPipeline
from product_generators.manufacturability.profile import ManufacturingProfile

CASES = (
    {"id":"01_cube","label":"Cubo","expected_morphology":{"cuboid"},"expected_semantic":{"cuboid","cube","cubic"},"prompt":"Haz una maceta funcional con cuerpo de cubo, hueca, abierta arriba y con drenaje inferior. Sin texto, sin decoración y sin patrones."},
    {"id":"02_rectangular","label":"Prisma rectangular","expected_morphology":{"rectangular_prism"},"expected_semantic":{"rectangular_prism","rectangular"},"prompt":"Haz una maceta funcional con cuerpo de prisma rectangular horizontal, hueca, abierta arriba y con drenaje inferior. Sin texto, sin decoración y sin patrones."},
    {"id":"03_cylinder","label":"Cilindro","expected_morphology":{"cylindrical"},"expected_semantic":{"cylindrical","cylinder"},"prompt":"Haz una maceta funcional cilíndrica recta, hueca, abierta arriba y con drenaje inferior. Sin texto, sin decoración y sin patrones."},
    {"id":"04_cone","label":"Tronco de cono","expected_morphology":{"tapered_revolution"},"expected_semantic":{"tapered","tapered_revolution","conical"},"prompt":"Haz una maceta funcional troncocónica, más estrecha abajo y más ancha en la boca, hueca, abierta arriba y con drenaje inferior. Sin texto, sin decoración y sin patrones."},
    {"id":"05_sphere","label":"Esfera","expected_morphology":{"spherical_mass"},"expected_semantic":{"spherical","sphere"},"prompt":"Haz una maceta funcional esférica, truncada por una abertura superior, hueca y con drenaje inferior. Sin texto, sin decoración y sin patrones."},
    {"id":"06_ovoid","label":"Ovoide","expected_morphology":{"ovoid"},"expected_semantic":{"ovoid","ellipsoidal"},"prompt":"Haz una maceta funcional ovoide o elipsoidal, hueca, abierta arriba y con drenaje inferior. Sin texto, sin decoración y sin patrones."},
    {"id":"07_triangular","label":"Prisma triangular","expected_morphology":{"triangular_prism"},"expected_semantic":{"triangular_prism","triangular"},"prompt":"Haz una maceta funcional con cuerpo de prisma triangular, hueca, abierta arriba y con drenaje inferior. Sin texto, sin decoración y sin patrones."},
)

def _mesh(path: str) -> trimesh.Trimesh:
    value=trimesh.load_mesh(path,process=True)
    if isinstance(value,trimesh.Scene): value=trimesh.util.concatenate(tuple(value.geometry.values()))
    if not isinstance(value,trimesh.Trimesh) or len(value.faces)==0: raise RuntimeError("STL did not contain a usable mesh")
    return value

def _render(mesh: trimesh.Trimesh,target: Path,elev: float,azim: float)->None:
    vertices=np.asarray(mesh.vertices,dtype=float); faces=np.asarray(mesh.faces,dtype=np.int64)
    if len(faces)>65000: faces=faces[::max(1,len(faces)//65000)]
    used=np.unique(faces.reshape(-1)); remap=np.full(len(vertices),-1,dtype=np.int64); remap[used]=np.arange(len(used)); v=vertices[used]; f=remap[faces]
    v=v-(v.min(axis=0)+v.max(axis=0))/2.0; v=v/float(max(np.maximum(np.ptp(v,axis=0),1.0)))
    fig=plt.figure(figsize=(6.2,6.2)); ax=fig.add_subplot(111,projection="3d"); ax.plot_trisurf(v[:,0],v[:,1],v[:,2],triangles=f,linewidth=0.02,shade=True)
    ax.view_init(elev=elev,azim=azim); ax.set_xlim(-.58,.58); ax.set_ylim(-.58,.58); ax.set_zlim(-.58,.58); ax.set_box_aspect((1,1,1)); ax.set_axis_off(); fig.tight_layout(pad=0); fig.savefig(target,dpi=180,bbox_inches="tight",pad_inches=0); plt.close(fig)

def run(output_root: str|Path="outputs-ci/primitive-pot-benchmark")->dict:
    root=Path(output_root); root.mkdir(parents=True,exist_ok=True)
    if not os.environ.get("OPENAI_API_KEY","").strip(): raise RuntimeError("OPENAI_API_KEY is not configured")
    interpreter=PromptSemanticInterpreter(OpenAIResponsesSemanticClient(model=os.environ.get("DOBO_SEMANTIC_MODEL","gpt-4.1-mini"))); pipeline=DoboStructuralPipeline(); profile=ManufacturingProfile(); records=[]
    for case in CASES:
        d=root/case["id"]; d.mkdir(parents=True,exist_ok=True); (d/"PROMPT.txt").write_text(case["prompt"]+"\n",encoding="utf-8")
        r={"id":case["id"],"label":case["label"],"status":"FAIL","stage":"start","error":None,"semantic_family":None,"style_tags":[],"body_profile":None,"morphology_profile":None,"semantic_shape_match":False,"morphology_match":False,"no_surface_features":False,"opening_valid":False,"watertight":False,"winding_consistent":False,"production_size_valid":False,"three_mf_valid":False,"renders":{}}
        try:
            r["stage"]="semantic"; interpreted=interpreter.interpret(case["prompt"]); semantic=interpreted.program; semantic.validate(); r["semantic_family"]=semantic.body.family; r["style_tags"]=list(semantic.body.style_tags); r["no_surface_features"]=len(semantic.features)==0; semantic_observed={str(semantic.body.family),*map(str,semantic.body.style_tags)}; r["semantic_shape_match"]=bool(semantic_observed & case["expected_semantic"]); r["opening_valid"]=semantic.body.opening_shape in {"circular","elliptical","polygonal"} and .15<=semantic.body.opening_width_ratio<=.95 and .15<=semantic.body.opening_depth_ratio<=.95
            r["stage"]="surface_bridge"; intents=SemanticSurfaceIntentBridge.compile(semantic); r["stage"]="physical_generation"; result=pipeline.generate_from_semantic(semantic,output_root=d/"generated",interpreter_version=interpreted.trace.interpreter_version,model=interpreted.trace.model,response_id=interpreted.trace.response_id,surface_intents=intents); result.validate(); r["body_profile"]=result.trace.body_profile; motor=json.loads(Path(result.motor_path).read_text(encoding="utf-8")); r["morphology_profile"]=motor.get("morphogenesis",{}).get("profile"); r["morphology_match"]=str(r["morphology_profile"]) in case["expected_morphology"]
            stl=d/(case["id"]+".stl"); mf=d/(case["id"]+".3mf"); shutil.copy2(result.stl_path,stl); shutil.copy2(result.three_mf_path,mf); mesh=_mesh(str(stl)); r["watertight"]=bool(mesh.is_watertight); r["winding_consistent"]=bool(mesh.is_winding_consistent); ext=np.asarray(mesh.extents,float); r["mesh_extents_mm"]=ext.tolist(); r["production_size_valid"]=bool(ext[0]<=profile.max_size_x and ext[1]<=profile.max_size_y and ext[2]<=profile.max_size_z)
            r["stage"]="3mf"; z=ZipFile(mf,"r"); corrupt=z.testzip(); names=set(z.namelist()); z.close(); r["three_mf_valid"]=bool(corrupt is None and {"[Content_Types].xml","_rels/.rels","3D/3dmodel.model"}.issubset(names)); r["stage"]="render"
            for name,elev,azim in (("front",0,0),("side",0,90),("top",90,-90),("iso",28,42)): p=d/(name+".png"); _render(mesh,p,elev,azim); r["renders"][name]=str(p)
            physical=all((r["opening_valid"],r["watertight"],r["winding_consistent"],r["production_size_valid"],r["three_mf_valid"],Path(r["renders"]["top"]).is_file(),Path(r["renders"]["iso"]).is_file()))
            complete=physical and r["semantic_shape_match"] and r["morphology_match"] and r["no_surface_features"]
            r["status"]="PASS" if complete else ("PARTIAL" if physical else "FAIL"); r["stage"]="complete"
        except Exception as exc: r["error"]=f"{type(exc).__name__}: {exc}"
        records.append(r); (d/"AUDIT.json").write_text(json.dumps(r,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    tile_w,tile_h=700,760; board=Image.new("RGB",(tile_w*4,tile_h*2),"white"); draw=ImageDraw.Draw(board)
    try: font=ImageFont.truetype("DejaVuSans.ttf",28); small=ImageFont.truetype("DejaVuSans.ttf",18)
    except Exception: font=ImageFont.load_default(); small=font
    for i,r in enumerate(records):
        x=(i%4)*tile_w; y=(i//4)*tile_h; iso=r["renders"].get("iso")
        if iso and Path(iso).is_file(): im=Image.open(iso).convert("RGB"); im.thumbnail((650,610)); board.paste(im,(x+(tile_w-im.width)//2,y+55))
        else: draw.rectangle((x+25,y+75,x+tile_w-25,y+620),outline="black",width=2); draw.text((x+110,y+320),"SIN RENDER",fill="black",font=font)
        draw.text((x+15,y+12),r["label"],fill="black",font=font); draw.text((x+15,y+675),f"{r['status']} semantic={r['semantic_family']}",fill="black",font=small); draw.text((x+15,y+705),f"morph={r['morphology_profile']}",fill="black",font=small)
    board_path=root/"DOBO_PRIMITIVE_POTS_RENDER_BOARD.jpg"; board.save(board_path,quality=92); summary={"schema":"dobo.primitive_pots.audit.2","case_count":len(records),"pass":sum(r["status"]=="PASS" for r in records),"partial":sum(r["status"]=="PARTIAL" for r in records),"fail":sum(r["status"]=="FAIL" for r in records),"cases":records,"render_board":str(board_path)}; (root/"BENCHMARK_SUMMARY.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8"); print(json.dumps({k:summary[k] for k in ("case_count","pass","partial","fail","render_board")},indent=2))
    if summary["pass"] != len(CASES):
        raise RuntimeError(f"Primitive planter gate failed: {summary['pass']}/{len(CASES)} PASS")
    return summary

if __name__=="__main__": run()
