# DOBO CAD Kernel

# Data Model Specification

Version: 2.0

---

# 1. Purpose

This document defines the official data contracts used by the DOBO CAD Kernel.

Every Engine exchanges information exclusively through these contracts.

The objective is to remove implicit communication between subsystems and replace it with explicit, well-defined data structures.

These contracts are independent from their implementation.

Whether they are implemented as dataclasses, Pydantic models, dictionaries or other structures is an implementation detail.

---

# 2. Data Flow

The Kernel processes data using the following sequence.

Configuration

↓

ProviderRequest

↓

Contour

↓

Placement

↓

SurfacePlacement

↓

ExtrusionProfile

↓

Solid

↓

BooleanRequest

↓

ModelState

↓

ExportRequest

---

# 3. Configuration

Configuration represents the complete description of a project.

Responsibilities

• store project parameters

• store object definitions

• store export options

Configuration never stores generated geometry.

---

# 4. ProviderRequest

Represents the information required by a Provider.

Typical fields include

• provider name

• parameters

• metadata

Output

Contour Collection

---

# 5. Contour

A Contour represents closed two-dimensional geometry.

Properties

• identifier

• vertices

• curves

• holes

• metadata

A Contour contains no three-dimensional information.

---

# 6. Placement

Placement describes where geometry should exist.

Properties

• position

• rotation

• scale

• alignment

Placement never modifies topology.

---

# 7. SurfacePlacement

Represents geometry already projected onto a target surface.

Properties

• local plane

• transformation

• oriented contours

Output

Placed Contours

---

# 8. ExtrusionProfile

Defines how geometry becomes solid.

Properties

• depth

• taper

• shell

• offset

• direction

Output

Solid

---

# 9. Solid

Represents valid CAD solid geometry.

Properties

• shape

• volume

• bounding box

• metadata

Solid is the primary object manipulated by the Boolean Engine.

---

# 10. BooleanRequest

Defines how a Solid interacts with the current Model.

Properties

• operation

• operand

• priority

Supported operations

Union

Cut

Intersect

---

# 11. ModelState

Represents the current geometric state of the project.

Properties

• current solid

• history

• metadata

The ModelState travels through the entire Kernel.

---

# 12. ExportRequest

Represents a request to export the final Model.

Properties

• format

• destination

• tolerance

• units

---

# 13. ExecutionContext

Contains runtime information shared by the Pipeline.

Examples

• warnings

• errors

• statistics

• execution time

• generated operations

The ExecutionContext never contains geometry.

---

# 14. Metadata

Every contract may optionally contain metadata.

Examples

• author

• tags

• identifiers

• timestamps

Metadata never affects geometry generation.

---

# 15. Contract Rules

Every contract must be immutable whenever possible.

Contracts should contain data only.

Business logic belongs to Engines.

Contracts never execute operations.

Contracts should be serializable.

Contracts should remain independent from CadQuery.

---

# 16. Dependency Graph

Configuration

↓

ProviderRequest

↓

Contour

↓

Placement

↓

SurfacePlacement

↓

ExtrusionProfile

↓

Solid

↓

BooleanRequest

↓

ModelState

↓

ExportRequest

No Engine may bypass this chain.

---

# 17. Future Contracts

Future Kernel versions may introduce additional contracts.

Examples

Material

Texture

Simulation

ManufacturingProfile

Mesh

AIRequest

OptimizerRequest

Future contracts should extend the pipeline without modifying existing ones.

---

# 18. Summary

The Data Model defines the common language shared by every Engine.

By exchanging explicit contracts instead of implementation details, the Kernel remains modular, testable and extensible.