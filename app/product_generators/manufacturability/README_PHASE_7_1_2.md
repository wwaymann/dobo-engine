# DOBO Phase 7.1.2 — True Ray Local Thickness

Phase 7.1.1 still reported a suspicious 0.061 mm minimum on the smooth DOBO
product.

Root cause:

The previous algorithm identified faces intersected by a ray but then measured
the **minimum Euclidean point-to-face distance**. On curved surfaces, that is
not the same as the distance to the intersection point along the ray.

## Correct method

Phase 7.1.2 now creates a real finite line edge and intersects it with each CAD
face.

For every intersection vertex it computes:

```text
distance_along_ray = dot(hit - ray_start, inward_direction)
```

Only positive forward hits outside the numerical guard band are accepted.

The nearest valid forward hit defines the local thickness.

## Regression fixtures

Two fixtures are required to pass:

```text
0.4 mm hollow wall -> detected as ~0.4 mm and THIN
2.0 mm hollow wall -> detected as ~2.0 mm and NOT THIN
```

This is substantially stronger than validating only the thin fixture.

## Scope

This remains a sampled local-thickness estimator rather than an exact medial
axis solver, but the reported value is now based on actual line/surface
intersections.

No Kernel changes.
No product geometry changes.
No manufacturing thresholds changed.

## Run

```powershell
python -m py_compile app\product_generators\manufacturability\local_thickness.py
python -m py_compile app\product_generators\manufacturability\test_phase_7_manufacturability.py

python -m product_generators.manufacturability.test_phase_7_manufacturability
```

Expected beginning:

```text
thin-wall fixture 0.400 mm DETECTED OK
thick-wall fixture 2.000 mm CLEAR OK
```
