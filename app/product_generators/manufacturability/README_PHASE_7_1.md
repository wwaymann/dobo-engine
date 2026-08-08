# DOBO Phase 7.1 — Local Thickness Analysis

Phase 7.1 replaces the weak global bounding-box feature proxy with a real
local sampling analysis.

## What it measures

For sampled points on trimmed CAD faces:

1. obtain face normal
2. step slightly inside the solid
3. cast inward along the normal
4. find the first opposite boundary
5. measure the local solid span

This is useful for detecting:

- thin planter walls
- narrow ribs
- thin embossed/debossed geometry
- narrow local printable features

It does not modify the DOBO Kernel or product geometry.

## Validation fixture

The test contains a known hollow box with approximately 0.4 mm walls.

With:

`min_wall_thickness = 0.8 mm`

the analyzer must measure approximately 0.4 mm and detect thin samples.

This prevents a false "Valid OK" caused only by the final product being large.

## Scope

This is a sampled local-thickness estimator, not an exact medial-axis solver.
The report exposes the minimum measured span and thin-sample count.

Overhang analysis remains a separate future check.

## Install

Replace the Phase 7 `manufacturability` folder with this folder.

## Run

```powershell
python -m py_compile app\product_generators\manufacturability\local_thickness.py
python -m py_compile app\product_generators\manufacturability\analyzer.py
python -m py_compile app\product_generators\manufacturability\test_phase_7_manufacturability.py

python -m product_generators.manufacturability.test_phase_7_manufacturability
```

Expected beginning:

```text
thin-wall fixture 0.400 mm DETECTED OK
```

Then the finished Phase 6.5 DOBO product is analyzed with the same local
thickness method.
