from __future__ import annotations

from .phase_5_design_matrix import (
    DesignMatrixCase,
    _botanical,
    _cat,
    _feature,
    _geometric,
    _program,
    _relation,
)


def _helical():
    features = [
        _feature(
            f"flow_{index + 1}",
            "flow_ridge",
            "slit",
            "recessed",
            region=region,
            horizontal=horizontal,
            vertical=0.36 + 0.10 * index,
            width=0.20,
            height=0.055,
            depth=1.1,
            roll=-28.0 + 18.0 * index,
        )
        for index, (region, horizontal) in enumerate(
            (("front", -0.45), ("right", -0.1), ("back", 0.15), ("left", 0.4))
        )
    ]
    relations = [
        _relation("repeated_from", f"flow_{index}", f"flow_{index + 1}")
        for index in range(1, 4)
    ]
    return _program(
        "matrix_helical_sculptural_planter",
        "Maceta escultórica orgánica de cuerpo torsionado y flujo ascendente.",
        family="organic",
        height=122.0,
        width=108.0,
        depth=102.0,
        opening_shape="elliptical",
        opening_width=0.50,
        opening_depth=0.48,
        style_tags=["organic", "sculptural", "twisted"],
        features=features,
        relations=relations,
    )


def morphogenesis_matrix() -> tuple[DesignMatrixCase, ...]:
    return (
        DesignMatrixCase(
            "bilateral",
            "Bilateral creature",
            "character",
            "childlike",
            "pointed",
            _cat(),
        ),
        DesignMatrixCase(
            "radial",
            "Radial botanical",
            "organic",
            "organic",
            "leaf",
            _botanical(),
        ),
        DesignMatrixCase(
            "helical",
            "Helical sculptural",
            "organic",
            "organic",
            "relief",
            _helical(),
        ),
        DesignMatrixCase(
            "faceted",
            "Axial faceted",
            "faceted_proxy",
            "geometric",
            "relief",
            _geometric(),
        ),
    )
