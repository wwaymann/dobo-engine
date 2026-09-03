from __future__ import annotations
import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from .phase_d_visual_matrix import d_visual_matrix
from .structural_pipeline import DoboStructuralPipeline
BENCHMARK_VERSION="D1.0-consolidation"
def _mesh(path):
    m=trimesh.load_mesh(path,process=True)
    return trimesh.util.concatenate(tuple(m.geometry.values())) if isinstance(m,trimesh.Scene) else m
def run(output_root):
    root=Path(output_root).resolve(); root.mkdir(parents=True,exist_ok=True); records=[]; meshes={}
    for case in d_visual_matrix():
        try:
            r=DoboStructuralPipeline().generate_from_semantic(case.program,output_root=root/"generated"/case.id); m=_mesh(r.stl_path); meshes[case.id]=m; motor=json.loads(Path(r.motor_path).read_text(encoding="utf-8")); profile=str(motor.get("morphogenesis",{}).get("profile",""))
            records.append({"id":case.id,"label":case.label,"goal":case.visual_goal,"profile":profile,"expected_profile":case.expected_profile,"status":"PASS" if profile==case.expected_profile and m.is_watertight and len(tuple(m.split(only_watertight=False)))==1 else "FAIL","stl":r.stl_path,"three_mf":r.three_mf_path,"watertight":bool(m.is_watertight),"components":len(tuple(m.split(only_watertight=False)))})
        except Exception as exc: records.append({"id":case.id,"label":case.label,"status":"FAIL","failure":f"{type(exc).__name__}: {exc}"})
    passed=sum(x["status"]=="PASS" for x in records); payload={"benchmark_version":BENCHMARK_VERSION,"summary":{"PASS":passed,"FAIL":len(records)-passed},"records":records}
    manifest=root/"d1_consolidation_manifest.json"; manifest.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("D1 CONSOLIDATION PASS",passed,"FAIL",len(records)-passed); print("manifest",manifest)
    if passed!=len(records): raise SystemExit(1)
    return payload
if __name__=="__main__": run("outputs/consolidation_macroblock_d")
