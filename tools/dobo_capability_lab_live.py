from __future__ import annotations

"""Live DOBO capability laboratory.

Exact primitive buttons remain deterministic/offline. Any edited/free prompt uses
OpenAI only for semantic interpretation. The physical object is always generated
by the DOBO geometry pipeline.

The live lab keeps its temporary repair bridge for capabilities that are still
being observed there, but all seven promoted primitive bodies must exercise the
same native CAD routes as the consolidated core regressions. This prevents the
lab from accidentally showing old implicit/voxel approximations after a
capability has already been promoted.
"""

import unicodedata

import dobo_capability_lab as lab
from product_generators.design_interpreter.body_family_expansion import (
    GeneralBodyFamilyExpander,
)
from product_generators.design_interpreter.design_pipeline import DoboDesignPipeline
from dobo_capability_repairs import install
from dobo_retry_repairs import install_retry_repairs


LIVE_CAPABILITY_LAB_VERSION = "LABLIVE.9-profiled-native-text"

# Capture the promoted/core body-family implementation before the lab repair
# bridge replaces _fields_for. Native primitive CAD routing reconstructs its
# dimensions from this canonical field contract, so promoted profiles keep it.
_CANONICAL_FIELDS_FOR = GeneralBodyFamilyExpander._fields_for.__func__

# Install the temporary lab repairs before the first generation request and make
# the base lab construct the repaired structural pipeline.
install_retry_repairs()
LivePipeline = install()
_REPAIRED_FIELDS_FOR = GeneralBodyFamilyExpander._fields_for.__func__


def _live_fields_for(cls, profile: str, program):
    if profile in {
        "cuboid",
        "rectangular_prism",
        "cylindrical",
        "triangular_prism",
        "tapered_revolution",
        "spherical",
        "ovoid",
    }:
        return _CANONICAL_FIELDS_FOR(cls, profile, program)
    return _REPAIRED_FIELDS_FOR(cls, profile, program)


GeneralBodyFamilyExpander._fields_for = classmethod(_live_fields_for)

# Explicitly reconnect promoted primitive capabilities after the temporary lab
# bridge. The installs are idempotent, so this remains safe if package import
# order has already registered an adapter.
from product_generators.design_interpreter.native_cad_primitive_adapter import (
    install_native_cad_primitive_adapter,
)
from product_generators.design_interpreter.native_angular_text_reconnection import (
    install_native_angular_text_reconnection,
)
from product_generators.design_interpreter.native_tapered_cad_adapter import (
    install_native_tapered_cad_adapter,
)
from product_generators.design_interpreter.native_radial_cad_adapter import (
    install_native_radial_cad_adapter,
)
from product_generators.design_interpreter.native_foundational_cad_adapter import (
    install_native_foundational_cad_adapter,
)
from product_generators.design_interpreter.native_profiled_cad_adapter import (
    install_native_profiled_cad_adapter,
)

install_native_cad_primitive_adapter()
install_native_angular_text_reconnection()
install_native_tapered_cad_adapter()
install_native_radial_cad_adapter()
# Foundational preserves the primitive chain; profiled is installed after the
# temporary Lab bridge so the catalog uses the same native CAD route as CI.
install_native_foundational_cad_adapter()
install_native_profiled_cad_adapter()


def _assert_promoted_retry_chain() -> None:
    """Refuse to serve the Lab if the final promoted CAD router was overwritten."""
    retry = DoboDesignPipeline._generate_with_retry.__func__
    if not getattr(retry, "_dobo_profiled_cad_adapter", False):
        raise RuntimeError(
            "DOBO Lab startup lost the promoted profiled CAD router; refusing "
            "to serve legacy or non-native planter geometry."
        )


_assert_promoted_retry_chain()

# The exact WALTER regression already proved that semantic text needs the
# temporary 120-second diagnostic budget before mesh generation. The live lab
# must use the same path; applying the budget after generate_from_semantic()
# returns is too late because the structural result validates internally.
_original_live_generate_from_semantic = LivePipeline.generate_from_semantic


def _live_generate_from_semantic(self, program, **kwargs):
    if any(feature.form_hint == "text" for feature in program.features):
        kwargs.setdefault("generation_budget_seconds", 120.0)
    return _original_live_generate_from_semantic(self, program, **kwargs)


LivePipeline.generate_from_semantic = _live_generate_from_semantic
lab.DoboStructuralPipeline = LivePipeline


