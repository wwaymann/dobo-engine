# DOBO Phase 7.4 — Structural Body Suite

This phase implements the structural block defined by the Phase 7.3
Manufacturing Validation Contract.

## Critical source correction

Structural wall thickness is now measured from a dedicated structural CAD
source rebuilt from the validated Phase-4 product body:

- organic core
- primitive composition
- subtractive booleans

It intentionally excludes:

- text
- SVG material decoration
- decorative studs
- multicolor material partition boundaries

Therefore Body/Text/Decoration interfaces cannot create false structural wall
thickness warnings.

## Structural checks

### Implemented now

1. Structural wall thickness
   - native OCC ray analysis
   - known 0.4 mm / 2.0 mm regression fixtures

2. Base stability
   - bed-contact support polygon
   - projected center of mass
   - minimum margin to polygon edge

### Explicitly source-dependent

3. Internal usable volume
4. Drainage connectivity
5. Undeclared closed cavities

These three are **not guessed** from an arbitrary final B-Rep.

They require the product generator to expose explicit semantic geometry:

```python
StructuralBodySource(
    structural_body=...,
    internal_cavity=...,
    drainage_tools=(...),
)
```

Until those sources exist, their status is:

```text
NOT_AVAILABLE
```

That is intentional. A validation engine must never report a guessed cavity or
drainage result as a real manufacturing validation.

## Why this matters

The previous `body_region` was a material partition:

```text
final product
- text material
- decoration material
= body material region
```

That geometry contains artificial internal boundaries and is not the same
thing as the structural planter body.

Phase 7.4 makes this distinction explicit.

## Run

Copy this folder to:

`app/product_generators/manufacturability/`

Then run:

```powershell
python -m py_compile app\product_generators\manufacturability\source.py
python -m py_compile app\product_generators\manufacturability\stability.py
python -m py_compile app\product_generators\manufacturability\cavity.py
python -m py_compile app\product_generators\manufacturability\structural.py
python -m py_compile app\product_generators\manufacturability\test_phase_7_4_structural.py

python -m product_generators.manufacturability.test_phase_7_4_structural
```

Expected first regressions:

```text
wall fixtures thin=0.400 thick=2.000 OK
stability fixture margin=20.000 mm OK
```

Then the actual DOBO structural body is evaluated.
