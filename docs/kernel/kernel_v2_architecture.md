# DOBO Kernel v2 Architecture

## 1. Purpose

DOBO Kernel v2 separates mathematical geometry from CAD-backend geometry.

The Kernel must be able to describe, project, offset and transform geometry without depending on CadQuery, OpenCascade or another CAD backend until the final construction stages.

The central architectural rule is:

> Mathematical geometry must remain independent from CAD geometry.

This separation makes the Kernel easier to test, extend and migrate to other CAD backends.

---

## 2. Core Data Flow

The complete geometry flow is:

```text
ProviderRequest
        │
        ▼
DefinitionProvider
        │
        ▼
ContourDefinitionSet
        │
        ▼
GeometryProjectionEngine
        │
        ▼
ProjectedContourSet
        │
        ▼
OffsetEngine
        │
        ▼
OffsetContourSet
        │
        ▼
WireBuilder
        │
        ▼
WireBuildResult
        │
        ▼
SolidBuilder / ExtrusionEngine
        │
        ▼
Solid
        │
        ▼
BooleanEngine
        │
        ▼
ModelState
```

Each stage transforms one explicit contract into another.

No stage should silently perform responsibilities that belong to another stage.

---

## 3. Architectural Layers

### 3.1 Definition Layer

The definition layer contains backend-independent two-dimensional geometry.

Main contracts:

```text
Point2D
ContourDefinition
ContourDefinitionSet
```

Providers produce geometry in this layer.

Examples:

```text
CircleDefinitionProvider
PolygonDefinitionProvider
SVGDefinitionProvider
TextDefinitionProvider
DXFDefinitionProvider
```

A definition provider must not create:

```text
cq.Wire
cq.Face
cq.Solid
cq.Workplane
```

A provider only interprets input and produces ordered two-dimensional points.

---

### 3.2 Projection Layer

The projection layer maps two-dimensional geometry onto a three-dimensional surface.

Main contracts:

```text
ProjectedPoint
ProjectedContour
ProjectedContourSet
```

Main service:

```text
GeometryProjectionEngine
```

Its responsibility is:

```text
ContourDefinitionSet
→
ProjectedContourSet
```

It performs mathematical transformations only.

It must not import CadQuery or OpenCascade.

Supported projection strategies may include:

```text
Plane
Cylinder
Cone
Sphere
Torus
Mesh
NURBS
Height map
```

---

### 3.3 Offset Layer

The offset layer gives thickness or depth to projected geometry.

Main contracts:

```text
OffsetPoint
OffsetContour
OffsetContourSet
```

Main service:

```text
OffsetEngine
```

Its responsibility is:

```text
ProjectedContourSet
→
OffsetContourSet
```

The offset direction is derived from each projected point normal.

Examples:

```text
Plane
→ constant normal

Cylinder
→ radial normal

Cone
→ conical surface normal

Sphere
→ radial normal from sphere center

Mesh
→ interpolated mesh normal
```

The `OffsetEngine` must not create CAD solids.

It only calculates the geometric layers required to build them.

---

### 3.4 CAD Construction Layer

The CAD construction layer is the first layer allowed to depend on CadQuery or OpenCascade.

Main services:

```text
WireBuilder
SolidBuilder
BooleanEngine
```

Main CAD contracts:

```text
WireBuildResult
Solid
ModelState
```

The CAD construction layer converts mathematical geometry into backend geometry.

---

## 4. Contracts

### 4.1 Point2D

A two-dimensional point represented as:

```python
tuple[float, float]
```

It belongs to local provider coordinates.

---

### 4.2 ContourDefinition

Represents one ordered two-dimensional contour.

Expected fields:

```text
id
points
closed
source
metadata
```

Example:

```python
ContourDefinition(
    points=(
        (0.0, 0.0),
        (20.0, 0.0),
        (20.0, 10.0),
        (0.0, 10.0),
    ),
    closed=True,
)
```

A closed contour requires at least three distinct points.

An open contour requires at least two distinct points.

`ContourDefinition` must never contain CAD-backend objects.

---

### 4.3 ContourDefinitionSet

Represents an immutable collection of `ContourDefinition` objects.

Expected fields:

```text
contours
source
metadata
```

