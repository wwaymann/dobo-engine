from __future__ import annotations

import cadquery as cq

from product_generators.surface_features.surface_feature_api import (
    SurfaceFeatureAPI,
    SurfaceFeatureMode,
)

from .contracts import (
    SurfaceDesignMode,
    SurfaceDesignResult,
)
from .native_svg_face import (
    NativeSvgFaceDecorator,
)
from .native_text import (
    NativeSurfaceTextBuilder,
)
from .native_text_face import (
    NativeTextFaceDecorator,
)
from .svg_factory import (
    SurfaceDesignerSvgFactory,
)


class SurfaceDesigner:
    """
    High-level product-facing surface design API.

    Two compatible routes are supported by the same public methods:

    1. Existing procedural route:
         surface=<SurfaceSampler>

       Kept intact for current DOBO products and explicit mapping.

    2. Universal native face route:
         target_face=<cq.Face>

       Uses OCC faceOn() + offset() and works on validated analytical
       and freeform faces: cone, sphere, torus and organic lofts.

    No new architecture layer is introduced.
    """

    def __init__(self) -> None:
        self._surface_features = SurfaceFeatureAPI()
        self._svg_factory = SurfaceDesignerSvgFactory()
        self._native_text = NativeSurfaceTextBuilder()

        self._native_face_text = (
            NativeTextFaceDecorator()
        )
        self._native_face_svg = (
            NativeSvgFaceDecorator()
        )

    def add_svg(
        self,
        *,
        base_shape: cq.Shape,
        svg: str,
        mode: SurfaceDesignMode,
        depth: float,
        surface=None,
        target_face: cq.Face | None = None,
        u_offset: float = 0.0,
        v_offset: float = 0.0,
        scale_u: float = 1.0,
        scale_v: float = 1.0,
        document_id: str = "surface_designer_svg",
        width_fraction: float = 0.28,
        height_fraction: float = 0.22,
        u_center: float = 0.5,
        v_center: float = 0.5,
    ) -> SurfaceDesignResult:
        self._validate_mode(mode)

        if target_face is not None:
            result = self._native_face_svg.decorate(
                base_shape=base_shape,
                target_face=target_face,
                svg=svg,
                mode=mode.value,
                depth=float(depth),
                width_fraction=float(width_fraction),
                height_fraction=float(height_fraction),
                u_center=float(u_center),
                v_center=float(v_center),
                document_id=document_id,
            )

            output = SurfaceDesignResult(
                shape=result.shape,
                operation=mode.value,
                source_kind="svg",
                metadata={
                    "document_id": document_id,
                    "boolean_count": 1,
                    "approximation": False,
                    "surface_route": (
                        "cadquery_native_faceOn"
                    ),
                    "mapped_face_count": len(
                        result.mapped_faces.Faces()
                    ),
                    "tool_solid_count": len(
                        result.tool.Solids()
                    ),
                    "base_volume": (
                        result.base_volume
                    ),
                    "final_volume": (
                        result.final_volume
                    ),
                },
            )
            output.validate()
            return output

        if surface is None:
            raise ValueError(
                "add_svg requires either target_face "
                "or surface."
            )

        result = self._surface_features.apply_svg(
            svg=svg,
            base_shape=base_shape,
            surface=surface,
            mode=self._map_mode(mode),
            depth=float(depth),
            document_id=document_id,
            u_offset=float(u_offset),
            v_offset=float(v_offset),
            scale_u=float(scale_u),
            scale_v=float(scale_v),
        )

        metadata = {
            "document_id": document_id,
            "loop_count": result.loop_count,
            "boolean_count": result.boolean_count,
            "surface_route": (
                "dobo_surface_mapping"
            ),
        }

        # Preserve compatibility with the fragment-normalization
        # result used by the validated Phase 3.4 fix when present.
        if hasattr(
            result,
            "discarded_fragment_count",
        ):
            metadata[
                "discarded_fragment_count"
            ] = result.discarded_fragment_count

        if hasattr(
            result,
            "discarded_fragment_volume",
        ):
            metadata[
                "discarded_fragment_volume"
            ] = result.discarded_fragment_volume

        output = SurfaceDesignResult(
            shape=result.shape,
            operation=mode.value,
            source_kind="svg",
            metadata=metadata,
        )
        output.validate()
        return output

    def add_badge(
        self,
        *,
        base_shape: cq.Shape,
        width: float,
        height: float,
        kind: str,
        mode: SurfaceDesignMode,
        depth: float,
        surface=None,
        target_face: cq.Face | None = None,
        u_offset: float = 0.0,
        v_offset: float = 0.0,
        width_fraction: float = 0.28,
        height_fraction: float = 0.22,
        u_center: float = 0.5,
        v_center: float = 0.5,
    ) -> SurfaceDesignResult:
        svg = self._svg_factory.badge(
            width=width,
            height=height,
            kind=kind,
        )

        return self.add_svg(
            base_shape=base_shape,
            surface=surface,
            target_face=target_face,
            svg=svg,
            mode=mode,
            depth=depth,
            u_offset=u_offset,
            v_offset=v_offset,
            width_fraction=width_fraction,
            height_fraction=height_fraction,
            u_center=u_center,
            v_center=v_center,
            document_id=f"badge_{kind}",
        )

    def add_frame(
        self,
        *,
        base_shape: cq.Shape,
        width: float,
        height: float,
        border: float,
        mode: SurfaceDesignMode,
        depth: float,
        surface=None,
        target_face: cq.Face | None = None,
        u_offset: float = 0.0,
        v_offset: float = 0.0,
        width_fraction: float = 0.30,
        height_fraction: float = 0.24,
        u_center: float = 0.5,
        v_center: float = 0.5,
    ) -> SurfaceDesignResult:
        svg = self._svg_factory.frame(
            width=width,
            height=height,
            border=border,
        )

        return self.add_svg(
            base_shape=base_shape,
            surface=surface,
            target_face=target_face,
            svg=svg,
            mode=mode,
            depth=depth,
            u_offset=u_offset,
            v_offset=v_offset,
            width_fraction=width_fraction,
            height_fraction=height_fraction,
            u_center=u_center,
            v_center=v_center,
            document_id="surface_frame",
        )

    def add_text(
        self,
        *,
        base_shape: cq.Shape,
        text: str,
        size: float,
        mode: SurfaceDesignMode,
        depth: float,
        surface=None,
        target_face: cq.Face | None = None,
        font: str = "Arial",
        kind: str = "regular",
        u_offset: float = 0.0,
        v_offset: float = 0.0,
        scale_u: float = 1.0,
        scale_v: float = 1.0,
        width_fraction: float = 0.30,
        height_fraction: float = 0.22,
        u_center: float = 0.5,
        v_center: float = 0.5,
    ) -> SurfaceDesignResult:
        self._validate_mode(mode)

        if target_face is not None:
            result = self._native_face_text.decorate(
                base_shape=base_shape,
                target_face=target_face,
                text_value=text,
                size=float(size),
                depth=float(depth),
                mode=mode.value,
                font=font,
                kind=kind,
                width_fraction=float(width_fraction),
                height_fraction=float(height_fraction),
                u_center=float(u_center),
                v_center=float(v_center),
            )

            output = SurfaceDesignResult(
                shape=result.shape,
                operation=mode.value,
                source_kind="text",
                metadata={
                    "text": text,
                    "font": font,
                    "kind": kind,
                    "size": float(size),
                    "boolean_count": 1,
                    "approximation": False,
                    "text_route": (
                        "cadquery_native_faceOn"
                    ),
                    "mapped_face_count": len(
                        result.mapped_faces.Faces()
                    ),
                    "tool_solid_count": len(
                        result.tool.Solids()
                    ),
                    "base_volume": (
                        result.base_volume
                    ),
                    "final_volume": (
                        result.final_volume
                    ),
                },
            )
            output.validate()
            return output

        if surface is None:
            raise ValueError(
                "add_text requires either target_face "
                "or surface."
            )

        if (
            abs(float(scale_u) - 1.0) > 1e-12
            or abs(float(scale_v) - 1.0) > 1e-12
        ):
            raise NotImplementedError(
                "Legacy native text route does not expose "
                "independent U/V scaling. Use target_face "
                "for universal native face decoration."
            )

        result = self._native_text.apply(
            base_shape=base_shape,
            surface=surface,
            text_value=text,
            size=float(size),
            depth=float(depth),
            mode=mode.value,
            font=font,
            kind=kind,
            u_offset=float(u_offset),
            v_offset=float(v_offset),
        )

        output = SurfaceDesignResult(
            shape=result.shape,
            operation=mode.value,
            source_kind="text",
            metadata={
                "text": text,
                "font": font,
                "kind": kind,
                "size": float(size),
                "boolean_count": 1,
                "approximation": False,
                "text_route": (
                    "cadquery_native_surface_text"
                ),
            },
        )
        output.validate()
        return output

    @staticmethod
    def _validate_mode(
        mode: SurfaceDesignMode,
    ) -> None:
        if not isinstance(
            mode,
            SurfaceDesignMode,
        ):
            raise TypeError(
                "mode must be SurfaceDesignMode."
            )

    @staticmethod
    def _map_mode(
        mode: SurfaceDesignMode,
    ) -> SurfaceFeatureMode:
        SurfaceDesigner._validate_mode(
            mode
        )

        return (
            SurfaceFeatureMode.EMBOSS
            if mode is SurfaceDesignMode.EMBOSS
            else SurfaceFeatureMode.DEBOSS
        )
