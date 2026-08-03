# ADR-002 — Terminology

**Status:** Accepted

**Date:** 2026-08-03

**Version:** 2.0

---

# 1. Purpose

This document defines the official terminology used throughout the DOBO CAD Kernel.

Every architectural discussion, implementation, ADR, and technical document shall use the terminology defined here.

The purpose of this glossary is to establish a common language across the entire project.

---

# 2. Provider

A Provider is a component responsible for generating two-dimensional geometric information.

A Provider never creates solids.

Examples:

- Circle Provider
- Polygon Provider
- Text Provider
- SVG Provider
- DXF Provider

Output:

- Contours

---

# 3. Contour

A Contour is a closed two-dimensional geometric description.

Contours are the common language of the Kernel.

Every Provider produces Contours.

Contours are later transformed into solids by the Extrusion Engine.

---

# 4. Surface

A Surface represents the geometric target on which a Contour will be positioned.

Examples:

- Plane
- Cylinder
- Cone
- Sphere
- Mesh

A Surface never owns geometry.

It only defines spatial placement.

---

# 5. Placement

Placement defines where and how geometry is positioned.

A Placement contains information such as:

- position
- orientation
- rotation
- scale

Placement never modifies geometry.

---

# 6. Extrusion

Extrusion is the process of converting a Contour into a three-dimensional solid.

Extrusion does not perform boolean operations.

Extrusion does not know the final model.

---

# 7. Boolean Operation

A Boolean Operation combines solids.

Supported operations include:

- Union
- Cut
- Intersect

Boolean Operations never create geometry.

---

# 8. Model

The Model represents the current geometric state of the object being built.

Each pipeline stage receives the current Model and returns an updated Model.

---

# 9. Pipeline

The Pipeline coordinates the execution of the Kernel.

It is responsible for invoking the different subsystems in the correct order.

The Pipeline never performs geometric calculations.

---

# 10. Registry

A Registry stores and discovers pluggable components.

Examples include:

- Pattern Registry
- Decoration Registry
- Provider Registry

Registries allow the Kernel to grow without modifying existing code.

---

# 11. Plugin

A Plugin is an extension that adds new functionality without modifying the Kernel.

Plugins are registered dynamically through a Registry.

---

# 12. Service

A Service performs a specific operation within the Kernel.

Examples:

- Surface Service
- Extrusion Service
- Boolean Service

A Service owns behavior.

It never owns business rules.

---

# 13. Design Rule

Every component inside the Kernel shall use the terminology defined in this document.

New architectural terms should be added here before being introduced into the implementation.
