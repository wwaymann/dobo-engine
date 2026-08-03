# DOBO CAD Kernel

# Extrusion Engine API Specification

Version: 2.0

---

# 1. Purpose

This document defines the public API of the Extrusion Engine.

The Extrusion Engine is responsible for transforming two-dimensional geometry adapted to a surface into valid three-dimensional solid geometry.

It is the only subsystem responsible for creating solids from SurfacePlacement objects.

---

# 2. Responsibility

The Extrusion Engine converts surface-adapted geometry into CAD solids.

## Inputs

- SurfacePlacement
- ExtrusionProfile

## Output

- Solid

---

# 3. Pipeline Position

```
Provider

↓

Contour

↓

Surface Engine

↓

SurfacePlacement

↓

Extrusion Engine

↓

Solid

↓

Boolean Engine
```

---

# 4. Public Interface

```python
class ExtrusionEngine(ABC):

    @abstractmethod
    def extrude(
        self,
        placement: SurfacePlacement,
        profile: ExtrusionProfile,
    ) -> Solid:
        """
        Creates solid geometry from a SurfacePlacement.
        """
```

---

# 5. Input: SurfacePlacement

The Extrusion Engine receives geometry already adapted to the target surface.

It never computes placement.

It never computes projections.

It never modifies the incoming geometry.

SurfacePlacement is considered immutable.

---

# 6. Input: ExtrusionProfile

ExtrusionProfile defines how solids are generated.

Typical properties include:

- depth
- direction
- taper angle
- shell thickness
- offset
- draft angle
- merge strategy
- tolerance

ExtrusionProfile contains no geometry.

---

# 7. Output: Solid

The result of the Extrusion Engine is always a valid CAD solid.

A Solid may contain:

- CAD shape
- volume
- bounding box
- center of mass
- metadata
- validation status

---

# 8. Responsibilities

The Extrusion Engine shall:

- extrude closed contours
- generate valid solids
- preserve topology
- validate generated solids
- compute optional shell geometry
- apply draft angles
- apply offsets
- preserve metadata

---

# 9. Forbidden Responsibilities

The Extrusion Engine shall never:

- generate Contours
- perform surface placement
- compute tangent planes
- perform boolean operations
- modify ModelState
- export geometry

---

# 10. Extrusion Modes

The Kernel may support different extrusion modes.

Examples:

Normal Extrusion

Extrudes along the local surface normal.

---

Bidirectional Extrusion

Extrudes equally in both directions.

---

Directional Extrusion

Extrudes along an explicit vector.

---

Variable Extrusion

Extrusion depth changes according to parameters.

---

Future extrusion modes shall extend the Engine without changing the public API.

---

# 11. Validation

The Extrusion Engine shall validate:

- closed contours
- self-intersections
- invalid profiles
- zero depth
- invalid taper angles
- invalid shell thickness

Invalid requests shall raise descriptive exceptions.

---

# 12. Geometry Quality

The generated solid shall satisfy quality requirements.

Examples include:

- manifold geometry
- watertight solids
- consistent face orientation
- valid topology

The Extrusion Engine shall reject invalid solid generation whenever possible.

---

# 13. Error Handling

Failures shall be reported through exceptions.

Examples:

- invalid contour
- failed extrusion
- invalid topology
- shell generation failure
- CAD kernel failure

The Engine never terminates the Pipeline.

---

# 14. Design Rules

Rule 1

The Extrusion Engine owns solid generation only.

Rule 2

It never performs placement.

Rule 3

It never performs boolean operations.

Rule 4

It always receives SurfacePlacement.

Rule 5

It always returns Solid.

Rule 6

The generated solid must be geometrically valid.

Rule 7

ExtrusionProfile contains behavior, not geometry.

---

# 15. Future Extensions

Future implementations may introduce:

- sweep extrusion
- loft extrusion
- revolve
- pipe
- multi-profile extrusion
- adaptive wall thickness
- manufacturing-aware extrusion

These capabilities shall extend the Engine without modifying the Provider or Surface APIs.

---

# 16. Summary

The Extrusion Engine is responsible exclusively for converting SurfacePlacement objects into valid CAD solids.

It represents the boundary between geometric description and solid modeling.

Every solid created by the Kernel originates from this Engine.