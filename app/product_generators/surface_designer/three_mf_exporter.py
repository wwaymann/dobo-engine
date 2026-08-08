from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import uuid
import zipfile
from xml.etree import ElementTree as ET

import cadquery as cq


CORE_NS = (
    "http://schemas.microsoft.com/"
    "3dmanufacturing/core/2015/02"
)
PROD_NS = (
    "http://schemas.microsoft.com/"
    "3dmanufacturing/production/2015/06"
)
BAMBU_NS = (
    "http://schemas.bambulab.com/"
    "package/2021"
)

_TEMPLATE_NAME = "creality_project_template.3mf"

# The three model resources follow the exact odd/even ID pattern
# used by the real Creality project:
#
# object file internal IDs: 1, 3, 5
# top-level object IDs:      2, 4, 6
_REGION_IDS = (
    (1, 2, "3D/Objects/object_1.model"),
    (3, 4, "3D/Objects/object_2.model"),
    (5, 6, "3D/Objects/object_3.model"),
)

# Redundant Creality paint hints observed in the real project.
# Part-level extruder assignment remains the primary explicit mapping.
_PAINT_HINT = {
    1: None,
    2: "8",
    3: "0C",
}


@dataclass(frozen=True, slots=True)
class ThreeMFRegion:
    name: str
    shape: cq.Shape
    color: str
    filament_slot: int

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError(
                "3MF region name must not be empty."
            )

        if not isinstance(
            self.shape,
            cq.Shape,
        ):
            raise TypeError(
                "3MF region shape must be a "
                "CadQuery Shape."
            )

        if not self.shape.isValid():
            raise RuntimeError(
                f"Region '{self.name}' is invalid."
            )

        if float(
            self.shape.Volume()
        ) <= 0.0:
            raise RuntimeError(
                f"Region '{self.name}' has "
                "zero volume."
            )

        if self.filament_slot not in {
            1,
            2,
            3,
        }:
            raise ValueError(
                "Creality template exporter "
                "supports slots 1, 2 and 3."
            )

        color = self.color.upper()

        if not (
            len(color) == 7
            and color.startswith("#")
        ):
            raise ValueError(
                "color must be #RRGGBB."
            )


@dataclass(frozen=True, slots=True)
class ThreeMFExportResult:
    path: str
    object_count: int
    region_object_count: int
    material_count: int
    triangle_count: int
    component_count: int
    build_item_count: int
    filament_slot_count: int
    region_names: tuple[str, ...]


