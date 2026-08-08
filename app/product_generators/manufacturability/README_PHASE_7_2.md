# DOBO Phase 7.2 — Semantic Manufacturing Checks

Phase 7.1 proved that applying one wall-thickness rule to the entire final
solid is semantically wrong.

The two samples below 0.8 mm were located on the decorative sphere ring at
Z=22 mm, not on the main product wall.

Phase 7.2 assigns manufacturing rules by semantic region.

## Body

Checks:

- valid CAD
- local wall thickness

Threshold:

- `min_wall_thickness = 0.8 mm`

## Text

Checks:

- valid solid geometry
- printable connected volume
- minimum region volume

This avoids treating the mathematical edge of embossed glyph geometry as a
container-wall failure.

## Decoration

Checks:

- valid solid geometry
- printable connected volume
- minimum region volume

Decorative spherical chords are no longer interpreted as body walls.

## Final product

Still checks:

- connected solid
- overall size
- bed contact
- color-region validity

## Important

Phase 7.2 does not lower any manufacturing threshold.

It corrects which rule applies to which geometry.

No Kernel changes.
No product geometry changes.
No changes to the validated Creality exporter.

## Run

```powershell
python -m py_compile app\product_generators\manufacturability\semantic.py
python -m py_compile app\product_generators\manufacturability\runner.py
python -m py_compile app\product_generators\manufacturability\test_phase_7_manufacturability.py

python -m product_generators.manufacturability.test_phase_7_manufacturability
```
