from __future__ import annotations

"""DOBO Design Lab: product-facing configurator over the real CAD engine.

Unlike the Capability Lab, this surface never asks an end user to write engine
prompts such as "crea una maceta curva S". It exposes a deliberately small set
of visual decisions and converts them directly into DOBO semantic contracts.
"""

import json
import mimetypes
import re
import sys
import threading
import traceback
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))

from product_generators.design_interpreter.intelligent_surfaces import SurfaceLayerIntent
from product_generators.design_interpreter.native_profiled_cad_adapter import (
    PROFILE_CATALOG,
    PROFILE_DEFAULT_DIMENSIONS,
    _smooth_profile,
)
from product_generators.design_interpreter.phase_5_design_matrix import _feature, _program
from product_generators.design_interpreter.structural_pipeline import DoboStructuralPipeline


DESIGN_LAB_VERSION = "DESIGNLAB.1-visual-configurator"
HOST = "127.0.0.1"
PORT = 8770
OUTPUT_ROOT = ROOT / "outputs" / "design-lab"
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


DESIGN_CATALOG: tuple[dict[str, str], ...] = (
    {"id": "soft_low", "variant": "low_urn", "name": "Suave", "group": "Orgánica", "caption": "baja y amplia"},
    {"id": "wide_bowl", "variant": "wide_bowl", "name": "Cuenco", "group": "Contemporánea", "caption": "abierta y horizontal"},
    {"id": "soft_taper", "variant": "inverted_taper", "name": "Taper", "group": "Minimal", "caption": "simple y ascendente"},
    {"id": "capsule", "variant": "capsule", "name": "Cápsula", "group": "Minimal", "caption": "alta y redondeada"},
    {"id": "bell", "variant": "cone_bell", "name": "Campana", "group": "Contemporánea", "caption": "base fina, boca amplia"},
    {"id": "tulip", "variant": "tulip", "name": "Tulipán", "group": "Orgánica", "caption": "abierta y suave"},
    {"id": "drop", "variant": "teardrop", "name": "Gota", "group": "Orgánica", "caption": "volumen concentrado"},
    {"id": "pedestal", "variant": "footed_bowl", "name": "Pedestal", "group": "Escultórica", "caption": "base elevada"},
    {"id": "hourglass", "variant": "hourglass", "name": "Cintura", "group": "Escultórica", "caption": "estrecha al centro"},
    {"id": "totem", "variant": "double_bulb", "name": "Tótem", "group": "Escultórica", "caption": "doble volumen"},
    {"id": "curve", "variant": "s_curve", "name": "Curva", "group": "Escultórica", "caption": "perfil asimétrico vertical"},
    {"id": "lantern", "variant": "lantern", "name": "Farol", "group": "Geométrica suave", "caption": "ritmo de volúmenes"},
)


FONT_STYLES = {
    "strong": {"tag": "font_strong", "label": "Fuerte"},
    "clean": {"tag": "font_clean", "label": "Limpia"},
    "editorial": {"tag": "font_editorial", "label": "Editorial"},
    "classic": {"tag": "font_classic", "label": "Clásica"},
    "tech": {"tag": "font_tech", "label": "Técnica"},
}

POSITIONS = {
    "top": 0.72,
    "center": 0.52,
    "bottom": 0.31,
    "wrap": 0.52,
}

TEXT_SIZES = {
    "small": 0.075,
    "medium": 0.12,
    "large": 0.18,
    "xl": 0.27,
}


def _slug(value: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip()).strip("-").lower()
    return clean[:70] or "design"


def _catalog_payload() -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for item in DESIGN_CATALOG:
        variant = item["variant"]
        dense = _smooth_profile(PROFILE_CATALOG[variant])
        maximum = max(radius for _z, radius in dense)
        points = [
            [round(float(z), 5), round(float(radius / maximum), 5)]
            for z, radius in dense
        ]
        payload.append({**item, "profile": points})
    return payload


