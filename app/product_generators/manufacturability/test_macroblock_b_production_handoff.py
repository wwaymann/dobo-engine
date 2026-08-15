from __future__ import annotations

import json
from pathlib import Path

from .production_handoff import ProductionHandoffBuilder
from .product_integration import validate_real_multicolor_product


SPEC_PATH = (
    Path(__file__).resolve().parents[1]
    / "surface_designer"
    / "phase_5_product_spec.json"
)


def main() -> None:
    result = validate_real_multicolor_product(SPEC_PATH)
    builder = ProductionHandoffBuilder()
    manifest = builder.build(
        result=result,
        source_specification=SPEC_PATH,
    )

    if len(result.report.results) != 24:
        raise RuntimeError("Production handoff requires the complete 24-rule report.")
    if manifest.blocking_error_codes:
        raise RuntimeError(
            "Production handoff cannot be ready with blocking errors: "
            f"{manifest.blocking_error_codes}"
        )
    if not manifest.ready_for_production:
        raise RuntimeError("Validated real product was not production-ready.")
    if len(manifest.three_mf_sha256) != 64:
        raise RuntimeError("3MF SHA-256 fingerprint is invalid.")
    if manifest.build_item_count != 1 or manifest.component_count != 3:
        raise RuntimeError("Unexpected final 3MF production structure.")
    if manifest.filament_slots != (1, 2, 3):
        raise RuntimeError(f"Unexpected filament slots: {manifest.filament_slots}")
    if sum(manifest.rule_counts.values()) != 24:
        raise RuntimeError("Handoff rule counts do not conserve the 24-rule contract.")

    output = (
        Path(result.three_mf_path).parent
        / "production_handoff_manifest.json"
    )
    written = Path(builder.write(manifest, output))
    payload = json.loads(written.read_text(encoding="utf-8"))
    if payload["three_mf_sha256"] != manifest.three_mf_sha256:
        raise RuntimeError("Serialized handoff fingerprint changed unexpectedly.")
    if payload["production_orientation"] != result.production_orientation:
        raise RuntimeError("Serialized handoff lost the selected production orientation.")

    print("DOBO Macroblock B - Production Handoff")
    print("-----------------------------------")
    print("ready", manifest.ready_for_production)
    print("orientation", manifest.production_orientation)
    print("rules", sum(manifest.rule_counts.values()))
    print("blocking errors", len(manifest.blocking_error_codes))
    print("filaments", manifest.filament_slots)
    print("3MF sha256", manifest.three_mf_sha256)
    print("manifest", written)
    print("-----------------------------------")
    print("Macroblock B Production Handoff: Valid OK")


if __name__ == "__main__":
    main()
