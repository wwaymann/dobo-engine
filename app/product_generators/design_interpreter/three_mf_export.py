from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np

from .intelligent_surfaces import (
    IntelligentSurfaceProgram,
    SurfaceMaterialMapper,
)


CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
</Types>
"""

RELATIONSHIPS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>
"""


@dataclass(frozen=True, slots=True)
class ThreeMFExportResult:
    path: str
    vertex_count: int
    triangle_count: int
    archive_members: tuple[str, ...]
    material_count: int = 1
    painted_triangle_count: int = 0

    def validate(self) -> None:
        target = Path(self.path)
        if not target.is_file() or target.stat().st_size <= 0:
            raise RuntimeError("3MF export was not created.")
        if self.vertex_count <= 0 or self.triangle_count <= 0:
            raise RuntimeError("3MF export contains no mesh geometry.")
        if not 1 <= self.material_count <= 16:
            raise RuntimeError("3MF export material count is invalid.")
        if not 0 <= self.painted_triangle_count <= self.triangle_count:
            raise RuntimeError("3MF painted triangle count is invalid.")
        required = {
            "[Content_Types].xml",
            "_rels/.rels",
            "3D/3dmodel.model",
        }
        if not required.issubset(self.archive_members):
            raise RuntimeError("3MF package is missing required parts.")


class ThreeMFMeshExporter:
    """Write one triangular mesh as a standards-based 3MF core package."""

    @classmethod
    def export(
        cls,
        mesh: Any,
        path: str | Path,
        *,
        name: str,
        surface_program: IntelligentSurfaceProgram | None = None,
    ) -> ThreeMFExportResult:
        vertices = np.asarray(mesh.vertices, dtype=np.float64)
        faces = np.asarray(mesh.faces, dtype=np.int64)
        if vertices.ndim != 2 or vertices.shape[1] != 3 or not len(vertices):
            raise ValueError("3MF mesh vertices must be a non-empty Nx3 array.")
        if faces.ndim != 2 or faces.shape[1] != 3 or not len(faces):
            raise ValueError("3MF mesh faces must be a non-empty Nx3 array.")
        if not np.all(np.isfinite(vertices)):
            raise ValueError("3MF mesh vertices must be finite.")
        if faces.min() < 0 or faces.max() >= len(vertices):
            raise ValueError("3MF mesh faces reference invalid vertices.")

        triangle_materials = None
        palette = ("#E8E1D5",)
        if surface_program is not None:
            surface_program.validate()
            triangle_materials = SurfaceMaterialMapper.triangle_materials(
                mesh, surface_program
            )
            palette = surface_program.palette

        target = Path(path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=target.parent) as directory:
            model_path = Path(directory) / "3dmodel.model"
            cls._write_model(
                model_path,
                vertices,
                faces,
                name=name,
                palette=palette,
                triangle_materials=triangle_materials,
            )
            temporary = Path(directory) / "package.3mf"
            with ZipFile(temporary, "w", compression=ZIP_DEFLATED) as package:
                package.writestr("[Content_Types].xml", CONTENT_TYPES)
                package.writestr("_rels/.rels", RELATIONSHIPS)
                package.write(model_path, "3D/3dmodel.model")
            temporary.replace(target)

        with ZipFile(target, "r") as package:
            if package.testzip() is not None:
                raise RuntimeError("3MF package failed ZIP integrity validation.")
            members = tuple(sorted(package.namelist()))
        result = ThreeMFExportResult(
            path=str(target),
            vertex_count=len(vertices),
            triangle_count=len(faces),
            archive_members=members,
            material_count=len(palette),
            painted_triangle_count=(
                int(np.count_nonzero(triangle_materials))
                if triangle_materials is not None
                else 0
            ),
        )
        result.validate()
        return result

    @staticmethod
    def _write_model(
        path: Path,
        vertices: np.ndarray,
        faces: np.ndarray,
        *,
        name: str,
        palette: tuple[str, ...],
        triangle_materials: np.ndarray | None,
    ) -> None:
        safe_name = escape(name.strip() or "DOBO model", quote=True)
        with path.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            stream.write(
                '<model unit="millimeter" xml:lang="en-US" '
                'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">\n'
            )
            stream.write(f'  <metadata name="Title">{safe_name}</metadata>\n')
            stream.write('  <metadata name="Application">DOBO</metadata>\n')
            stream.write("  <resources>\n")
            stream.write('    <basematerials id="2">\n')
            for index, color in enumerate(palette):
                stream.write(
                    f'      <base name="DOBO material {index + 1}" '
                    f'displaycolor="{escape(color.upper(), quote=True)}FF"/>\n'
                )
            stream.write("    </basematerials>\n")
            stream.write('    <object id="1" type="model">\n')
            stream.write("      <mesh>\n")
            stream.write("        <vertices>\n")
            for x, y, z in vertices:
                stream.write(
                    '          <vertex x="{}" y="{}" z="{}"/>\n'.format(
                        format(float(x), ".9g"),
                        format(float(y), ".9g"),
                        format(float(z), ".9g"),
                    )
                )
            stream.write("        </vertices>\n")
            stream.write("        <triangles>\n")
            for index, (first, second, third) in enumerate(faces):
                material = (
                    int(triangle_materials[index])
                    if triangle_materials is not None
                    else 0
                )
                stream.write(
                    f'          <triangle v1="{int(first)}" '
                    f'v2="{int(second)}" v3="{int(third)}" '
                    f'pid="2" p1="{material}"/>\n'
                )
            stream.write("        </triangles>\n")
            stream.write("      </mesh>\n")
            stream.write("    </object>\n")
            stream.write("  </resources>\n")
            stream.write("  <build>\n")
            stream.write('    <item objectid="1"/>\n')
            stream.write("  </build>\n")
            stream.write("</model>\n")
