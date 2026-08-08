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


class ThreeMFProjectInspector:
    """
    Inspect the real DOBO Creality Phase-6.5 3MF structure.

    Validated exporter contract:

      3D/3dmodel.model
        - one top-level compound object
        - three component references
        - one build item

      3D/Objects/object_1.model
      3D/Objects/object_2.model
      3D/Objects/object_3.model
        - one material mesh object each

      Metadata/model_settings.config
        - three <part> entries
        - explicit extruder assignments 1 / 2 / 3
    """

    _REGION_FILES = (
        "3D/Objects/object_1.model",
        "3D/Objects/object_2.model",
        "3D/Objects/object_3.model",
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

        with zipfile.ZipFile(
            project_path,
            "r",
        ) as archive:
            names = set(
                archive.namelist()
            )

            required = {
                "3D/3dmodel.model",
                "Metadata/model_settings.config",
                *self._REGION_FILES,
            }

            missing = (
                required
                - names
            )

            if missing:
                raise RuntimeError(
                    "3MF project is missing required files: "
                    f"{sorted(missing)}"
                )

            top_root = ET.fromstring(
                archive.read(
                    "3D/3dmodel.model"
                )
            )

            settings_root = ET.fromstring(
                archive.read(
                    "Metadata/model_settings.config"
                )
            )

            region_roots = tuple(
                ET.fromstring(
                    archive.read(
                        filename
                    )
                )
                for filename
                in self._REGION_FILES
            )

        ns = {
            "m": CORE_NS,
        }

        top_objects = top_root.findall(
            "./m:resources/m:object",
            ns,
        )

        components = top_root.findall(
            "./m:resources/m:object/"
            "m:components/m:component",
            ns,
        )

        build_items = top_root.findall(
            "./m:build/m:item",
            ns,
        )

        region_object_count = 0

        for root in region_roots:
            objects = root.findall(
                "./m:resources/m:object",
                ns,
            )

            if len(objects) != 1:
                continue

            mesh = objects[0].find(
                "m:mesh",
                ns,
            )

            if mesh is None:
                continue

            vertices = mesh.findall(
                "./m:vertices/m:vertex",
                ns,
            )

            triangles = mesh.findall(
                "./m:triangles/m:triangle",
                ns,
            )

            if (
                vertices
                and triangles
            ):
                region_object_count += 1

        filament_slots: list[int] = []

        for part in settings_root.findall(
            ".//part"
        ):
            extruder_value: str | None = None

            for metadata in part.findall(
                "metadata"
            ):
                if (
                    metadata.attrib.get(
                        "key"
                    )
                    == "extruder"
                ):
                    extruder_value = (
                        metadata.attrib.get(
                            "value"
                        )
                    )
                    break

            if extruder_value is None:
                continue

            try:
                slot = int(
                    extruder_value
                )
            except ValueError:
                continue

            filament_slots.append(
                slot
            )

        unique_slots = tuple(
            sorted(
                set(
                    filament_slots
                )
            )
        )

        valid = bool(
            len(top_objects) == 1
            and len(components) == 3
            and len(build_items) == 1
            and region_object_count == 3
            and unique_slots
            == (1, 2, 3)
        )

        return ThreeMFProjectInspection(
            valid=valid,
            build_item_count=len(
                build_items
            ),
            component_count=len(
                components
            ),
            top_level_object_count=len(
                top_objects
            ),
            region_object_count=(
                region_object_count
            ),
            filament_slots=(
                unique_slots
            ),
        )
