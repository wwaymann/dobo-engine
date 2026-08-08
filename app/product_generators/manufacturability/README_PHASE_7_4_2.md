# DOBO Phase 7.4.2 — Section Footprint Stability

Phase 7.4.1 still produced:

```text
Base stability ERROR
margin = None
```

That means no valid support polygon was found.

The product was not proven unstable. The support extraction method was still
too dependent on CAD face topology.

## New method

Phase 7.4.2 derives support from a horizontal section of the complete
structural body:

```text
z_probe = z_min + 0.10 mm
```

Then:

1. section structural body with XY plane
2. collect all section edges
3. sample each geometric edge
4. create XY convex hull
5. project center of mass into XY
6. verify it lies inside the hull
7. calculate minimum margin to hull edge

This is robust for:

- circular bases
- organic bases
- fillets
- curved pedestal transitions
- faces with no useful vertices at z_min

## Why sample edges

A circular CAD edge may have only one topological vertex. Sampling
`edge.positionAt(t)` provides enough geometry to reconstruct the actual
footprint.

## Test behavior

A centered 40 x 40 mm box must still return approximately:

```text
margin = 20 mm
support area ~= 1600 mm^2
```

The real DOBO product must now return an actual measured stability margin or
fail for a real geometric reason.

No Kernel changes.
No product geometry changes.
No manufacturing thresholds changed.

## Run

```powershell
python -m py_compile app\product_generators\manufacturability\stability.py
python -m py_compile app\product_generators\manufacturability\test_phase_7_4_structural.py

python -m product_generators.manufacturability.test_phase_7_4_structural
```
