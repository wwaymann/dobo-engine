from __future__ import annotations

"""Live DOBO capability laboratory.

Exact primitive buttons remain deterministic/offline. Any edited/free prompt uses
OpenAI only for semantic interpretation. The physical object is always generated
by the DOBO geometry pipeline.

The live lab keeps its temporary repair bridge for capabilities that are still
being observed there, but promoted cube/rectangular-prism/cone bodies must
exercise the same native CAD routes as the consolidated core regressions. This
prevents the lab from accidentally showing old implicit approximations after a
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


LIVE_CAPABILITY_LAB_VERSION = "LABLIVE.4-promoted-route-guard"

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
    if profile in {"cuboid", "rectangular_prism", "tapered_revolution"}:
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

install_native_cad_primitive_adapter()
install_native_angular_text_reconnection()
install_native_tapered_cad_adapter()


def _assert_promoted_retry_chain() -> None:
    """Refuse to serve the Lab if the final tapered CAD router was overwritten.

    The temporary lab retry bridge is allowed to wrap legacy capabilities, but
    promoted primitives must never silently fall back to the old implicit
    geometry while the UI still reports a green topology result.
    """
    retry = DoboDesignPipeline._generate_with_retry.__func__
    if not getattr(retry, "_dobo_native_tapered_cad_adapter", False):
        raise RuntimeError(
            "DOBO Lab startup lost the promoted tapered CAD router; refusing "
            "to serve legacy tapered geometry."
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
}

_PROMOTED_ROUTE_FOR = {
    "crea una maceta cubo": "analytic_cad_angular_primitive",
    "crea una maceta cubica": "analytic_cad_angular_primitive",
    "crea una maceta prisma rectangular": "analytic_cad_angular_primitive",
    "crea una maceta rectangular": "analytic_cad_angular_primitive",
    "crea una maceta cono": "analytic_cad_tapered_primitive",
    "crea una maceta conica": "analytic_cad_tapered_primitive",
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


def _guard_promoted_result(normalized_prompt: str, result: dict) -> None:
    """Prevent false PASSes for primitives that already have promoted CAD.

    The user's browser exposed the exact failure this guard is meant to catch:
    a legacy tapered mesh can be watertight and single-component while still
    being visibly wrong. For exact primitive buttons/aliases, route identity is
    therefore a physical acceptance invariant, not merely diagnostic metadata.
    """
    expected_route = _PROMOTED_ROUTE_FOR.get(normalized_prompt)
    motor = result.get("motor")
    route = motor.get("_capability_route") if isinstance(motor, dict) else None
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

    # The promoted plain frustum tessellates in the low thousands of vertices.
    # A six-figure count is a reliable signature of the old stacked implicit
    # approximation seen in the browser. Keep a generous ceiling so normal CAD
    # tessellation changes do not create a brittle regression.
    if expected_route == "analytic_cad_tapered_primitive":
        vertices = int(trace.get("vertices") or 0)
        if vertices <= 0 or vertices >= 20_000:
            raise RuntimeError(
                "DOBO Lab rejected non-native tapered mesh complexity: "
                f"vertices={vertices}; expected promoted CAD below 20000."
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
