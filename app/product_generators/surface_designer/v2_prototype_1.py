from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

import cadquery as cq
from cadquery.func import faceOn, offset, text

from .face_selector import SurfaceFaceSelector
from .uv_placement import UVPlacementResolver
from .v2_prototype_1_spec import V2Prototype1Spec


@dataclass(frozen=True, slots=True)
class V2Prototype1Result:
    product_id: str
    shape: cq.Shape
    stl_path: str
    preview_path: str
    volume: float
    solid_count: int
    triangle_count: int
    stage_seconds: dict[str, float]
    generation_seconds: float
    max_generation_seconds: float


def _timed(stages: dict[str, float], name: str, operation):
    started = perf_counter()
    result = operation()
    stages[name] = perf_counter() - started
    return result


def _build_planter(spec: V2Prototype1Spec) -> cq.Shape:
    body = spec.body
    outer = cq.Solid.makeCone(
        body.bottom_radius_mm,
        body.top_radius_mm,
        body.height_mm,
    )
    inner = cq.Solid.makeCone(
        body.bottom_radius_mm - body.wall_mm,
        body.top_radius_mm - body.wall_mm,
        body.height_mm - body.bottom_mm + 1.0,
        cq.Vector(0.0, 0.0, body.bottom_mm),
    )
    shape = outer.cut(inner, tol=0.005).clean()
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise RuntimeError("V2 Prototype 1 planter is not one valid solid.")
    return shape


def _transform(shape: cq.Shape, placement) -> cq.Shape:
    matrix = cq.Matrix(
        [
            [placement.scale_u, 0.0, 0.0, placement.u_offset],
            [0.0, placement.scale_v, 0.0, placement.v_offset],
            [0.0, 0.0, 1.0, 0.0],
        ]
    )
    transformed = shape.transformGeometry(matrix)
    if not transformed.isValid():
        raise RuntimeError("Placed text geometry is invalid.")
    return transformed


def _text_tools(base_shape: cq.Shape, spec: V2Prototype1Spec) -> tuple[cq.Shape, ...]:
    face = SurfaceFaceSelector().largest_external(
        base_shape,
        geom_type="CONE",
    )
    resolver = UVPlacementResolver()
    tools: list[cq.Shape] = []

    for item in spec.texts:
        planar = text(
            item.content,
            item.size_mm,
            font=item.font,
            kind=item.kind,
            halign="center",
            valign="center",
        )
        if not isinstance(planar, cq.Shape) or not planar.isValid():
            raise RuntimeError(f"Could not build text '{item.content}'.")
        placement = resolver.centered(
            target_face=face,
            planar_shape=planar,
            width_fraction=item.width_fraction,
            height_fraction=item.height_fraction,
            u_center=item.u_center,
            v_center=item.v_center,
        )
        mapped = faceOn(face, _transform(planar, placement))
        tool = offset(mapped, item.depth_mm, cap=True)
        if not isinstance(tool, cq.Shape) or not tool.isValid():
            raise RuntimeError(f"Text tool '{item.content}' is invalid.")
        tools.append(tool)

    return tuple(tools)


def _fuse_once(base_shape: cq.Shape, tools: tuple[cq.Shape, ...]) -> cq.Shape:
    if not tools:
        return base_shape
    combined = base_shape.fuse(*tools, tol=0.005).clean()
    solids = tuple(combined.Solids())
    if not solids:
        raise RuntimeError("Text fusion produced no solid.")
    final_shape = max(solids, key=lambda solid: float(solid.Volume())).clean()
    if not final_shape.isValid() or len(final_shape.Solids()) != 1:
        raise RuntimeError("Text fusion did not produce one valid product.")
    return final_shape


def _triangle_count(shape: cq.Shape, tolerance: float, angular: float) -> int:
    vertices, triangles = shape.tessellate(tolerance, angular)
    if not vertices or not triangles:
        raise RuntimeError("Final product tessellation is empty.")
    return len(triangles)


def build_v2_prototype_1(spec: V2Prototype1Spec) -> V2Prototype1Result:
    spec.validate()
    total_started = perf_counter()
    stages: dict[str, float] = {}

    base = _timed(stages, "planter", lambda: _build_planter(spec))
    tools = _timed(stages, "text_mapping", lambda: _text_tools(base, spec))
    final_shape = _timed(stages, "text_boolean", lambda: _fuse_once(base, tools))

    spec.output.directory.mkdir(parents=True, exist_ok=True)
    stl_path = spec.output.directory / f"{spec.output.basename}.stl"
    preview_path = spec.output.directory / f"{spec.output.basename}_preview.svg"

    def export_stl() -> None:
        cq.exporters.export(
            final_shape,
            str(stl_path),
            tolerance=spec.output.mesh_tolerance_mm,
            angularTolerance=spec.output.angular_tolerance,
        )

    def export_preview() -> None:
        cq.exporters.export(
            final_shape,
            str(preview_path),
            opt={
                "projectionDir": (1.0, -1.0, 0.75),
                "showAxes": False,
                "showHidden": False,
            },
        )

    _timed(stages, "stl_export", export_stl)
    _timed(stages, "preview_render", export_preview)
    triangle_count = _timed(
        stages,
        "mesh_validation",
        lambda: _triangle_count(
            final_shape,
            spec.output.mesh_tolerance_mm,
            spec.output.angular_tolerance,
        ),
    )

    for path in (stl_path, preview_path):
        if not path.is_file() or path.stat().st_size <= 0:
            raise RuntimeError(f"Prototype output was not created: {path}")

    return V2Prototype1Result(
        product_id=spec.id,
        shape=final_shape,
        stl_path=str(stl_path),
        preview_path=str(preview_path),
        volume=float(final_shape.Volume()),
        solid_count=len(final_shape.Solids()),
        triangle_count=triangle_count,
        stage_seconds=stages,
        generation_seconds=perf_counter() - total_started,
        max_generation_seconds=spec.manufacturing.max_generation_seconds,
    )
