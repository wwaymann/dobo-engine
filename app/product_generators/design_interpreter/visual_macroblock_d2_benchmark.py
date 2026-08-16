from __future__ import annotations

import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from .phase_d2_visual_matrix import d2_visual_matrix
from .structural_pipeline import DoboStructuralPipeline

BENCHMARK_VERSION="D2.0"

def _mesh(path:str):
    m=trimesh.load_mesh(path,process=True)
    return trimesh.util.concatenate(tuple(m.geometry.values())) if isinstance(m,trimesh.Scene) else m

def run(output_root:str|Path)->dict:
    root=Path(output_root).resolve(); root.mkdir(parents=True,exist_ok=True); records=[]; meshes={}
    for case in d2_visual_matrix():
        try:
            r=DoboStructuralPipeline().generate_from_semantic(case.program,output_root=root/"generated"/case.id); m=_mesh(r.stl_path); meshes[case.id]=m
            records.append({"id":case.id,"label":case.label,"goal":case.visual_goal,"profile":r.trace.body_profile,"status":"PASS","stl":r.stl_path,"three_mf":r.three_mf_path,"watertight":bool(m.is_watertight),"components":len(tuple(m.split(only_watertight=False)))})
        except Exception as exc:
            records.append({"id":case.id,"label":case.label,"goal":case.visual_goal,"profile":case.expected_profile,"status":"FAIL","failure":f"{type(exc).__name__}: {exc}"}); print("D2 FAILURE",case.id,type(exc).__name__,exc)
    fig=plt.figure(figsize=(15,23))
    for row,rec in enumerate(records):
        info=fig.add_subplot(len(records),4,row*4+1); info.axis("off"); info.text(0,.92,f"{row+1:02d} {rec['label']}",weight="bold",fontsize=10); info.text(0,.72,f"Profile: {rec['profile']}\nPhysical: {rec['status']}\n{rec['goal']}",fontsize=7.3,va="top",wrap=True)
        m=meshes.get(rec['id'])
        if m is None: continue
        v=m.vertices.copy(); v-=(v.min(0)+v.max(0))/2; v/=max(float(max(v.max(0)-v.min(0))),1e-9)
        for off,(elev,azim,title) in enumerate(((24,-42,"Perspective"),(0,-90,"Front"),(90,-90,"Top")),2):
            ax=fig.add_subplot(len(records),4,row*4+off,projection="3d"); ax.plot_trisurf(v[:,0],v[:,1],v[:,2],triangles=m.faces,linewidth=.025,shade=True); ax.view_init(elev=elev,azim=azim); ax.set_axis_off(); ax.set_xlim(-.56,.56); ax.set_ylim(-.56,.56); ax.set_zlim(-.56,.56)
            if row==0: ax.set_title(title,fontsize=9)
    fig.suptitle("DOBO Macroblock D2 — High-detail Reference-driven Construction",fontsize=16,y=.997); fig.tight_layout(rect=(.015,.01,.985,.985)); board=root/"d2_real_high_detail_board.png"; fig.savefig(board,dpi=175); plt.close(fig)
    passed=sum(x['status']=="PASS" for x in records); payload={"benchmark_version":BENCHMARK_VERSION,"summary":{"PASS":passed,"FAIL":len(records)-passed},"human_visual_gate_required":True,"records":records,"board":str(board)}; manifest=root/"d2_manifest.json"; manifest.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8"); print("D2 PASS",passed,"FAIL",len(records)-passed); print("board",board)
    if passed!=len(records): raise SystemExit(1)
    return payload

if __name__=="__main__": run("outputs/macroblock_d2_visual_benchmark")
