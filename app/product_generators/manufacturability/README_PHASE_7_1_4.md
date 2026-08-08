# DOBO Phase 7.1.4 — Thickness Fixture Fix

The OCC ray intersector correctly measured:

- thin fixture: 0.400 mm
- thick fixture: 1.000 mm

The 1.000 mm result exposed a bug in the TEST FIXTURE, not in the analyzer.

The hollow-box helper used:

```python
workplane(offset=1.0)
height - 1.0
```

so every fixture had a fixed 1.0 mm bottom thickness.

That meant the "2.0 mm wall" fixture actually had:

```text
side walls = 2.0 mm
bottom wall = 1.0 mm
minimum thickness = 1.0 mm
```

Phase 7.1.4 fixes the fixture to use:

```python
workplane(offset=wall)
height - wall
```

Now both the side walls and bottom use the requested wall thickness.

Expected regression:

```text
thin-wall fixture 0.400 mm DETECTED OK
thick-wall fixture 2.000 mm CLEAR OK
```

No analyzer changes.
No Kernel changes.
No product geometry changes.
