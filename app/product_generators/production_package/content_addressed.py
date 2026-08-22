from __future__ import annotations

import json
from pathlib import Path
from shutil import copy2

from .bundle import GenerationPackageManifest


class ContentAddressedPackageWriter:
    @staticmethod
    def materialize(manifest: GenerationPackageManifest, *, source_specification: str | Path, output_root: str | Path) -> Path:
        root = Path(output_root) / manifest.package_sha256
        source_dir = root / "source"
        artifact_dir = root / "artifacts"
        source_dir.mkdir(parents=True, exist_ok=True)
        artifact_dir.mkdir(parents=True, exist_ok=True)

        source = Path(source_specification)
        copied_source = source_dir / source.name
        copy2(source, copied_source)

        for record in manifest.artifacts:
            source_artifact = Path(record.path)
            destination = artifact_dir / f"{record.kind}__{source_artifact.name}"
            copy2(source_artifact, destination)

        manifest_path = root / "production_package_manifest.json"
        manifest_path.write_text(json.dumps(manifest.to_json_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return root
