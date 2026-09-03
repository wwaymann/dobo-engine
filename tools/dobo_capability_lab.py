from __future__ import annotations

import json
import mimetypes
import os
import re
import sys
import threading
import traceback
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))

from product_generators.design_interpreter.phase_5_design_matrix import _program
from product_generators.design_interpreter.prompt_interpreter import OpenAIResponsesSemanticClient
from product_generators.design_interpreter.structural_pipeline import DoboStructuralPipeline

HOST = os.environ.get("DOBO_LAB_HOST", "127.0.0.1")
PORT = int(os.environ.get("DOBO_LAB_PORT", "8765"))
OUTPUT_ROOT = ROOT / "outputs" / "capability-lab"
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

PRIMITIVES = {
    "cubo": dict(family="organic", tags=["cuboid"], height=110.0, width=110.0, depth=110.0, opening="polygonal"),
    "cube": dict(family="organic", tags=["cuboid"], height=110.0, width=110.0, depth=110.0, opening="polygonal"),
    "rectangular": dict(family="organic", tags=["rectangular_prism"], height=105.0, width=145.0, depth=95.0, opening="polygonal"),
    "prisma rectangular": dict(family="organic", tags=["rectangular_prism"], height=105.0, width=145.0, depth=95.0, opening="polygonal"),
    "cilindro": dict(family="cylindrical", tags=["cylindrical"], height=115.0, width=110.0, depth=110.0, opening="circular"),
    "cylinder": dict(family="cylindrical", tags=["cylindrical"], height=115.0, width=110.0, depth=110.0, opening="circular"),
    "cono": dict(family="tapered", tags=["tapered_revolution"], height=120.0, width=120.0, depth=120.0, opening="circular"),
    "cone": dict(family="tapered", tags=["tapered_revolution"], height=120.0, width=120.0, depth=120.0, opening="circular"),
    "esfera": dict(family="spherical", tags=["spherical"], height=112.0, width=122.0, depth=122.0, opening="circular"),
    "sphere": dict(family="spherical", tags=["spherical"], height=112.0, width=122.0, depth=122.0, opening="circular"),
    "ovoide": dict(family="organic", tags=["ovoid"], height=125.0, width=112.0, depth=106.0, opening="elliptical"),
    "ovoid": dict(family="organic", tags=["ovoid"], height=125.0, width=112.0, depth=106.0, opening="elliptical"),
    "triangular": dict(family="hexagonal", tags=["triangular_prism"], height=112.0, width=120.0, depth=120.0, opening="polygonal"),
    "prisma triangular": dict(family="hexagonal", tags=["triangular_prism"], height=112.0, width=120.0, depth=120.0, opening="polygonal"),
    "anfora ahusada": dict(family="tapered", tags=["amphora_tapered"], height=135.0, width=120.0, depth=120.0, opening="circular"),
    "urna globular": dict(family="tapered", tags=["urn_bellied"], height=120.0, width=125.0, depth=125.0, opening="circular"),
    "barril": dict(family="tapered", tags=["barrel"], height=115.0, width=125.0, depth=125.0, opening="circular"),
    "cuello estrecho": dict(family="tapered", tags=["narrow_neck"], height=135.0, width=120.0, depth=120.0, opening="circular"),
    "borde ensanchado": dict(family="tapered", tags=["flared_rim"], height=120.0, width=125.0, depth=125.0, opening="circular"),
    "tronco invertido": dict(family="tapered", tags=["inverted_taper"], height=120.0, width=120.0, depth=120.0, opening="circular"),
    "reloj de arena": dict(family="tapered", tags=["hourglass"], height=130.0, width=120.0, depth=120.0, opening="circular"),
    "ahusada alta": dict(family="tapered", tags=["tall_taper"], height=150.0, width=105.0, depth=105.0, opening="circular"),
    "ovoide alta": dict(family="tapered", tags=["oval_tall"], height=145.0, width=115.0, depth=115.0, opening="circular"),
    "urna pedestal": dict(family="tapered", tags=["pedestal_urn"], height=145.0, width=120.0, depth=120.0, opening="circular"),
}