def _catalog_item(design_id: str) -> dict[str, str]:
    for item in DESIGN_CATALOG:
        if item["id"] == design_id:
            return item
    raise ValueError("Selecciona una forma válida.")


def _hex(value: object, fallback: str) -> str:
    text = str(value or fallback).upper()
    if not re.fullmatch(r"#[0-9A-F]{6}", text):
        return fallback
    return text


def _design_program(spec: dict[str, Any]):
    item = _catalog_item(str(spec.get("shape", "soft_low")))
    variant = item["variant"]
    height, width = PROFILE_DEFAULT_DIMENSIONS[variant]

    text_value = str(spec.get("text", "")).strip()
    if len(text_value) > 80:
        raise ValueError("El texto puede tener como máximo 80 caracteres.")

    position_key = str(spec.get("position", "center"))
    size_key = str(spec.get("size", "medium"))
    relief = str(spec.get("relief", "raised"))
    font_key = str(spec.get("font", "strong"))

    if position_key not in POSITIONS:
        raise ValueError("La posición de texto no es válida.")
    if size_key not in TEXT_SIZES:
        raise ValueError("El tamaño de texto no es válido.")
    if relief not in {"raised", "recessed"}:
        raise ValueError("El relieve de texto no es válido.")
    if font_key not in FONT_STYLES:
        raise ValueError("La tipografía no es válida.")

    style_tags = [variant, FONT_STYLES[font_key]["tag"]]
    if position_key == "wrap":
        style_tags.append("text_layout_wrap")

    features = []
    if text_value:
        features.append(
            _feature(
                "user_text",
                "text_user",
                "text",
                relief,
                region="front",
                horizontal=0.0,
                vertical=POSITIONS[position_key],
                width=0.92 if position_key == "wrap" else 0.62,
                height=TEXT_SIZES[size_key],
                depth=1.20,
            )
        )

    safe_text = text_value.replace('"', "'")
    prompt = (
        f'DOBO Design Lab. Forma {item["name"]}. Texto exacto "{safe_text}".'
        if text_value
        else f'DOBO Design Lab. Forma {item["name"]}. Sin texto.'
    )

    program = _program(
        f"design_lab_{item['id']}_{_slug(text_value or 'plain')}",
        prompt,
        family="tapered",
        height=height,
        width=width,
        depth=width,
        opening_shape="circular",
        opening_width=0.58,
        opening_depth=0.58,
        style_tags=style_tags,
        features=features,
        relations=[],
    )
    return program, item, text_value, position_key, size_key, relief


