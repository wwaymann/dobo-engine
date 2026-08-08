from __future__ import annotations

from dataclasses import dataclass
import math
import os

import cadquery as cq

from .composition_spec import (
    ProductCompositionParser,
)
from .gallery_phase_4_hybrid import (
    _boolean_details,
    _hybridize,
    _organic_core,
    _primary_solid,
    _select_organic_face,
)
from .native_text_face import (
    NativeTextFaceDecorator,
)
from .native_svg_face import (
    NativeSvgFaceDecorator,
)
from .three_mf_exporter import (
    ThreeMFExporter,
    ThreeMFRegion,
)


OUTPUT_DIRECTORY = (
    "outputs/product_generators/"
    "surface_designer/phase_6_multicolor_3mf"
)


@dataclass(frozen=True, slots=True)
class MulticolorProductResult:
    final_shape: cq.Shape
    body_region: cq.Shape
    text_region: cq.Shape
    decoration_region: cq.Shape
    step_path: str
    three_mf_path: str
    region_count: int
    triangle_count: int
    volume_final: float
    volume_regions: float


def _stud_tool() -> cq.Shape:
    count = 10
    radius = 42.0
    z = 22.0

    tools: list[cq.Shape] = []

    for index in range(count):
        angle = (
            2.0
            * math.pi
            * index
            / count
        )

        center = cq.Vector(
            radius * math.cos(angle),
            radius * math.sin(angle),
            z,
        )

        tools.append(
            cq.Solid.makeSphere(
                3.2,
                center,
            )
        )

    tool = tools[0]

    for item in tools[1:]:
        tool = tool.fuse(
            item,
            tol=0.005,
        ).clean()

    if not tool.isValid():
        raise RuntimeError(
            "Decoration zone tool is invalid."
        )

    return tool


def _apply_studs(
    shape: cq.Shape,
    studs: cq.Shape,
) -> cq.Shape:
    result = shape.fuse(
        studs,
        tol=0.005,
    ).clean()

    return _primary_solid(
        result
    )


def _partition_zone(
    final_shape: cq.Shape,
    tool: cq.Shape,
) -> cq.Shape:
    zone = final_shape.intersect(
        tool,
        tol=0.005,
    ).clean()

    solids = tuple(
        zone.Solids()
    )

    if not solids:
        raise RuntimeError(
            "Multicolor zone intersection "
            "produced no solid."
        )

    if len(solids) == 1:
        return solids[0].clean()

    merged = solids[0]

    for solid in solids[1:]:
        merged = merged.fuse(
            solid,
            tol=0.005,
        ).clean()

    if not merged.isValid():
        raise RuntimeError(
            "Merged multicolor zone is invalid."
        )

    return merged.clean()


