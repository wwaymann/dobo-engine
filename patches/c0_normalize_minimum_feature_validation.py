from __future__ import annotations

from pathlib import Path

TARGET = Path("app/product_generators/organic_shapes/adaptive_layout.py")

before = """        singular = np.linalg.svd(\n            placement.matrix[:3, :3], compute_uv=False\n        )\n        minimum_scale = float(singular.min())\n        extents = feature_half_extents(placement.feature)\n        minimum_feature = 2.0 * float(extents.min()) * minimum_scale\n        depth_axis = feature_depth_axis(placement.feature)\n        depth_scale = float(\n            np.linalg.norm(placement.matrix[:3, depth_axis])\n        )\n"""

after = """        singular = np.linalg.svd(\n            placement.matrix[:3, :3], compute_uv=False\n        )\n        minimum_scale = float(singular.min())\n        extents = feature_half_extents(placement.feature)\n        depth_axis = feature_depth_axis(placement.feature)\n        lateral_axes = tuple(axis for axis in range(3) if axis != depth_axis)\n        lateral_sizes = tuple(\n            2.0\n            * float(extents[axis])\n            * float(np.linalg.norm(placement.matrix[:3, axis]))\n            for axis in lateral_axes\n        )\n        # minimum_feature describes printable in-plane width/height. Relief\n        # extrusion is validated independently by minimum_depth/maximum_depth,\n        # so a deliberately shallow relief must not fail the lateral feature gate.\n        minimum_feature = min(lateral_sizes)\n        depth_scale = float(\n            np.linalg.norm(placement.matrix[:3, depth_axis])\n        )\n"""

text = TARGET.read_text(encoding="utf-8")
if after in text:
    print(f"already normalized: {TARGET}")
elif before in text:
    TARGET.write_text(text.replace(before, after, 1), encoding="utf-8")
    print(TARGET)
else:
    raise SystemExit("adaptive-layout minimum-feature block no longer matches expected source")