def generate_design(spec: dict[str, Any]) -> dict[str, Any]:
    program, item, text_value, position_key, size_key, relief = _design_program(spec)

    body_color = _hex(spec.get("body_color"), "#E8E0D4")
    text_color = _hex(spec.get("text_color"), "#262626")
    accent_color = _hex(spec.get("accent_color"), "#BDA37A")

    surface_intents: tuple[SurfaceLayerIntent, ...] = ()
    if text_value:
        if len({body_color, text_color, accent_color}) != 3:
            raise ValueError("Cuerpo, texto y acento deben usar tres colores distintos.")
        surface_intents = (
            SurfaceLayerIntent(
                id="user_text_material",
                kind="text",
                payload=text_value,
                region="all_around" if position_key == "wrap" else "front",
                u_center=0.5,
                v_center=POSITIONS[position_key],
                width_fraction=1.0 if position_key == "wrap" else 0.68,
                height_fraction=TEXT_SIZES[size_key],
                effect=relief,
                depth_mm=1.20,
                color=text_color,
                filament_slot=2,
            ),
            SurfaceLayerIntent(
                id="design_accent",
                kind="procedural_relief",
                payload="upper design accent",
                region="upper",
                u_center=0.5,
                v_center=0.95,
                width_fraction=1.0,
                height_fraction=0.07,
                effect="color_only",
                depth_mm=0.0,
                color=accent_color,
                filament_slot=3,
            ),
        )

    output = OUTPUT_ROOT / _slug(
        f"{item['id']}-{text_value or 'plain'}-{position_key}-{size_key}-{relief}"
    )
    pipeline = DoboStructuralPipeline()
    result = pipeline.generate_from_semantic(
        program,
        output_root=output,
        surface_intents=surface_intents,
        base_color=body_color,
        generation_budget_seconds=240.0,
    )
    result.validate()

    motor = json.loads(Path(result.motor_path).read_text(encoding="utf-8"))
    manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
    native_text = motor.get("_native_profiled_text", {})
    multicolor = motor.get("_profiled_multicolor", {})
    saucer = motor.get("_profiled_saucer", {})

    return {
        "ok": True,
        "version": DESIGN_LAB_VERSION,
        "shape": item,
        "selection": {
            "text": text_value,
            "position": position_key,
            "size": size_key,
            "relief": relief,
            "font": str(spec.get("font", "strong")),
            "body_color": body_color,
            "text_color": text_color,
            "accent_color": accent_color,
        },
        "validation": manifest.get("validation", {}),
        "text": native_text,
        "multicolor": multicolor,
        "trace": {
            "route": motor.get("_capability_route"),
            "vertices": result.trace.vertex_count,
            "faces": result.trace.face_count,
            "seconds": result.trace.generation_seconds,
        },
        "artifacts": {
            "stl": _artifact_url(result.stl_path),
            "three_mf": _artifact_url(result.three_mf_path),
            "saucer": (
                _artifact_url(str(saucer.get("stl_path")))
                if isinstance(saucer, dict) and saucer.get("stl_path")
                else None
            ),
        },
    }


def _artifact_url(path: str | Path) -> str:
    target = Path(path).resolve()
    try:
        relative = target.relative_to(ROOT)
    except ValueError as error:
        raise RuntimeError("Design Lab artifact escaped the repository.") from error
    return "/artifact?path=" + urllib.parse.quote(str(relative).replace("\\", "/"))


