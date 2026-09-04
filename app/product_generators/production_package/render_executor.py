from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import trimesh

from .render_contract import RenderContract

RENDER_EXECUTOR_VERSION = "dobo.render-executor.v1"


@dataclass(frozen=True, slots=True)
class RenderArtifact:
    view_name: str
    path: str
    width_px: int
    height_px: int


class DeterministicRenderExecutor:
    @staticmethod
    def _basis(direction):
        forward = np.asarray(direction, dtype=float)
        forward /= np.linalg.norm(forward)
        up = np.asarray((0.0, 0.0, 1.0))
        if abs(float(np.dot(forward, up))) > 0.98:
            up = np.asarray((0.0, 1.0, 0.0))
        right = np.cross(forward, up)
        right /= np.linalg.norm(right)
        up = np.cross(right, forward)
        up /= np.linalg.norm(up)
        return right, up, forward

    @classmethod
    def execute(cls, mesh_path: str | Path, contract: RenderContract, output_directory: str | Path) -> tuple[RenderArtifact, ...]:
        contract.validate()
        loaded = trimesh.load_mesh(mesh_path, process=False)
        mesh = trimesh.util.concatenate(tuple(loaded.geometry.values())) if isinstance(loaded, trimesh.Scene) else loaded
        if not isinstance(mesh, trimesh.Trimesh) or len(mesh.vertices) == 0:
            raise RuntimeError("Render source mesh is empty.")
        vertices = np.asarray(mesh.vertices, dtype=float)
        faces = np.asarray(mesh.faces, dtype=int)
        vertices -= 0.5 * (vertices.min(0) + vertices.max(0))
        root = Path(output_directory)
        result = []
        for view in contract.views:
            right, up, forward = cls._basis(view.direction)
            x = vertices @ right
            y = vertices @ up
            z = vertices @ forward
            span = max(float(np.ptp(x)), float(np.ptp(y)), 1e-9)
            scale = 0.82 * min(view.width_px, view.height_px) / span
            px = view.width_px * 0.5 + x * scale
            py = view.height_px * 0.5 - y * scale
            mode = "RGBA" if view.transparent_background else "RGB"
            background = (255, 255, 255, 0) if mode == "RGBA" else (245, 245, 245)
            image = Image.new(mode, (view.width_px, view.height_px), background)
            draw = ImageDraw.Draw(image)
            edge = (70, 70, 70, 255) if mode == "RGBA" else (70, 70, 70)
            for fi in np.argsort(z[faces].mean(1)):
                shade = int(150 + 70 * abs(float(np.dot(np.asarray(mesh.face_normals[fi]), forward))))
                fill = (shade, shade, shade, 255) if mode == "RGBA" else (shade, shade, shade)
                draw.polygon([(float(px[i]), float(py[i])) for i in faces[fi]], fill=fill, outline=edge)
            path = root / f"{view.name}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            image.save(path, format="PNG", compress_level=9)
            result.append(RenderArtifact(view.name, str(path), view.width_px, view.height_px))
        return tuple(result)
