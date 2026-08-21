from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import zipfile
from xml.etree import ElementTree as ET


CORE_NS = (
    "http://schemas.microsoft.com/"
    "3dmanufacturing/core/2015/02"
)


@dataclass(frozen=True, slots=True)
class ThreeMFProjectInspection:
    valid: bool
    build_item_count: int
    component_count: int
    top_level_object_count: int
    region_object_count: int
    filament_slots: tuple[int, ...]
    build_transform: tuple[float, ...] | None
    transformed_bounds: tuple[float, float, float, float, float, float] | None


class ThreeMFProjectInspector:
    """Inspect the real DOBO Creality 3MF structure and build placement.

    Besides the established compound/material integrity contract, the inspector
    derives the physical post-transform bounds from the actual mesh vertices
    and the top-level 3MF build transform. This allows ORIENTATION_ON_BED to be
    validated from exported production data instead of inferring it from the
    number of build items.
    """

    _REGION_FILES = (
        "3D/Objects/object_1.model",
        "3D/Objects/object_2.model",
        "3D/Objects/object_3.model",
    )

    @staticmethod
    def _parse_transform(value: str | None) -> tuple[float, ...] | None:
        if value is None:
            return (
                1.0,
                0.0,
                0.0,
                0.0,
                1.0,
                0.0,
                0.0,
                0.0,
                1.0,
                0.0,
                0.0,
                0.0,
            )
        try:
            values = tuple(float(item) for item in value.split())
        except ValueError:
            return None
        return values if len(values) == 12 else None

    @staticmethod
    def _transform_vertex(
        vertex: tuple[float, float, float],
        transform: tuple[float, ...],
    ) -> tuple[float, float, float]:
        x, y, z = vertex
        return (
            x * transform[0]
            + y * transform[3]
            + z * transform[6]
            + transform[9],
            x * transform[1]
            + y * transform[4]
            + z * transform[7]
            + transform[10],
            x * transform[2]
            + y * transform[5]
            + z * transform[8]
            + transform[11],
        )

    @classmethod
    def _transformed_bounds(
        cls,
        vertices: tuple[tuple[float, float, float], ...],
        transform: tuple[float, ...] | None,
    ) -> tuple[float, float, float, float, float, float] | None:
        if not vertices or transform is None:
            return None
        transformed = tuple(
            cls._transform_vertex(vertex, transform)
            for vertex in vertices
        )
        xs = tuple(point[0] for point in transformed)
        ys = tuple(point[1] for point in transformed)
        zs = tuple(point[2] for point in transformed)
        return (
            min(xs),
            max(xs),
            min(ys),
            max(ys),
            min(zs),
            max(zs),
        )

    def inspect(
        self,
        path: str | Path,
    ) -> ThreeMFProjectInspection:
        project_path = Path(path)

        if not project_path.is_file():
            raise FileNotFoundError(
                f"3MF project does not exist: {project_path}"
            )

        with zipfile.ZipFile(project_path, "r") as archive:
            names = set(archive.namelist())
            required = {
                "3D/3dmodel.model",
                "Metadata/model_settings.config",
                *self._REGION_FILES,
            }
            missing = required - names
            if missing:
                raise RuntimeError(
                    "3MF project is missing required files: "
                    f"{sorted(missing)}"
                )

            top_root = ET.fromstring(archive.read("3D/3dmodel.model"))
            settings_root = ET.fromstring(
                archive.read("Metadata/model_settings.config")
            )
            region_roots = tuple(
                ET.fromstring(archive.read(filename))
                for filename in self._REGION_FILES
            )

        ns = {"m": CORE_NS}
        top_objects = top_root.findall("./m:resources/m:object", ns)
        components = top_root.findall(
            "./m:resources/m:object/m:components/m:component",
            ns,
        )
        build_items = top_root.findall("./m:build/m:item", ns)

        build_transform = None
        if len(build_items) == 1:
            build_transform = self._parse_transform(
                build_items[0].attrib.get("transform")
            )

        region_object_count = 0
        raw_vertices: list[tuple[float, float, float]] = []
        for root in region_roots:
            objects = root.findall("./m:resources/m:object", ns)
            if len(objects) != 1:
                continue
            mesh = objects[0].find("m:mesh", ns)
            if mesh is None:
                continue
            vertices = mesh.findall("./m:vertices/m:vertex", ns)
            triangles = mesh.findall("./m:triangles/m:triangle", ns)
            if vertices and triangles:
                region_object_count += 1
            for vertex in vertices:
                try:
                    raw_vertices.append(
                        (
                            float(vertex.attrib["x"]),
                            float(vertex.attrib["y"]),
                            float(vertex.attrib["z"]),
                        )
                    )
                except (KeyError, ValueError):
                    continue

        filament_slots: list[int] = []
        for part in settings_root.findall(".//part"):
            extruder_value: str | None = None
            for metadata in part.findall("metadata"):
                if metadata.attrib.get("key") == "extruder":
                    extruder_value = metadata.attrib.get("value")
                    break
            if extruder_value is None:
                continue
            try:
                filament_slots.append(int(extruder_value))
            except ValueError:
                continue

        unique_slots = tuple(sorted(set(filament_slots)))
        transformed_bounds = self._transformed_bounds(
            tuple(raw_vertices),
            build_transform,
        )
        valid = bool(
            len(top_objects) == 1
            and len(components) == 3
            and len(build_items) == 1
            and region_object_count == 3
            and unique_slots == (1, 2, 3)
            and build_transform is not None
            and transformed_bounds is not None
        )

        return ThreeMFProjectInspection(
            valid=valid,
            build_item_count=len(build_items),
            component_count=len(components),
            top_level_object_count=len(top_objects),
            region_object_count=region_object_count,
            filament_slots=unique_slots,
            build_transform=build_transform,
            transformed_bounds=transformed_bounds,
        )
