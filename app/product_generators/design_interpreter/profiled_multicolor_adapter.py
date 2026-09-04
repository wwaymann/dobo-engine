from __future__ import annotations

"""Reconnect promoted profiled CAD text to DOBO's validated Creality multicolor 3MF.

This adapter deliberately reuses the existing Phase 6.5 compound-object exporter:
one printable Creality object, three internal material parts, one shared transform.

For promoted profiled planters the material partition is reconstructed from the
same analytic CAD contract used by the body/text pipeline:

- Body   -> filament 1
- Raised physical text -> filament 2
- Upper/lower accent band -> filament 3

The three regions are non-overlapping and must conserve the final CAD volume.
"""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import cadquery as cq

from product_generators.surface_designer.three_mf_exporter import (
    CORE_NS,
    ThreeMFExporter,
    ThreeMFRegion,
)

from .intelligent_surfaces import IntelligentSurfaceProgram, ResolvedSurfaceLayer
from .native_profiled_cad_adapter import _profiled_body
from .native_profiled_text_adapter import _apply_text_block, uses_native_profiled_text
from .native_text_pipeline_adapter import _text_features
from .semantic_contract import DesignSemanticProgram


PROFILED_MULTICOLOR_ADAPTER_VERSION = "PMC.1-creality-compound-profiled-text"
_BOOLEAN_TOLERANCE_MM = 0.005


@dataclass(frozen=True, slots=True)
class ProfiledMulticolorExportResult:
    path: str
    vertex_count: int
    triangle_count: int
    archive_members: tuple[str, ...]
    material_count: int
    painted_triangle_count: int
    region_names: tuple[str, ...]
    filament_slots: tuple[int, ...]
    colors: tuple[str, ...]
    volume_final_mm3: float
    volume_regions_mm3: float
    volume_error_mm3: float

    def validate(self) -> None:
        target = Path(self.path)
        if not target.is_file() or target.stat().st_size <= 0:
            raise RuntimeError("Profiled multicolor 3MF was not created.")
        if self.vertex_count <= 0 or self.triangle_count <= 0:
            raise RuntimeError("Profiled multicolor 3MF contains no geometry.")
        if self.material_count != 3:
            raise RuntimeError("Profiled multicolor 3MF must contain three materials.")
        if self.filament_slots != (1, 2, 3):
            raise RuntimeError(
                f"Profiled multicolor filament mapping changed: {self.filament_slots!r}."
            )
        if len(self.colors) != 3 or len(set(self.colors)) != 3:
            raise RuntimeError("Profiled multicolor 3MF requires three distinct colors.")
        if self.volume_error_mm3 > max(1.0, self.volume_final_mm3 * 2.0e-4):
            raise RuntimeError("Profiled multicolor partition does not conserve volume.")

        with ZipFile(target, "r") as archive:
            if archive.testzip() is not None:
                raise RuntimeError("Profiled multicolor 3MF ZIP integrity failed.")
            members = tuple(sorted(archive.namelist()))
            required = {
                "3D/3dmodel.model",
                "Metadata/model_settings.config",
                "Metadata/project_settings.config",
            }
            if not required.issubset(members):
                raise RuntimeError(
                    "Profiled multicolor 3MF is missing Creality project metadata."
                )

            top_model = ET.fromstring(archive.read("3D/3dmodel.model"))
            model_settings = ET.fromstring(
                archive.read("Metadata/model_settings.config")
            )
            project_settings = json.loads(
                archive.read("Metadata/project_settings.config")
            )

        ns = {"m": CORE_NS}
        objects = top_model.findall(".//m:resources/m:object", ns)
        build_items = top_model.findall(".//m:build/m:item", ns)
        components = top_model.findall(".//m:components/m:component", ns)
        if len(objects) != 1 or len(build_items) != 1 or len(components) != 3:
            raise RuntimeError(
                "Profiled multicolor project must remain one printable compound "
                "object with three internal components."
            )

        object_nodes = model_settings.findall("object")
        if len(object_nodes) != 1:
            raise RuntimeError("Creality model_settings lost the compound object.")
        parts = object_nodes[0].findall("part")
        slots: list[int] = []
        names: list[str] = []
        for part in parts:
            slot = None
            name = None
            for metadata in part.findall("metadata"):
                if metadata.get("key") == "extruder":
                    slot = int(metadata.get("value"))
                elif metadata.get("key") == "name":
                    name = str(metadata.get("value"))
            if slot is None or name is None:
                raise RuntimeError("Creality material part lost name/extruder metadata.")
            slots.append(slot)
            names.append(name)
        if tuple(slots) != self.filament_slots:
            raise RuntimeError(
                f"Creality part filament mapping disagrees: {tuple(slots)!r}."
            )
        if tuple(names) != self.region_names:
            raise RuntimeError(
                f"Creality part names disagree: {tuple(names)!r}."
            )

        project_colors = tuple(
            str(value).upper()
            for value in project_settings.get("filament_colour", [])
        )
        if project_colors != self.colors:
            raise RuntimeError(
                f"Creality filament colors disagree: {project_colors!r}."
            )


