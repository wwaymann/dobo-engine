# DOBO Phase 7.1.1 — Local Thickness Self-Hit Fix

The first Phase 7.1 run correctly detected a 0.400 mm thin-wall fixture, but
reported 0.020 mm on the organic DOBO product.

That value was diagnostic:

- inward_offset = 0.010 mm
- false measured span = 0.020 mm

OCC/CadQuery was returning the source face as an immediate intersection on
some curved/trimmed surfaces.

## Fix

The ray sampler now:

1. starts inside the solid as before
2. evaluates all faces returned along the inward ray
3. rejects candidate intersections inside a self-hit guard band
4. selects the nearest physically meaningful opposite boundary

Guard:

```text
max(5 * inward_offset, 0.05 mm)
```

The known 0.400 mm fixture remains part of the regression test.

No Kernel changes.
No product geometry changes.
No manufacturing thresholds changed.

## Run

```powershell
python -m py_compile app\product_generators\manufacturability\local_thickness.py
python -m py_compile app\product_generators\manufacturability\test_phase_7_manufacturability.py

python -m product_generators.manufacturability.test_phase_7_manufacturability
```

The decisive check is that the finished DOBO product no longer reports the
artificial 0.020 mm value.
