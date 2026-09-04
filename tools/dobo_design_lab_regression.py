from __future__ import annotations

"""Physical acceptance for the end-user DOBO Design Lab."""

import json
from pathlib import Path

import cadquery as cq

from dobo_design_lab import (
    DESIGN_CATALOG,
    DESIGN_LAB_VERSION,
    FONT_FAMILIES,
    FONT_STYLES,
    HTML,
    SHAPE_FAMILIES,
    _design_program,
    generate_design,
)
from product_generators.design_interpreter.native_profiled_cad_adapter import (
    _resolved_font_contract,
)


OUTPUT = Path("outputs-ci/design-lab")


def _font_signature(font_key: str) -> tuple[float, float, int]:
    contract = _resolved_font_contract(FONT_STYLES[font_key]["tag"])
    values = [
        value
        for value in cq.Workplane("XY").text(
            "WALTER",
            18.0,
            1.0,
            combine=False,
            font=contract["font"],
            kind=contract["kind"],
            fontPath=contract["font_path"],
            halign="center",
            valign="center",
        ).vals()
        if isinstance(value, cq.Shape)
    ]
    if not values:
        raise RuntimeError(f"Font {font_key} produced no CAD glyphs.")
    volume = sum(float(value.Volume()) for value in values)
    boxes = [value.BoundingBox() for value in values]
    width = max(box.xmax for box in boxes) - min(box.xmin for box in boxes)
    return round(volume, 3), round(width, 3), len(values)


