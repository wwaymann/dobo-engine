from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path

from .consolidated_validator import ValidationStatus
from .product_integration import RealProductValidationResult
from .three_mf_project_inspector import ThreeMFProjectInspector


@dataclass(frozen=True, slots=True)
class ProductionHandoffManifest:
    schema_version: str
    source_specification: str
    three_mf_path: str
    three_mf_sha256: str
    production_orientation: str
    final_volume_mm3: float
    rule_counts: dict[str, int]
    blocking_error_codes: tuple[str, ...]
    build_item_count: int
    component_count: int
    filament_slots: tuple[int, ...]
    transformed_bounds_mm: tuple[float, float, float, float, float, float] | None
    ready_for_production: bool

    def to_json_dict(self) -> dict[str, object]:
        return asdict(self)


class ProductionHandoffBuilder:
    """Create auditable production evidence from the validated real 3MF.

    The handoff is deliberately derived only from already-validated outputs:
    the consolidated 24-rule report and the final exported 3MF. It does not
    weaken any manufacturing threshold and it cannot turn a failed validation
    into a production-ready result.
    """

    SCHEMA_VERSION = "dobo.production-handoff.v1"

    @staticmethod
    def _file_sha256(path: Path) -> str:
        digest = sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def build(
        self,
        *,
        result: RealProductValidationResult,
        source_specification: str | Path,
    ) -> ProductionHandoffManifest:
        project_path = Path(result.three_mf_path)
        project = ThreeMFProjectInspector().inspect(project_path)
        blocking_codes = tuple(item.code for item in result.report.blocking_errors)
        counts = {
            status.value: result.report.count(status)
            for status in ValidationStatus
        }
        ready = bool(
            not blocking_codes
            and project.valid
            and project.build_item_count == 1
            and project.transformed_bounds is not None
            and len(project.filament_slots) == 3
        )
        return ProductionHandoffManifest(
            schema_version=self.SCHEMA_VERSION,
            source_specification=str(Path(source_specification)),
            three_mf_path=str(project_path),
            three_mf_sha256=self._file_sha256(project_path),
            production_orientation=result.production_orientation,
            final_volume_mm3=float(result.final_volume),
            rule_counts=counts,
            blocking_error_codes=blocking_codes,
            build_item_count=project.build_item_count,
            component_count=project.component_count,
            filament_slots=project.filament_slots,
            transformed_bounds_mm=project.transformed_bounds,
            ready_for_production=ready,
        )

    @staticmethod
    def write(
        manifest: ProductionHandoffManifest,
        path: str | Path,
    ) -> str:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(manifest.to_json_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return str(output)
