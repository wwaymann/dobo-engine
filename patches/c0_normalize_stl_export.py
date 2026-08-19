from __future__ import annotations

from pathlib import Path

TARGET = Path("app/product_generators/organic_shapes/vessel_engine.py")

OLD = '''        specification.output.directory.mkdir(parents=True, exist_ok=True)\n        stl_path = specification.output.directory / f"{specification.output.basename}.stl"\n        self._timed(stages, "stl_export", lambda: mesh.export(str(stl_path)))\n        if not stl_path.is_file() or stl_path.stat().st_size <= 0:\n            raise RuntimeError("Organic vessel STL export was not created.")\n'''

NEW = '''        specification.output.directory.mkdir(parents=True, exist_ok=True)\n        stl_path = specification.output.directory / f"{specification.output.basename}.stl"\n\n        # STL serializes triangle coordinates as float32. Preserve the approved\n        # DOBO surface while normalizing only precision-bound topology before\n        # writing the file, so an internally watertight mesh remains watertight\n        # after the STL representation boundary.\n        export_mesh = mesh.copy()\n        export_mesh.vertices = np.asarray(\n            export_mesh.vertices, dtype=np.float32\n        ).astype(np.float64)\n        export_mesh.merge_vertices(digits_vertex=6)\n        export_mesh.update_faces(export_mesh.nondegenerate_faces())\n        export_mesh.update_faces(export_mesh.unique_faces())\n        export_mesh.remove_unreferenced_vertices()\n        if (\n            not export_mesh.is_watertight\n            or not export_mesh.is_winding_consistent\n            or len(tuple(export_mesh.split(only_watertight=False))) != 1\n        ):\n            raise RuntimeError(\n                "Organic vessel STL precision normalization produced invalid topology."\n            )\n        self._timed(\n            stages, "stl_export", lambda: export_mesh.export(str(stl_path))\n        )\n        if not stl_path.is_file() or stl_path.stat().st_size <= 0:\n            raise RuntimeError("Organic vessel STL export was not created.")\n'''

text = TARGET.read_text(encoding="utf-8")
if NEW in text:
    print(TARGET)
    raise SystemExit(0)
if OLD not in text:
    raise SystemExit("Expected STL export block was not found; refusing broad patch")
TARGET.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
print(TARGET)
