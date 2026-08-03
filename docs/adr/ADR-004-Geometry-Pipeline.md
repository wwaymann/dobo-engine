# ADR-004 — Geometry Pipeline

**Status:** Accepted

**Date:** 2026-08-03

**Version:** 2.0

---

# 1. Purpose

This document defines the canonical geometry processing pipeline of the DOBO CAD Kernel.

Every geometric element processed by the Kernel shall follow this pipeline.

The objective is to ensure that every source of geometry is processed consistently regardless of its origin.

---

# 2. Pipeline Philosophy

The Kernel does not process objects.

The Kernel processes geometry.

Every geometric element follows exactly the same sequence of transformations.

The origin of the geometry does not modify the pipeline.

---

# 3. Canonical Pipeline

```

Application

↓

Configuration

↓

Provider

↓

Contours

↓

Placement

↓

Surface Engine

↓

Extrusion Engine

↓

Boolean Engine

↓

Model

↓

Exporter

```

---

# 4. Configuration Stage

The Application provides a configuration describing the desired geometry.

Examples include:

- dimensions
- positions
- pattern definitions
- decorations
- materials
- export options

Configuration never contains geometry.

---

# 5. Provider Stage

The Provider generates Contours.

Examples:

Circle Provider

Polygon Provider

SVG Provider

Text Provider

DXF Provider

The Provider does not know:

- surfaces
- solids
- boolean operations
- models

---

# 6. Contour Stage

Contours are the common geometric language of the Kernel.

A Contour represents closed two-dimensional geometry.

Every Provider must return Contours.

---

# 7. Placement Stage

Placement determines where geometry should exist.

Placement defines:

- position
- orientation
- rotation
- scale

Placement never changes topology.

---

# 8. Surface Engine

The Surface Engine transforms Placement into local geometric coordinates.

Responsibilities include:

- tangent planes
- local coordinate systems
- orientation
- surface adaptation

Output:

Placed Contours

---

# 9. Extrusion Engine

The Extrusion Engine converts placed Contours into solids.

Supported operations include:

- extrusion
- shell
- taper
- offset

Output:

Solid Geometry

---

# 10. Boolean Engine

The Boolean Engine merges solids into the current Model.

Supported operations:

Union

Cut

Intersect

The Boolean Engine does not know where geometry originated.

---

# 11. Model Stage

The Model stores the current geometric state.

Each pipeline stage receives a Model.

Each pipeline stage returns a Model.

No subsystem permanently owns the Model.

---

# 12. Export Stage

Export converts the Model into external representations.

Supported formats include:

STEP

STL

3MF

Future formats may be added without modifying previous pipeline stages.

---

# 13. Pipeline Rules

Rule 1

Every geometric element follows the same pipeline.

Rule 2

Pipeline stages never skip intermediate stages.

Rule 3

Each stage transforms data but never changes the responsibility of another stage.

Rule 4

No Provider generates solids.

Rule 5

No Surface Engine performs extrusion.

Rule 6

No Extrusion Engine performs boolean operations.

Rule 7

The Boolean Engine never creates geometry.

---

# 14. Future Extensions

Future Providers automatically become compatible with the Kernel because they only need to generate Contours.

Examples include:

SVG

DXF

QR Codes

Voronoi

L-Systems

Fractals

AI-generated geometry

Future Surface types automatically become compatible with every Provider because Placement is independent from geometry generation.

---

# 15. Summary

The Geometry Pipeline establishes a universal processing sequence that every geometric element must follow.

By enforcing a single pipeline, the Kernel minimizes duplicated logic, maximizes reuse, and allows new capabilities to be added without modifying existing stages.