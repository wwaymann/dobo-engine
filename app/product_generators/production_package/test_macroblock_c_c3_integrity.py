from __future__ import annotations

import json
from pathlib import Path

from .package_integrity import PackageIntegrityVerifier

B_CHECKPOINT = "b9ceaddf89b31d0b9cbd50f07657dc56ad355d72"
OUTPUT_ROOT = Path("outputs/product_generators/surface_designer/v2_prototype_1")


def main() -> None:
    package_root = OUTPUT_ROOT / "production_packages"
    manifests = sorted(package_root.glob("*/production_package_manifest.json"))
    if not manifests:
        raise RuntimeError("No materialized V2 production package found after C3 generation.")

    manifest_path = manifests[-1]
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "dobo.production-package.v2":
        raise RuntimeError("V2 content-addressed package schema was not produced.")
    source_revision = str(payload.get("source_revision", ""))
    if f"macroblock-b:{B_CHECKPOINT}" not in source_revision:
        raise RuntimeError("Accepted Macroblock B checkpoint is missing from package provenance.")
    if "git:" not in source_revision:
        raise RuntimeError("Motor/source Git revision is missing from package provenance.")

    records = {str(item["kind"]): item for item in payload.get("artifacts", [])}
    required = {
        "stl",
        "3mf",
        "manufacturing_evidence",
        "production_provenance",
        "render_perspective",
        "render_front",
        "render_top",
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
    if str(provenance.get("motor_source_revision", "")) not in source_revision:
        raise RuntimeError("Manifest and materialized Motor/source revision disagree.")

    report = PackageIntegrityVerifier.verify(manifest_path.parent)
    if report.artifact_count != len(records):
        raise RuntimeError("Integrity verifier did not validate the complete artifact set.")

    print("DOBO Macroblock C - C3 Package Integrity")
    print("-----------------------------------")
    print("package schema", payload["schema_version"], "OK")
    print("Macroblock B checkpoint", B_CHECKPOINT, "PRESERVED")
    print("Motor/source revision", provenance["motor_source_revision"], "VERIFIED")
    print("source JSON hash", "VERIFIED")
    print("artifact hashes", report.artifact_count, "VERIFIED")
    print("content-addressed identity", report.package_sha256, "VERIFIED")
    print("STL/3MF/render/manufacturing evidence", "COMPLETE")
    print("-----------------------------------")
    print("Macroblock C C3 Package Integrity: Valid OK")


if __name__ == "__main__":
    main()