def _slug(text: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", text.strip()).strip("-").lower()
    return value[:70] or "design"


def _offline_semantic(prompt: str):
    lowered = prompt.lower()
    match = None
    for key in sorted(PRIMITIVES, key=len, reverse=True):
        if key in lowered:
            match = PRIMITIVES[key]
            break
    if match is None:
        return None
    return _program(
        f"lab_{_slug(prompt)}",
        prompt,
        family=match["family"],
        height=match["height"],
        width=match["width"],
        depth=match["depth"],
        opening_shape=match["opening"],
        opening_width=0.58,
        opening_depth=0.58,
        style_tags=match["tags"],
        features=[],
        relations=[],
    )


def _rel(path: str | Path) -> str:
    p = Path(path).resolve()
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


def _physical_vessel_checks(result, vessel: dict) -> tuple[bool, bool, dict]:
    """Report generated geometry, not legacy/missing motor aliases."""
    checks = dict(getattr(result.mesh_result, "semantic_checks", {}) or {})

    if "cavity_is_empty" in checks or "opening_is_clear" in checks:
        cavity_ok = bool(checks.get("cavity_is_empty", False)) and bool(
            checks.get("opening_is_clear", False)
        )
    else:
        cavity_ok = bool(vessel.get("opening")) or (
            vessel.get("opening_center") is not None
            and vessel.get("opening_radii") is not None
        )

    if "drain_is_clear" in checks:
        drain_ok = bool(checks["drain_is_clear"])
    else:
        drain_ok = bool(vessel.get("drain")) or (
            vessel.get("drain_center") is not None
            and vessel.get("drain_radius_mm") is not None
        )

    return cavity_ok, drain_ok, checks


def generate(prompt: str, mode: str = "auto") -> dict:
    prompt = prompt.strip()
    if not prompt:
        raise ValueError("Escribe una instrucción para el Motor DOBO.")

    semantic = _offline_semantic(prompt) if mode in {"auto", "offline"} else None
    source = "offline-semantic"
    if semantic is not None:
        pipeline = DoboStructuralPipeline()
        result = pipeline.generate_from_semantic(semantic, output_root=OUTPUT_ROOT / _slug(prompt))
    else:
        if mode == "offline":
            raise ValueError("El modo offline reconoce por ahora las familias básicas del laboratorio.")
        model = os.environ.get("DOBO_OPENAI_MODEL")
        if not model:
            raise RuntimeError("Para prompts libres define DOBO_OPENAI_MODEL y OPENAI_API_KEY. Las familias básicas y los perfiles catalogados funcionan sin OpenAI.")
        source = "openai-prompt"
        client = OpenAIResponsesSemanticClient(model=model)
        pipeline = DoboStructuralPipeline(prompt_client=client)
        result = pipeline.generate_from_prompt(prompt, output_root=OUTPUT_ROOT / _slug(prompt))

    result.validate()
    semantic_data = json.loads(Path(result.semantic_path).read_text(encoding="utf-8"))
    motor_data = json.loads(Path(result.motor_path).read_text(encoding="utf-8"))
    manifest_data = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
    validation = manifest_data.get("validation", {})
    vessel = motor_data.get("vessel", {})
    cavity_ok, drain_ok, semantic_checks = _physical_vessel_checks(result, vessel)

    return {
        "ok": True,
        "prompt": prompt,
        "source": source,
        "profile": result.trace.body_profile,
        "morphology": motor_data.get("morphogenesis", {}).get("profile"),
        "semantic": semantic_data,
        "motor": motor_data,
        "validation": validation,
        "vessel": {
            "wall_mm": vessel.get("wall_mm"),
            "bottom_mm": vessel.get("bottom_mm"),
            "opening": cavity_ok,
            "drain": drain_ok,
            "semantic_checks": semantic_checks,
        },
        "artifacts": {
            "stl": "/artifact?path=" + urllib.parse.quote(_rel(result.stl_path)),
            "three_mf": "/artifact?path=" + urllib.parse.quote(_rel(result.three_mf_path)),
            "semantic": "/artifact?path=" + urllib.parse.quote(_rel(result.semantic_path)),
            "motor": "/artifact?path=" + urllib.parse.quote(_rel(result.motor_path)),
            "manifest": "/artifact?path=" + urllib.parse.quote(_rel(result.manifest_path)),
        },
        "trace": {
            "pipeline": result.trace.pipeline_version,
            "generation_seconds": result.trace.generation_seconds,
            "vertices": result.trace.vertex_count,
            "faces": result.trace.face_count,
            "generation_attempts": result.trace.generation_attempts,
        },
    }


HTML = r'''<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DOBO Capability Lab</title>
<style>
:root{--bg:#111310;--panel:#1a1e19;--panel2:#20251f;--line:#343b32;--text:#f3f0e8;--muted:#a6afa0;--accent:#d6ff54;--bad:#ff7c68;--good:#82e67c}
*{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif;height:100vh;overflow:hidden}
header{height:58px;border-bottom:1px solid var(--line);display:flex;align-items:center;padding:0 20px;gap:14px;background:#141713}.brand{font-weight:800;letter-spacing:.08em}.brand b{color:var(--accent)}.sub{font-size:12px;color:var(--muted)}.status{margin-left:auto;font-size:12px;border:1px solid var(--line);border-radius:999px;padding:6px 10px}
main{display:grid;grid-template-columns:320px 1fr 360px;height:calc(100vh - 58px)} aside,.right{background:var(--panel);padding:18px;overflow:auto}.left{border-right:1px solid var(--line)}.right{border-left:1px solid var(--line)}
label,h3{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted)}textarea{width:100%;height:150px;background:#111410;border:1px solid var(--line);border-radius:14px;color:var(--text);padding:14px;resize:vertical;font:inherit;line-height:1.4;outline:none}textarea:focus{border-color:#6d7d51}
button{border:0;border-radius:11px;padding:11px 13px;font-weight:750;cursor:pointer}.run{width:100%;background:var(--accent);color:#10130b;margin-top:10px}.run:disabled{opacity:.45;cursor:wait}
.examples{display:flex;flex-wrap:wrap;gap:7px;margin:12px 0 18px}.chip{font-size:11px;padding:7px 9px;border-radius:999px;background:#262c24;border:1px solid var(--line);cursor:pointer;color:#dbe1d6}
.section{margin-top:20px}.cap{display:grid;grid-template-columns:1fr auto;gap:8px;padding:9px 0;border-bottom:1px solid #292e27;font-size:12px}.dot{width:8px;height:8px;border-radius:50%;background:#6b7168;display:inline-block;margin-right:7px}
.stage{position:relative;min-width:0;background:radial-gradient(circle at 50% 45%,#2b3029,#121411 62%);overflow:hidden}.toolbar{position:absolute;z-index:4;left:16px;top:16px;display:flex;gap:7px}.toolbar button{padding:8px 10px;font-size:11px;background:rgba(24,28,23,.9);border:1px solid var(--line);color:var(--text)}#viewer{width:100%;height:calc(100% - 160px);display:block}.renders{height:160px;border-top:1px solid var(--line);padding:12px 16px;background:#151815}.renderrow{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;height:110px}.shot{background:#20241f;border:1px solid var(--line);border-radius:10px;overflow:hidden;position:relative}.shot img{width:100%;height:100%;object-fit:cover}.shot span{position:absolute;left:7px;bottom:5px;font-size:10px;background:#111b;padding:3px 5px;border-radius:5px}
.placeholder{position:absolute;inset:0 0 160px 0;display:grid;place-items:center;text-align:center;color:var(--muted);pointer-events:none}.placeholder strong{display:block;color:#dfe5da;font-size:18px;margin-bottom:6px}.card{background:var(--panel2);border:1px solid var(--line);border-radius:13px;padding:13px;margin-bottom:12px}.big{font-size:26px;font-weight:800}.muted{color:var(--muted);font-size:12px}.checks{display:grid;grid-template-columns:1fr auto;gap:7px;font-size:12px;margin-top:8px}.pass{color:var(--good)}.fail{color:var(--bad)}pre{font:11px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;word-break:break-word;background:#111410;padding:10px;border-radius:9px;max-height:260px;overflow:auto;color:#cbd3c6}.tabs{display:flex;gap:5px;margin-bottom:8px}.tabs button{font-size:10px;padding:6px 8px;background:#282e26;color:var(--muted)}.tabs button.active{color:#10130b;background:var(--accent)}.links{display:grid;grid-template-columns:1fr 1fr;gap:7px}.links a{text-decoration:none;text-align:center;padding:8px;border-radius:8px;border:1px solid var(--line);color:#e8eee3;font-size:11px;background:#242923}.error{border-color:#713d38;color:#ffd1c9;background:#2a1816}.spinner{display:inline-block;width:11px;height:11px;border:2px solid #0004;border-top-color:#111;border-radius:50%;animation:spin .7s linear infinite;margin-right:7px}@keyframes spin{to{transform:rotate(360deg)}}
@media(max-width:1000px){main{grid-template-columns:270px 1fr}.right{position:absolute;right:0;top:58px;width:340px;height:calc(100vh - 58px);transform:translateX(100%)}}
</style>
</head>
<body>
<header><div class="brand">DOBO <b>LAB</b></div><div class="sub">Banco de prueba del motor consolidado · integration-consolidation-core</div><div class="status" id="engineStatus">Motor listo</div></header>
<main>
<aside class="left"><label>Instrucción humana</label><textarea id="prompt" placeholder="Ej: Crea una maceta esférica hueca con abertura superior...">Crea una maceta cúbica</textarea><button class="run" id="run">Generar con Motor DOBO</button><div class="examples"><span class="chip">Cubo</span><span class="chip">Prisma rectangular</span><span class="chip">Cilindro</span><span class="chip">Cono</span><span class="chip">Esfera</span><span class="chip">Ovoide</span><span class="chip">Prisma triangular</span><span class="chip">Ánfora ahusada</span><span class="chip">Urna globular</span><span class="chip">Barril</span><span class="chip">Cuello estrecho</span><span class="chip">Borde ensanchado</span><span class="chip">Tronco invertido</span><span class="chip">Reloj de arena</span><span class="chip">Ahusada alta</span><span class="chip">Ovoide alta</span><span class="chip">Urna pedestal</span></div>
<div class="section"><h3>Qué estamos comprobando</h3><div class="cap"><span><i class="dot"></i>Interpretación</span><b id="cSemantic">—</b></div><div class="cap"><span><i class="dot"></i>Geometría</span><b id="cGeometry">—</b></div><div class="cap"><span><i class="dot"></i>Cavidad</span><b id="cCavity">—</b></div><div class="cap"><span><i class="dot"></i>Drenaje</span><b id="cDrain">—</b></div><div class="cap"><span><i class="dot"></i>Fabricación</span><b id="cMfg">—</b></div></div>
<div class="section"><h3>Modo</h3><div class="muted">Las 7 familias básicas y 10 perfiles de revolución se ejecutan offline. Los prompts libres usan OpenAI solo para interpretar, si hay API configurada. El modelo físico siempre lo construye DOBO.</div></div></aside>
<section class="stage"><div class="toolbar"><button id="home">Encuadrar</button><button id="wire">Wireframe</button><button id="rotate">Auto-rotar</button></div><canvas id="viewer"></canvas><div class="placeholder" id="placeholder"><div><strong>Modelo 3D en vivo</strong>Ejecuta una instrucción para inspeccionar la geometría real.</div></div><div class="renders"><h3 style="margin:0 0 9px">Renders del modelo generado</h3><div class="renderrow"><div class="shot"><img id="shot1"><span>Frontal</span></div><div class="shot"><img id="shot2"><span>3/4</span></div><div class="shot"><img id="shot3"><span>Superior</span></div></div></div></section>
<section class="right"><div id="summary" class="card"><div class="muted">Resultado</div><div class="big">Sin prueba</div><div class="muted">Aquí aparecerá exactamente lo que el motor consiguió generar.</div></div><div id="error" class="card error" style="display:none"></div><div class="card"><h3>Validación física</h3><div class="checks" id="checks"><span>Watertight</span><b>—</b><span>Winding consistente</span><b>—</b><span>Componentes</span><b>—</b><span>Intentos</span><b>—</b></div></div><div class="card"><h3>Artefactos reales</h3><div class="links" id="links"><a>STL</a><a>3MF</a><a>Motor JSON</a><a>Manifest</a></div></div><div class="card"><div class="tabs"><button class="active" data-tab="semantic">Semántica</button><button data-tab="motor">Motor</button></div><pre id="json">Todavía no hay datos.</pre></div></section>
</main>
<script type="importmap">{"imports":{"three":"https://unpkg.com/three@0.164.1/build/three.module.js","three/addons/":"https://unpkg.com/three@0.164.1/examples/jsm/"}}</script>
<script type="module">
import * as THREE from 'three';import {OrbitControls} from 'three/addons/controls/OrbitControls.js';import {STLLoader} from 'three/addons/loaders/STLLoader.js';
const canvas=document.querySelector('#viewer'),stage=canvas.parentElement;const renderer=new THREE.WebGLRenderer({canvas,antialias:true,preserveDrawingBuffer:true,alpha:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.shadowMap.enabled=true;
const scene=new THREE.Scene();const camera=new THREE.PerspectiveCamera(38,1,.1,5000);camera.position.set(180,-210,150);const controls=new OrbitControls(camera,canvas);controls.enableDamping=true;controls.target.set(0,0,40);scene.add(new THREE.HemisphereLight(0xffffff,0x293023,2.2));const key=new THREE.DirectionalLight(0xffffff,3.1);key.position.set(-140,-180,240);key.castShadow=true;scene.add(key);const fill=new THREE.DirectionalLight(0xbfd7ff,1.2);fill.position.set(180,80,120);scene.add(fill);const floor=new THREE.Mesh(new THREE.PlaneGeometry(800,800),new THREE.MeshStandardMaterial({color:0x171a16,roughness:1}));floor.rotation.x=-Math.PI/2;floor.position.z=-3;floor.receiveShadow=true;scene.add(floor);
let mesh=null,auto=false,wire=false,data=null;
function size(){const h=stage.clientHeight-160;renderer.setSize(stage.clientWidth,h,false);camera.aspect=stage.clientWidth/h;camera.updateProjectionMatrix()}addEventListener('resize',size);size();
function fit(){if(!mesh)return;const box=new THREE.Box3().setFromObject(mesh),s=box.getSize(new THREE.Vector3()),c=box.getCenter(new THREE.Vector3()),max=Math.max(s.x,s.y,s.z);controls.target.copy(c);camera.position.set(c.x+max*1.55,c.y-max*1.8,c.z+max*1.25);camera.near=max/100;camera.far=max*30;camera.updateProjectionMatrix();controls.update()}
function loop(){requestAnimationFrame(loop);if(auto&&mesh)mesh.rotation.z+=.005;controls.update();renderer.render(scene,camera)}loop();
async function loadSTL(url){return new Promise((ok,bad)=>new STLLoader().load(url,g=>{if(mesh){scene.remove(mesh);mesh.geometry.dispose();mesh.material.dispose()}g.computeVertexNormals();mesh=new THREE.Mesh(g,new THREE.MeshStandardMaterial({color:0xb7c48b,roughness:.58,metalness:.02,side:THREE.DoubleSide}));mesh.castShadow=true;mesh.receiveShadow=true;scene.add(mesh);document.querySelector('#placeholder').style.display='none';fit();setTimeout(shots,250);ok()},undefined,bad))}
function shot(pos,target=[0,0,35]){const oldP=camera.position.clone(),oldT=controls.target.clone();camera.position.set(...pos);controls.target.set(...target);controls.update();renderer.render(scene,camera);const img=renderer.domElement.toDataURL('image/png');camera.position.copy(oldP);controls.target.copy(oldT);controls.update();return img}
function shots(){if(!mesh)return;const box=new THREE.Box3().setFromObject(mesh),s=box.getSize(new THREE.Vector3()),c=box.getCenter(new THREE.Vector3()),m=Math.max(s.x,s.y,s.z);document.querySelector('#shot1').src=shot([c.x,c.y-m*2.4,c.z+.2*m],[c.x,c.y,c.z]);document.querySelector('#shot2').src=shot([c.x+1.6*m,c.y-1.8*m,c.z+1.25*m],[c.x,c.y,c.z]);document.querySelector('#shot3').src=shot([c.x+.05,c.y-.05,c.z+2.8*m],[c.x,c.y,c.z])}
const q=s=>document.querySelector(s),run=q('#run'),prompt=q('#prompt');document.querySelectorAll('.chip').forEach(x=>x.onclick=()=>{prompt.value='Crea una maceta '+x.textContent.toLowerCase()});q('#home').onclick=fit;q('#wire').onclick=()=>{wire=!wire;if(mesh)mesh.material.wireframe=wire};q('#rotate').onclick=()=>auto=!auto;
function mark(id,val){const e=q(id);e.textContent=val?'PASS':'FAIL';e.className=val?'pass':'fail'}
function update(d){data=d;q('#summary').innerHTML=`<div class="muted">Resultado real</div><div class="big">${d.morphology||d.profile||'Generado'}</div><div class="muted">${d.source} · ${d.trace.generation_seconds.toFixed(2)} s · ${d.trace.vertices.toLocaleString()} vértices</div>`;const v=d.validation||{};q('#checks').innerHTML=`<span>Watertight</span><b class="${v.watertight?'pass':'fail'}">${String(v.watertight)}</b><span>Winding consistente</span><b class="${v.winding_consistent?'pass':'fail'}">${String(v.winding_consistent)}</b><span>Componentes</span><b>${v.component_count??'—'}</b><span>Intentos</span><b>${d.trace.generation_attempts}</b>`;mark('#cSemantic',true);mark('#cGeometry',!!v.watertight);mark('#cCavity',!!d.vessel?.opening);mark('#cDrain',!!d.vessel?.drain);mark('#cMfg',!!v.watertight&&!!v.winding_consistent);q('#json').textContent=JSON.stringify(d.semantic,null,2);q('#links').innerHTML=`<a href="${d.artifacts.stl}" download>STL</a><a href="${d.artifacts.three_mf}" download>3MF</a><a href="${d.artifacts.motor}" target="_blank">Motor JSON</a><a href="${d.artifacts.manifest}" target="_blank">Manifest</a>`;loadSTL(d.artifacts.stl)}
run.onclick=async()=>{run.disabled=true;run.innerHTML='<span class="spinner"></span>Generando...';q('#error').style.display='none';q('#engineStatus').textContent='Motor ejecutando';try{const r=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:prompt.value,mode:'auto'})});const d=await r.json();if(!r.ok||!d.ok)throw new Error(d.error||'Fallo de generación');update(d);q('#engineStatus').textContent='Generación válida'}catch(e){q('#error').style.display='block';q('#error').textContent=e.message;q('#engineStatus').textContent='Generación fallida'}finally{run.disabled=false;run.textContent='Generar con Motor DOBO'}};
document.querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>{document.querySelectorAll('.tabs button').forEach(x=>x.classList.remove('active'));b.classList.add('active');q('#json').textContent=data?JSON.stringify(data[b.dataset.tab],null,2):'Todavía no hay datos.'});
</script></body></html>'''


class Handler(BaseHTTPRequestHandler):
    server_version = "DOBOCapabilityLab/1.0"

    def _json(self, payload: dict, status: int = 200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/status":
            self._json({"ok": True, "branch": "integration-consolidation-core", "openai_model": os.environ.get("DOBO_OPENAI_MODEL"), "output_root": str(OUTPUT_ROOT)})
            return
        if parsed.path == "/artifact":
            value = urllib.parse.parse_qs(parsed.query).get("path", [""])[0]
            target = (ROOT / value).resolve()
            if ROOT not in target.parents or not target.is_file():
                self.send_error(404)
                return
            body = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Content-Disposition", f'inline; filename="{target.name}"')
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def do_POST(self):
        if self.path != "/api/generate":
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(size).decode("utf-8"))
            result = generate(str(payload.get("prompt", "")), str(payload.get("mode", "auto")))
            self._json(result)
        except Exception as exc:
            traceback.print_exc()
            self._json({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, 500)

    def log_message(self, fmt, *args):
        print("[DOBO LAB]", fmt % args)


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}"
    print("DOBO Capability Lab")
    print("Branch: integration-consolidation-core")
    print("URL:", url)
    print("Las familias básicas y los perfiles catalogados funcionan offline; prompts libres requieren OPENAI_API_KEY + DOBO_OPENAI_MODEL.")
    if os.environ.get("DOBO_LAB_NO_BROWSER") != "1":
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
