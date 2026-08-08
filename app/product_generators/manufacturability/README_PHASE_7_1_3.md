# DOBO Phase 7.1.3 — Native OCC Ray Intersection

Phase 7.1.2 produced zero fixture measurements because CadQuery boolean
`Face.intersect(Edge)` did not return usable intersection vertices in the
installed CadQuery/OCC build.

Phase 7.1.3 uses OpenCascade's native:

`BRepIntCurveSurface_Inter`

This is the exact OCC operation for intersecting a geometric line with the
faces of a shape.

## Algorithm

For each sampled face point:

1. get outward face normal
2. reverse it to obtain inward direction
3. move 0.01 mm inside the solid
4. create `gp_Lin`
5. run `BRepIntCurveSurface_Inter` against the complete CAD shape
6. calculate signed distance of every OCC intersection point along the ray
7. reject numerical source-face hits
8. use the nearest meaningful forward hit

## Required regression fixtures

```text
0.4 mm wall -> approximately 0.400 mm, thin detected
2.0 mm wall -> approximately 2.000 mm, no thin warning
```

No Kernel changes.
No product geometry changes.
No new geometry engine.
This uses CadQuery's underlying native OpenCascade implementation.

## Run

```powershell
python -m py_compile app\product_generators\manufacturability\local_thickness.py
python -m py_compile app\product_generators\manufacturability\test_phase_7_manufacturability.py

python -m product_generators.manufacturability.test_phase_7_manufacturability
```
