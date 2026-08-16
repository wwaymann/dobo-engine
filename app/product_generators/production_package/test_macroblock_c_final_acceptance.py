from __future__ import annotations

import json
import os
from pathlib import Path

from .package_integrity import PackageIntegrityVerifier

B_CHECKPOINT = "b9ceaddf89b31d0b9cbd50f07657dc56ad355d72"
SPEC_PATH = Path(__file__).resolve().parents[1] / "surface_designer" / "v2_prototype_1_dobo.json"
OUTPUT_ROOT = Path("outputs/product_generators/surface_designer") / SPEC_PATH.stem
REQUIRED_ARTIFACTS = {
    "stl",
    "3mf",
    "manufacturing_evidence",
    "production_provenance",
    "render_front",
    "render_side",
    "render_top",
    "render_iso",
}


def main() -> None:
    revision = os.environ.get("DOBO_MOTOR_SOURCE_REVISION", "").strip()
    if not revision:
        raise RuntimeError("Final acceptance requires the current Motor/source revision.")

    candidates: list[tuple[Path, dict]] = []
    for manifest_path in (OUTPUT_ROOT / "production_packages").glob(
        "*/production_package_manifest.json"
    ):
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        if f"git:{revision}" in str(payload.get("source_revision", "")):
            candidates.append((manifest_path, payload))
    if len(candidates) != 1:
        raise RuntimeError(
            f"Final acceptance expected one current-revision package, found {len(candidates)}."
        )

    manifest_path, payload = candidates[0]
    if payload.get("schema_version") != "dobo.production-package.v2":
        raise RuntimeError("Final package is not V2.")
    if payload.get("motor_version") != "macroblock-c.C3":
        raise RuntimeError("Unexpected Motor production-package stage.")
    source_revision = str(payload.get("source_revision", ""))
    if f"macroblock-b:{B_CHECKPOINT}" not in source_revision:
        raise RuntimeError("Macroblock B accepted checkpoint provenance was lost.")

    artifacts = {str(record["kind"]): record for record in payload.get("artifacts", [])}
    missing = REQUIRED_ARTIFACTS - set(artifacts)
    if missing:
        raise RuntimeError(f"Final package evidence is incomplete: {sorted(missing)}")
    if len(artifacts) != len(payload.get("artifacts", [])):
        raise RuntimeError("Final package contains duplicate artifact kinds.")

    source_copy = manifest_path.parent / "source" / SPEC_PATH.name
    if not source_copy.is_file() or source_copy.read_bytes() != SPEC_PATH.read_bytes():
        raise RuntimeError("Final package source JSON is not an exact preserved copy.")

    provenance_record = artifacts["production_provenance"]
    provenance_path = manifest_path.parent / "artifacts" / (
        f"production_provenance__{provenance_record['logical_name']}"
    )
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    if provenance.get("motor_source_revision") != revision:
        raise RuntimeError("Production provenance is not bound to the current revision.")
    if provenance.get("macroblock_b_checkpoint") != B_CHECKPOINT:
        raise RuntimeError("Production provenance changed the accepted B checkpoint.")
    if provenance.get("source_json") != SPEC_PATH.name:
        raise RuntimeError("Production provenance does not identify the preserved source JSON.")

    integrity = PackageIntegrityVerifier.verify(manifest_path.parent)
    if integrity.artifact_count != len(artifacts):
        raise RuntimeError("Final integrity verification did not cover every artifact.")

    manufacturing_record = artifacts["manufacturing_evidence"]
    manufacturing_path = manifest_path.parent / "artifacts" / (
        f"manufacturing_evidence__{manufacturing_record['logical_name']}"
    )
    manufacturing = json.loads(manufacturing_path.read_text(encoding="utf-8"))
    if manufacturing.get("macroblock_b_checkpoint") != B_CHECKPOINT:
        raise RuntimeError("Manufacturing evidence is not bound to accepted Macroblock B.")
    if not manufacturing.get("watertight") or not manufacturing.get("winding_consistent"):
        raise RuntimeError("Final manufacturing evidence is not topologically valid.")
    if int(manufacturing.get("component_count", 0)) != 1:
        raise RuntimeError("Final manufacturing evidence is not a single connected product.")

    print("DOBO Macroblock C - Final Acceptance")
    print("-----------------------------------")
    print("V2 package schema", payload["schema_version"], "OK")
    print("current Motor/source revision", revision, "BOUND")
    print("Macroblock B checkpoint", B_CHECKPOINT, "PRESERVED")
    print("source JSON exact copy", SPEC_PATH.name, "OK")
    print("required evidence", len(REQUIRED_ARTIFACTS), "COMPLETE")
    print("artifact hashes", integrity.artifact_count, "VERIFIED")
    print("content-addressed identity", integrity.package_sha256, "VERIFIED")
    print("manufacturing topology", "VALID")
    print("-----------------------------------")
    print("Macroblock C Final Acceptance: Valid OK")


if __name__ == "__main__":
    main()
