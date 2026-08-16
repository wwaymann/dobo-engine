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

    Package identity is content-addressed: it depends on the source JSON,
    Motor/source revision, render contract version and artifact hashes. Runtime
    timestamps are intentionally excluded so the same generation inputs produce
    the same identity.
    """

    SCHEMA_VERSION = "dobo.production-package.v1"

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
        identity_payload: dict[str, object] = {
            "schema_version": self.SCHEMA_VERSION,
            "motor_version": motor_version,
            "source_revision": source_revision,
            "source_specification": str(source_path),
            "source_sha256": source_hash,
            "render_contract_version": render_contract.schema_version,
            "artifacts": [asdict(record) for record in records],
        }
        package_hash = sha256(self._canonical_bytes(identity_payload)).hexdigest()

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