It provides:

```text
count
point_count
bounds
validation
```

---

### 4.4 ProjectedPoint

Represents one point after surface projection.

Expected fields:

```text
x
y
z
```

It may expose a tuple representation:

```python
(x, y, z)
```

---

### 4.5 ProjectedContour

Represents one contour projected into three-dimensional space.

Expected fields:

```text
points
closed
normals
metadata
```

When normals are present, there must be exactly one normal per projected point.

Each normal must be non-zero.

Normals should normally be normalized before entering this contract.

---

### 4.6 ProjectedContourSet

Represents an immutable collection of `ProjectedContour` objects.

Expected fields:

```text
contours
metadata
```

It provides:

```text
count
point_count
validation
```

---

### 4.7 OffsetPoint

Represents the two sides of one offset operation.

Proposed fields:

```text
source_point
normal
inner_point
outer_point
distance
```

This contract remains independent from CadQuery.

---

### 4.8 OffsetContour

Represents one projected contour after thickness has been applied.

Proposed fields:

```text
inner_points
outer_points
closed
metadata
```

For a closed input contour, the offset result defines:

```text
inner loop
outer loop
side connections
```

---

### 4.9 OffsetContourSet

Represents a collection of `OffsetContour` objects.

It is the final backend-independent geometry contract before CAD construction.

---

### 4.10 WireBuildResult

Represents wires created by the selected CAD backend.

Expected fields:

```text
wires
source
metadata
```

CadQuery-backed implementations may store:

```python
tuple[cq.Wire, ...]
```

This contract belongs to the CAD boundary.

---

### 4.11 Solid

Represents validated solid CAD geometry.

Expected information includes:

```text
geometry
volume
center of mass
bounding box
validation
source
metadata
```

---

### 4.12 ModelState

Represents the current accumulated model.

It contains:

```text
current Solid
version
operation history
metadata
```

Boolean operations return a new `ModelState`.

---

## 5. Services

### 5.1 Definition Providers

Definition providers convert external input into pure 2D geometry.

Examples:

```text
CircleDefinitionProvider
PolygonDefinitionProvider
SVGDefinitionProvider
TextDefinitionProvider
```

Responsibilities:

```text
read input
validate provider parameters
normalize coordinates
produce ContourDefinitionSet
```

Forbidden responsibilities:

```text
surface projection
offset generation
wire creation
extrusion
boolean operations
export
```

---

### 5.2 GeometryProjectionEngine

Transforms:

```text
ContourDefinitionSet
→
ProjectedContourSet
```

Responsibilities:

```text
apply placement
apply scale
apply rotation
map local 2D coordinates to a target surface
calculate one normal per projected point
validate projection bounds
```

Forbidden responsibilities:

```text
wire creation
face creation
solid creation
boolean operations
```

---

### 5.3 OffsetEngine

Transforms:

```text
ProjectedContourSet
→
OffsetContourSet
```

Responsibilities:

```text
read projected normals
calculate inner and outer layers
support positive and negative depth
support symmetric offset when required
preserve contour topology
```

The `OffsetEngine` must treat thickness as mathematical displacement.

It must not perform CAD extrusion.

---

### 5.4 WireBuilder

Transforms mathematical 3D contour data into CAD wires.

Possible inputs:

```text
ProjectedContourSet
OffsetContourSet
```

Responsibilities:

```text
preserve point order
create one wire per contour loop
close closed contours
validate generated wires
avoid implicit resampling
```

The builder must never increase point count unless an explicit interpolation strategy requests it.

A contour with 64 points should normally create a wire with approximately 64 edges.

---

### 5.5 SolidBuilder

The final design should introduce a generic:

```text
SolidBuilder
```

rather than forcing every result through linear extrusion.

Responsibilities may include:

```text
planar extrusion
radial skin construction
loft between contour layers
side-wall construction
shell creation
solid validation
```

The existing `WireExtrusionEngine` may remain as a specialized planar implementation.

Proposed implementations:

```text
PlanarExtrusionBuilder
OffsetLoftBuilder
RadialSolidBuilder
```

---

### 5.6 BooleanEngine

Transforms:

```text
ModelState + Solid
→
ModelState
```

Supported operations:

