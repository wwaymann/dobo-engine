# DOBO Phase 7.1.5 — Thin Spot Diagnostics

The native OCC local-thickness analyzer now passes both regression fixtures:

- 0.400 mm wall -> correctly detected
- 2.000 mm wall -> correctly cleared

The finished DOBO product reports a minimum sampled thickness of approximately
0.609 mm against a preferred minimum of 0.800 mm.

Phase 7.1.5 does NOT change geometry or thresholds.

Its purpose is to locate the measured thin regions before any modeling change
is considered.

## Outputs

The diagnostic exports:

- `thin_spots.csv`
- `thin_spots.json`
- `thin_spot_markers.step`

The STEP contains small spheres centered on the 20 thinnest sampled points.

Open the normal DOBO reference STEP together with `thin_spot_markers.step` in
the same CAD viewer. Because both use the same CAD coordinates, the spheres
show exactly where the thickness samples were found.

## Console output

The test prints the 10 thinnest points:

```text
face=<index>
t=<thickness mm>
xyz=(x, y, z)
```

This lets us determine whether the 0.609 mm result belongs to:

- the organic body wall
- text
- decorative studs
- boolean port/slot geometry
- another local feature

Only after locating it should the product geometry or manufacturing rule be
changed.

## Run

```powershell
python -m py_compile app\product_generators\manufacturability\diagnostics.py
python -m py_compile app\product_generators\manufacturability\test_phase_7_manufacturability.py

python -m product_generators.manufacturability.test_phase_7_manufacturability
```
