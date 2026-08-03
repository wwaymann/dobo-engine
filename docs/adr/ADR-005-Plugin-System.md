# ADR-005 — Plugin System

**Status:** Accepted

**Date:** 2026-08-03

**Version:** 2.0

---

# 1. Purpose

This document defines the plugin architecture of the DOBO CAD Kernel.

Plugins are the primary mechanism used to extend the Kernel without modifying its internal implementation.

The objective of this architecture is to allow the Kernel to grow through composition instead of modification.

---

# 2. Philosophy

The Kernel is closed for modification and open for extension.

Core services should rarely change.

New functionality should be implemented as plugins.

---

# 3. Plugin Types

The Kernel supports different categories of plugins.

Current categories include:

• Geometry Providers

• Patterns

• Decorations

Future categories may include:

• Surface Providers

• Exporters

• Materials

• Optimizers

• AI Services

---

# 4. Registration

Every plugin must register itself through the corresponding Registry.

Registration is performed during module initialization.

The Kernel never discovers plugins by scanning source code.

Registries are responsible for plugin discovery.

---

# 5. Registries

Each plugin category owns its own Registry.

Examples:

Provider Registry

Pattern Registry

Decoration Registry

Each Registry exposes a common API:

• register()

• unregister()

• get()

• exists()

• list()

---

# 6. Plugin Independence

Plugins must never know other plugins.

A Pattern cannot depend on another Pattern.

A Decoration cannot depend on another Decoration.

Communication always occurs through the Kernel.

---

# 7. Responsibilities

Plugins own domain-specific behavior.

The Kernel owns orchestration.

Example:

A Circle Provider generates circles.

The Kernel decides when to invoke it.

---

# 8. Configuration

Plugins receive configuration through contracts supplied by the Kernel.

Plugins must never read global application state.

Plugins must never modify configuration received from the Kernel.

Configuration is treated as immutable.

---

# 9. Error Handling

Plugins should report failures through exceptions.

Plugins must never terminate the execution pipeline.

The Pipeline is responsible for deciding how failures are handled.

---

# 10. Version Compatibility

Plugins should remain compatible across Kernel versions whenever possible.

Breaking API changes must be documented through new ADRs.

---

# 11. Future Growth

The plugin architecture is expected to support hundreds of independent components.

Examples:

Circle Provider

Polygon Provider

SVG Provider

DXF Provider

Voronoi Provider

QR Provider

Text Provider

Leaf Pattern

Honeycomb Pattern

Wave Pattern

Logo Decoration

Handle Decoration

Feet Decoration

AI Layout Provider

Future plugins should integrate without requiring modifications to existing plugins.

---

# 12. Architectural Rules

Rule 1

Plugins never communicate directly.

Rule 2

Plugins never own the execution pipeline.

Rule 3

Plugins never own the Model.

Rule 4

Plugins perform one responsibility only.

Rule 5

Plugins must be independently testable.

Rule 6

Plugins must be replaceable.

Rule 7

Registries are the only discovery mechanism.

---

# 13. Summary

The Plugin System allows the DOBO CAD Kernel to evolve indefinitely while preserving architectural stability.

The Kernel remains small and stable.

Functionality grows through plugins.