def _patch_live_lab_html() -> None:
    """Keep the visual Lab truthful without changing generated CAD.

    STLLoader exposes duplicated triangle vertices. Recomputing normals directly
    on that non-indexed geometry leaves every triangle visually faceted, which
    made valid conical CAD look covered by large triangular defects around text.
    Three.js ``toCreasedNormals`` smooths only continuous faces while preserving
    real sharp text/rim edges.

    The base Lab also retained the previous successful model when a new request
    failed. That made a failed deboss request appear to have generated geometry.
    On failure the live Lab now clears the stale mesh, renders and PASS cards.
    """
    import_line = (
        "import * as THREE from 'three';import {OrbitControls} from "
        "'three/addons/controls/OrbitControls.js';import {STLLoader} from "
        "'three/addons/loaders/STLLoader.js';"
    )
    patched_import = import_line + (
        "import {toCreasedNormals} from "
        "'three/addons/utils/BufferGeometryUtils.js';"
    )
    if import_line not in lab.HTML:
        raise RuntimeError("DOBO Lab UI import contract changed; live patch cannot be applied safely.")
    lab.HTML = lab.HTML.replace(import_line, patched_import, 1)

    old_loader = (
        "async function loadSTL(url){return new Promise((ok,bad)=>new STLLoader().load(url,g=>{"
        "if(mesh){scene.remove(mesh);mesh.geometry.dispose();mesh.material.dispose()}"
        "g.computeVertexNormals();mesh=new THREE.Mesh(g,new THREE.MeshStandardMaterial({"
        "color:0xb7c48b,roughness:.58,metalness:.02,side:THREE.DoubleSide}));"
        "mesh.castShadow=true;mesh.receiveShadow=true;scene.add(mesh);"
        "document.querySelector('#placeholder').style.display='none';fit();"
        "setTimeout(shots,250);ok()},undefined,bad))}"
    )
    new_loader = (
        "async function loadSTL(url){return new Promise((ok,bad)=>new STLLoader().load(url,g=>{"
        "if(mesh){scene.remove(mesh);mesh.geometry.dispose();mesh.material.dispose()}"
        "const smooth=toCreasedNormals(g,Math.PI/6);if(smooth!==g)g.dispose();"
        "mesh=new THREE.Mesh(smooth,new THREE.MeshStandardMaterial({"
        "color:0xb7c48b,roughness:.58,metalness:.02,side:THREE.DoubleSide}));"
        "mesh.castShadow=true;mesh.receiveShadow=true;scene.add(mesh);"
        "document.querySelector('#placeholder').style.display='none';fit();"
        "setTimeout(shots,250);ok()},undefined,bad))}"
    )
    if old_loader not in lab.HTML:
        raise RuntimeError("DOBO Lab STL loader contract changed; live shading patch cannot be applied safely.")
    lab.HTML = lab.HTML.replace(old_loader, new_loader, 1)

    mark_line = (
        "function mark(id,val){const e=q(id);e.textContent=val?'PASS':'FAIL';"
        "e.className=val?'pass':'fail'}"
    )
    reset_function = mark_line + (
        "function clearFailedResult(message){data=null;if(mesh){scene.remove(mesh);"
        "mesh.geometry.dispose();mesh.material.dispose();mesh=null;}"
        "q('#placeholder').style.display='grid';q('#placeholder').innerHTML="
        "'<div><strong>Generación fallida</strong>No se muestra geometría de una ejecución anterior.</div>';"
        "['#shot1','#shot2','#shot3'].forEach(id=>q(id).removeAttribute('src'));"
        "q('#summary').innerHTML=`<div class=\"muted\">Resultado actual</div><div class=\"big\">Sin modelo válido</div><div class=\"muted\">${message}</div>`;"
        "q('#checks').innerHTML='<span>Watertight</span><b>—</b><span>Winding consistente</span><b>—</b><span>Componentes</span><b>—</b><span>Intentos</span><b>—</b>';"
        "['#cSemantic','#cGeometry','#cCavity','#cDrain','#cMfg'].forEach(id=>{"
        "const e=q(id);e.textContent='—';e.className='';});"
        "q('#json').textContent='La generación actual falló; no hay semántica/motor válido para mostrar.';"
        "q('#links').innerHTML='<a>STL</a><a>3MF</a><a>Motor JSON</a><a>Manifest</a>';"
        "}"
    )
    if mark_line not in lab.HTML:
        raise RuntimeError("DOBO Lab status contract changed; stale-result patch cannot be applied safely.")
    lab.HTML = lab.HTML.replace(mark_line, reset_function, 1)

    old_catch = (
        "catch(e){q('#error').style.display='block';q('#error').textContent=e.message;"
        "q('#engineStatus').textContent='Generación fallida'}"
    )
    new_catch = (
        "catch(e){q('#error').style.display='block';q('#error').textContent=e.message;"
        "q('#engineStatus').textContent='Generación fallida';clearFailedResult(e.message)}"
    )
    if old_catch not in lab.HTML:
        raise RuntimeError("DOBO Lab error contract changed; stale-result patch cannot be applied safely.")
    lab.HTML = lab.HTML.replace(old_catch, new_catch, 1)


