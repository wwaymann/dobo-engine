# DOBO Phase 7.7 — Decoration Manufacturing

Rules implemented:

- DECORATION_FEATURE_SIZE
- DECORATION_REGION_VOLUME

## Feature size

Input:
- explicit decoration geometry

Method:
- inspect each connected decorative solid
- measure bounding-box X/Y/Z dimensions
- take the smallest positive dimension
- validate the smallest decoration feature

Default threshold:
- 0.80 mm

Fixtures:
- 0.60 mm diameter sphere -> FAIL
- 2.00 mm diameter sphere -> PASS
- mixed valid decoration -> PASS

## Region volume

Input:
- explicit final decoration material region

Checks:
- valid B-Rep
- at least one solid
- volume >= 1.0 mm^3

Fixtures:
- 0.5 mm^3 -> FAIL
- 32.0 mm^3 -> PASS

Known validated Phase-6 decoration region:
- 68.629 mm^3 -> PASS

## Product API status

The algorithms are validated.

The current Phase-4 helper still does not expose the raw decorative studs
through a dedicated manufacturing-semantic output, so
DECORATION_FEATURE_SIZE remains SOURCE_PENDING for the complete product API.

The known Phase-6 decoration region is validated numerically, but direct API
exposure is still pending for consolidated manufacturing validation.

No Kernel changes.
No Surface Designer architecture changes.
No exporter changes.

## Run

```powershell
python -m py_compile app\product_generators\manufacturability\profile.py
python -m py_compile app\product_generators\manufacturability\decoration_validation.py
python -m py_compile app\product_generators\manufacturability\test_phase_7_7_decoration_manufacturing.py

python -m product_generators.manufacturability.test_phase_7_7_decoration_manufacturing
```