def build_multicolor_product(
    specification_path,
) -> MulticolorProductResult:
    parser = ProductCompositionParser()

    specification = parser.parse_file(
        specification_path
    )

    if specification.text is None:
        raise ValueError(
            "Phase 6 requires a text region."
        )

    if specification.svg is None:
        raise ValueError(
            "Phase 6 requires the validated "
            "SVG operation."
        )

    # ---------------------------------------------------------
    # 1. Base organic geometry
    # ---------------------------------------------------------

    model = _organic_core()

    # ---------------------------------------------------------
    # 2. Existing validated primitive composition
    # ---------------------------------------------------------

    if specification.primitives:
        model = _hybridize(
            model
        )

    # ---------------------------------------------------------
    # 3. Existing validated subtractive booleans
    # ---------------------------------------------------------

    if specification.booleans:
        model = _boolean_details(
            model
        )

    # ---------------------------------------------------------
    # 4. Geometric decoration
    #
    # Keep the original tool because it will become its own
    # material / filament region later.
    # ---------------------------------------------------------

    studs = _stud_tool()

    if specification.geometric_decoration:
        model = _apply_studs(
            model,
            studs,
        )

    # ---------------------------------------------------------
    # 5. Native text
    #
    # We retain text_result.tool so the embossed text volume
    # can later be isolated as Filament 2.
    # ---------------------------------------------------------

    text_spec = specification.text

    text_face = _select_organic_face(
        model
    )

    text_decorator = (
        NativeTextFaceDecorator()
    )

    text_result = (
        text_decorator.decorate(
            base_shape=model,
            target_face=text_face,
            text_value=text_spec.content,
            size=text_spec.size,
            depth=text_spec.depth,
            mode=text_spec.mode,
            font=text_spec.font,
            kind=text_spec.kind,
            width_fraction=(
                text_spec.width_fraction
            ),
            height_fraction=(
                text_spec.height_fraction
            ),
            u_center=text_spec.u_center,
            v_center=text_spec.v_center,
        )
    )

    model = _primary_solid(
        text_result.shape
    )

    text_tool = (
        text_result.tool.clean()
    )

    # ---------------------------------------------------------
    # 6. Native SVG
    #
    # The current product uses DEBOSS.
    # Therefore SVG does not create a separate material volume.
    # It remains a recess in the Body material.
    # ---------------------------------------------------------

    svg_spec = specification.svg

    svg_face = _select_organic_face(
        model
    )

    svg_decorator = (
        NativeSvgFaceDecorator()
    )

    svg_result = (
        svg_decorator.decorate(
            base_shape=model,
            target_face=svg_face,
            svg=svg_spec.svg,
            mode=svg_spec.mode,
            depth=svg_spec.depth,
            width_fraction=(
                svg_spec.width_fraction
            ),
            height_fraction=(
                svg_spec.height_fraction
            ),
            u_center=svg_spec.u_center,
            v_center=svg_spec.v_center,
            document_id=(
                svg_spec.document_id
            ),
        )
    )

    final_shape = _primary_solid(
        svg_result.shape
    )

    if not final_shape.isValid():
        raise RuntimeError(
            "Phase 6 final CAD body is invalid."
        )

    if len(final_shape.Solids()) != 1:
        raise RuntimeError(
            "Phase 6 final CAD body must "
            "contain one solid."
        )

    # ---------------------------------------------------------
    # 7. Material partition
    #
    # Text and decoration become separate physical volumes.
    # Body is the remainder.
    # ---------------------------------------------------------

    text_region = _partition_zone(
        final_shape,
        text_tool,
    )

    decoration_region = (
        _partition_zone(
            final_shape,
            studs,
        )
    )

    body_region = (
        final_shape
        .cut(
            text_region,
            tol=0.005,
        )
        .cut(
            decoration_region,
            tol=0.005,
        )
        .clean()
    )

    body_region = _primary_solid(
        body_region
    )

    if not body_region.isValid():
        raise RuntimeError(
            "Body material region is invalid."
        )

    if not text_region.isValid():
        raise RuntimeError(
            "Text material region is invalid."
        )

    if not decoration_region.isValid():
        raise RuntimeError(
            "Decoration material region "
            "is invalid."
        )

    # ---------------------------------------------------------
    # 8. Volume conservation
    #
    # The three material regions together must reproduce
    # the original final CAD volume.
    # ---------------------------------------------------------

    final_volume = float(
        final_shape.Volume()
    )

    region_volume = sum(
        float(
            shape.Volume()
        )
        for shape in (
            body_region,
            text_region,
            decoration_region,
        )
    )

    tolerance = max(
        1.0,
        final_volume * 2.0e-4,
    )

    volume_error = abs(
        region_volume
        - final_volume
    )

    if volume_error > tolerance:
        raise RuntimeError(
            "Multicolor partition does not "
            "conserve model volume: "
            f"final={final_volume}, "
            f"regions={region_volume}, "
            f"error={volume_error}, "
            f"tolerance={tolerance}."
        )

    # ---------------------------------------------------------
    # 9. Reference STEP export
    # ---------------------------------------------------------

    os.makedirs(
        OUTPUT_DIRECTORY,
        exist_ok=True,
    )

    step_path = os.path.join(
        OUTPUT_DIRECTORY,
        "dobo_multicolor_reference.step",
    )

    cq.exporters.export(
        final_shape,
        step_path,
    )

    if not os.path.isfile(
        step_path
    ):
        raise RuntimeError(
            "Reference STEP export failed."
        )

    # ---------------------------------------------------------
    # 10. Multicolor 3MF export
    #
    # Filament assignments:
    #
    # Body       -> Filament 1
    # Text       -> Filament 2
    # Decoration -> Filament 3
    # ---------------------------------------------------------

    three_mf_path = os.path.join(
        OUTPUT_DIRECTORY,
        "dobo_multicolor_product.3mf",
    )

    export = (
        ThreeMFExporter().export(
            regions=(
                ThreeMFRegion(
                    name="Body",
                    shape=body_region,
                    color="#EAEAEA",
                    filament_slot=1,
                ),
                ThreeMFRegion(
                    name="Text",
                    shape=text_region,
                    color="#6D3BFF",
                    filament_slot=2,
                ),
                ThreeMFRegion(
                    name="Decoration",
                    shape=(
                        decoration_region
                    ),
                    color="#19A974",
                    filament_slot=3,
                ),
            ),
            path=three_mf_path,
        )
    )

    if export.region_object_count != 3:
        raise RuntimeError(
            "Expected exactly three "
            "3MF material regions."
        )

    if export.filament_slot_count != 3:
        raise RuntimeError(
            "Expected exactly three "
            "3MF filament assignments."
        )

    # ---------------------------------------------------------
    # 11. Final result
    # ---------------------------------------------------------

    result = MulticolorProductResult(
        final_shape=final_shape,
        body_region=body_region,
        text_region=text_region,
        decoration_region=(
            decoration_region
        ),
        step_path=step_path,
        three_mf_path=three_mf_path,

        # IMPORTANT:
        # object_count is 4 because the 3MF contains
        # 3 region objects + 1 assembly object.
        #
        # region_count must remain 3.
        region_count=(
            export.region_object_count
        ),

        triangle_count=(
            export.triangle_count
        ),
        volume_final=final_volume,
        volume_regions=region_volume,
    )

    return result