from __future__ import annotations

from dataclasses import dataclass
import os
import cadquery as cq

from .composition_spec import ProductCompositionSpec
from .contracts import SurfaceDesignMode
from .designer import SurfaceDesigner
from .gallery_phase_4_hybrid import (
    _boolean_details,
    _geometric_decoration,
    _hybridize,
    _organic_core,
    _primary_solid,
    _select_organic_face,
)

OUTPUT_DIRECTORY = "outputs/product_generators/surface_designer/phase_5_json_composition"


@dataclass(frozen=True, slots=True)
class ProductCompositionResult:
    shape: cq.Shape
    path: str
    solids: int
    faces: int
    volume_initial: float
    volume_final: float
    operations: tuple[str, ...]

    def validate(self) -> None:
        if not self.shape.isValid():
            raise RuntimeError("JSON product composition produced invalid geometry.")
        if self.solids != 1:
            raise RuntimeError("JSON product composition must produce one solid.")
        if self.volume_initial <= 0.0 or self.volume_final <= 0.0:
            raise RuntimeError("JSON product composition volumes must be positive.")


class JsonProductComposer:
    """Structured orchestration over already validated DOBO capabilities."""

    def __init__(self) -> None:
        self._designer = SurfaceDesigner()

    def compose(self, specification: ProductCompositionSpec) -> ProductCompositionResult:
        specification.validate()
        operations: list[str] = []

        model = _organic_core()
        initial_volume = float(model.Volume())
        operations.append("body:phase4_organic")

        if specification.primitives:
            model = _hybridize(model)
            operations.append("primitives")

        if specification.booleans:
            model = _boolean_details(model)
            operations.append("booleans")

        if specification.geometric_decoration:
            model = _geometric_decoration(model)
            operations.append("geometric_decoration")

        if specification.text is not None:
            text = specification.text
            result = self._designer.add_text(
                base_shape=model,
                target_face=_select_organic_face(model),
                text=text.content,
                size=text.size,
                mode=self._mode(text.mode),
                depth=text.depth,
                font=text.font,
                kind=text.kind,
                width_fraction=text.width_fraction,
                height_fraction=text.height_fraction,
                u_center=text.u_center,
                v_center=text.v_center,
            )
            model = _primary_solid(result.shape)
            operations.append(f"text:{text.mode}")

        if specification.svg is not None:
            svg = specification.svg
            result = self._designer.add_svg(
                base_shape=model,
                target_face=_select_organic_face(model),
                svg=svg.svg,
                mode=self._mode(svg.mode),
                depth=svg.depth,
                width_fraction=svg.width_fraction,
                height_fraction=svg.height_fraction,
                u_center=svg.u_center,
                v_center=svg.v_center,
                document_id=svg.document_id,
            )
            model = _primary_solid(result.shape)
            operations.append(f"svg:{svg.mode}")

        model = _primary_solid(model)
        if not model.isValid() or len(model.Solids()) != 1:
            raise RuntimeError("Final JSON-composed product must be one valid solid.")

        os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)
        path = os.path.join(OUTPUT_DIRECTORY, specification.output_filename)
        cq.exporters.export(model, path)
        if not os.path.isfile(path):
            raise RuntimeError("STEP export failed.")

        result = ProductCompositionResult(
            shape=model,
            path=path,
            solids=len(model.Solids()),
            faces=len(model.Faces()),
            volume_initial=initial_volume,
            volume_final=float(model.Volume()),
            operations=tuple(operations),
        )
        result.validate()
        return result

    @staticmethod
    def _mode(value: str) -> SurfaceDesignMode:
        if value == "emboss":
            return SurfaceDesignMode.EMBOSS
        if value == "deboss":
            return SurfaceDesignMode.DEBOSS
        raise ValueError(f"Unsupported surface mode '{value}'.")
