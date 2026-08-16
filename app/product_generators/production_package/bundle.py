from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Mapping

from .render_contract import RenderContract


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    kind: str
    logical_name: str
    path: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class GenerationPackageManifest:
    schema_version: str
    motor_version: str
    source_revision: str
    source_specification: str
    source_sha256: str
    render_contract_version: str
    artifacts: tuple[ArtifactRecord, ...]
    package_sha256: str

    def to_json_dict(self) -> dict[str, object]:
        return asdict(self)


class ProductionPackageBuilder:
    """Build a deterministic, auditable record of a DOBO generation.

    Package identity is content-addressed and intentionally independent from
    absolute filesystem locations. It depends only on source content, declared
    Motor/source revision, render contract version, artifact logical names,
    artifact kinds, sizes and hashes. This allows the same production inputs to
    receive the same identity on a developer workstation and in CI.
    """

    SCHEMA_VERSION = "dobo.production-package.v2"

    @staticmethod
    def _file_sha256(path: Path) -> str:
        digest = sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _canonical_bytes(payload: dict[str, object]) -> bytes:
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

    @classmethod
    def identity_payload(
        cls,
        *,
        motor_version: str,
        source_revision: str,
        source_sha256: str,
        source_logical_name: str,
        render_contract_version: str,
        artifacts: tuple[ArtifactRecord, ...],
    ) -> dict[str, object]:
        return {
            "schema_version": cls.SCHEMA_VERSION,
            "motor_version": motor_version,
            "source_revision": source_revision,
            "source_logical_name": source_logical_name,
            "source_sha256": source_sha256,
            "render_contract_version": render_contract_version,
            "artifacts": [
                {
                    "kind": record.kind,
                    "logical_name": record.logical_name,
                    "sha256": record.sha256,
                    "size_bytes": record.size_bytes,
                }
                for record in artifacts
            ],
        }

    @classmethod
    def package_hash_from_manifest(cls, manifest: GenerationPackageManifest) -> str:
        payload = cls.identity_payload(
            motor_version=manifest.motor_version,
            source_revision=manifest.source_revision,
            source_sha256=manifest.source_sha256,
            source_logical_name=Path(manifest.source_specification).name,
            render_contract_version=manifest.render_contract_version,
            artifacts=manifest.artifacts,
        )
        return sha256(cls._canonical_bytes(payload)).hexdigest()

    def build(
        self,
        *,
        source_specification: str | Path,
        motor_version: str,
        source_revision: str,
        artifacts: Mapping[str, str | Path],
        render_contract: RenderContract,
        required_artifacts: tuple[str, ...] = (),
    ) -> GenerationPackageManifest:
        source_path = Path(source_specification)
        if not source_path.is_file():
            raise FileNotFoundError(source_path)
        if not motor_version.strip():
            raise ValueError("motor_version is required")
        if not source_revision.strip():
            raise ValueError("source_revision is required")
        render_contract.validate()

        missing_required = sorted(set(required_artifacts) - set(artifacts))
        if missing_required:
            raise RuntimeError(
                f"Missing required production artifacts: {missing_required}"
            )

        records: list[ArtifactRecord] = []
        for kind, raw_path in sorted(artifacts.items()):
            path = Path(raw_path)
            if not path.is_file():
                raise FileNotFoundError(path)
            records.append(
                ArtifactRecord(
                    kind=str(kind),
                    logical_name=path.name,
                    path=str(path),
                    sha256=self._file_sha256(path),
                    size_bytes=path.stat().st_size,
                )
            )

        source_hash = self._file_sha256(source_path)
        provisional = GenerationPackageManifest(
            schema_version=self.SCHEMA_VERSION,
            motor_version=motor_version,
            source_revision=source_revision,
            source_specification=str(source_path),
            source_sha256=source_hash,
            render_contract_version=render_contract.schema_version,
            artifacts=tuple(records),
            package_sha256="",
        )
        package_hash = self.package_hash_from_manifest(provisional)

        return GenerationPackageManifest(
            schema_version=self.SCHEMA_VERSION,
            motor_version=motor_version,
            source_revision=source_revision,
            source_specification=str(source_path),
            source_sha256=source_hash,
            render_contract_version=render_contract.schema_version,
            artifacts=tuple(records),
            package_sha256=package_hash,
        )

    @staticmethod
    def write(
        manifest: GenerationPackageManifest,
        path: str | Path,
    ) -> str:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(manifest.to_json_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return str(output)
