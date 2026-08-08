# DOBO Phase 6.5 — Creality Compound Object Fix

Phase 6.4 solved color/profile/grid compatibility, but still exported:

- Body as one build item
- Text as another build item
- Decoration as another build item

Creality Print therefore treated them as three independent printable objects
and automatically dropped Text and Decoration to the bed.

Phase 6.5 changes only the project structure:

## Before

3 top-level printable objects
3 build items

## Now

1 top-level printable object
3 internal material components
1 build item
1 shared bed transform

The original CAD coordinates of Body/Text/Decoration are unchanged.

Material mapping remains:

- Body -> Filament 1
- Text -> Filament 2
- Decoration -> Filament 3

The real K1 Max Creality project template and all validated printer/process
settings remain unchanged.

No Kernel changes.
No CAD geometry changes.

## Install

Replace:

- `three_mf_exporter.py`
- `test_phase_6_multicolor_3mf.py`

Keep:

- `creality_project_template.3mf`

beside the exporter.

## Run

```powershell
python -m py_compile app\product_generators\surface_designer\three_mf_exporter.py
python -m py_compile app\product_generators\surface_designer\test_phase_6_multicolor_3mf.py

python -m product_generators.surface_designer.test_phase_6_multicolor_3mf
```

Expected test:

- top-level printable objects 1
- build items 1
- internal material parts 3
- part filaments [1, 2, 3]
- Phase 6.5 Creality Compound: Valid OK

Then open the generated 3MF in Creality Print.

The decisive visual check is that Text and Decoration remain on the DOBO model
instead of being independently placed on Z=0.