def _multicolor_layers(
    program: IntelligentSurfaceProgram,
) -> tuple[ResolvedSurfaceLayer, ResolvedSurfaceLayer] | None:
    if len(program.palette) != 3:
        return None

    text_layers = [
        layer
        for layer in program.layers
        if layer.kind == "text"
        and layer.color.upper() != program.base_color.upper()
        and layer.filament_slot == 2
    ]
    accent_layers = [
        layer
        for layer in program.layers
        if layer.kind != "text"
        and layer.region in {"upper", "lower"}
        and layer.color.upper() not in {
            program.base_color.upper(),
            text_layers[0].color.upper() if text_layers else "",
        }
        and layer.filament_slot == 3
    ]
    if not text_layers or not accent_layers:
        return None
    return text_layers[0], accent_layers[0]


def uses_profiled_compound_multicolor(
    program: DesignSemanticProgram,
    surface_program: IntelligentSurfaceProgram,
) -> bool:
    if not uses_native_profiled_text(program):
        return False
    text_features = tuple(_text_features(program))
    if not text_features:
        return False
    if any(
        feature.surface_effect not in {"raised"}
        for feature in text_features
    ):
        # The validated Creality compound route partitions actual positive
        # material volumes. Recessed text remains on the standards-based painted
        # 3MF route until a dedicated inlay contract is promoted.
        return False
    return _multicolor_layers(surface_program) is not None


def _accent_region(
    base: cq.Shape,
    route: dict[str, Any],
    layer: ResolvedSurfaceLayer,
) -> cq.Shape:
    height = float(route["height_mm"])
    maximum_radius = 0.5 * float(route["diameter_mm"])
    _u0, v0, _u1, v1 = layer.uv_bounds
    z0 = max(0.0, min(height, float(v0) * height))
    z1 = max(0.0, min(height, float(v1) * height))
    if z1 - z0 < 0.75:
        raise RuntimeError("Profiled multicolor accent band is too thin.")

    band_tool = (
        cq.Workplane("XY")
        .workplane(offset=z0)
        .circle(maximum_radius + 5.0)
        .extrude(z1 - z0)
        .val()
    )
    region = base.intersect(band_tool, tol=_BOOLEAN_TOLERANCE_MM).clean()
    if not isinstance(region, cq.Shape) or not region.isValid():
        raise RuntimeError("Profiled multicolor accent region is invalid.")
    if float(region.Volume()) <= 1e-6:
        raise RuntimeError("Profiled multicolor accent region has zero volume.")
    return region


