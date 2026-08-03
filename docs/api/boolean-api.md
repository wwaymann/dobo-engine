# DOBO CAD Kernel

# Boolean Engine API Specification

Version: 2.0

---

# 1. Purpose

This document defines the public API of the Boolean Engine.

The Boolean Engine is responsible for combining solid geometry into the current Model.

It is the only subsystem allowed to modify ModelState through boolean operations.

---

# 2. Responsibility

The Boolean Engine combines CAD solids.

It never creates geometry.

It never performs placement.

It never generates contours.

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

↓

ModelState
```

---

# 4. Public Interface

```python
class BooleanEngine(ABC):

    @abstractmethod
    def apply(
        self,
        model: ModelState,
        request: BooleanRequest,
    ) -> ModelState:
        """
        Applies a boolean operation and returns
        a new ModelState.
        """
```

---

# 5. Input: ModelState

ModelState represents the current CAD model.

The Boolean Engine never owns the model.

It only transforms it.

ModelState is treated as immutable.

The returned object represents a new state.

---

# 6. Input: BooleanRequest

BooleanRequest describes a single boolean operation.

It contains:

- operation
- operand
- tolerance
- metadata

---

# 7. Supported Operations

The initial Kernel supports:

Union

Adds geometry.

---

Cut

Removes geometry.

---

Intersect

Keeps common volume.

Future versions may introduce:

- Split
- Slice
- Fuse Groups
- Multi-Boolean

---

# 8. Output

Output is always:

ModelState

No other object may be returned.

---

# 9. Responsibilities

The Boolean Engine shall:

- validate operands
- validate topology
- execute boolean operations
- preserve model integrity
- preserve metadata
- return a valid ModelState

---

# 10. Forbidden Responsibilities

The Boolean Engine shall never:

- generate Contours
- compute Placement
- compute tangent planes
- generate solids
- export geometry
- read Provider configuration

---

# 11. Validation

Before executing a boolean operation the Engine shall validate:

- valid operands
- compatible topology
- supported operation
- non-null solids

Invalid operations shall raise descriptive exceptions.

---

# 12. Geometry Quality

The resulting ModelState should satisfy:

- manifold topology
- closed volume
- consistent face orientation
- valid CAD solid

Whenever possible the Engine shall reject invalid geometry.

---

# 13. Error Handling

Failures shall be reported through exceptions.

Examples:

- boolean failure
- topology corruption
- invalid operands
- unsupported operation

The Boolean Engine never terminates the Pipeline.

---

# 14. Design Rules

Rule 1

The Boolean Engine owns model composition.

Rule 2

It never creates geometry.

Rule 3

It never computes placement.

Rule 4

It never performs extrusion.

Rule 5

It always returns ModelState.

Rule 6

It is the only Engine allowed to modify ModelState.

---

# 15. Future Extensions

Future versions may include:

- Boolean optimization
- Operation batching
- Parallel execution
- Lazy evaluation
- Incremental model updates

These capabilities must preserve the public API.

---

# 16. Summary

The Boolean Engine is the final geometric stage of the Kernel.

Its responsibility is to combine valid solids into a consistent ModelState while preserving the integrity of the CAD model.

No other subsystem may perform boolean operations.