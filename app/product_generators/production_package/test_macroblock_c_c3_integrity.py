from __future__ import annotations

import json
import os
from pathlib import Path

from .package_integrity import PackageIntegrityVerifier

B_CHECKPOINT = "b9ceaddf89b31d0b9cbd50f07657dc56ad355d72"
SPEC_PATH = Path(__file__).resolve().parents[1] / "surface_designer" / "v2_prototype_1_dobo.json"
OUTPUT_ROOT = Path("outputs/product_generators/surface_designer") / SPEC_PATH.stem


def _current_manifest(package_root: Path, motor_revision: str) -> tuple[Path, dict]:
    expected_revision = f"git:{motor_revision}"
    matches: list[tuple[Path, dict]] = []
    for manifest_path in package_root.glob("*/production_package_manifest.json"):
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        if expected_revision in str(payload.get("source_revision", "")):
            matches.append((manifest_path, payload))
    if len(matches) != 1:
        raise RuntimeError(
            "Expected exactly one materialized package for current Motor/source "
            f"revision {motor_revision}, found {len(matches)}."
        )
    return matches[0]


def main() -> None:
    motor_revision = os.environ.get("DOBO_MOTOR_SOURCE_REVISION", "").strip()
    if not motor_revision:
        raise RuntimeError("Current Motor/source Git revision is unavailable.")

    package_root = OUTPUT_ROOT / "production_packages"
    manifest_path, payload = _current_manifest(package_root, motor_revision)
    if payload.get("schema_version") != "dobo.production-package.v2":
        raise RuntimeError("V2 content-addressed package schema was not produced.")
    source_revision = str(payload.get("source_revision", ""))
    if f"macroblock-b:{B_CHECKPOINT}" not in source_revision:
        raise RuntimeError("Accepted Macroblock B checkpoint is missing from package provenance.")
    if f"git:{motor_revision}" not in source_revision:
        raise RuntimeError("Current Motor/source Git revision is missing from package provenance.")

    records = {str(item["kind"]): item for item in payload.get("artifacts", [])}
    required = {
        "stl",
        "3mf",
        "manufacturing_evidence",
        "production_provenance",
        "render_front",
        "render_side",
        "render_top",
        "render_iso",
    }
    missing = sorted(required - set(records))
    if missing:
        raise RuntimeError(f"C3 package is missing end-to-end evidence: {missing}")

    provenance_record = records["production_provenance"]
    provenance_file = manifest_path.parent / "artifacts" / (
        f"production_provenance__{provenance_record['logical_name']}"
    )
    provenance = json.loads(provenance_file.read_text(encoding="utf-8"))
    if provenance.get("macroblock_b_checkpoint") != B_CHECKPOINT:
        raise RuntimeError("Materialized provenance changed the accepted B checkpoint.")
    if provenance.get("motor_source_revision") != motor_revision:
        raise RuntimeError("Materialized provenance is not bound to the current Motor revision.")

    source_copy = manifest_path.parent / "source" / SPEC_PATH.name
    if not source_copy.is_file():
        raise RuntimeError("Materialized package did not preserve the source JSON.")

    report = PackageIntegrityVerifier.verify(manifest_path.parent)
    if report.artifact_count != len(records):
        raise RuntimeError("Integrity verifier did not validate the complete artifact set.")

    print("DOBO Macroblock C - C3 Package Integrity")
    print("-----------------------------------")
    print("package schema", payload["schema_version"], "OK")
    print("Macroblock B checkpoint", B_CHECKPOINT, "PRESERVED")
    print("Motor/source revision", motor_revision, "VERIFIED")
    print("source JSON", SPEC_PATH.name, "PRESERVED")
    print("artifact hashes", report.artifact_count, "VERIFIED")
    print("content-addressed identity", report.package_sha256, "VERIFIED")
    print("STL/3MF/render/manufacturing evidence", "COMPLETE")
    print("-----------------------------------")
    print("Macroblock C C3 Package Integrity: Valid OK")


if __name__ == "__main__":
    main()
