# ADR-006 - Organic Shape Engine

**Status:** Accepted

**Date:** 2026-08-12

**Version:** 1.0

---

# 1. Context

The CadQuery/OpenCascade solid backend is reliable for deterministic CAD
operations such as loft, extrusion, shell, drainage, text, and booleans.
Prototype 2 demonstrated that assembling those operations does not provide the
continuous transitions required for expressive organic product envelopes.

# 2. Decision

DOBO adds an Organic Shape Engine as an independent product-generator
extension. It evaluates signed distance fields (SDFs), composes them with
smooth operations, extracts the zero surface with Marching Cubes, and validates
the resulting triangular mesh before export.

The initial backend uses:

- NumPy for vectorized field evaluation.
- scikit-image for topologically correct surface extraction.
- Trimesh for mesh validation and export.

CadQuery remains the solid CAD backend. The Organic Shape Engine does not
replace or modify the existing Provider, Surface, Extrusion, Boolean, or Export
services.

# 3. Terminology

**Signed Distance Field (SDF)**

A sampled scalar field whose zero level defines an organic surface. Negative
values describe the interior and positive values describe the exterior.

**Organic Field**

A parameterized SDF primitive used to influence an organic envelope.

**Smooth Union**

A composition operation that joins organic fields with a controlled continuous
transition instead of a hard Boolean seam.

**Organic Mesh**

A closed triangular surface extracted from a composed organic field and
validated for connectivity, watertightness, winding consistency, and volume.

# 4. Architectural Boundaries

- Applications provide structured specifications; they do not calculate SDFs.
- The Organic Shape Engine owns field evaluation and surface extraction.
- Mesh validation is completed before a result enters manufacturing workflows.
- The extension communicates through explicit specification and result
  contracts.
- Existing Kernel services never import the Organic Shape Engine.
- Reverse dependencies remain forbidden.

# 5. Phase 2A Acceptance Contract

The first mandatory proof shall:

- read two organic fields from JSON;
- compose them with a parameterized smooth union;
- produce exactly one connected component;
- produce a watertight mesh with consistent winding and positive volume;
- export a non-empty STL;
- complete within 30 seconds on the reference development environment.

# 6. Consequences

DOBO can generate continuous organic envelopes without Blender or manual
sculpting. Future phases must still add cavity, controlled wall thickness,
opening, stable base, drainage, semantic shape controls, and manufacturing
integration before the engine can produce an approved planter.
