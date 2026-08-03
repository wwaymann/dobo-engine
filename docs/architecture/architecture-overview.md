# DOBO CAD Kernel

# Architecture Overview

**Version:** 2.0

---

# 1. Purpose

This document describes the overall architecture of the DOBO CAD Kernel.

It defines the major subsystems of the Kernel, their responsibilities, and the relationships between them.

This document is implementation-independent.

It describes *what* the architecture is, not *how* it is implemented.

---

# 2. Architectural Vision

The DOBO CAD Kernel is organized as a collection of independent services connected through a deterministic processing pipeline.

Each service owns a single responsibility.

Communication between services occurs through explicit contracts rather than direct implementation dependencies.

The architecture follows four fundamental principles:

- Separation of Responsibilities
- Predictable Data Flow
- Extensibility
- Reusability

---

# 3. High-Level Architecture

```

                           Applications

                                 │

                                 ▼

                         DOBO CAD Kernel

                                 │

                 ┌───────────────┼───────────────┐

                 ▼               ▼               ▼

            Pipeline         Registries      Configuration

                 │

                 ▼

          Geometry Providers

                 │

                 ▼

             Contours (2D)

                 │

                 ▼

          Placement Service

                 │

                 ▼

          Surface Engine

                 │

                 ▼

         Extrusion Engine

                 │

                 ▼

          Boolean Engine

                 │

                 ▼

             Model State

                 │

                 ▼

              Exporters

```

---

# 4. Kernel Layers

The Kernel is divided into logical layers.

---

## Layer 1

Application Layer

Responsibilities

- User interaction
- Configuration
- Project management

This layer never performs geometry calculations.

---

## Layer 2

Pipeline Layer

Responsibilities

- Execute services
- Preserve execution order
- Manage execution context

The Pipeline coordinates work but performs no geometric calculations.

---

## Layer 3

Provider Layer

Responsibilities

Generate reusable geometric descriptions.

Output

Contours.

Providers never generate solids.

---

## Layer 4

Geometry Layer

Responsibilities

- Placement
- Surface calculations
- Coordinate systems

The Geometry Layer transforms geometric information without modifying topology.

---

## Layer 5

Solid Layer

Responsibilities

- Extrusion
- Boolean operations

This layer converts geometric descriptions into CAD solids.

---

## Layer 6

Export Layer

Responsibilities

Convert the final model into external representations.

Examples

- STEP
- STL
- 3MF

---

# 5. Core Subsystems

The Kernel currently defines the following core subsystems.

---

## Pipeline

Coordinates execution.

Owns no geometry.

---

## Provider System

Generates reusable Contours.

---

## Surface Engine

Computes local coordinate systems.

Creates tangent planes.

Positions geometry.

---

## Extrusion Engine

Converts Contours into solids.

---

## Boolean Engine

Combines solids.

Maintains Model integrity.

---

## Registry System

Discovers plugins.

Creates extensibility.

---

## Export System

Converts Models into manufacturing formats.

---

# 6. Data Flow

Information always flows in one direction.

Configuration

↓

Provider

↓

Contour

↓

Placement

↓

Surface

↓

Extrusion

↓

Boolean

↓

Model

↓

Export

No subsystem may reverse this flow.

---

# 7. Dependency Rules

Dependencies follow strict rules.

Applications depend on the Kernel.

The Kernel never depends on Applications.

Providers never depend on Services.

Services never depend on Providers.

Boolean operations never depend on geometry generation.

Exporters never modify Models.

Reverse dependencies are forbidden.

---

# 8. Extensibility

The architecture is designed to grow through extension.

Future additions include:

- New Providers
- New Patterns
- New Decorations
- New Surface types
- New Exporters
- AI-assisted generators
- Optimization engines

Existing components should not require modification when new capabilities are introduced.

---

# 9. Architectural Principles

Every subsystem owns one responsibility.

Every subsystem communicates through contracts.

Geometry generation is independent from placement.

Placement is independent from extrusion.

Extrusion is independent from boolean operations.

The Kernel grows through plugins.

Architecture takes precedence over implementation.

---

# 10. Future Evolution

The architecture intentionally separates interfaces from implementations.

Future versions may replace internal implementations without affecting the architectural contracts defined by this specification.

The architecture is expected to remain stable while implementations evolve.

---

# 11. Summary

The DOBO CAD Kernel is a modular geometric platform built around a deterministic processing pipeline.

Its architecture separates geometry generation, placement, solid construction, and model composition into independent subsystems connected through explicit contracts.

This separation enables long-term maintainability, extensibility, and reuse across multiple CAD-oriented applications.