```text
union
cut
intersect
```

It must not know how the operand solid was generated.

---

## 6. Surface Projection Rules

### 6.1 Plane

Local coordinates:

```text
local X → plane X
local Y → plane Y
```

Projection:

```text
(x, y)
→
(origin.x + x, origin.y + y, origin.z)
```

Normal:

```text
constant plane normal
```

Initial implementation supports:

```text
normal = (0, 0, 1)
```

Future implementations may support arbitrary orthonormal plane bases.

---

### 6.2 Cylinder

Local convention:

```text
local X → arc length
local Y → vertical displacement
```

Angular offset:

```text
angle offset = local X / radius
```

Projection:

```text
X = origin.x + radius × sin(angle)
Y = origin.y + radius × cos(angle)
Z = center_z + local_y
```

Normal:

```text
normalize(
    projected point XY
    -
    cylinder origin XY
)
```

The cylinder projection must preserve the original point count.

It must not reconstruct points from an existing CAD wire.

---

### 6.3 Cone

Local convention:

```text
local X → arc-related horizontal displacement
local Y → vertical displacement
```

The radius varies with height:

```text
radius(z)
=
bottom_radius
+
(top_radius - bottom_radius)
×
(z / height)
```

The cone normal must include the radius slope.

Cone support should be implemented after the cylinder flow is stable.

---

### 6.4 Sphere

The sphere projection maps local coordinates to angular displacement.

A sphere implementation must define:

```text
longitude convention
latitude convention
surface bounds
pole behavior
seam behavior
```

Sphere support should not be implemented until seam handling is explicitly designed.

---

## 7. Pipeline

The future public geometry pipeline should receive one typed configuration:

```python
result = pipeline.execute(
    configuration=configuration,
    model=current_model,
)
```

Proposed internal flow:

```text
ProviderStage
→
ProjectionStage
→
OffsetStage
→
CADBuildStage
→
BooleanStage
→
ExportStage
```

The public API should remain stable even when internal services evolve.

---

## 8. Configuration Structure

A complete configuration may contain:

```text
ProviderConfiguration
SurfaceConfiguration
OffsetConfiguration
BuildConfiguration
BooleanConfiguration
ExportConfiguration
```

The existing `ExtrusionConfiguration` may remain for compatibility but should eventually become part of a more general `BuildConfiguration`.

Possible build modes:

```text
planar_extrusion
offset_loft
radial_skin
sweep
revolve
```

---

## 9. Migration Strategy

The current Kernel and the new mathematical Kernel may coexist temporarily.

### Legacy flow

```text
Provider
→
ContourSet with cq.Wire
→
SurfaceEngine
→
SurfacePlacement
→
ExtrusionEngine
```

### New flow

```text
DefinitionProvider
→
ContourDefinitionSet
→
GeometryProjectionEngine
→
ProjectedContourSet
→
OffsetEngine
→
OffsetContourSet
→
WireBuilder
→
SolidBuilder
```

The legacy flow must not be removed until the new flow passes equivalent tests.

---

## 10. Migration Order

Recommended order:

```text
1. ContourDefinition contracts
2. ProjectedContour contracts
3. GeometryProjectionEngine
4. CircleDefinitionProvider
5. PolygonDefinitionProvider
6. SVGDefinitionProvider
7. Offset contracts
8. OffsetEngine
9. WireBuilder extensions
10. SolidBuilder
11. GeometryPipeline
12. Pipeline integration
13. Legacy pipeline deprecation
14. Legacy SurfaceEngine removal
15. Legacy Provider removal
```

---

## 11. Validation Strategy

Every stage must have isolated tests.

### Definition tests

```text
point count
bounds
closed/open state
distinct points
provider normalization
```

### Projection tests

```text
point count preserved
surface bounds respected
normal count equals point count
normal lengths equal approximately 1
known points map to expected coordinates
```

### Offset tests

```text
offset distance is correct
direction follows normals
inner and outer layers preserve topology
point counts remain equal
```

### CAD build tests

```text
wire count
edge count
wire closure
wire validity
face validity
solid validity
positive volume
```

### Pipeline tests

```text
all stages execute
ModelState version increments
boolean history is preserved
export succeeds
```

---

