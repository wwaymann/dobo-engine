from __future__ import annotations

"""DOBO Design Lab: product-facing configurator over the real CAD engine.

The end user selects visual families, an actual pot silhouette, text layout,
typographic family, scale, relief and colors. The Lab translates those small
choices into DOBO semantic/CAD contracts; it does not require engine prompts.
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


DESIGN_LAB_VERSION = "DESIGNLAB.2-family-multicolor-typography"
HOST = "127.0.0.1"
PORT = 8770
OUTPUT_ROOT = ROOT / "outputs" / "design-lab"
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


SHAPE_FAMILIES: tuple[dict[str, str], ...] = (
    {"id": "rectas", "name": "Rectas & limpias", "caption": "perfiles simples, compactos y contemporáneos"},
    {"id": "bajas", "name": "Bajas & cuencos", "caption": "macetas horizontales, abiertas y de centro bajo"},
    {"id": "organicas", "name": "Orgánicas", "caption": "curvas continuas, gotas, óvalos y flores"},
    {"id": "escultoricas", "name": "Escultóricas", "caption": "cinturas, dobles volúmenes y ritmos verticales"},
    {"id": "abiertas", "name": "Abertura amplia", "caption": "bordes expandidos, campanas y copas"},
    {"id": "cuello", "name": "Cuello & hombros", "caption": "transiciones entre cuerpo, hombro y abertura"},
    {"id": "volumen", "name": "Volumen clásico", "caption": "cuerpos redondos reinterpretados como maceta"},
)


DESIGN_CATALOG: tuple[dict[str, str], ...] = (
    {"id":"soft_taper","variant":"inverted_taper","name":"Taper","family":"rectas","caption":"ascendente"},
    {"id":"tall_taper","variant":"tall_taper","name":"Alta","family":"rectas","caption":"esbelta"},
    {"id":"capsule","variant":"capsule","name":"Cápsula","family":"rectas","caption":"redondeada"},
    {"id":"drum","variant":"drum","name":"Tambor","family":"rectas","caption":"compacta"},
    {"id":"bell","variant":"cone_bell","name":"Campana","family":"rectas","caption":"abierta"},

    {"id":"soft_low","variant":"low_urn","name":"Suave","family":"bajas","caption":"baja y amplia"},
    {"id":"wide_bowl","variant":"wide_bowl","name":"Cuenco","family":"bajas","caption":"muy horizontal"},
    {"id":"pedestal","variant":"footed_bowl","name":"Pedestal","family":"bajas","caption":"base elevada"},
    {"id":"bulb","variant":"bulb","name":"Bulbo","family":"bajas","caption":"volumen lleno"},

    {"id":"tulip","variant":"tulip","name":"Tulipán","family":"organicas","caption":"abierta y suave"},
    {"id":"drop","variant":"teardrop","name":"Gota","family":"organicas","caption":"concentrada"},
    {"id":"pear","variant":"pear","name":"Pera","family":"organicas","caption":"orgánica baja"},
    {"id":"oval_tall","variant":"oval_tall","name":"Óvalo","family":"organicas","caption":"vertical"},
    {"id":"spindle","variant":"spindle","name":"Huso","family":"organicas","caption":"tensión central"},

    {"id":"hourglass","variant":"hourglass","name":"Cintura","family":"escultoricas","caption":"estrecha al centro"},
    {"id":"curve","variant":"s_curve","name":"Curva","family":"escultoricas","caption":"ritmo en S"},
    {"id":"totem","variant":"double_bulb","name":"Tótem","family":"escultoricas","caption":"doble volumen"},
    {"id":"lantern","variant":"lantern","name":"Farol","family":"escultoricas","caption":"ritmo vertical"},
    {"id":"chalice","variant":"chalice","name":"Cáliz","family":"escultoricas","caption":"pie y copa"},

    {"id":"bell_vase","variant":"bell_vase","name":"Borde campana","family":"abiertas","caption":"boca amplia"},
    {"id":"flared_rim","variant":"flared_rim","name":"Borde abierto","family":"abiertas","caption":"rim expandido"},
    {"id":"trumpet","variant":"trumpet","name":"Trompeta","family":"abiertas","caption":"apertura progresiva"},
    {"id":"goblet","variant":"goblet","name":"Copa alta","family":"abiertas","caption":"abierta y alta"},

    {"id":"bottle","variant":"bottle","name":"Botella","family":"cuello","caption":"cuello marcado"},
    {"id":"narrow_neck","variant":"narrow_neck","name":"Cuello fino","family":"cuello","caption":"cuerpo ancho"},
    {"id":"shoulder_jar","variant":"shoulder_jar","name":"Hombros","family":"cuello","caption":"transición amplia"},
    {"id":"amphora","variant":"amphora_tapered","name":"Ánfora","family":"cuello","caption":"cuerpo afinado"},

    {"id":"urn","variant":"urn_bellied","name":"Redonda","family":"volumen","caption":"vientre amplio"},
    {"id":"barrel","variant":"barrel","name":"Barril","family":"volumen","caption":"volumen continuo"},
    {"id":"pedestal_urn","variant":"pedestal_urn","name":"Base clásica","family":"volumen","caption":"pie integrado"},
)


FONT_STYLES = {
    "strong": {"tag":"font_strong","label":"Fuerte","family":"sans","preview":"WALTER"},
    "clean": {"tag":"font_clean","label":"Limpia","family":"sans","preview":"Walter"},
    "editorial": {"tag":"font_editorial","label":"Editorial","family":"serif","preview":"Walter"},
    "classic": {"tag":"font_classic","label":"Clásica","family":"serif","preview":"Walter"},
    "tech": {"tag":"font_tech","label":"Técnica","family":"mono","preview":"WALTER"},
}

FONT_FAMILIES = (
    {"id":"sans","name":"Sans","caption":"limpia o fuerte"},
    {"id":"serif","name":"Serif","caption":"editorial o clásica"},
    {"id":"mono","name":"Mono","caption":"técnica y geométrica"},
)

POSITIONS = {"top":0.72,"center":0.52,"bottom":0.31,"wrap":0.52}
TEXT_SIZES = {"small":0.070,"medium":0.120,"large":0.190,"xl":0.300}


def _slug(value: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip()).strip("-").lower()
    return clean[:70] or "design"


def _profile_points(variant: str) -> list[list[float]]:
    dense = _smooth_profile(PROFILE_CATALOG[variant])
    maximum = max(radius for _z, radius in dense)
    return [
        [round(float(z), 5), round(float(radius / maximum), 5)]
        for z, radius in dense
    ]


def _catalog_payload() -> list[dict[str, Any]]:
    return [{**item, "profile": _profile_points(item["variant"])} for item in DESIGN_CATALOG]


def _family_payload() -> list[dict[str, Any]]:
    result = []
    for family in SHAPE_FAMILIES:
        options = [item for item in DESIGN_CATALOG if item["family"] == family["id"]]
        representative = options[0]
        result.append({
            **family,
            "count": len(options),
            "representative": {**representative, "profile": _profile_points(representative["variant"])},
        })
    return result


def _catalog_item(design_id: str) -> dict[str, str]:
    for item in DESIGN_CATALOG:
        if item["id"] == design_id:
            return item
    raise ValueError("Selecciona una forma válida.")


def _hex(value: object, fallback: str) -> str:
    text = str(value or fallback).upper()
    return text if re.fullmatch(r"#[0-9A-F]{6}", text) else fallback


def _resolved_text_lines(spec: dict[str, Any], relief: str) -> tuple[str, ...]:
    if relief == "none":
        return ()
    requested_count = int(spec.get("line_count", 1))
    if requested_count not in {1, 2, 3}:
        raise ValueError("El texto admite 1, 2 o 3 líneas.")

    values = spec.get("text_lines")
    if isinstance(values, list):
        lines = tuple(str(value).strip() for value in values[:requested_count])
    else:
        raw = str(spec.get("text", "")).replace("\\n", "\n")
        split = tuple(part.strip() for part in raw.splitlines())
        lines = split[:requested_count] if split else ("",)

    if len(lines) < requested_count:
        lines = lines + tuple("" for _ in range(requested_count - len(lines)))
    if any(not line for line in lines):
        raise ValueError("Completa todas las líneas de texto seleccionadas.")
    if sum(len(line) for line in lines) > 80:
        raise ValueError("El texto completo puede tener como máximo 80 caracteres.")
    return lines


def _design_program(spec: dict[str, Any]):
    item = _catalog_item(str(spec.get("shape", "soft_low")))
    variant = item["variant"]
    height, width = PROFILE_DEFAULT_DIMENSIONS[variant]

    position_key = str(spec.get("position", "center"))
    size_key = str(spec.get("size", "medium"))
    relief = str(spec.get("relief", "raised"))
    font_key = str(spec.get("font", "strong"))

    if position_key not in POSITIONS:
        raise ValueError("La posición de texto no es válida.")
    if size_key not in TEXT_SIZES:
        raise ValueError("El tamaño de texto no es válido.")
    if relief not in {"raised", "recessed", "none"}:
        raise ValueError("El relieve de texto no es válido.")
    if font_key not in FONT_STYLES:
        raise ValueError("La tipografía no es válida.")

    lines = _resolved_text_lines(spec, relief)
    if position_key == "wrap" and len(lines) > 1:
        raise ValueError("Rodea usa una sola línea; cambia a 1 línea o usa Arriba/Centro/Abajo.")
    text_value = "\n".join(lines)

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
                width=0.98 if position_key == "wrap" else 0.70,
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
    return program, item, lines, position_key, size_key, relief


def generate_design(spec: dict[str, Any]) -> dict[str, Any]:
    program, item, lines, position_key, size_key, relief = _design_program(spec)
    text_value = "\n".join(lines)

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
                width_fraction=1.0 if position_key == "wrap" else 0.72,
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
    result = DoboStructuralPipeline().generate_from_semantic(
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
            "text_lines": list(lines),
            "line_count": len(lines),
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
        "preview": {
            "preferred": "three_mf" if multicolor.get("compound_object") else "stl",
            "colors": [body_color, text_color, accent_color],
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
:root{--bg:#f3f0ea;--paper:#fffdf8;--ink:#20211e;--muted:#77786f;--line:#d8d5cc;--ok:#347a42}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif}
header{height:62px;padding:0 24px;display:flex;align-items:center;border-bottom:1px solid var(--line);background:var(--paper);position:sticky;top:0;z-index:20}
.brand{font-weight:900;letter-spacing:.08em}.brand b{font-weight:500;color:#777}.status{margin-left:auto;font-size:12px;color:var(--muted)}
main{display:grid;grid-template-columns:410px minmax(420px,1fr) 330px;min-height:calc(100vh - 62px)}
.left,.right{padding:22px;background:var(--paper);overflow:auto}.left{border-right:1px solid var(--line)}.right{border-left:1px solid var(--line)}
.stage{position:sticky;top:62px;height:calc(100vh - 62px);background:radial-gradient(circle at 50% 42%,#fdfbf6,#e5e0d7 70%);overflow:hidden}
h2{font-size:18px;margin:0 0 5px}h3{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin:22px 0 9px}.hint{font-size:12px;color:var(--muted);line-height:1.45}
.familyGrid{display:grid;grid-template-columns:repeat(2,1fr);gap:9px}.family{background:#f8f5ef;border:1px solid var(--line);border-radius:14px;padding:10px;cursor:pointer;min-height:150px}.family:hover,.family.active{border-color:#444}.family svg{display:block;width:100%;height:90px}.family strong{font-size:12px;display:block}.family small{font-size:10px;color:var(--muted)}
.currentShape{margin-top:9px;padding:9px 11px;border-radius:10px;background:#eee9df;font-size:12px;display:flex;justify-content:space-between}
.seg{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}.seg.three{grid-template-columns:repeat(3,1fr)}.choice{border:1px solid var(--line);background:#faf8f3;border-radius:10px;padding:9px 5px;font-size:11px;cursor:pointer;text-align:center}.choice.active{background:#222;color:white;border-color:#222}
.lineInputs{display:grid;gap:6px}.lineInputs input{width:100%;border:1px solid var(--line);border-radius:10px;padding:10px;background:#faf8f3;font:inherit}
.fontFamilyGrid{display:grid;grid-template-columns:repeat(3,1fr);gap:7px}.fontFamily{border:1px solid var(--line);border-radius:10px;background:#faf8f3;padding:9px;cursor:pointer;text-align:center;font-size:11px}.fontFamily.active{background:#222;color:#fff}.fontVariants{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:7px}.font{border:1px solid var(--line);border-radius:10px;background:#faf8f3;padding:10px;cursor:pointer;font-size:18px}.font.active{outline:2px solid #222}.f-clean{font-family:Arial,sans-serif;font-weight:400}.f-strong{font-family:Arial,sans-serif;font-weight:800}.f-editorial{font-family:Georgia,serif;font-weight:700}.f-classic{font-family:Georgia,serif;font-style:italic}.f-tech{font-family:ui-monospace,monospace;font-weight:800}
.colors{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.colorbox{font-size:10px;color:var(--muted)}input[type=color]{width:100%;height:42px;border:1px solid var(--line);border-radius:9px;background:white;padding:3px}
.generate{width:100%;border:0;border-radius:12px;background:#222;color:#fff;padding:13px;font-weight:800;margin-top:18px;cursor:pointer}.generate:disabled{opacity:.5}
#viewer{width:100%;height:100%;display:block}.empty{position:absolute;inset:0;display:grid;place-items:center;text-align:center;color:#777;pointer-events:none}.empty b{display:block;font-size:20px;color:#333;margin-bottom:6px}
.panel{border:1px solid var(--line);background:#faf8f3;border-radius:14px;padding:13px;margin-bottom:12px}.resultName{font-size:22px;font-weight:850}.metric{display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid #e5e1d8;font-size:12px}.metric:last-child{border:0}.ok{color:var(--ok)}.links{display:grid;grid-template-columns:1fr 1fr;gap:7px}.links a{border:1px solid var(--line);padding:9px;border-radius:9px;color:#222;text-decoration:none;text-align:center;font-size:11px}.error{color:#992b21;background:#fff2ef;border-color:#e4b9b3}
.swatches{display:flex;gap:6px;margin-top:8px}.swatch{width:28px;height:28px;border-radius:7px;border:1px solid #bbb}
.modal{position:fixed;inset:0;background:#0008;z-index:50;display:none;align-items:center;justify-content:center;padding:24px}.modal.open{display:flex}.modalCard{width:min(780px,96vw);max-height:82vh;overflow:auto;background:var(--paper);border-radius:18px;padding:18px}.modalHead{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}.modalHead button{border:0;background:#eee8df;border-radius:8px;padding:8px 10px;cursor:pointer}.shapeOptions{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.shapeOption{border:1px solid var(--line);background:#f8f5ef;border-radius:12px;padding:8px;cursor:pointer;text-align:center}.shapeOption.active{outline:2px solid #222}.shapeOption svg{width:100%;height:110px}.shapeOption strong{display:block;font-size:12px}.shapeOption small{font-size:10px;color:var(--muted)}
@media(max-width:1100px){main{grid-template-columns:380px 1fr}.right{display:none}}@media(max-width:760px){main{display:block}.stage{height:55vh;top:62px}.shapeOptions{grid-template-columns:repeat(2,1fr)}}
</style></head>
<body>
<header><div class="brand">DOBO <b>DESIGN LAB</b></div><div class="status" id="status">elige · personaliza · genera</div></header>
<main>
<section class="left">
<h2>Diseña tu maceta</h2><div class="hint">Elige visualmente. Los nombres técnicos quedan detrás del motor.</div>
<h3>1 · Familia de forma</h3><div class="familyGrid" id="families"></div><div class="currentShape"><span>Forma elegida</span><b id="shapeName">Suave</b></div>

<h3>2 · Texto</h3>
<div class="seg three" id="lineCounts"><div class="choice active" data-value="1">1 línea</div><div class="choice" data-value="2">2 líneas</div><div class="choice" data-value="3">3 líneas</div></div>
<div class="lineInputs" id="lineInputs"></div>

<h3>3 · Dónde va</h3><div class="seg" id="positions">
<div class="choice" data-value="top">Arriba</div><div class="choice active" data-value="center">Centro</div><div class="choice" data-value="bottom">Abajo</div><div class="choice" data-value="wrap">Rodea</div></div>

<h3>4 · Tamaño</h3><div class="seg" id="sizes">
<div class="choice" data-value="small">Pequeño</div><div class="choice active" data-value="medium">Medio</div><div class="choice" data-value="large">Grande</div><div class="choice" data-value="xl">XL</div></div>

<h3>5 · Relieve</h3><div class="seg three" id="reliefs">
<div class="choice active" data-value="raised">Sobrerrelieve</div><div class="choice" data-value="recessed">Bajorrelieve</div><div class="choice" data-value="none">Sin texto</div></div>

<h3>6 · Familia tipográfica</h3><div class="fontFamilyGrid" id="fontFamilies"></div><div class="fontVariants" id="fontVariants"></div>

<h3>7 · Color</h3><div class="colors"><label class="colorbox">Cuerpo<input id="bodyColor" type="color" value="#e8e0d4"></label><label class="colorbox">Texto<input id="textColor" type="color" value="#262626"></label><label class="colorbox">Acento<input id="accentColor" type="color" value="#bda37a"></label></div>
<button class="generate" id="generate">Generar diseño real</button>
</section>

<section class="stage"><canvas id="viewer"></canvas><div class="empty" id="empty"><div><b>Tu diseño aparecerá aquí</b>La vista usa el 3MF multicolor cuando existe.</div></div></section>

<section class="right">
<div class="panel"><div class="hint">Diseño actual</div><div class="resultName" id="resultName">Sin generar</div><div class="hint" id="resultMeta">—</div><div class="swatches" id="swatches"></div></div>
<div class="panel"><div class="metric"><span>Geometría cerrada</span><b id="watertight">—</b></div><div class="metric"><span>Texto</span><b id="textMode">—</b></div><div class="metric"><span>Tipografía física</span><b id="fontMode">—</b></div><div class="metric"><span>Líneas</span><b id="lineMode">—</b></div><div class="metric"><span>Tamaño efectivo</span><b id="sizeMode">—</b></div><div class="metric"><span>Ubicación</span><b id="placeMode">—</b></div><div class="metric"><span>Vista</span><b id="previewMode">—</b></div></div>
<div class="panel"><div class="links" id="links"><a>STL</a><a>3MF</a></div></div>
<div class="panel error" id="error" style="display:none"></div>
</section>
</main>

<div class="modal" id="shapeModal"><div class="modalCard"><div class="modalHead"><div><b id="modalTitle">Familia</b><div class="hint">Elige una forma dentro de esta familia</div></div><button id="closeModal">Cerrar</button></div><div class="shapeOptions" id="shapeOptions"></div></div></div>

<script type="importmap">{"imports":{"three":"https://unpkg.com/three@0.164.1/build/three.module.js","three/addons/":"https://unpkg.com/three@0.164.1/examples/jsm/"}}</script>
<script type="module">
import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {STLLoader} from 'three/addons/loaders/STLLoader.js';
import {ThreeMFLoader} from 'three/addons/loaders/3MFLoader.js';

const catalog=__CATALOG__,families=__FAMILIES__,fontStyles=__FONT_STYLES__,fontFamilies=__FONT_FAMILIES__;
const $=s=>document.querySelector(s);
let state={shape:'soft_low',position:'center',size:'medium',relief:'raised',font:'strong',fontFamily:'sans',lineCount:1,lineValues:['WALTER','','']};
let model=null;

function pathFor(profile){const right=profile.map(([z,r])=>[50+r*34,94-z*82]);const left=[...profile].reverse().map(([z,r])=>[50-r*34,94-z*82]);return 'M '+[...right,...left].map(p=>p.map(v=>v.toFixed(2)).join(' ')).join(' L ')+' Z'}
function byId(id){return catalog.find(x=>x.id===id)}
function familyOfShape(){return byId(state.shape)?.family}

function renderFamilies(){
 const el=$('#families');el.innerHTML='';
 families.forEach(f=>{const r=f.representative,d=document.createElement('div');d.className='family'+(f.id===familyOfShape()?' active':'');d.innerHTML='<svg viewBox="0 0 100 100"><path d="'+pathFor(r.profile)+'" fill="#ded8cd" stroke="#444" stroke-width="1.2"/></svg><strong>'+f.name+'</strong><small>'+f.count+' formas · '+f.caption+'</small>';d.onclick=()=>openFamily(f.id);el.appendChild(d)})
}
function openFamily(id){
 const family=families.find(x=>x.id===id);$('#modalTitle').textContent=family.name;const el=$('#shapeOptions');el.innerHTML='';
 catalog.filter(x=>x.family===id).forEach(x=>{const d=document.createElement('div');d.className='shapeOption'+(x.id===state.shape?' active':'');d.innerHTML='<svg viewBox="0 0 100 100"><path d="'+pathFor(x.profile)+'" fill="#ddd6ca" stroke="#444" stroke-width="1.1"/></svg><strong>'+x.name+'</strong><small>'+x.caption+'</small>';d.onclick=()=>{state.shape=x.id;$('#shapeName').textContent=x.name;$('#shapeModal').classList.remove('open');renderFamilies()};el.appendChild(d)});
 $('#shapeModal').classList.add('open')
}
$('#closeModal').onclick=()=>$('#shapeModal').classList.remove('open');$('#shapeModal').onclick=e=>{if(e.target===$('#shapeModal'))$('#shapeModal').classList.remove('open')};

function renderLines(){
 const el=$('#lineInputs');el.innerHTML='';
 for(let i=0;i<state.lineCount;i++){const input=document.createElement('input');input.maxLength=40;input.value=state.lineValues[i]||'';input.placeholder='Línea '+(i+1);input.oninput=()=>state.lineValues[i]=input.value;el.appendChild(input)}
}
function renderFontFamilies(){
 const el=$('#fontFamilies');el.innerHTML='';
 fontFamilies.forEach(f=>{const d=document.createElement('div');d.className='fontFamily'+(state.fontFamily===f.id?' active':'');d.innerHTML='<b>'+f.name+'</b><br><span>'+f.caption+'</span>';d.onclick=()=>{state.fontFamily=f.id;const options=Object.entries(fontStyles).filter(([k,v])=>v.family===f.id);if(options.length&&!options.some(([k])=>k===state.font))state.font=options[0][0];renderFontFamilies();renderFontVariants()};el.appendChild(d)})
}
function renderFontVariants(){
 const el=$('#fontVariants');el.innerHTML='';
 Object.entries(fontStyles).filter(([k,v])=>v.family===state.fontFamily).forEach(([key,value])=>{const d=document.createElement('div');d.className='font f-'+key+(state.font===key?' active':'');d.textContent=value.preview+' · '+value.label;d.onclick=()=>{state.font=key;renderFontVariants()};el.appendChild(d)})
}
function bind(id,key,after){
 document.querySelectorAll(id+' [data-value]').forEach(e=>e.onclick=()=>{document.querySelectorAll(id+' [data-value]').forEach(x=>x.classList.remove('active'));e.classList.add('active');state[key]=e.dataset.value;if(after)after(e.dataset.value)})
}
bind('#positions','position',v=>{if(v==='wrap'&&state.lineCount>1){state.lineCount=1;document.querySelectorAll('#lineCounts [data-value]').forEach(x=>x.classList.toggle('active',x.dataset.value==='1'));renderLines()}});
bind('#sizes','size');bind('#reliefs','relief');
bind('#lineCounts','lineCount',v=>{state.lineCount=Number(v);if(state.position==='wrap'&&state.lineCount>1){state.position='center';document.querySelectorAll('#positions [data-value]').forEach(x=>x.classList.toggle('active',x.dataset.value==='center'))}renderLines()});
renderFamilies();renderLines();renderFontFamilies();renderFontVariants();

const canvas=$('#viewer'),stage=canvas.parentElement,renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.outputColorSpace=THREE.SRGBColorSpace;const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(35,1,.1,5000),controls=new OrbitControls(camera,canvas);scene.add(new THREE.HemisphereLight(0xffffff,0x776f62,2.4));const key=new THREE.DirectionalLight(0xffffff,3.2);key.position.set(-150,-180,250);scene.add(key);const floor=new THREE.Mesh(new THREE.PlaneGeometry(800,800),new THREE.MeshStandardMaterial({color:0xd9d4ca,roughness:1}));floor.rotation.x=-Math.PI/2;floor.position.z=-2;scene.add(floor);
function resize(){renderer.setSize(stage.clientWidth,stage.clientHeight,false);camera.aspect=stage.clientWidth/stage.clientHeight;camera.updateProjectionMatrix()}addEventListener('resize',resize);resize();
function clearModel(){if(!model)return;scene.remove(model);model.traverse?.(n=>{if(n.geometry)n.geometry.dispose?.();if(n.material){if(Array.isArray(n.material))n.material.forEach(m=>m.dispose?.());else n.material.dispose?.()}});model=null}
function fit(){if(!model)return;const b=new THREE.Box3().setFromObject(model),s=b.getSize(new THREE.Vector3()),c=b.getCenter(new THREE.Vector3()),m=Math.max(s.x,s.y,s.z);controls.target.copy(c);camera.position.set(c.x+1.5*m,c.y-1.8*m,c.z+1.15*m);controls.update()}
function loop(){requestAnimationFrame(loop);controls.update();renderer.render(scene,camera)}loop();
function loadSTL(url,color){return new Promise((ok,bad)=>new STLLoader().load(url,g=>{clearModel();g.computeVertexNormals();model=new THREE.Mesh(g,new THREE.MeshStandardMaterial({color:new THREE.Color(color),roughness:.55,metalness:.01}));scene.add(model);$('#empty').style.display='none';fit();ok()},undefined,bad))}
function load3MF(url){return new Promise((ok,bad)=>new ThreeMFLoader().load(url,obj=>{clearModel();model=obj;model.traverse(n=>{if(n.isMesh){n.castShadow=true;n.receiveShadow=true;if(n.material){const mats=Array.isArray(n.material)?n.material:[n.material];mats.forEach(m=>{m.roughness=.55;m.metalness=.01;m.needsUpdate=true})}}});scene.add(model);$('#empty').style.display='none';fit();ok()},undefined,bad))}
async function loadPreview(d){if(d.preview.preferred==='three_mf'){try{await load3MF(d.artifacts.three_mf);$('#previewMode').textContent='3MF multicolor';return}catch(e){console.warn('3MF preview fallback',e)}}await loadSTL(d.artifacts.stl,d.selection.body_color);$('#previewMode').textContent='STL monocolor (fallback)'}
function swatches(colors){$('#swatches').innerHTML=colors.map(c=>'<span class="swatch" style="background:'+c+'" title="'+c+'"></span>').join('')}

$('#generate').onclick=async()=>{
 const btn=$('#generate');btn.disabled=true;btn.textContent='Generando…';$('#error').style.display='none';$('#status').textContent='DOBO está construyendo geometría real';
 try{
  const lines=state.lineValues.slice(0,state.lineCount);
  const payload={...state,line_count:state.lineCount,text_lines:state.relief==='none'?[]:lines,body_color:$('#bodyColor').value,text_color:$('#textColor').value,accent_color:$('#accentColor').value};
  const r=await fetch('/api/design',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}),d=await r.json();if(!r.ok||!d.ok)throw new Error(d.error||'Fallo de generación');
  $('#resultName').textContent=d.shape.name;$('#resultMeta').textContent=d.shape.family+' · '+d.trace.vertices.toLocaleString()+' vértices';$('#watertight').textContent=d.validation.watertight?'PASS':'FAIL';$('#watertight').className=d.validation.watertight?'ok':'';
  $('#textMode').textContent=d.selection.relief;$('#fontMode').textContent=d.text.font_label||d.text.font_style||d.selection.font;$('#lineMode').textContent=d.selection.line_count;
  const sizes=d.text.effective_line_heights_mm||[];$('#sizeMode').textContent=sizes.length?sizes.map(x=>Number(x).toFixed(1)+' mm').join(' / '):'—';
  $('#placeMode').textContent=d.text.text_layout==='wrap'?'rodea 360°':d.selection.position;swatches(d.preview.colors);
  let links='<a href="'+d.artifacts.stl+'" download>Maceta STL</a><a href="'+d.artifacts.three_mf+'" download>3MF</a>';if(d.artifacts.saucer)links+='<a href="'+d.artifacts.saucer+'" download>Plato STL</a>';$('#links').innerHTML=links;
  await loadPreview(d);$('#status').textContent='Diseño válido';
 }catch(e){$('#error').style.display='block';$('#error').textContent=e.message;$('#status').textContent='Revisa la selección'}finally{btn.disabled=false;btn.textContent='Generar diseño real'}
};
</script></body></html>'''
HTML = (
    HTML.replace("__CATALOG__", json.dumps(_catalog_payload(), ensure_ascii=False))
        .replace("__FAMILIES__", json.dumps(_family_payload(), ensure_ascii=False))
        .replace("__FONT_STYLES__", json.dumps(FONT_STYLES, ensure_ascii=False))
        .replace("__FONT_FAMILIES__", json.dumps(FONT_FAMILIES, ensure_ascii=False))
)


class Handler(BaseHTTPRequestHandler):
    server_version = "DOBODesignLab/2.0"

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
            self._json({
                "ok": True,
                "version": DESIGN_LAB_VERSION,
                "catalog": _catalog_payload(),
                "families": _family_payload(),
                "font_families": FONT_FAMILIES,
                "font_styles": FONT_STYLES,
            })
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
    print("DOBO Design Lab", DESIGN_LAB_VERSION)
    print("URL:", url)
    print("Visual family configurator over the real DOBO CAD/3MF pipeline.")
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
