# DOBO Phase 7 — Manufacturability

This phase begins the Validation Engine described in the DOBO technical
specification.

The analyzer evaluates the finished product after geometry generation and
before production export.

Current checks:

- CAD validity
- connected-solid count
- valid overall size
- bed-contact area
- conservative global minimum-feature check
- multicolor region validity and minimum volume

The module is intentionally independent from the DOBO Kernel.

## Important scope note

Phase 7 does **not** yet claim full local wall-thickness or overhang analysis.
Those require dedicated geometric sampling / surface-to-surface analysis and
will be added as separate checks rather than approximated silently.

## Default profile

```text
nozzle_diameter          0.40 mm
layer_height             0.20 mm
min_wall_thickness       0.80 mm
min_feature_size         0.45 mm
min_color_region_volume  1.00 mm^3
max_overhang_angle       50 degrees
min_bed_contact_area     25.0 mm^2
min_clearance            0.25 mm
```

## Install

Copy the `manufacturability` folder into:

`app/product_generators/`

## Run

```powershell
python -m py_compile app\product_generators\manufacturability\profile.py
python -m py_compile app\product_generators\manufacturability\report.py
python -m py_compile app\product_generators\manufacturability\analyzer.py
python -m py_compile app\product_generators\manufacturability\runner.py
python -m py_compile app\product_generators\manufacturability\test_phase_7_manufacturability.py

python -m product_generators.manufacturability.test_phase_7_manufacturability
```

Expected report format:

```text
Connected solid          OK
Overall size             OK
Bed contact              OK/WARNING
Minimum global feature   OK
Color regions            OK
overall                  OK/WARNING
printable                True
Phase 7 Manufacturability: Valid OK
```

This follows the DOBO V2 requirement that the engine validate manufacturability
and structural constraints before production output.