def export_profiled_compound_multicolor(
    *,
    motor: dict[str, Any],
    program: DesignSemanticProgram,
    surface_program: IntelligentSurfaceProgram,
    path: str | Path,
) -> ProfiledMulticolorExportResult:
    layers = _multicolor_layers(surface_program)
    if layers is None or not uses_profiled_compound_multicolor(
        program, surface_program
    ):
        raise RuntimeError(
            "Profiled compound multicolor requires raised native text plus "
            "three validated color zones."
        )
    text_layer, accent_layer = layers

    route = motor.get("_profiled_revolution")
    if not isinstance(route, dict):
        raise RuntimeError("Profiled multicolor route is missing profiled CAD data.")

    base = _profiled_body(route)
    final, base_volume, final_volume, line_count, glyph_count = _apply_text_block(
        base, route, program
    )
    if final_volume <= base_volume:
        raise RuntimeError(
            "Profiled compound multicolor requires positive raised text volume."
        )

    # The physical text material is exactly the volume added by the promoted
    # emboss operation. It therefore matches the real glyph geometry rather than
    # an approximate UV bitmap.
    text_region = final.cut(base, tol=_BOOLEAN_TOLERANCE_MM).clean()
    if not isinstance(text_region, cq.Shape) or not text_region.isValid():
        raise RuntimeError("Profiled multicolor text material region is invalid.")
    if float(text_region.Volume()) <= 1e-6:
        raise RuntimeError("Profiled multicolor text material region has zero volume.")

    accent_region = _accent_region(base, route, accent_layer)
    body_region = base.cut(accent_region, tol=_BOOLEAN_TOLERANCE_MM).clean()
    if not isinstance(body_region, cq.Shape) or not body_region.isValid():
        raise RuntimeError("Profiled multicolor body material region is invalid.")
    if float(body_region.Volume()) <= 1e-6:
        raise RuntimeError("Profiled multicolor body material region has zero volume.")

    region_volume = sum(
        float(shape.Volume())
        for shape in (body_region, text_region, accent_region)
    )
    volume_error = abs(region_volume - final_volume)
    volume_tolerance = max(1.0, final_volume * 2.0e-4)
    if volume_error > volume_tolerance:
        raise RuntimeError(
            "Profiled multicolor partition does not conserve CAD volume: "
            f"final={final_volume}, regions={region_volume}, "
            f"error={volume_error}, tolerance={volume_tolerance}."
        )

    colors = (
        surface_program.base_color.upper(),
        text_layer.color.upper(),
        accent_layer.color.upper(),
    )
    if len(set(colors)) != 3:
        raise RuntimeError("Profiled multicolor route requires three distinct colors.")

    regions = (
        ThreeMFRegion(
            name="Body",
            shape=body_region,
            color=colors[0],
            filament_slot=1,
        ),
        ThreeMFRegion(
            name="Text",
            shape=text_region,
            color=colors[1],
            filament_slot=2,
        ),
        ThreeMFRegion(
            name="Accent",
            shape=accent_region,
            color=colors[2],
            filament_slot=3,
        ),
    )
    output = ThreeMFExporter().export(regions=regions, path=path)

    tessellations = [
        shape.tessellate(0.03, 0.08)
        for shape in (body_region, text_region, accent_region)
    ]
    vertex_count = sum(len(vertices) for vertices, _triangles in tessellations)
    non_body_triangles = sum(
        len(triangles) for _vertices, triangles in tessellations[1:]
    )

    target = Path(output.path)
    with ZipFile(target, "r") as archive:
        members = tuple(sorted(archive.namelist()))

    motor["_profiled_multicolor"] = {
        "adapter_version": PROFILED_MULTICOLOR_ADAPTER_VERSION,
        "method": "cad_volume_partition_creality_compound",
        "region_names": ["Body", "Text", "Accent"],
        "filament_slots": [1, 2, 3],
        "colors": list(colors),
        "text_lines": line_count,
        "text_glyphs": glyph_count,
        "volume_final_mm3": final_volume,
        "volume_regions_mm3": region_volume,
        "volume_error_mm3": volume_error,
        "compound_object": True,
        "build_items": 1,
    }

    result = ProfiledMulticolorExportResult(
        path=str(target),
        vertex_count=vertex_count,
        triangle_count=int(output.triangle_count),
        archive_members=members,
        material_count=3,
        painted_triangle_count=non_body_triangles,
        region_names=("Body", "Text", "Accent"),
        filament_slots=(1, 2, 3),
        colors=colors,
        volume_final_mm3=final_volume,
        volume_regions_mm3=region_volume,
        volume_error_mm3=volume_error,
    )
    result.validate()
    return result