_patch_live_lab_html()


def _plain(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.lower())
    return "".join(ch for ch in value if not unicodedata.combining(ch)).strip()


# Map exact primitive aliases to strings that the deterministic base lab parser
# already recognizes. In particular, the UI default "maceta cúbica" normalizes
# to "maceta cubica" but the legacy parser recognizes "cubo".
_BASIC_PROMPTS = {
    "crea una maceta cubo": "Crea una maceta cubo",
    "crea una maceta cubica": "Crea una maceta cubo",
    "crea una maceta prisma rectangular": "Crea una maceta prisma rectangular",
    "crea una maceta rectangular": "Crea una maceta rectangular",
    "crea una maceta cilindro": "Crea una maceta cilindro",
    "crea una maceta cilindrica": "Crea una maceta cilindro",
    "crea una maceta cono": "Crea una maceta cono",
    "crea una maceta conica": "Crea una maceta cono",
    "crea una maceta esfera": "Crea una maceta esfera",
    "crea una maceta esferica": "Crea una maceta esfera",
    "crea una maceta ovoide": "Crea una maceta ovoide",
    "crea una maceta prisma triangular": "Crea una maceta prisma triangular",
    "crea una maceta triangular": "Crea una maceta triangular",
    "crea una maceta anfora ahusada": "Crea una maceta anfora ahusada",
    "crea una maceta urna globular": "Crea una maceta urna globular",
    "crea una maceta barril": "Crea una maceta barril",
    "crea una maceta cuello estrecho": "Crea una maceta cuello estrecho",
    "crea una maceta borde ensanchado": "Crea una maceta borde ensanchado",
    "crea una maceta tronco invertido": "Crea una maceta tronco invertido",
    "crea una maceta reloj de arena": "Crea una maceta reloj de arena",
    "crea una maceta ahusada alta": "Crea una maceta ahusada alta",
    "crea una maceta ovoide alta": "Crea una maceta ovoide alta",
    "crea una maceta urna pedestal": "Crea una maceta urna pedestal",
}

_PROMOTED_ROUTE_FOR = {
    "crea una maceta cubo": "analytic_cad_angular_primitive",
    "crea una maceta cubica": "analytic_cad_angular_primitive",
    "crea una maceta prisma rectangular": "analytic_cad_angular_primitive",
    "crea una maceta rectangular": "analytic_cad_angular_primitive",
    "crea una maceta cilindro": "analytic_cad_cylindrical_text",
    "crea una maceta cilindrica": "analytic_cad_cylindrical_text",
    "crea una maceta prisma triangular": "analytic_cad_triangular_primitive",
    "crea una maceta triangular": "analytic_cad_triangular_primitive",
    "crea una maceta cono": "analytic_cad_tapered_primitive",
    "crea una maceta conica": "analytic_cad_tapered_primitive",
    "crea una maceta esfera": "analytic_cad_spherical_primitive",
    "crea una maceta esferica": "analytic_cad_spherical_primitive",
    "crea una maceta ovoide": "analytic_cad_ovoid_primitive",
    "crea una maceta anfora ahusada": "analytic_cad_profiled_revolution",
    "crea una maceta urna globular": "analytic_cad_profiled_revolution",
    "crea una maceta barril": "analytic_cad_profiled_revolution",
    "crea una maceta cuello estrecho": "analytic_cad_profiled_revolution",
    "crea una maceta borde ensanchado": "analytic_cad_profiled_revolution",
    "crea una maceta tronco invertido": "analytic_cad_profiled_revolution",
    "crea una maceta reloj de arena": "analytic_cad_profiled_revolution",
    "crea una maceta ahusada alta": "analytic_cad_profiled_revolution",
    "crea una maceta ovoide alta": "analytic_cad_profiled_revolution",
    "crea una maceta urna pedestal": "analytic_cad_profiled_revolution",
}

