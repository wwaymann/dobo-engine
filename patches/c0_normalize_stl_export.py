from __future__ import annotations

from pathlib import Path

TARGET = Path("app/product_generators/organic_shapes/vessel_engine.py")

OLD = '''        specification.output.directory.mkdir(parents=True, exist_ok=True)\n        stl_path = specification.output.directory / f"{specification.output.basename}.stl"\n        self._timed(stages, "stl_export", lambda: mesh.export(str(stl_path)))\n        if not stl_path.is_file() or stl_path.stat().st_size <= 0:\n            raise RuntimeError("Organic vessel STL export was not created.")\n'''

NEW = '''        specification.output.directory.mkdir(parents=True, exist_ok=True)\n        stl_path = specification.output.directory / f"{specification.output.basename}.stl"\n\n        # STL is a float32 triangle-soup boundary. Keep the already-approved DOBO\n        # mesh unchanged and repair only topology that collapses at serialization\n        # precision. The search is bounded from sub-micron to 0.001 mm and must\n        # still produce one watertight, winding-consistent component.\n        export_mesh = None\n        for digits in (7, 6, 5, 4, 3):\n            candidate = mesh.copy()\n            candidate.vertices = np.asarray(\n                candidate.vertices, dtype=np.float32\n            ).astype(np.float64)\n            candidate.merge_vertices(digits_vertex=digits)\n            candidate.update_faces(candidate.nondegenerate_faces())\n            candidate.update_faces(candidate.unique_faces())\n            candidate.remove_unreferenced_vertices()\n            candidate.fill_holes()\n            candidate.fix_normals()\n            candidate.remove_unreferenced_vertices()\n            if (\n                candidate.is_watertight\n                and candidate.is_winding_consistent\n                and len(tuple(candidate.split(only_watertight=False))) == 1\n            ):\n                export_mesh = candidate\n                break\n        if export_mesh is None:\n            raise RuntimeError(\n                "Organic vessel STL precision repair could not preserve valid topology."\n            )\n        self._timed(\n            stages, "stl_export", lambda: export_mesh.export(str(stl_path))\n        )\n        if not stl_path.is_file() or stl_path.stat().st_size <= 0:\n            raise RuntimeError("Organic vessel STL export was not created.")\n'''

text = TARGET.read_text(encoding="utf-8")
if NEW in text:
    print(TARGET)
    raise SystemExit(0)
if OLD not in text:
    raise SystemExit("Expected STL export block was not found; refusing broad patch")
TARGET.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
print(TARGET)
