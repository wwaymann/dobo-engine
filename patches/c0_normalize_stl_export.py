from __future__ import annotations

from pathlib import Path

TARGET = Path("app/product_generators/organic_shapes/vessel_engine.py")

OLD = '''        specification.output.directory.mkdir(parents=True, exist_ok=True)\n        stl_path = specification.output.directory / f"{specification.output.basename}.stl"\n        self._timed(stages, "stl_export", lambda: mesh.export(str(stl_path)))\n        if not stl_path.is_file() or stl_path.stat().st_size <= 0:\n            raise RuntimeError("Organic vessel STL export was not created.")\n'''

NEW = '''        specification.output.directory.mkdir(parents=True, exist_ok=True)\n        stl_path = specification.output.directory / f"{specification.output.basename}.stl"\n\n        # Do not mutate an already-approved DOBO mesh merely to accommodate the\n        # binary STL float32 boundary.  ASCII STL remains standard STL while\n        # preserving the source vertex coordinates at text precision, avoiding\n        # serialization-induced edge collapse on dense organic surfaces.\n        if not mesh.is_watertight or not mesh.is_winding_consistent:\n            raise RuntimeError("Organic vessel mesh is invalid before STL export.")\n        if len(tuple(mesh.split(only_watertight=False))) != 1:\n            raise RuntimeError("Organic vessel must remain one component before STL export.")\n\n        def export_ascii_stl() -> None:\n            payload = trimesh.exchange.stl.export_stl_ascii(mesh)\n            stl_path.write_text(payload, encoding="ascii")\n\n        self._timed(stages, "stl_export", export_ascii_stl)\n        if not stl_path.is_file() or stl_path.stat().st_size <= 0:\n            raise RuntimeError("Organic vessel STL export was not created.")\n'''

text = TARGET.read_text(encoding="utf-8")
if NEW in text:
    print(TARGET)
    raise SystemExit(0)
if OLD not in text:
    raise SystemExit("Expected STL export block was not found; refusing broad patch")
TARGET.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
print(TARGET)
