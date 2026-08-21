from __future__ import annotations

from pathlib import Path

TARGET = Path("app/product_generators/organic_shapes/vessel_engine.py")

OLD = '''        specification.output.directory.mkdir(parents=True, exist_ok=True)\n        stl_path = specification.output.directory / f"{specification.output.basename}.stl"\n        self._timed(stages, "stl_export", lambda: mesh.export(str(stl_path)))\n        if not stl_path.is_file() or stl_path.stat().st_size <= 0:\n            raise RuntimeError("Organic vessel STL export was not created.")\n'''

NEW = '''        specification.output.directory.mkdir(parents=True, exist_ok=True)\n        stl_path = specification.output.directory / f"{specification.output.basename}.stl"\n\n        # STL has no shared-vertex index. Preserve the already-approved DOBO\n        # topology by serializing every triangle directly from the indexed mesh\n        # with one deterministic high-precision text representation.  Use\n        # vectorized NumPy formatting in bounded chunks: the previous per-facet\n        # Python writer preserved topology but made STL serialization itself\n        # dominate the 30 s generation budget on dense accepted meshes.\n        if not mesh.is_watertight or not mesh.is_winding_consistent:\n            raise RuntimeError("Organic vessel mesh is invalid before STL export.")\n        if len(tuple(mesh.split(only_watertight=False))) != 1:\n            raise RuntimeError("Organic vessel must remain one component before STL export.")\n\n        def export_ascii_stl() -> None:\n            vertices = np.asarray(mesh.vertices, dtype=np.float64)\n            faces = np.asarray(mesh.faces, dtype=np.int64)\n            normals = np.asarray(mesh.face_normals, dtype=np.float64)\n            facet_format = (\n                "  facet normal %.17g %.17g %.17g\\n"\n                "    outer loop\\n"\n                "      vertex %.17g %.17g %.17g\\n"\n                "      vertex %.17g %.17g %.17g\\n"\n                "      vertex %.17g %.17g %.17g\\n"\n                "    endloop\\n"\n                "  endfacet"\n            )\n            chunk_size = 50000\n            with stl_path.open("w", encoding="ascii", newline="\\n", buffering=1024 * 1024) as handle:\n                handle.write(f"solid {specification.output.basename}\\n")\n                for start in range(0, len(faces), chunk_size):\n                    stop = min(start + chunk_size, len(faces))\n                    triangle_vertices = vertices[faces[start:stop]].reshape(-1, 9)\n                    rows = np.concatenate((normals[start:stop], triangle_vertices), axis=1)\n                    np.savetxt(handle, rows, fmt=facet_format, delimiter="", newline="\\n")\n                handle.write(f"endsolid {specification.output.basename}\\n")\n\n        self._timed(stages, "stl_export", export_ascii_stl)\n        if not stl_path.is_file() or stl_path.stat().st_size <= 0:\n            raise RuntimeError("Organic vessel STL export was not created.")\n'''

text = TARGET.read_text(encoding="utf-8")
if NEW in text:
    print(TARGET)
    raise SystemExit(0)
if OLD not in text:
    raise SystemExit("Expected STL export block was not found; refusing broad patch")
TARGET.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
print(TARGET)
