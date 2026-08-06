# DOBO Textured Planters — Phase 2

This phase adds product-domain texture generation without modifying `app/kernel`.

## Executable collection

- Vertical Rib Planter
- Wide Rib Planter
- Fine Fluted Planter
- Corner Rib Planter
- Front Panel Planter
- Alternating Rib Planter

Textures are generated as real protruding solids, extruded using the existing
GeometryRequest path and joined to the planter with the existing Boolean engine.

## Architecture

```text
TexturedPlanterSpecification
    -> Basic planter base
    -> Kernel geometry
    -> Product-layer top-face inspection
    -> Kernel shell
    -> TextureProfile generator
    -> Kernel extrude texture tools
    -> Kernel boolean union
    -> STEP export
```

No file under `app/kernel` is changed.

## Deliberately deferred textures

Diamond, wave, hex-surface and organic textures are not faked in this phase.
They require reusable surface/pattern generators and belong in the next
generator-focused extension above the Kernel.

## Run

```powershell
python -m py_compile app\product_collections\textured_planters\specification.py
python -m py_compile app\product_collections\textured_planters\texture_generator.py
python -m py_compile app\product_collections\textured_planters\builder.py
python -m py_compile app\product_collections\textured_planters\runner.py
python -m py_compile app\product_collections\textured_planters\test_phase_2.py

python -m product_collections.textured_planters.test_phase_2
```
