from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

from .bundle import ArtifactRecord, GenerationPackageManifest, ProductionPackageBuilder


@dataclass(frozen=True, slots=True)
class PackageIntegrityReport:
    package_root: str
    package_sha256: str
    source_verified: bool
    artifact_count: int
    artifact_hashes_verified: bool
    identity_verified: bool

    def validate(self) -> None:
        if not self.source_verified:
            raise RuntimeError("Materialized source JSON hash mismatch.")
        if self.artifact_count <= 0:
            raise RuntimeError("Materialized package has no production artifacts.")
        if not self.artifact_hashes_verified:
            raise RuntimeError("Materialized production artifact hash mismatch.")
        if not self.identity_verified:
            raise RuntimeError("Materialized package identity mismatch.")


class PackageIntegrityVerifier:
    @staticmethod
    def _sha256(path: Path) -> str:
        digest = sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _manifest_from_json(payload: dict[str, object]) -> GenerationPackageManifest:
        records = tuple(ArtifactRecord(kind=str(item["kind"]), logical_name=str(item["logical_name"]), path=str(item["path"]), sha256=str(item["sha256"]), size_bytes=int(item["size_bytes"])) for item in payload["artifacts"])
        return GenerationPackageManifest(schema_version=str(payload["schema_version"]), motor_version=str(payload["motor_version"]), source_revision=str(payload["source_revision"]), source_specification=str(payload["source_specification"]), source_sha256=str(payload["source_sha256"]), render_contract_version=str(payload["render_contract_version"]), artifacts=records, package_sha256=str(payload["package_sha256"]))

    @classmethod
    def verify(cls, package_root: str | Path) -> PackageIntegrityReport:
        root = Path(package_root)
        manifest_path = root / "production_package_manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(manifest_path)
        manifest = cls._manifest_from_json(json.loads(manifest_path.read_text(encoding="utf-8")))
        if manifest.schema_version != ProductionPackageBuilder.SCHEMA_VERSION:
            raise RuntimeError(f"Unsupported package schema {manifest.schema_version!r}; expected {ProductionPackageBuilder.SCHEMA_VERSION!r}.")

        copied_source = root / "source" / Path(manifest.source_specification).name
        source_verified = copied_source.is_file() and copied_source.stat().st_size > 0 and cls._sha256(copied_source) == manifest.source_sha256

        artifacts_verified = True
        verified_count = 0
        for record in manifest.artifacts:
            materialized = root / "artifacts" / f"{record.kind}__{record.logical_name}"
            if not materialized.is_file() or materialized.stat().st_size != record.size_bytes or cls._sha256(materialized) != record.sha256:
                artifacts_verified = False
                break
            verified_count += 1

        expected_identity = ProductionPackageBuilder.package_hash_from_manifest(manifest)
        identity_verified = root.name == manifest.package_sha256 and expected_identity == manifest.package_sha256
        report = PackageIntegrityReport(str(root), manifest.package_sha256, source_verified, verified_count, artifacts_verified, identity_verified)
        report.validate()
        return report
