from __future__ import annotations

import json
from pathlib import Path

import trimesh

from .bundle import ProductionPackageBuilder
from .content_addressed import ContentAddressedPackageWriter
from .package_integrity import PackageIntegrityVerifier
from .render_contract import RenderContract, RenderIntent
from .render_executor import DeterministicRenderExecutor


def test_physical_artifact_to_verified_content_addressed_package(tmp_path: Path) -> None:
    source = tmp_path / "source_specification.json"
    source.write_text(json.dumps({"product": "planter", "audit_case": "production-package-boundary"}, sort_keys=True), encoding="utf-8")

    mesh = trimesh.creation.icosphere(subdivisions=2, radius=30.0)
    stl_path = tmp_path / "audit_product.stl"
    mesh.export(stl_path)
    assert stl_path.is_file() and stl_path.stat().st_size > 0

    contract = RenderContract.standard(RenderIntent.PRODUCTION)
    renders = DeterministicRenderExecutor.execute(stl_path, contract, tmp_path / "renders")
    assert {render.view_name for render in renders} == {"front", "side", "top", "iso"}
    assert all(Path(render.path).is_file() and Path(render.path).stat().st_size > 0 for render in renders)

    artifacts = {"stl": stl_path}
    artifacts.update({f"render_{render.view_name}": Path(render.path) for render in renders})

    builder = ProductionPackageBuilder()
    manifest = builder.build(
        source_specification=source,
        motor_version="integration-consolidation-core",
        source_revision="differential-audit-production-package",
        artifacts=artifacts,
        render_contract=contract,
        required_artifacts=("stl", "render_front", "render_side", "render_top", "render_iso"),
    )
    assert manifest.schema_version == "dobo.production-package.v2"
    assert len(manifest.artifacts) == 5
    assert len(manifest.package_sha256) == 64

    materialized = ContentAddressedPackageWriter.materialize(
        manifest,
        source_specification=source,
        output_root=tmp_path / "packages",
    )
    verified = PackageIntegrityVerifier.verify(materialized)
    assert verified.source_verified
    assert verified.artifact_hashes_verified
    assert verified.identity_verified
    assert verified.artifact_count == 5

    duplicate = builder.build(
        source_specification=source,
        motor_version="integration-consolidation-core",
        source_revision="differential-audit-production-package",
        artifacts=artifacts,
        render_contract=contract,
        required_artifacts=("stl", "render_front", "render_side", "render_top", "render_iso"),
    )
    assert duplicate.package_sha256 == manifest.package_sha256
