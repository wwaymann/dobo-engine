from __future__ import annotations

"""Physical acceptance for the end-user DOBO Design Lab."""

import json
from pathlib import Path

from dobo_design_lab import (
    DESIGN_CATALOG,
    DESIGN_LAB_VERSION,
    FONT_STYLES,
    _design_program,
    generate_design,
)


OUTPUT = Path("outputs-ci/design-lab")


def run() -> dict:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    if len(DESIGN_CATALOG) < 10:
        raise RuntimeError("Design Lab must expose a useful visual catalog.")

    static = []
    for font_key, contract in FONT_STYLES.items():
        program, item, text, position, size, relief = _design_program(
            {
                "shape": "soft_low",
                "text": "WALTER",
                "position": "center",
                "size": "medium",
                "relief": "raised",
                "font": font_key,
            }
        )
        assertions = {
            "font_tag": contract["tag"] in program.body.style_tags,
            "shape_tag": item["variant"] in program.body.style_tags,
            "literal_prompt": 'Texto exacto "WALTER"' in program.source.prompt,
            "position": position == "center",
            "size": size == "medium",
            "relief": relief == "raised",
            "text": text == "WALTER",
        }
        static.append(
            {
                "font": font_key,
                "status": "PASS" if all(assertions.values()) else "FAIL",
                "assertions": assertions,
            }
        )

    cases = (
        {
            "name": "deep_recess_editorial_bottom",
            "spec": {
                "shape": "pedestal",
                "text": "PLANTA UNA IDEA",
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
            "name": "wrap_tech_large",
            "spec": {
                "shape": "capsule",
                "text": "DOBO",
                "position": "wrap",
                "size": "large",
                "relief": "raised",
                "font": "tech",
                "body_color": "#E6E6E6",
                "text_color": "#222222",
                "accent_color": "#B79A6B",
            },
        },
    )

    physical = []
    for case in cases:
        try:
            result = generate_design(case["spec"])
            validation = result.get("validation", {})
            text = result.get("text", {})
            multicolor = result.get("multicolor", {})
            assertions = {
                "watertight": bool(validation.get("watertight")),
                "winding": bool(validation.get("winding_consistent")),
                "one_component": int(validation.get("component_count", 0)) == 1,
                "native_text": bool(text),
                "compound_multicolor": bool(multicolor.get("compound_object")),
                "three_materials": tuple(multicolor.get("filament_slots", [])) == (1, 2, 3),
                "saucer": bool(result.get("artifacts", {}).get("saucer")),
            }
            if case["spec"]["relief"] == "recessed":
                assertions["deep_recess"] = float(
                    multicolor.get("visible_recess_depth_mm", 0.0)
                ) >= 0.30
                assertions["deep_inlay"] = (
                    multicolor.get("deboss_inlay_mode") == "deep_extruded_insert"
                )
                assertions["font"] = text.get("font_style") == "font_editorial"
            if case["spec"]["position"] == "wrap":
                assertions["wrap"] = text.get("text_layout") == "wrap"
                assertions["font"] = text.get("font_style") == "font_tech"

            physical.append(
                {
                    "name": case["name"],
                    "status": "PASS" if all(assertions.values()) else "FAIL",
                    "assertions": assertions,
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

    summary = {
        "schema": "dobo.design_lab_regression.1",
        "version": DESIGN_LAB_VERSION,
        "catalog_count": len(DESIGN_CATALOG),
        "static_count": len(static),
        "physical_count": len(physical),
        "pass": sum(item["status"] == "PASS" for item in static + physical),
        "fail": sum(item["status"] != "PASS" for item in static + physical),
        "static": static,
        "physical": physical,
    }
    target = OUTPUT / "DOBO_DESIGN_LAB_REGRESSION.json"
    target.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if summary["fail"]:
        failed = [
            item.get("name", item.get("font"))
            for item in static + physical
            if item["status"] != "PASS"
        ]
        raise RuntimeError("DOBO Design Lab regression failed: " + ", ".join(failed))
    return summary


if __name__ == "__main__":
    run()
