# DOBO CAD Kernel

# Engine Responsibilities

Version: 2.0

---

# 1. Purpose

This document defines the responsibilities, inputs, outputs and constraints of every Engine that composes the DOBO CAD Kernel.

Each Engine owns exactly one responsibility.

No Engine should perform work belonging to another Engine.

This separation is the foundation of the Kernel architecture.

---

# 2. Kernel Overview

The Kernel is composed of the following Engines.

Application

↓

Pipeline Engine

↓

Provider Engine

↓

Surface Engine

↓

Extrusion Engine

↓

Boolean Engine

↓

Export Engine

---

# 3. Pipeline Engine

## Responsibility

Coordinate the complete execution of the Kernel.

The Pipeline is responsible for orchestrating every Engine in the correct order.

It never creates geometry.

---

### Inputs

Configuration

Current Model

Execution Context

---

### Outputs

Updated Model

Execution Report

---

### Responsibilities

• Execute Providers

• Execute Surface Engine

• Execute Extrusion Engine

• Execute Boolean Engine

• Execute Export Engine

• Handle errors

• Preserve execution order

---

### Forbidden Responsibilities

The Pipeline must never:

• Create geometry

• Perform boolean operations

• Compute coordinates

• Generate solids

---

# 4. Provider Engine

## Responsibility

Generate reusable two-dimensional geometry.

Providers represent every geometric source supported by the Kernel.

---

### Examples

Circle

Polygon

Text

SVG

DXF

Voronoi

QR Code

AI Provider

---

### Inputs

Configuration

Parameters

---

### Outputs

Contours

---

### Responsibilities

Generate Contours.

Validate parameters.

Expose reusable geometry.

---

### Forbidden Responsibilities

Providers must never:

Create solids.

Know surfaces.

Perform booleans.

Modify the Model.

---

# 5. Surface Engine

## Responsibility

Place geometry over target surfaces.

---

### Inputs

Contours

Placement

Surface Definition

---

### Outputs

Placed Contours

---

### Responsibilities

Compute tangent planes.

Compute local coordinate systems.

Orient contours.

Rotate geometry.

Scale geometry.

---

### Forbidden Responsibilities

Never create solids.

Never perform boolean operations.

Never modify topology.

---

# 6. Extrusion Engine

## Responsibility

Transform Contours into three-dimensional solids.

---

### Inputs

Placed Contours

Extrusion Profile

---

### Outputs

Solid Geometry

---

### Responsibilities

Extrusion.

Offset.

Shell.

Taper.

Thickness.

---

### Forbidden Responsibilities

Never create contours.

Never perform booleans.

Never know Providers.

---

# 7. Boolean Engine

## Responsibility

Merge solids into the current Model.

---

### Inputs

Current Model

Solid Geometry

Boolean Operation

---

### Outputs

Updated Model

---

### Supported Operations

Union

Cut

Intersect

---

### Forbidden Responsibilities

Never generate geometry.

Never modify Providers.

Never perform placement.

---

# 8. Export Engine

## Responsibility

Convert the final Model into external formats.

---

### Inputs

Model

Export Configuration

---

### Outputs

STEP

STL

3MF

Future formats

---

### Responsibilities

Serialize geometry.

Write files.

Validate export.

---

### Forbidden Responsibilities

Never modify the Model.

Never execute booleans.

Never generate geometry.

---

# 9. Registry System

The Registry System is shared by all plugin categories.

Current Registries

Provider Registry

Pattern Registry

Decoration Registry

Future Registries

Material Registry

Exporter Registry

Surface Registry

Optimization Registry

---

Responsibilities

Register plugins.

Find plugins.

Instantiate plugins.

Provide discovery.

---

Forbidden Responsibilities

Never execute plugins.

Never own business logic.

Never modify Models.

---

# 10. Engine Communication

Every Engine communicates through explicit contracts.

No Engine should import implementation details from another Engine.

Communication always occurs through data contracts.

Configuration

↓

Contour

↓

Placement

↓

Extrusion Request

↓

Boolean Request

↓

Model State

---

# 11. Dependency Graph

Application

↓

Pipeline

↓

Provider

↓

Surface

↓

Extrusion

↓

Boolean

↓

Export

Dependencies never flow upward.

Circular dependencies are forbidden.

---

# 12. Architectural Rules

Every Engine owns one responsibility.

Every Engine is independently testable.

Every Engine exposes a public interface.

Every Engine hides its implementation.

Every Engine may evolve independently provided its contracts remain stable.

---

# 13. Summary

The DOBO CAD Kernel separates geometry generation into independent Engines connected through explicit contracts.

This organization minimizes coupling, maximizes reuse and allows the Kernel to evolve without compromising architectural stability.