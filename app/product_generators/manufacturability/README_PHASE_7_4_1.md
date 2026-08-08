# DOBO Phase 7.4.1 — Stability Support Detection Fix

This patch fixes two issues discovered in the Phase 7.4 run.

## 1. Support face detection

The previous stability analyzer selected bed-contact faces using:

`face.Center().z`

That fails on curved or trimmed faces because a face can touch `z_min` while
its geometric center is much higher.

Phase 7.4.1 now uses:

- `face.BoundingBox().zmin`
- horizontal-normal test using `abs(normal.z)`

This makes support detection independent of OCC face orientation and robust
for compound/organic geometry.

## 2. Blocking errors now fail the test

The previous test printed:

`Phase 7.4 Structural Body Suite: Valid OK`

even when `blocking errors = 1`.

That was wrong.

The test now raises `RuntimeError` whenever any structural check has status
`ERROR`.

## No changes to

- Kernel
- structural wall-thickness algorithm
- product geometry
- manufacturing thresholds
- Creality exporter

## Run

```powershell
python -m py_compile app\product_generators\manufacturability\stability.py
python -m py_compile app\product_generators\manufacturability\test_phase_7_4_structural.py

python -m product_generators.manufacturability.test_phase_7_4_structural
```
