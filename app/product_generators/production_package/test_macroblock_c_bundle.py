from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from .bundle import ProductionPackageBuilder
from .render_contract import RenderContract, RenderIntent


def main() -> None:
    builder = ProductionPackageBuilder()
    contract = RenderContract.standard(RenderIntent.PRODUCTION)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        source = root / "design.json"
        stl = root / "design.stl"
        render = root / "design.png"
        source.write_text('{"id":"c1","shape":"test"}\n', encoding="utf-8")
        stl.write_bytes(b"solid-dobo-c1")
        render.write_bytes(b"render-dobo-c1")

        first = builder.build(
            source_specification=source,
            motor_version="C1.0",
            source_revision="test-revision",
            artifacts={"stl": stl, "render": render},
            render_contract=contract,
            required_artifacts=("stl", "render"),
        )
        reordered = builder.build(
            source_specification=source,
            motor_version="C1.0",
            source_revision="test-revision",
            artifacts={"render": render, "stl": stl},
            render_contract=contract,
            required_artifacts=("render", "stl"),
        )
        if first.package_sha256 != reordered.package_sha256:
            raise RuntimeError("Package identity depends on artifact insertion order.")
        if len(first.package_sha256) != 64 or len(first.source_sha256) != 64:
            raise RuntimeError("Package fingerprints are invalid.")

        stl.write_bytes(b"solid-dobo-c1-mutated")
        mutated = builder.build(
            source_specification=source,
            motor_version="C1.0",
            source_revision="test-revision",
            artifacts={"stl": stl, "render": render},
            render_contract=contract,
            required_artifacts=("stl", "render"),
        )
        if first.package_sha256 == mutated.package_sha256:
            raise RuntimeError("Artifact mutation did not change package identity.")

        rejected_missing = False
        try:
            builder.build(
                source_specification=source,
                motor_version="C1.0",
                source_revision="test-revision",
                artifacts={"stl": stl},
                render_contract=contract,
                required_artifacts=("stl", "render"),
            )
        except RuntimeError:
            rejected_missing = True
        if not rejected_missing:
            raise RuntimeError("Missing required artifact was accepted.")

        written = Path(builder.write(first, root / "production_package_manifest.json"))
        if not written.is_file() or written.stat().st_size <= 0:
            raise RuntimeError("Production package manifest was not written.")

    print("DOBO Macroblock C - Production Package")
    print("-----------------------------------")
    print("deterministic identity", "OK")
    print("content mutation detection", "OK")
    print("required artifact gate", "OK")
    print("manifest serialization", "OK")
    print("-----------------------------------")
    print("Macroblock C Production Package: Valid OK")


if __name__ == "__main__":
    main()
