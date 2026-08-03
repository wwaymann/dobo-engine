# ADR-003 — Kernel Architecture

**Status:** Accepted

**Date:** 2026-08-03

**Version:** 2.0

---

# 1. Purpose

This document defines the high-level architecture of the DOBO CAD Kernel.

The objective of this architecture is to separate responsibilities into independent services connected through a predictable processing pipeline.

The architecture is intentionally modular to maximize extensibility, maintainability and testability.

---

# 2. Architectural Overview

The Kernel is composed of independent subsystems.

Each subsystem performs exactly one responsibility.

No subsystem should perform work that belongs to another subsystem.

The complete processing flow is:

Application

↓

Pipeline

↓

Providers

↓

Contours

↓

Surface Engine

↓

Extrusion Engine

↓

Boolean Engine

↓

Model

↓

Export

---

# 3. Applications

Applications are clients of the Kernel.

Examples:

- DOBO Planter
- DOBO Jewelry
- DOBO Lamps
- DOBO Architecture

Applications never contain geometric algorithms.

Applications only describe what should be built.

---

# 4. Pipeline

The Pipeline coordinates the execution of the Kernel.

Responsibilities:

- execute services
- preserve execution order
- propagate context
- report errors

The Pipeline never creates geometry.

---

# 5. Providers

Providers generate geometry.

Responsibilities:

- create Contours
- validate parameters
- expose reusable geometry

Providers never:

- extrude
- perform booleans
- modify models

Examples:

- Circle Provider
- Polygon Provider
- SVG Provider
- Text Provider
- DXF Provider

---

# 6. Surface Engine

The Surface Engine positions geometry over a target surface.

Responsibilities:

- compute local coordinate systems
- compute tangential planes
- orient contours

The Surface Engine never creates solids.

---

# 7. Extrusion Engine

The Extrusion Engine converts Contours into solids.

Responsibilities:

- extrusion
- taper
- thickness
- shell generation

The Extrusion Engine never performs boolean operations.

---

# 8. Boolean Engine

The Boolean Engine combines solids.

Supported operations:

- Union
- Cut
- Intersect

The Boolean Engine never creates geometry.

---

# 9. Model

The Model represents the current solid being generated.

Every stage receives a Model.

Every stage returns a Model.

No subsystem owns the Model permanently.

---

# 10. Export

Export converts the final Model into external formats.

Examples:

- STEP
- STL
- 3MF

Export never modifies geometry.

---

# 11. Dependency Rules

Dependencies always flow downward.

Application

↓

Pipeline

↓

Providers

↓

Surface

↓

Extrusion

↓

Boolean

↓

Export

Reverse dependencies are forbidden.

---

# 12. Architectural Rules

The following rules are mandatory.

Rule 1

Each subsystem owns exactly one responsibility.

Rule 2

Subsystems communicate only through defined contracts.

Rule 3

Subsystems never import implementation details from higher layers.

Rule 4

Geometry generation is independent from placement.

Rule 5

Placement is independent from extrusion.

Rule 6

Extrusion is independent from boolean operations.

Rule 7

The Kernel grows by extension rather than modification.

---

# 13. Extensibility

Future functionality shall be implemented by extending existing interfaces.

Examples include:

- new Providers
- new Surface types
- new Export formats
- new Decorations
- new Patterns

No architectural change should be required to add these capabilities.

---

# 14. Summary

The Kernel architecture separates geometry generation, placement, solid generation and boolean operations into independent services connected through a single processing pipeline.

This separation ensures long-term maintainability while allowing the Kernel to evolve without increasing coupling between components.
