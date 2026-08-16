from __future__ import annotations

from .geometry_composer import (
    Capability,
    GeometryComposer,
    GeometryRepresentation,
    c0_accumulation_request,
)


def main() -> None:
    composer = GeometryComposer()
    plan = composer.plan(c0_accumulation_request())
    plan.validate_coverage()

    if Capability.MORPHOLOGY not in plan.covered:
        raise RuntimeError("C0 lost morphological generation.")
    if Capability.TEXT not in plan.covered:
        raise RuntimeError("C0 lost text capability.")
    if Capability.SURFACE_RELIEF not in plan.covered:
        raise RuntimeError("C0 lost surface relief capability.")
    if Capability.BOOLEAN not in plan.covered:
        raise RuntimeError("C0 lost boolean capability.")
    if Capability.MULTICOLOR not in plan.covered:
        raise RuntimeError("C0 lost multicolor capability.")
    if Capability.MANUFACTURABILITY not in plan.covered:
        raise RuntimeError("C0 lost manufacturability capability.")

    expected_representations = {
        GeometryRepresentation.BREP,
        GeometryRepresentation.MESH,
    }
    if set(plan.geometry_representations) != expected_representations:
        raise RuntimeError(
            "C0 must expose the real BRep/mesh integration boundary; "
            f"got {sorted(item.value for item in plan.geometry_representations)}"
        )
    if not plan.bridge_required:
        raise RuntimeError(
            "C0 must not silently pretend BRep and mesh capabilities are already composable."
        )

    provider_names = {provider.name for provider in plan.providers}
    required_providers = {
        "morphological-engine",
        "cad-kernel-v2",
        "surface-designer",
        "manufacturability-engine",
        "production-package",
    }
    missing_providers = required_providers - provider_names
    if missing_providers:
        raise RuntimeError(f"C0 provider registry incomplete: {sorted(missing_providers)}")

    print("DOBO C0 Capability Accumulation Matrix")
    print("--------------------------------------")
    print("requested", len(plan.requested))
    print("covered", len(plan.covered))
    print("missing", len(plan.missing))
    print("providers", ", ".join(provider.name for provider in plan.providers))
    print("representations", ", ".join(sorted(item.value for item in plan.geometry_representations)))
    print("hybrid bridge required", plan.bridge_required)
    print("C0 capability coverage: OK")


if __name__ == "__main__":
    main()