_FOUNDATIONAL_ROUTE_BY_PROFILE = {
    "cylindrical": "analytic_cad_cylindrical_text",
    "triangular_prism": "analytic_cad_triangular_primitive",
}

_original_generate = lab.generate


def _validated_vessel_flags(result: dict) -> None:
    """Expose vessel facts in the legacy UI using the actual Motor contract."""
    motor = result.get("motor")
    vessel = motor.get("vessel", {}) if isinstance(motor, dict) else {}
    view = result.setdefault("vessel", {})
    opening_ok = (
        isinstance(vessel.get("opening_radii"), list)
        and len(vessel["opening_radii"]) == 2
        and all(float(value) > 0.0 for value in vessel["opening_radii"])
        and float(vessel.get("opening_start_z_mm", 0.0))
        > float(vessel.get("cavity_floor_z_mm", 0.0))
    )
    drain_ok = (
        float(vessel.get("drain_radius_mm", 0.0)) > 0.0
        and float(vessel.get("drain_start_z_mm", 0.0))
        < float(vessel.get("base_z_mm", 0.0))
        and float(vessel.get("drain_end_z_mm", 0.0))
        > float(vessel.get("cavity_floor_z_mm", 0.0))
    )
    view["opening"] = {"validated": True} if opening_ok else None
    view["drain"] = {"validated": True} if drain_ok else None


def _guard_promoted_result(normalized_prompt: str, result: dict) -> None:
    """Prevent false PASSes for primitives that already have promoted CAD."""
    expected_route = _PROMOTED_ROUTE_FOR.get(normalized_prompt)
    motor = result.get("motor")
    route = motor.get("_capability_route") if isinstance(motor, dict) else None
    morphology = motor.get("morphogenesis", {}) if isinstance(motor, dict) else {}
    profile = str(morphology.get("profile", "")) if isinstance(morphology, dict) else ""
    # Cylinder and triangular-prism free prompts (including text) must remain on
    # their promoted exact CAD routes, not merely the exact no-text button cases.
    expected_route = _FOUNDATIONAL_ROUTE_BY_PROFILE.get(profile, expected_route)
    if profile == "profiled_revolution":
        profiled_text = motor.get("_native_profiled_text", {}) if isinstance(motor, dict) else {}
        expected_route = (
            "analytic_cad_profiled_text"
            if isinstance(profiled_text, dict) and int(profiled_text.get("line_count", 0)) > 0
            else "analytic_cad_profiled_revolution"
        )
    trace = result.setdefault("trace", {})
    trace["live_lab_version"] = LIVE_CAPABILITY_LAB_VERSION
    trace["capability_route"] = route

    if expected_route is None:
        return
    if route != expected_route:
        raise RuntimeError(
            "DOBO Lab rejected a legacy primitive fallback: "
            f"prompt={normalized_prompt!r}, route={route!r}, "
            f"expected={expected_route!r}."
        )

    if expected_route in {
        "analytic_cad_cylindrical_text",
        "analytic_cad_triangular_primitive",
        "analytic_cad_tapered_primitive",
        "analytic_cad_spherical_primitive",
        "analytic_cad_ovoid_primitive",
        "analytic_cad_profiled_revolution",
        "analytic_cad_profiled_text",
    }:
        vertices = int(trace.get("vertices") or 0)
        ceiling = (
            150_000
            if expected_route in {
                "analytic_cad_profiled_revolution",
                "analytic_cad_profiled_text",
            }
            else 30_000
        )
        if vertices <= 0 or vertices >= ceiling:
            raise RuntimeError(
                "DOBO Lab rejected non-native promoted mesh complexity: "
                f"vertices={vertices}; expected CAD below {ceiling}."
            )


def generate(prompt: str, mode: str = "auto") -> dict:
    normalized = _plain(prompt)
    if mode == "offline" or (mode == "auto" and normalized in _BASIC_PROMPTS):
        deterministic_prompt = _BASIC_PROMPTS.get(normalized, prompt)
        result = _original_generate(deterministic_prompt, mode="offline")
    else:
        result = _original_generate(prompt, mode="openai")
    _guard_promoted_result(normalized, result)
    _validated_vessel_flags(result)
    return result


lab.generate = generate


if __name__ == "__main__":
    lab.main()
