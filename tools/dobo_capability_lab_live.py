from __future__ import annotations

"""Live DOBO capability laboratory.

Exact primitive buttons remain deterministic/offline. Any edited/free prompt uses
OpenAI only for semantic interpretation. The physical object is always generated
by the DOBO geometry pipeline.
"""

import unicodedata

import dobo_capability_lab as lab
from dobo_capability_repairs import install


# Install the repairs before the first generation request and make the base lab
# construct the repaired structural pipeline.
lab.DoboStructuralPipeline = install()


def _plain(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.lower())
    return "".join(ch for ch in value if not unicodedata.combining(ch)).strip()


_BASIC_PROMPTS = {
    "crea una maceta cubo",
    "crea una maceta cubica",
    "crea una maceta prisma rectangular",
    "crea una maceta rectangular",
    "crea una maceta cilindro",
    "crea una maceta cilindrica",
    "crea una maceta cono",
    "crea una maceta conica",
    "crea una maceta esfera",
    "crea una maceta esferica",
    "crea una maceta ovoide",
    "crea una maceta prisma triangular",
    "crea una maceta triangular",
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
        result = _original_generate(prompt, mode="offline")
    else:
        result = _original_generate(prompt, mode="openai")
    _validated_vessel_flags(result)
    return result


lab.generate = generate


if __name__ == "__main__":
    lab.main()