## 12. Point-Count Invariant

A critical invariant of Kernel v2 is:

> A stage must not unexpectedly increase geometric resolution.

Examples:

```text
64 definition points
→
64 projected points
→
64 offset points per layer
→
approximately 64 CAD edges per loop
```

Resampling is allowed only when:

```text
the configuration explicitly requests it
the interpolation strategy is documented
the resulting point count is recorded in metadata
```

The 6017-edge diagnostic demonstrated why implicit resampling must be prohibited.

---

## 13. Backend Independence

The following modules must not import CadQuery:

```text
contour_definition.py
contour_definition_set.py
projected_point.py
projected_contour.py
projected_contour_set.py
offset_point.py
offset_contour.py
offset_contour_set.py
geometry_projection_engine.py
offset_engine.py
definition providers
```

CadQuery is allowed in:

```text
wire_builder.py
solid builders
boolean_engine.py
export services
CAD validation adapters
```

This boundary must be enforced during code review.

---

## 14. Metadata Rules

Metadata may describe execution details, but it must not replace typed contract fields.

Good metadata examples:

```text
provider name
source file
sampling count
projection strategy
surface type
configuration ID
diagnostic values
```

Bad metadata examples:

```text
required radius stored only in metadata
required normal stored only in metadata
essential topology stored only in metadata
```

Data required for correctness should be represented by typed fields.

---

## 15. Error Handling

Each service must raise errors at its own boundary.

Examples:

```text
DefinitionProvider
→ invalid input parameters

GeometryProjectionEngine
→ unsupported surface or projection outside bounds

OffsetEngine
→ missing normals or invalid offset distance

WireBuilder
→ invalid contour topology

SolidBuilder
→ invalid shell or zero-volume solid

BooleanEngine
→ failed CAD boolean operation
```

Errors should include the stage name and relevant configuration context.

---

## 16. Naming Direction

During migration, names containing `Definition` may be used to distinguish new providers from legacy providers:

```text
CircleDefinitionProvider
PolygonDefinitionProvider
SVGDefinitionProvider
```

After legacy providers are removed, the preferred final names may return to:

```text
CircleProvider
PolygonProvider
SVGProvider
```

The final provider interface should return `ContourDefinitionSet`.

---

## 17. Architectural Decisions

### Decision 1

Providers produce mathematical geometry, not CAD geometry.

### Decision 2

Surface projection is a pure mathematical operation.

### Decision 3

Thickness is modeled by an offset stage, not by the projection engine.

### Decision 4

CadQuery begins at the CAD construction boundary.

### Decision 5

Point order and point count must be preserved unless explicit resampling is configured.

### Decision 6

The public Pipeline API remains configuration-driven.

### Decision 7

Legacy components remain available until equivalent new-flow tests pass.

---

## 18. Current Implementation Status

Implemented:

```text
ContourDefinition
ContourDefinitionSet
CircleDefinitionProvider
ProjectedPoint
ProjectedContour
ProjectedContourSet
GeometryProjectionEngine
Plane projection
Cylinder projection
Per-point projected normals
WireBuilder
Planar WireExtrusionEngine
```

Pending:

```text
OffsetPoint
OffsetContour
OffsetContourSet
OffsetEngine
Radial solid construction
PolygonDefinitionProvider
SVGDefinitionProvider
GeometryPipeline
KernelPipeline integration
Legacy component removal
```

---

## 19. Next Implementation Step

The next implementation milestone is:

```text
ProjectedContourSet
→
OffsetEngine
→
OffsetContourSet
```

The first supported offset strategies should be:

```text
constant planar offset
per-point normal offset
```

The cylinder test should verify:

```text
64 projected points
64 inner points
64 outer points
64 normals
constant radial thickness
```

After the offset contracts and engine are validated, the Kernel can implement a CAD builder that creates a closed solid between the inner and outer contour layers.

---

## 20. Final Principle

The Kernel should model geometry first and CAD entities second.

```text
Meaning
before
representation
```

Providers describe shapes.

Projection places shapes.

Offset gives shapes thickness.

CAD builders create backend entities.

Boolean operations combine solids.

The Pipeline coordinates the complete process without absorbing the responsibilities of any individual stage.
