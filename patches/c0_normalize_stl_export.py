from __future__ import annotations

from pathlib import Path

TARGET = Path("app/product_generators/organic_shapes/vessel_engine.py")

OLD = '''        specification.output.directory.mkdir(parents=True, exist_ok=True)\n        stl_path = specification.output.directory / f"{specification.output.basename}.stl"\n        self._timed(stages, "stl_export", lambda: mesh.export(str(stl_path)))\n        if not stl_path.is_file() or stl_path.stat().st_size <= 0:\n            raise RuntimeError("Organic vessel STL export was not created.")\n'''

NEW = '''        specification.output.directory.mkdir(parents=True, exist_ok=True)\n        stl_path = specification.output.directory / f"{specification.output.basename}.stl"\n\n        # STL has no shared-vertex index. Preserve the already-approved DOBO\n        # topology by serializing every triangle directly from the indexed mesh\n        # with one deterministic text representation for each source coordinate.\n        # This keeps equal source vertices byte-identical across adjacent facets\n        # and avoids binary float32 edge collapse on dense organic surfaces.\n        if not mesh.is_watertight or not mesh.is_winding_consistent:\n            raise RuntimeError("Organic vessel mesh is invalid before STL export.")\n        if len(tuple(mesh.split(only_watertight=False))) != 1:\n            raise RuntimeError("Organic vessel must remain one component before STL export.")\n\n        def export_ascii_stl() -> None:\n            vertices = np.asarray(mesh.vertices, dtype=np.float64)\n            faces = np.asarray(mesh.faces, dtype=np.int64)\n            normals = np.asarray(mesh.face_normals, dtype=np.float64)\n            with stl_path.open("w", encoding="ascii", newline="\\n") as handle:\n                handle.write(f"solid {specification.output.basename}\\n")\n                for face_index, face in enumerate(faces):\n                    normal = normals[face_index]\n                    handle.write(\n                        "  facet normal "\n                        f"{normal[0]:.17g} {normal[1]:.17g} {normal[2]:.17g}\\n"\n                    )\n                    handle.write("    outer loop\\n")\n                    for vertex_index in face:\n                        vertex = vertices[int(vertex_index)]\n                        handle.write(\n                            "      vertex "\n                            f"{vertex[0]:.17g} {vertex[1]:.17g} {vertex[2]:.17g}\\n"\n                        )\n                    handle.write("    endloop\\n")\n                    handle.write("  endfacet\\n")\n                handle.write(f"endsolid {specification.output.basename}\\n")\n\n        self._timed(stages, "stl_export", export_ascii_stl)\n        if not stl_path.is_file() or stl_path.stat().st_size <= 0:\n            raise RuntimeError("Organic vessel STL export was not created.")\n'''

text = TARGET.read_text(encoding="utf-8")
if NEW in text:
    print(TARGET)
    raise SystemExit(0)
if OLD not in text:
    raise SystemExit("Expected STL export block was not found; refusing broad patch")
TARGET.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
print(TARGET)
