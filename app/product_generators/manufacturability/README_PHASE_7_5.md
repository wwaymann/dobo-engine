# DOBO Phase 7.5 — Explicit Cavity & Drainage Semantics

Phase 7.4 validated:

- structural wall thickness
- base stability

The remaining structural rules require product semantics that cannot be
reliably reconstructed from an arbitrary final B-Rep:

- internal usable volume
- drainage connectivity
- declared/undeclared closed cavities

Phase 7.5 formalizes those sources.

## StructuralBodySource

A product generator can now expose:

```python
StructuralBodySource(
    structural_body=...,
    internal_cavity=...,
    drainage_tools=(...),
    declared_closed_cavities=(...),
)
```

These are explicit CAD solids, not metadata-only values.

## Validation fixture

The ZIP includes a deterministic hollow cylindrical planter fixture with:

- outer radius: 30 mm
- wall: 2 mm
- bottom: 2 mm
- height: 50 mm
- one drainage hole

The fixture validates:

1. internal cavity volume against the analytic cylinder volume
2. drainage tool intersects cavity
3. drainage tool crosses structural material
4. drainage reaches exterior/bottom
5. zero undeclared sealed cavities at the semantic layer

## Current Phase-4 hybrid product

The existing Phase-4/5/6 stress-test product is not a semantic planter
generator and does not expose an explicit internal cavity or drain tools.

Therefore its structural report correctly keeps:

```text
Internal usable volume  NOT_AVAILABLE
Drainage path           NOT_AVAILABLE
Closed cavities         NOT_AVAILABLE
```

This is not a failed manufacturing check.

It means the product generator has not declared those semantics.

When the real planter generators expose these sources, the same validators
will produce real results automatically.

## No architecture change

- Kernel unchanged
- Surface Designer unchanged
- Creality exporter unchanged
- Validation remains a product-output analysis layer

## Run

```powershell
python -m py_compile app\product_generators\manufacturability\source.py
python -m py_compile app\product_generators\manufacturability\cavity.py
python -m py_compile app\product_generators\manufacturability\structural.py
python -m py_compile app\product_generators\manufacturability\test_phase_7_5_cavity_drainage.py

python -m product_generators.manufacturability.test_phase_7_5_cavity_drainage
```

Expected fixture output includes:

```text
wall fixtures ... OK
stability fixture ... OK
planter semantic fixture volume=... drains=1 undeclared_cavities=0 OK
```
