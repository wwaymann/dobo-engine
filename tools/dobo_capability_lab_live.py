from __future__ import annotations

"""Live DOBO capability laboratory.

Exact primitive buttons remain deterministic/offline. Any edited/free prompt uses
OpenAI only for semantic interpretation. The physical object is always generated
by the DOBO geometry pipeline.

The live lab keeps its temporary repair bridge for capabilities that are still
being observed there, but promoted cube/rectangular-prism bodies must exercise
the same native CAD route as the consolidated core regressions.  This prevents
the lab from accidentally showing the old superellipsoid approximation after a
capability has already been promoted.
"""

import unicodedata

import dobo_capability_lab as lab
from product_generators.design_interpreter.body_family_expansion import (
    GeneralBodyFamilyExpander,
)
from dobo_capability_repairs import install
from dobo_retry_repairs import install_retry_repairs


# Capture the promoted/core body-family implementation before the lab repair
# bridge replaces _fields_for.  Angular CAD routing reconstructs its dimensions
# from this canonical field contract, so cube and rectangular prism must keep it.
_CANONICAL_FIELDS_FOR = GeneralBodyFamilyExpander._fields_for.__func__

# Install the temporary lab repairs before the first generation request and make
# the base lab construct the repaired structural pipeline.
install_retry_repairs()
LivePipeline = install()
_REPAIRED_FIELDS_FOR = GeneralBodyFamilyExpander._fields_for.__func__


def _live_fields_for(cls, profile: str, program):
    if profile in {"cuboid", "rectangular_prism"}:
        return _CANONICAL_FIELDS_FOR(cls, profile, program)
    return _REPAIRED_FIELDS_FOR(cls, profile, program)


GeneralBodyFamilyExpander._fields_for = classmethod(_live_fields_for)

# Explicitly reconnect promoted angular capabilities after the temporary lab
# bridge.  The installs are idempotent, so this remains safe if package import
# order has already registered either adapter.
from product_generators.design_interpreter.native_cad_primitive_adapter import (
    install_native_cad_primitive_adapter,
)
from product_generators.design_interpreter.native_angular_text_reconnection import (
    install_native_angular_text_reconnection,
)

install_native_cad_primitive_adapter()
install_native_angular_text_reconnection()

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


def _plain(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.lower())
    return "".join(ch for ch in value if not unicodedata.combining(ch)).strip()


# Map exact primitive aliases to strings that the deterministic base lab parser
# already recognizes.  In particular, the UI default "maceta cúbica" normalizes
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
}

_original_generate = lab.generate


def _validated_vessel_flags(result: dict) -> None:
    """Expose vessel facts in the legacy UI using the actual Motor contract.

    A successful structural generation has already passed OrganicVesselResult
    semantic validation, including cavity_is_empty, opening_is_clear and
    drain_is_clear. The old UI looked for non-existent ``opening``/``drain``
    keys, which is why it displayed false FAIL values.
    """
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


def generate(prompt: str, mode: str = "auto") -> dict:
    normalized = _plain(prompt)
    if mode == "offline" or (mode == "auto" and normalized in _BASIC_PROMPTS):
        deterministic_prompt = _BASIC_PROMPTS.get(normalized, prompt)
        result = _original_generate(deterministic_prompt, mode="offline")
    else:
        result = _original_generate(prompt, mode="openai")
    _validated_vessel_flags(result)
    return result


lab.generate = generate


if __name__ == "__main__":
    lab.main()