HTML = r'''<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DOBO Design Lab</title>
<style>
:root{--bg:#f3f0ea;--paper:#fffdf8;--ink:#20211e;--muted:#787970;--line:#d8d5cc;--accent:#222;--ok:#347a42}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif}
header{height:62px;padding:0 24px;display:flex;align-items:center;border-bottom:1px solid var(--line);background:var(--paper);position:sticky;top:0;z-index:10}
.brand{font-weight:900;letter-spacing:.08em}.brand b{font-weight:500;color:#777}.status{margin-left:auto;font-size:12px;color:var(--muted)}
main{display:grid;grid-template-columns:390px minmax(420px,1fr) 330px;min-height:calc(100vh - 62px)}
.left,.right{padding:22px;background:var(--paper);overflow:auto}.left{border-right:1px solid var(--line)}.right{border-left:1px solid var(--line)}
.stage{position:sticky;top:62px;height:calc(100vh - 62px);background:radial-gradient(circle at 50% 42%,#fdfbf6,#e5e0d7 70%);overflow:hidden}
h2{font-size:18px;margin:0 0 5px}h3{font-size:12px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin:24px 0 10px}.hint{font-size:12px;color:var(--muted);line-height:1.45}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:9px}.shape{background:#f8f5ef;border:1px solid var(--line);border-radius:14px;padding:9px;cursor:pointer;min-height:128px;text-align:center}.shape:hover{border-color:#aaa59a}.shape.active{border:2px solid #222;padding:8px}.shape svg{display:block;width:100%;height:82px}.shape strong{display:block;font-size:12px}.shape small{display:block;color:var(--muted);font-size:10px;margin-top:2px}
textarea{width:100%;min-height:78px;border:1px solid var(--line);background:#faf8f3;border-radius:12px;padding:11px;font:inherit;resize:vertical}
.seg{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}.seg.three{grid-template-columns:repeat(3,1fr)}.seg.five{grid-template-columns:repeat(5,1fr)}.choice{border:1px solid var(--line);background:#faf8f3;border-radius:10px;padding:9px 5px;font-size:11px;cursor:pointer;text-align:center}.choice.active{background:#222;color:white;border-color:#222}
.fonts{display:grid;grid-template-columns:1fr 1fr;gap:7px}.font{border:1px solid var(--line);border-radius:10px;background:#faf8f3;padding:10px;cursor:pointer;font-size:17px}.font.active{outline:2px solid #222}.f-clean{font-family:Arial,sans-serif;font-weight:400}.f-strong{font-family:Arial,sans-serif;font-weight:800}.f-editorial{font-family:Georgia,serif;font-weight:700}.f-classic{font-family:Georgia,serif}.f-tech{font-family:ui-monospace,monospace;font-weight:800}
.colors{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.colorbox{font-size:10px;color:var(--muted)}input[type=color]{width:100%;height:42px;border:1px solid var(--line);border-radius:9px;background:white;padding:3px}
.generate{width:100%;border:0;border-radius:12px;background:#222;color:#fff;padding:13px;font-weight:800;margin-top:18px;cursor:pointer}.generate:disabled{opacity:.5}
#viewer{width:100%;height:100%;display:block}.empty{position:absolute;inset:0;display:grid;place-items:center;text-align:center;color:#777;pointer-events:none}.empty b{display:block;font-size:20px;color:#333;margin-bottom:6px}
.panel{border:1px solid var(--line);background:#faf8f3;border-radius:14px;padding:13px;margin-bottom:12px}.resultName{font-size:22px;font-weight:850}.metric{display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid #e5e1d8;font-size:12px}.metric:last-child{border:0}.ok{color:var(--ok)}.links{display:grid;grid-template-columns:1fr 1fr;gap:7px}.links a{border:1px solid var(--line);padding:9px;border-radius:9px;color:#222;text-decoration:none;text-align:center;font-size:11px}.error{color:#992b21;background:#fff2ef;border-color:#e4b9b3}
@media(max-width:1100px){main{grid-template-columns:360px 1fr}.right{display:none}.grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:760px){main{display:block}.left{border:0}.stage{height:55vh;top:62px}.grid{grid-template-columns:repeat(3,1fr)}}
</style></head>
<body>
<header><div class="brand">DOBO <b>DESIGN LAB</b></div><div class="status" id="status">elige · personaliza · genera</div></header>
<main>
<section class="left">
<h2>Diseña tu maceta</h2><div class="hint">No necesitas escribirle instrucciones al motor. Elige visualmente y DOBO resuelve la geometría por detrás.</div>
<h3>1 · Elige una forma</h3><div class="grid" id="shapes"></div>
<h3>2 · Escribe tu texto</h3><textarea id="text" maxlength="80" placeholder="Ej: PLANTA UNA IDEA">WALTER</textarea>
<h3>3 · Dónde va</h3><div class="seg" id="positions">
<div class="choice" data-value="top">Arriba</div><div class="choice active" data-value="center">Centro</div><div class="choice" data-value="bottom">Abajo</div><div class="choice" data-value="wrap">Rodea</div></div>
<h3>4 · Tamaño</h3><div class="seg" id="sizes">
<div class="choice" data-value="small">Pequeño</div><div class="choice active" data-value="medium">Medio</div><div class="choice" data-value="large">Grande</div><div class="choice" data-value="xl">XL</div></div>
<h3>5 · Relieve</h3><div class="seg three" id="reliefs">
<div class="choice active" data-value="raised">Sobrerrelieve</div><div class="choice" data-value="recessed">Bajorrelieve</div><div class="choice" data-value="none">Sin texto</div></div>
<h3>6 · Tipografía</h3><div class="fonts" id="fonts">
<div class="font f-strong active" data-value="strong">DOBO · Fuerte</div><div class="font f-clean" data-value="clean">DOBO · Limpia</div>
<div class="font f-editorial" data-value="editorial">DOBO · Editorial</div><div class="font f-classic" data-value="classic">DOBO · Clásica</div>
<div class="font f-tech" data-value="tech">DOBO · Técnica</div></div>
<h3>7 · Color</h3><div class="colors"><label class="colorbox">Cuerpo<input id="bodyColor" type="color" value="#e8e0d4"></label><label class="colorbox">Texto<input id="textColor" type="color" value="#262626"></label><label class="colorbox">Acento<input id="accentColor" type="color" value="#bda37a"></label></div>
<button class="generate" id="generate">Generar diseño real</button>
</section>
<section class="stage"><canvas id="viewer"></canvas><div class="empty" id="empty"><div><b>Tu diseño aparecerá aquí</b>Elige una forma y genera. No hay prompts técnicos.</div></div></section>
<section class="right">
<div class="panel"><div class="hint">Diseño actual</div><div class="resultName" id="resultName">Sin generar</div><div class="hint" id="resultMeta">—</div></div>
<div class="panel"><div class="metric"><span>Geometría cerrada</span><b id="watertight">—</b></div><div class="metric"><span>Texto</span><b id="textMode">—</b></div><div class="metric"><span>Tipografía</span><b id="fontMode">—</b></div><div class="metric"><span>Ubicación</span><b id="placeMode">—</b></div><div class="metric"><span>Multicolor</span><b id="multiMode">—</b></div></div>
<div class="panel"><div class="links" id="links"><a>STL</a><a>3MF</a></div></div>
<div class="panel error" id="error" style="display:none"></div>
</section>
</main>
<script type="importmap">{"imports":{"three":"https://unpkg.com/three@0.164.1/build/three.module.js","three/addons/":"https://unpkg.com/three@0.164.1/examples/jsm/"}}</script>
<script type="module">
import * as THREE from 'three';import {OrbitControls} from 'three/addons/controls/OrbitControls.js';import {STLLoader} from 'three/addons/loaders/STLLoader.js';
const catalog=__CATALOG__;
const $=s=>document.querySelector(s);let state={shape:catalog[0].id,position:'center',size:'medium',relief:'raised',font:'strong'};let mesh=null;
function pathFor(profile){const right=profile.map(([z,r])=>[50+r*34,94-z*82]);const left=[...profile].reverse().map(([z,r])=>[50-r*34,94-z*82]);const pts=[...right,...left];return 'M '+pts.map(p=>p.map(v=>v.toFixed(2)).join(' ')).join(' L ')+' Z'}
function renderShapes(){const el=$('#shapes');el.innerHTML='';catalog.forEach(x=>{const d=document.createElement('div');d.className='shape'+(x.id===state.shape?' active':'');d.innerHTML='<svg viewBox="0 0 100 100"><path d="'+pathFor(x.profile)+'" fill="#ded8cd" stroke="#444" stroke-width="1.2"/></svg><strong>'+x.name+'</strong><small>'+x.caption+'</small>';d.onclick=()=>{state.shape=x.id;renderShapes()};el.appendChild(d)})}renderShapes();
function bind(id,key){document.querySelectorAll(id+' [data-value]').forEach(e=>e.onclick=()=>{document.querySelectorAll(id+' [data-value]').forEach(x=>x.classList.remove('active'));e.classList.add('active');state[key]=e.dataset.value})}bind('#positions','position');bind('#sizes','size');bind('#reliefs','relief');bind('#fonts','font');
const canvas=$('#viewer'),stage=canvas.parentElement,renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.outputColorSpace=THREE.SRGBColorSpace;const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(35,1,.1,5000),controls=new OrbitControls(camera,canvas);scene.add(new THREE.HemisphereLight(0xffffff,0x776f62,2.3));const key=new THREE.DirectionalLight(0xffffff,3);key.position.set(-150,-180,250);scene.add(key);const floor=new THREE.Mesh(new THREE.PlaneGeometry(800,800),new THREE.MeshStandardMaterial({color:0xd9d4ca,roughness:1}));floor.rotation.x=-Math.PI/2;floor.position.z=-2;scene.add(floor);
function resize(){renderer.setSize(stage.clientWidth,stage.clientHeight,false);camera.aspect=stage.clientWidth/stage.clientHeight;camera.updateProjectionMatrix()}addEventListener('resize',resize);resize();
function fit(){if(!mesh)return;const b=new THREE.Box3().setFromObject(mesh),s=b.getSize(new THREE.Vector3()),c=b.getCenter(new THREE.Vector3()),m=Math.max(s.x,s.y,s.z);controls.target.copy(c);camera.position.set(c.x+1.5*m,c.y-1.8*m,c.z+1.15*m);controls.update()}function loop(){requestAnimationFrame(loop);controls.update();renderer.render(scene,camera)}loop();
function load(url,color){new STLLoader().load(url,g=>{if(mesh){scene.remove(mesh);mesh.geometry.dispose();mesh.material.dispose()}g.computeVertexNormals();mesh=new THREE.Mesh(g,new THREE.MeshStandardMaterial({color:new THREE.Color(color),roughness:.55,metalness:.01}));scene.add(mesh);$('#empty').style.display='none';fit()})}
$('#generate').onclick=async()=>{const btn=$('#generate');btn.disabled=true;btn.textContent='Generando…';$('#error').style.display='none';$('#status').textContent='DOBO está construyendo geometría real';try{const payload={...state,text:state.relief==='none'?'':$('#text').value,body_color:$('#bodyColor').value,text_color:$('#textColor').value,accent_color:$('#accentColor').value};const r=await fetch('/api/design',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const d=await r.json();if(!r.ok||!d.ok)throw new Error(d.error||'Fallo de generación');$('#resultName').textContent=d.shape.name;$('#resultMeta').textContent=d.shape.group+' · '+d.trace.vertices.toLocaleString()+' vértices';$('#watertight').textContent=d.validation.watertight?'PASS':'FAIL';$('#watertight').className=d.validation.watertight?'ok':'';$('#textMode').textContent=d.selection.relief;$('#fontMode').textContent=d.text.font_style||d.selection.font;$('#placeMode').textContent=d.text.text_layout==='wrap'?'rodea':d.selection.position;$('#multiMode').textContent=d.multicolor.compound_object?'3MF compuesto':'—';let links='<a href="'+d.artifacts.stl+'" download>Maceta STL</a><a href="'+d.artifacts.three_mf+'" download>3MF</a>';if(d.artifacts.saucer)links+='<a href="'+d.artifacts.saucer+'" download>Plato STL</a>';$('#links').innerHTML=links;load(d.artifacts.stl,d.selection.body_color);$('#status').textContent='Diseño válido'}catch(e){$('#error').style.display='block';$('#error').textContent=e.message;$('#status').textContent='Revisa la selección'}finally{btn.disabled=false;btn.textContent='Generar diseño real'}};
</script></body></html>'''.replace("__CATALOG__", json.dumps(_catalog_payload(), ensure_ascii=False))


class Handler(BaseHTTPRequestHandler):
    server_version = "DOBODesignLab/1.0"

    def _json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/catalog":
            self._json({"ok": True, "version": DESIGN_LAB_VERSION, "catalog": _catalog_payload()})
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

    def do_POST(self) -> None:
        if self.path != "/api/design":
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(size).decode("utf-8"))
            self._json(generate_design(payload))
        except Exception as error:
            traceback.print_exc()
            self._json({"ok": False, "error": f"{type(error).__name__}: {error}"}, 500)

    def log_message(self, fmt: str, *args: Any) -> None:
        print("[DOBO DESIGN LAB]", fmt % args)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}"
    print("DOBO Design Lab")
    print("URL:", url)
    print("Visual configurator over the real DOBO CAD pipeline.")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
