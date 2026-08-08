# DOBO Phase 7.6 — Text Manufacturing

Implements the three Text rules from the Phase 7.3 contract:

- TEXT_PRINTABLE_STROKE
- TEXT_DEPTH
- TEXT_REGION_VOLUME

## Principles

Text manufacturability is checked from semantic source geometry and operation
parameters, not reverse-engineered from the final product B-Rep.

### Printable stroke

Input:
- planar text source face(s)

Estimator:
- `2 * area / perimeter`

This is a conservative local-width proxy. Long narrow glyph strokes converge
closely to their physical width.

Default minimum:
- 0.45 mm

### Text depth

Input:
- explicit emboss/deboss depth

Validation uses absolute physical depth.

Default minimum:
- 0.40 mm

### Text region volume

Input:
- explicit final text material/removal region

Default minimum:
- 1.00 mm^3

## Status for current Phase-5 product

The Phase-5 JSON already declares text depth (1.8 mm), so TEXT_DEPTH can be
validated directly.

The current composer does not yet expose:
- planar text source geometry
- final text region as a manufacturing semantic artifact

Therefore those two rules are algorithm-validated but source-pending for that
specific product.

No Kernel changes.
No Surface Designer architecture changes.

## Run

```powershell
python -m py_compile app\product_generators\manufacturability\text_validation.py
python -m py_compile app\product_generators\manufacturability\test_phase_7_6_text_manufacturing.py

python -m product_generators.manufacturability.test_phase_7_6_text_manufacturing
```
