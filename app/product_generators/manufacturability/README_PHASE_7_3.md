# DOBO Phase 7.3 — Complete Manufacturing Validation Contract

This phase stops the incremental addition of isolated manufacturing checks.

Instead, it defines the complete Validation Engine contract first.

## Why

Phase 7.1 and 7.2 proved that a technically valid measurement can still be
semantically wrong if it is applied to the wrong geometry.

Example:

- measuring wall thickness on the final multicolor `body_region`
- includes artificial boundaries created by Text and Decoration partitioning
- can produce false structural warnings

The contract therefore defines both:

1. WHAT must be validated
2. WHICH semantic geometry source each validation must use

## Contract domains

### Final Product
- CAD validity
- connected final product
- degenerate geometry
- global physical size / machine limits
- clearances
- overhangs

### Structural Body
- structural wall thickness
- bed contact
- base stability
- internal usable volume
- drainage path
- unintended closed cavities

### Text
- minimum printable stroke
- emboss/deboss depth
- printable text-region volume

### Decoration
- minimum feature size
- printable decoration-region volume

### Color / Material Partition
- valid material regions
- minimum region volume
- connectivity / floating islands
- partition/interface integrity

### Production
- orientation on bed
- machine build-volume compatibility
- multicolor 3MF integrity
- filament assignment

## Severity

`ERROR`
Blocks production.

`WARNING`
Does not necessarily block printing, but must be surfaced or handled by a
product/manufacturing policy.

`INFO`
Diagnostic only.

## Critical semantic rule

```text
STRUCTURAL BODY
    -> pre-material-partition CAD geometry
    -> wall thickness / stability / drainage / internal volume

BODY MATERIAL REGION
    -> material validity only
    -> NOT structural wall-thickness source

TEXT
    -> stroke / depth / printable region rules

DECORATION
    -> minimum feature / printable region rules

COLOR REGIONS
    -> continuity / volume / interface rules

FINAL PRODUCT
    -> validity / connectivity / size / orientation / export integrity
```

## Files

- `contract.py`
- `manifest.py`
- `profile.py`
- `product_profile.py`
- `manufacturing_validation_contract.json`
- `test_phase_7_3_contract.py`

This ZIP is intentionally a specification/contract phase. It does not fake
unfinished algorithms.

Existing validated geometry-analysis code from Phase 7.1 remains useful and
will be plugged into the contract during implementation.

## Run

```powershell
python -m py_compile app\product_generators\manufacturability\contract.py
python -m py_compile app\product_generators\manufacturability\manifest.py
python -m py_compile app\product_generators\manufacturability\profile.py
python -m py_compile app\product_generators\manufacturability\product_profile.py
python -m py_compile app\product_generators\manufacturability\test_phase_7_3_contract.py

python -m product_generators.manufacturability.test_phase_7_3_contract
```

The contract currently contains 24 concrete validation rules.

Implementation will proceed by domain, not by inventing new architecture or
changing the Kernel.
