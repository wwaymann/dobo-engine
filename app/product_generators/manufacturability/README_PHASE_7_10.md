# DOBO Phase 7.10 — Real Product Manufacturing Integration

This is the final integration step before the manufacturability commit.

It builds the actual Phase-6.5 multicolor product and feeds real product
artifacts into the 24-rule Phase-7.9 contract.

## Real sources connected

- final CAD body
- structural body before material decoration
- text depth from JSON specification
- final text material region
- final decoration material region
- Body/Text/Decoration color partition
- physical product size
- generated Creality 3MF file
- 3MF top-level build item
- 3MF compound components
- actual Creality paint/filament hints

## Intentionally unresolved

SOURCE_PENDING:
- CLEARANCE
- OVERHANG
- TEXT_PRINTABLE_STROKE

NOT_AVAILABLE for the current hybrid stress-product:
- INTERNAL_VOLUME
- DRAINAGE_PATH
- NO_UNINTENDED_CLOSED_CAVITIES

These are visible, not silently passed.

## Expected real-product report

- 18 OK
- 0 WARNING
- 0 ERROR
- 3 SOURCE_PENDING
- 3 NOT_AVAILABLE
- 0 blocking errors

## Run

```powershell
python -m py_compile app\product_generators\manufacturability\three_mf_project_inspector.py
python -m py_compile app\product_generators\manufacturability\product_integration.py
python -m py_compile app\product_generators\manufacturability\test_phase_7_10_real_product_validation.py

python -m product_generators.manufacturability.test_phase_7_10_real_product_validation
```

After this passes, run the regression suite and commit the complete
manufacturability block.
