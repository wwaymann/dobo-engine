# DOBO CAD Kernel

# Roadmap

Version 2.0

Status: Active

---

# Vision

The long-term objective of the DOBO CAD Kernel is to become a modular, extensible and reusable geometric platform capable of supporting multiple CAD applications through a common architecture.

The roadmap is organized into milestones.

Each milestone represents a stable evolution of the Kernel.

---

# Version 2.0

## Objective

Define the architecture of the Kernel.

### Deliverables

- Kernel Philosophy
- Terminology
- Architecture
- Geometry Pipeline
- Plugin System
- Engine APIs
- Data Contracts

Status

Completed

---

# Version 2.1

## Objective

Implement the Kernel Foundation.

### Deliverables

Contracts

- Configuration
- ProviderRequest
- Contour
- Placement
- SurfacePlacement
- ExtrusionProfile
- Solid
- BooleanRequest
- ModelState
- ExecutionContext

Provider API

Provider Registry

Pipeline Foundation

Status

Planned

---

# Version 2.2

## Objective

Implement the Geometry Engines.

### Deliverables

Surface Engine

Extrusion Engine

Boolean Engine

Execution Pipeline

Status

Planned

---

# Version 2.3

## Objective

Implement the first official Providers.

### Deliverables

Circle Provider

Polygon Provider

SVG Provider

Text Provider

Status

Planned

---

# Version 2.4

## Objective

Migrate the existing DOBO Engine.

### Deliverables

Dots

Hexagons

Text

SVG

Pattern Registry

Decoration Registry

Pipeline integration

Status

Planned

---

# Version 2.5

## Objective

Advanced surface support.

### Deliverables

Sphere

Mesh

Bezier Surface

NURBS

Adaptive Projection

Surface Wrapping

Status

Planned

---

# Version 2.6

## Objective

Advanced geometry generation.

### Deliverables

Voronoi Provider

L-System Provider

QR Provider

DXF Provider

AI Geometry Provider

Status

Planned

---

# Version 2.7

## Objective

Advanced CAD Operations.

### Deliverables

Sweep

Loft

Revolve

Pipe

Variable Extrusion

Advanced Boolean Optimization

Status

Planned

---

# Version 2.8

## Objective

Manufacturing Support.

### Deliverables

Manufacturing Profiles

Tolerance Profiles

Mesh Repair

3MF Improvements

STEP Improvements

Status

Planned

---

# Version 2.9

## Objective

Performance.

### Deliverables

Parallel Providers

Boolean Cache

Geometry Cache

Incremental Model Updates

Lazy Evaluation

Status

Planned

---

# Version 3.0

## Objective

Stable Public Kernel.

### Deliverables

Stable Public API

Plugin SDK

Developer Documentation

Automated Tests

Example Applications

Semantic Versioning

Status

Future

---

# Long-Term Goals

The Kernel should eventually support:

- Parametric CAD
- Generative Design
- Digital Fabrication
- AI-assisted Modeling
- Plugin Ecosystem
- Multi-Application Support

---

# Applications

Applications built on top of the Kernel may include:

DOBO Planter

DOBO Jewelry

DOBO Lamps

DOBO Furniture

DOBO Architecture

DOBO Education

DOBO Generative Design

The Kernel remains independent from all applications.

---

# Guiding Principle

Every new capability should extend the Kernel rather than modify it.

Architectural stability always takes precedence over feature growth.

# Future Improvement

Geometry Backend Abstraction

Introduce a Geometry2D Protocol to replace the generic `Any`
used by Contour.geometry.

Goal

Completely decouple the Kernel from CadQuery and allow
multiple geometric backends.

Priority

Low

Version

2.2+