def run() -> dict:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    family_counts = {
        family["id"]: sum(item["family"] == family["id"] for item in DESIGN_CATALOG)
        for family in SHAPE_FAMILIES
    }
    interface_assertions = {
        "full_catalog_visible_through_families": len(DESIGN_CATALOG) == 30,
        "shape_family_count": len(SHAPE_FAMILIES) >= 6,
        "families_have_choices": all(count >= 3 for count in family_counts.values()),
        "three_font_families": len(FONT_FAMILIES) == 3,
        "multiline_ui": 'id="lineCounts"' in HTML and 'id="lineInputs"' in HTML,
        "shape_family_modal": 'id="shapeModal"' in HTML,
        "multicolor_preview": (
            "loadColoredParts" in HTML
            and "region_stls" in HTML
            and "ThreeMFLoader" in HTML
        ),
    }

    font_records = []
    signatures = {}
    for font_key, contract in FONT_STYLES.items():
        program, item, lines, position, size, relief = _design_program(
            {
                "shape": "soft_low",
                "text_lines": ["WALTER"],
                "line_count": 1,
                "position": "center",
                "size": "medium",
                "relief": "raised",
                "font": font_key,
            }
        )
        resolved = _resolved_font_contract(contract["tag"])
        signature = _font_signature(font_key)
        signatures[font_key] = signature
        assertions = {
            "font_tag": contract["tag"] in program.body.style_tags,
            "shape_tag": item["variant"] in program.body.style_tags,
            "literal_prompt": 'Texto exacto "WALTER"' in program.source.prompt,
            "single_line": lines == ("WALTER",),
            "position": position == "center",
            "size": size == "medium",
            "relief": relief == "raised",
            "font_file": Path(resolved["font_path"]).is_file(),
        }
        font_records.append(
            {
                "font": font_key,
                "signature": signature,
                "font_path": resolved["font_path"],
                "status": "PASS" if all(assertions.values()) else "FAIL",
                "assertions": assertions,
            }
        )

    distinct_font_signatures = len(set(signatures.values()))
    interface_assertions["physically_distinct_fonts"] = distinct_font_signatures == len(FONT_STYLES)

    cases = (
        {
            "name": "deep_recess_editorial_bottom",
            "spec": {
                "shape": "pedestal",
                "text_lines": ["PLANTA UNA IDEA"],
                "line_count": 1,
                "position": "bottom",
                "size": "large",
                "relief": "recessed",
                "font": "editorial",
                "body_color": "#E8E0D4",
                "text_color": "#262626",
                "accent_color": "#BDA37A",
            },
        },
        {
            "name": "multiline_classic_center",
            "spec": {
                "shape": "wide_bowl",
                "text_lines": ["PLANTA", "UNA", "IDEA"],
                "line_count": 3,
                "position": "center",
                "size": "medium",
                "relief": "raised",
                "font": "classic",
                "body_color": "#E4DED2",
                "text_color": "#27221E",
                "accent_color": "#A78E6C",
            },
        },
        {
            "name": "wrap_tech_large",
            "spec": {
                "shape": "capsule",
                "text_lines": ["DOBO"],
                "line_count": 1,
                "position": "wrap",
                "size": "large",
                "relief": "raised",
                "font": "tech",
                "body_color": "#E6E6E6",
                "text_color": "#222222",
                "accent_color": "#B79A6B",
            },
        },
        {
            "name": "size_small",
            "spec": {
                "shape": "soft_taper",
                "text_lines": ["WALTER"],
                "line_count": 1,
                "position": "center",
                "size": "small",
                "relief": "raised",
                "font": "strong",
                "body_color": "#E7E1D7",
                "text_color": "#222222",
                "accent_color": "#BCA177",
            },
        },
        {
            "name": "size_xl",
            "spec": {
                "shape": "soft_taper",
                "text_lines": ["WALTER"],
                "line_count": 1,
                "position": "center",
                "size": "xl",
                "relief": "raised",
                "font": "strong",
                "body_color": "#E7E1D7",
                "text_color": "#222222",
                "accent_color": "#BCA177",
            },
        },
    )

    physical = []
    effective_by_name: dict[str, float] = {}
    for case in cases:
        try:
            result = generate_design(case["spec"])
            validation = result.get("validation", {})
            text = result.get("text", {})
            multicolor = result.get("multicolor", {})
            effective = tuple(float(v) for v in text.get("effective_line_heights_mm", []))
            if effective:
                effective_by_name[case["name"]] = effective[0]

            assertions = {
                "watertight": bool(validation.get("watertight")),
                "winding": bool(validation.get("winding_consistent")),
                "one_component": int(validation.get("component_count", 0)) == 1,
                "native_text": bool(text),
                "compound_multicolor": bool(multicolor.get("compound_object")),
                "three_materials": tuple(multicolor.get("filament_slots", [])) == (1, 2, 3),
                "preview_parts": (
                    len(multicolor.get("preview_parts", [])) == 3
                    and all(
                        Path(str(part.get("path", ""))).is_file()
                        for part in multicolor.get("preview_parts", [])
                        if isinstance(part, dict)
                    )
                ),
                "saucer": bool(result.get("artifacts", {}).get("saucer")),
                "effective_size_recorded": bool(effective),
            }

            if case["spec"]["relief"] == "recessed":
                assertions["deep_recess"] = float(
                    multicolor.get("visible_recess_depth_mm", 0.0)
                ) >= 0.50
                assertions["deep_inlay"] = (
                    multicolor.get("deboss_inlay_mode") == "deep_extruded_insert"
                )
                assertions["font"] = text.get("font_style") == "font_editorial"

            if case["spec"]["line_count"] == 3:
                assertions["multiline"] = int(text.get("line_count", 0)) == 3
                assertions["font"] = text.get("font_style") == "font_classic"

            if case["spec"]["position"] == "wrap":
                assertions["wrap"] = text.get("text_layout") == "wrap"
                assertions["wrap_target"] = float(text.get("wrap_target_fraction", 0.0)) >= 0.95
                assertions["wrap_repeats"] = int(text.get("applied_glyph_count", 0)) > len("DOBO")
                assertions["font"] = text.get("font_style") == "font_tech"

            physical.append(
                {
                    "name": case["name"],
                    "status": "PASS" if all(assertions.values()) else "FAIL",
                    "assertions": assertions,
                    "effective_line_heights_mm": effective,
                    "trace": result.get("trace"),
                    "artifacts": result.get("artifacts"),
                }
            )
        except Exception as error:
            physical.append(
                {
                    "name": case["name"],
                    "status": "ERROR",
                    "error_type": type(error).__name__,
                    "error": str(error),
                }
            )

    small = effective_by_name.get("size_small", 0.0)
    xl = effective_by_name.get("size_xl", 0.0)
    interface_assertions["text_size_changes_geometry"] = small > 0.0 and xl >= 1.50 * small

    interface_status = "PASS" if all(interface_assertions.values()) else "FAIL"
    summary = {
        "schema": "dobo.design_lab_regression.3",
        "version": DESIGN_LAB_VERSION,
        "catalog_count": len(DESIGN_CATALOG),
        "shape_families": family_counts,
        "font_family_count": len(FONT_FAMILIES),
        "font_style_count": len(FONT_STYLES),
        "distinct_font_signatures": distinct_font_signatures,
        "interface": {
            "status": interface_status,
            "assertions": interface_assertions,
        },
        "fonts": font_records,
        "physical": physical,
        "pass": (
            int(interface_status == "PASS")
            + sum(item["status"] == "PASS" for item in font_records)
            + sum(item["status"] == "PASS" for item in physical)
        ),
        "fail": (
            int(interface_status != "PASS")
            + sum(item["status"] != "PASS" for item in font_records)
            + sum(item["status"] != "PASS" for item in physical)
        ),
    }

    target = OUTPUT / "DOBO_DESIGN_LAB_REGRESSION.json"
    target.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    if summary["fail"]:
        failed = []
        if interface_status != "PASS":
            failed.append("interface")
        failed.extend(item["font"] for item in font_records if item["status"] != "PASS")
        failed.extend(item["name"] for item in physical if item["status"] != "PASS")
        raise RuntimeError("DOBO Design Lab regression failed: " + ", ".join(failed))
    return summary


if __name__ == "__main__":
    run()