class ThreeMFExporter:
    """
    Creality Print project exporter based on a real,
    slicable Creality Print project template.

    The printer/process profile is never synthesized.

    We preserve the template project settings and replace only:
      - model geometry
      - object names
      - object/part filament assignments
      - project filament colors
      - build transforms

    This keeps the exported project coherent with Creality Print.
    """

    def __init__(
        self,
        template_path: str | Path | None = None,
    ) -> None:
        if template_path is None:
            template_path = (
                Path(__file__).resolve().parent
                / _TEMPLATE_NAME
            )

        self._template_path = Path(
            template_path
        )

        if not self._template_path.is_file():
            raise FileNotFoundError(
                "Creality project template "
                f"not found: {self._template_path}"
            )

    def export(
        self,
        *,
        regions: tuple[ThreeMFRegion, ...],
        path: str | Path,
        linear_deflection: float = 0.03,
        angular_deflection: float = 0.08,
    ) -> ThreeMFExportResult:
        if len(regions) != 3:
            raise ValueError(
                "Creality Phase 6.4 requires "
                "exactly three regions."
            )

        for region in regions:
            region.validate()

        output_path = Path(path)
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        # All three material meshes must use the SAME transform
        # so they remain perfectly aligned.
        transform = self._bed_transform(
            regions
        )

        object_files: dict[str, bytes] = {}
        total_triangles = 0

        for (
            region,
            (
                internal_id,
                _top_id,
                object_path,
            ),
        ) in zip(
            regions,
            _REGION_IDS,
        ):
            data, triangle_count = (
                self._object_model(
                    region=region,
                    internal_id=internal_id,
                    linear_deflection=(
                        linear_deflection
                    ),
                    angular_deflection=(
                        angular_deflection
                    ),
                )
            )

            object_files[
                object_path
            ] = data

            total_triangles += (
                triangle_count
            )

        top_model = self._top_model(
            regions=regions,
            transform=transform,
        )

        model_settings = (
            self._model_settings(
                regions=regions,
                transform=transform,
            )
        )

        project_settings = (
            self._project_settings(
                regions=regions,
            )
        )

        model_relationships = (
            self._model_relationships()
        )

        replacements = {
            "3D/3dmodel.model": (
                top_model
            ),
            "3D/_rels/3dmodel.model.rels": (
                model_relationships
            ),
            "Metadata/model_settings.config": (
                model_settings
            ),
            "Metadata/project_settings.config": (
                project_settings
            ),
            **object_files,
        }

        # Copy the known-good Creality project wholesale,
        # replacing only the files above.
        with zipfile.ZipFile(
            self._template_path,
            "r",
        ) as source:
            with zipfile.ZipFile(
                output_path,
                "w",
                compression=(
                    zipfile.ZIP_DEFLATED
                ),
            ) as target:
                for item in source.infolist():
                    name = item.filename

                    if name in replacements:
                        target.writestr(
                            name,
                            replacements.pop(
                                name
                            ),
                        )
                    else:
                        target.writestr(
                            item,
                            source.read(
                                name
                            ),
                        )

                # Defensive: write any replacement
                # not already present in template.
                for name, data in (
                    replacements.items()
                ):
                    target.writestr(
                        name,
                        data,
                    )

        if not output_path.is_file():
            raise RuntimeError(
                "Creality project export failed."
            )

        return ThreeMFExportResult(
            path=str(
                output_path
            ),
            object_count=1,
            region_object_count=3,
            material_count=3,
            triangle_count=(
                total_triangles
            ),
            component_count=3,
            build_item_count=1,
            filament_slot_count=3,
            region_names=tuple(
                region.name
                for region in regions
            ),
        )

    def _object_model(
        self,
        *,
        region: ThreeMFRegion,
        internal_id: int,
        linear_deflection: float,
        angular_deflection: float,
    ) -> tuple[bytes, int]:
        vertices, triangles = (
            region.shape.tessellate(
                linear_deflection,
                angular_deflection,
            )
        )

        if (
            not vertices
            or not triangles
        ):
            raise RuntimeError(
                "Could not tessellate "
                f"'{region.name}'."
            )

        root = ET.Element(
            "model",
            {
                "unit": "millimeter",
                "xml:lang": "en-US",
                "xmlns": CORE_NS,
                "xmlns:BambuStudio": (
                    BAMBU_NS
                ),
                "xmlns:p": PROD_NS,
                "requiredextensions": "p",
            },
        )

        ET.SubElement(
            root,
            "metadata",
            {
                "name": (
                    "BambuStudio:"
                    "3mfVersion"
                )
            },
        ).text = "1"

        resources = ET.SubElement(
            root,
            "resources",
        )

        object_node = ET.SubElement(
            resources,
            "object",
            {
                "id": str(
                    internal_id
                ),
                "type": "model",
                "p:UUID": str(
                    uuid.uuid4()
                ),
            },
        )

        mesh = ET.SubElement(
            object_node,
            "mesh",
        )

        vertices_node = ET.SubElement(
            mesh,
            "vertices",
        )

        for vertex in vertices:
            ET.SubElement(
                vertices_node,
                "vertex",
                {
                    "x": self._number(
                        vertex.x
                    ),
                    "y": self._number(
                        vertex.y
                    ),
                    "z": self._number(
                        vertex.z
                    ),
                },
            )

        triangles_node = ET.SubElement(
            mesh,
            "triangles",
        )

        paint_hint = _PAINT_HINT[
            region.filament_slot
        ]

        for triangle in triangles:
            attributes = {
                "v1": str(
                    int(
                        triangle[0]
                    )
                ),
                "v2": str(
                    int(
                        triangle[1]
                    )
                ),
                "v3": str(
                    int(
                        triangle[2]
                    )
                ),
            }

            # This is only a compatibility hint.
            # The explicit part/extruder mapping is
            # stored in model_settings.config.
            if paint_hint is not None:
                attributes[
                    "paint_color"
                ] = paint_hint

            ET.SubElement(
                triangles_node,
                "triangle",
                attributes,
            )

        ET.SubElement(
            root,
            "build",
        )

        return (
            ET.tostring(
                root,
                encoding="utf-8",
                xml_declaration=True,
            ),
            len(
                triangles
            ),
        )

    def _top_model(
        self,
        *,
        regions: tuple[
            ThreeMFRegion,
            ...
        ],
        transform: str,
    ) -> bytes:
        """
        One printable Creality object composed from all three material meshes.

        This is the critical Phase 6.5 change.

        Phase 6.4 emitted three independent build items. Creality Print was
        therefore free to "drop to bed" Body, Text and Decoration separately,
        which moved the text and decorative geometry onto the grid.

        Phase 6.5 emits:
          - one top-level object (id=2)
          - three component meshes inside that object
          - one build item
          - one shared bed transform

        The three meshes keep their original CAD coordinates relative to one
        another, so text/decorations cannot be independently repositioned.
        """
        root = ET.Element(
            "model",
            {
                "unit": "millimeter",
                "xml:lang": "en-US",
                "xmlns": CORE_NS,
                "xmlns:BambuStudio": (
                    BAMBU_NS
                ),
                "xmlns:p": PROD_NS,
                "requiredextensions": "p",
            },
        )

        ET.SubElement(
            root,
            "metadata",
            {
                "name": "Application"
            },
        ).text = (
            "Creality_Print "
            "V7.1.0.4414 Release"
        )

        ET.SubElement(
            root,
            "metadata",
            {
                "name": (
                    "BambuStudio:"
                    "3mfVersion"
                )
            },
        ).text = "1"

        resources = ET.SubElement(
            root,
            "resources",
        )

        compound = ET.SubElement(
            resources,
            "object",
            {
                "id": "2",
                "type": "model",
                "name": "DOBO Multicolor Product",
                "p:UUID": str(
                    uuid.uuid4()
                ),
            },
        )

        components = ET.SubElement(
            compound,
            "components",
        )

        for (
            _region,
            (
                internal_id,
                _unused_top_id,
                object_path,
            ),
        ) in zip(
            regions,
            _REGION_IDS,
        ):
            ET.SubElement(
                components,
                "component",
                {
                    "p:path": (
                        "/"
                        + object_path
                    ),
                    "objectid": str(
                        internal_id
                    ),
                    "p:UUID": str(
                        uuid.uuid4()
                    ),
                    "transform": (
                        "1 0 0 "
                        "0 1 0 "
                        "0 0 1 "
                        "0 0 0"
                    ),
                },
            )

        build = ET.SubElement(
            root,
            "build",
            {
                "p:UUID": str(
                    uuid.uuid4()
                )
            },
        )

        ET.SubElement(
            build,
            "item",
            {
                "objectid": "2",
                "p:UUID": str(
                    uuid.uuid4()
                ),
                "transform": (
                    transform
                ),
                "printable": "1",
            },
        )

        return ET.tostring(
            root,
            encoding="utf-8",
            xml_declaration=True,
        )

    def _model_settings(
        self,
        *,
        regions: tuple[
            ThreeMFRegion,
            ...
        ],
        transform: str,
    ) -> bytes:
        """
        One Creality object with three internal parts.

        Material assignment is stored per part:
          Body       -> extruder 1
          Text       -> extruder 2
          Decoration -> extruder 3
        """
        root = ET.Element(
            "config",
        )

        object_node = ET.SubElement(
            root,
            "object",
            {
                "id": "2"
            },
        )

        ET.SubElement(
            object_node,
            "metadata",
            {
                "key": "name",
                "value": (
                    "DOBO Multicolor Product"
                ),
            },
        )

        # Object-level fallback remains filament 1.
        # Actual material selection lives on each part below.
        ET.SubElement(
            object_node,
            "metadata",
            {
                "key": "extruder",
                "value": "1",
            },
        )

        for (
            region,
            (
                internal_id,
                _unused_top_id,
                _object_path,
            ),
        ) in zip(
            regions,
            _REGION_IDS,
        ):
            part = ET.SubElement(
                object_node,
                "part",
                {
                    "id": str(
                        internal_id
                    ),
                    "subtype": (
                        "normal_part"
                    ),
                },
            )

            ET.SubElement(
                part,
                "metadata",
                {
                    "key": "name",
                    "value": (
                        region.name
                    ),
                },
            )

            ET.SubElement(
                part,
                "metadata",
                {
                    "key": "matrix",
                    "value": (
                        "1 0 0 0 "
                        "0 1 0 0 "
                        "0 0 1 0 "
                        "0 0 0 1"
                    ),
                },
            )

            ET.SubElement(
                part,
                "metadata",
                {
                    "key": "extruder",
                    "value": str(
                        region.filament_slot
                    ),
                },
            )

            ET.SubElement(
                part,
                "mesh_stat",
                {
                    "edges_fixed": "0",
                    "degenerate_facets": "0",
                    "facets_removed": "0",
                    "facets_reversed": "0",
                    "backwards_edges": "0",
                },
            )

        plate = ET.SubElement(
            root,
            "plate",
        )

        ET.SubElement(
            plate,
            "metadata",
            {
                "key": "plater_id",
                "value": "1",
            },
        )

        instance = ET.SubElement(
            plate,
            "model_instance",
        )

        ET.SubElement(
            instance,
            "metadata",
            {
                "key": "object_id",
                "value": "2",
            },
        )

        ET.SubElement(
            instance,
            "metadata",
            {
                "key": "instance_id",
                "value": "0",
            },
        )

        assemble = ET.SubElement(
            root,
            "assemble",
        )

        ET.SubElement(
            assemble,
            "assemble_item",
            {
                "object_id": "2",
                "instance_id": "0",
                "transform": (
                    transform
                ),
                "offset": "0 0 0",
            },
        )

        return ET.tostring(
            root,
            encoding="utf-8",
            xml_declaration=True,
        )

    def _project_settings(
        self,
        *,
        regions: tuple[
            ThreeMFRegion,
            ...
        ],
    ) -> bytes:
        # Start from the complete known-good
        # Creality project profile.
        with zipfile.ZipFile(
            self._template_path,
            "r",
        ) as archive:
            settings = json.loads(
                archive.read(
                    "Metadata/"
                    "project_settings.config"
                )
            )

        colors = [
            region.color.upper()
            for region in regions
        ]

        # Change only product-level filament data.
        settings[
            "filament_colour"
        ] = colors

        settings[
            "filament_multi_colour"
        ] = colors

        settings[
            "default_filament_colour"
        ] = [
            ""
            for _ in regions
        ]

        # Preserve the real template's valid
        # Creality filament profile for all slots.
        base_profile = (
            settings.get(
                "default_filament_profile",
                [
                    (
                        "Hyper PLA "
                        "@Creality K1 Max "
                        "0.4 nozzle"
                    )
                ],
            )[0]
        )

        settings[
            "filament_settings_id"
        ] = [
            base_profile
            for _ in regions
        ]

        # Ensure vector-valued filament options
        # remain three-slot compatible where
        # the template already provides values.
        self._normalize_filament_vectors(
            settings,
            count=3,
        )

        return json.dumps(
            settings,
            indent=4,
        ).encode(
            "utf-8"
        )

    @staticmethod
    def _normalize_filament_vectors(
        settings: dict,
        *,
        count: int,
    ) -> None:
        # Do NOT invent unknown process settings.
        # Only replicate existing single-item
        # filament vectors where necessary.
        prefixes = (
            "filament_",
        )

        for key, value in list(
            settings.items()
        ):
            if not (
                isinstance(
                    value,
                    list,
                )
                and key.startswith(
                    prefixes
                )
            ):
                continue

            if len(value) == count:
                continue

            if len(value) == 1:
                settings[
                    key
                ] = (
                    value
                    * count
                )

    @staticmethod
    def _bed_transform(
        regions: tuple[
            ThreeMFRegion,
            ...
        ],
    ) -> str:
        # Compute one transform for all regions.
        # K1 Max template plate: 300 x 300 mm.
        min_x = min(
            float(
                region.shape.BoundingBox().xmin
            )
            for region in regions
        )
        max_x = max(
            float(
                region.shape.BoundingBox().xmax
            )
            for region in regions
        )

        min_y = min(
            float(
                region.shape.BoundingBox().ymin
            )
            for region in regions
        )
        max_y = max(
            float(
                region.shape.BoundingBox().ymax
            )
            for region in regions
        )

        min_z = min(
            float(
                region.shape.BoundingBox().zmin
            )
            for region in regions
        )

        width = (
            max_x
            - min_x
        )
        depth = (
            max_y
            - min_y
        )

        if (
            width > 295.0
            or depth > 295.0
        ):
            raise RuntimeError(
                "DOBO model exceeds the "
                "K1 Max template bed."
            )

        center_x = (
            min_x
            + max_x
        ) / 2.0

        center_y = (
            min_y
            + max_y
        ) / 2.0

        tx = (
            150.0
            - center_x
        )

        ty = (
            150.0
            - center_y
        )

        tz = (
            -min_z
        )

        return (
            "1 0 0 "
            "0 1 0 "
            "0 0 1 "
            f"{tx:.8f} "
            f"{ty:.8f} "
            f"{tz:.8f}"
        )

    @staticmethod
    def _model_relationships() -> bytes:
        root = ET.Element(
            "Relationships",
            {
                "xmlns": (
                    "http://schemas."
                    "openxmlformats.org/"
                    "package/2006/"
                    "relationships"
                )
            },
        )

        for index, (
            _internal_id,
            _top_id,
            object_path,
        ) in enumerate(
            _REGION_IDS,
            start=1,
        ):
            ET.SubElement(
                root,
                "Relationship",
                {
                    "Target": (
                        "/"
                        + object_path
                    ),
                    "Id": (
                        f"rel-{index}"
                    ),
                    "Type": (
                        "http://schemas."
                        "microsoft.com/"
                        "3dmanufacturing/"
                        "2013/01/3dmodel"
                    ),
                },
            )

        return ET.tostring(
            root,
            encoding="utf-8",
            xml_declaration=True,
        )

    @staticmethod
    def _number(
        value: float,
    ) -> str:
        return (
            f"{float(value):.8f}"
            .rstrip("0")
            .rstrip(".")
        )
