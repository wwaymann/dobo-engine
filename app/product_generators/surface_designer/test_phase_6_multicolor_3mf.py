from __future__ import annotations

from pathlib import Path
import json
import os
import zipfile
from xml.etree import ElementTree as ET

from .multicolor_product import (
    build_multicolor_product,
)


SPEC_PATH = (
    Path(__file__).resolve().parent
    / "phase_5_product_spec.json"
)

CORE_NS = (
    "http://schemas.microsoft.com/"
    "3dmanufacturing/core/2015/02"
)


def main() -> None:
    result = build_multicolor_product(
        SPEC_PATH
    )

    if result.region_count != 3:
        raise RuntimeError(
            "Expected 3 material regions."
        )

    with zipfile.ZipFile(
        result.three_mf_path,
        "r",
    ) as archive:
        top_model = ET.fromstring(
            archive.read(
                "3D/3dmodel.model"
            )
        )

        model_settings = ET.fromstring(
            archive.read(
                "Metadata/model_settings.config"
            )
        )

        project_settings = json.loads(
            archive.read(
                "Metadata/project_settings.config"
            )
        )

    ns = {
        "m": CORE_NS,
    }

    objects = top_model.findall(
        ".//m:resources/m:object",
        ns,
    )

    build_items = top_model.findall(
        ".//m:build/m:item",
        ns,
    )

    components = top_model.findall(
        ".//m:components/m:component",
        ns,
    )

    # Critical regression:
    # ONE printable object only.
    if len(objects) != 1:
        raise RuntimeError(
            "Creality project must contain "
            f"1 top-level compound object, got {len(objects)}."
        )

    if len(build_items) != 1:
        raise RuntimeError(
            "Creality project must contain "
            f"1 build item, got {len(build_items)}."
        )

    if len(components) != 3:
        raise RuntimeError(
            "Compound object must contain "
            f"3 material components, got {len(components)}."
        )

    build_transform = build_items[0].get(
        "transform"
    )

    object_nodes = model_settings.findall(
        "object"
    )

    if len(object_nodes) != 1:
        raise RuntimeError(
            "model_settings must contain "
            "one compound object."
        )

    parts = object_nodes[0].findall(
        "part"
    )

    if len(parts) != 3:
        raise RuntimeError(
            "Compound model_settings object "
            f"must contain 3 parts, got {len(parts)}."
        )

    part_slots = []

    for part in parts:
        slot = None

        for metadata in part.findall(
            "metadata"
        ):
            if metadata.get(
                "key"
            ) == "extruder":
                slot = int(
                    metadata.get(
                        "value"
                    )
                )

        part_slots.append(
            slot
        )

    if part_slots != [
        1,
        2,
        3,
    ]:
        raise RuntimeError(
            "Wrong part filament assignments: "
            f"{part_slots}"
        )

    model_instances = model_settings.findall(
        ".//plate/model_instance"
    )

    if len(model_instances) != 1:
        raise RuntimeError(
            "Plate must contain one model instance."
        )

    assemble_items = model_settings.findall(
        ".//assemble/assemble_item"
    )

    if len(assemble_items) != 1:
        raise RuntimeError(
            "Assemble section must contain "
            "one compound object."
        )

    if (
        assemble_items[0].get(
            "transform"
        )
        != build_transform
    ):
        raise RuntimeError(
            "Build and assemble transforms disagree."
        )

    expected_colors = [
        "#EAEAEA",
        "#6D3BFF",
        "#19A974",
    ]

    if project_settings.get(
        "filament_colour"
    ) != expected_colors:
        raise RuntimeError(
            "Filament colors were not preserved."
        )

    print(
        "DOBO Surface Designer - Phase 6.5\n"
        "Creality Compound Object Fix\n"
        "-----------------------------------"
    )
    print(
        "top-level printable objects",
        len(objects),
        "OK",
    )
    print(
        "build items",
        len(build_items),
        "OK",
    )
    print(
        "internal material parts",
        len(parts),
        "OK",
    )
    print(
        "part filaments",
        part_slots,
        "OK",
    )
    print(
        "shared object transform",
        build_transform,
        "OK",
    )
    print(
        "colors",
        expected_colors,
        "OK",
    )
    print(
        "3MF",
        result.three_mf_path,
        os.path.getsize(
            result.three_mf_path
        ),
        "bytes",
    )
    print(
        "-----------------------------------\n"
        "Phase 6.5 Creality Compound: Valid OK"
    )


if __name__ == "__main__":
    main()
