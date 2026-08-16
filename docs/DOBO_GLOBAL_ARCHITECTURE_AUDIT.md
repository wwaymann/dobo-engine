# DOBO Global Architecture Audit

Date: 2026-08-16
Scope: repository tree + branch topology + commit history + active Macroblock D pipeline.

## Executive conclusion

DOBO has not evolved as one single linear engine. It contains several generations of geometry capability that coexist in the same repository. The current Macroblock D execution path uses the semantic/structural interpreter plus the implicit organic-shape engine, but it does not directly route through several previously developed systems: the legacy CadQuery engine, Kernel v2, feature builders, the older surface-mapping stack, or the legacy advanced text stage.

This explains the observed regression in visible capability: older features were not necessarily deleted; many are present but disconnected from the current production path.

## Architectural generations

### G0/G1 — `app/engine`
Purpose: original parametric planter engine.
Capabilities present in tree: body, base surface, drainage, patterns, decoration, text, export, simple stage pipeline.
Key finding: `app/engine/text.py` implements embossed/engraved text, planar and curved/conical mapping, font selection, multiline content, alignment and angular/diagonal positioning.
Status: legacy / disconnected from current D structural pipeline.

### G2 — `app/kernel`
Purpose: backend-independent typed CAD execution kernel.
Subdomains: contracts, core, geometry, pipeline, plugins, providers, services, stages.
Capabilities present: geometry requests, projected geometry, extrusion, booleans, solid building, revolve, loft, sweep and shell.
Status: mature reusable tooling, but not on the active Macroblock D generation path.

### G2 feature layer — `app/features`
Purpose: higher-level feature definitions/builders over Kernel v2.
Evidence: extrude, boolean, loft, revolve and modeling-tool tests execute through the kernel.
Status: reusable capability layer; largely disconnected from current D path.

### Surface stack — `app/product_generators/surface_mapping`, `surface_features`, `surface_designer`, `decorative_patterns`, `vector_geometry`
Purpose: mapping geometry and artwork to surfaces, creating emboss/deboss/closed feature solids, surface composition and decoration, and multicolor output.
Evidence in history includes mapped emboss/deboss, topology-aware emboss/deboss, universal surface decoration and JSON composition + Creality multicolor 3MF.
Status: substantial capability exists; current D pipeline does not route generated body geometry through this complete stack.

### Product/preset layer — `app/product_collections`, `app/products`
Purpose: basic, commercial, organic and textured planter families and product-specific configurations/examples.
Status: reference/preset/product-family layer, not the current universal generation core.

### G3 — `app/product_generators/organic_shapes`
Purpose: implicit/SDF organic geometry and hierarchical feature-vessel generation.
Capabilities: implicit fields, smooth blends, adaptive layout/refinement, surface anchoring, feature programs, hierarchical composition, mesh quality, cat/structural examples.
Status: ACTIVE. This is the physical geometry backend used by `DoboStructuralPipeline` in Macroblock D through `HierarchicalFeatureVesselEngine`.

### G4 — `app/product_generators/design_interpreter`
Purpose: semantic contract, prompt/image interpretation, repair, grammar, structural vocabulary/compiler, morphogenesis, morphological fusion/continuity, intelligent surface description and 3MF export.
Status: ACTIVE orchestration layer for Macroblocks A–D.

### Manufacturing — `app/product_generators/manufacturability`
Purpose: final-geometry inspection, production orientation, repair controller, real overhang/clearance sources, 3MF placement and handoff evidence.
Status: ACTIVE downstream validation/production layer.

### Production package — `app/product_generators/production_package`
Purpose: deterministic render/package/integrity/content-addressed Macroblock C handoff.
Status: ACTIVE downstream packaging layer.

## Active D path

The current `DoboStructuralPipeline.generate_from_semantic()` performs:

semantic repair -> structural vocabulary -> structural compiler -> intelligent-surface program -> `HierarchicalFeatureParser` -> `HierarchicalFeatureVesselEngine` -> mesh -> `ThreeMFMeshExporter`.

The current implementation does not import or call `app/engine`, `app/kernel`, `app/features`, `surface_mapping`, `surface_features`, or `surface_designer` as geometry stages.

Therefore these capabilities do not automatically accumulate in D simply because their code remains in the repository.

## Capability audit

| Capability | Exists | Current D physical path | Assessment |
|---|---|---|---|
| Basic bodies/cavity/drain | yes | yes, via newer backend | retained/reimplemented |
| Legacy advanced text | yes (`app/engine/text.py`) | no | disconnected |
| Curved/conical text mapping | yes | no | disconnected |
| Boolean kernel | yes | not as general Kernel v2 stage | underused |
| Extrude | yes | partial through structural feature logic | duplicated capability |
| Revolve | yes in Kernel v2 | no direct route | disconnected |
| Loft | yes in Kernel v2 | no direct route | disconnected |
| Sweep | yes in Kernel v2 | no direct route | disconnected |
| Shell | yes in Kernel v2 | newer vessel shell path instead | duplicated/replaced |
| SVG/vector provider | yes in kernel/vector layers | no universal D route | disconnected |
| Surface mapping cylinder/cone/radial | yes | no direct D route | disconnected |
| Emboss/deboss topology-aware | yes | D has separate feature logic, not full prior stack | fragmented/duplicated |
| Decorative patterns | yes | no full D route | disconnected |
| Surface designer composition | yes | no | disconnected |
| Multicolor 3MF | yes | yes through newer exporter/package | retained/reimplemented |
| Implicit organic fields | yes | yes | active |
| Hierarchical composition | yes | yes | active |
| Morphogenesis/grammar | yes | yes | active |
| Manufacturability | yes | yes downstream | active |
| Production orientation/handoff | yes | yes downstream | active |
| Deterministic render/package | yes | yes downstream | active |

## Duplication / fragmentation findings

1. There are at least three geometry abstractions in the repository: the legacy `app/engine`, typed Kernel v2, and the implicit `organic_shapes` engine.
2. Surface operations exist both in old surface stacks and in newer structural/hierarchy code.
3. Text generation exists in legacy CadQuery code while newer manufacturability has text-geometry validation, but the current structural generation path does not call the old text generator.
4. Several capabilities were preserved as files/tests but ceased to be composition stages of the active pipeline.
5. Macroblock regression tests mainly protect the newer A/B/C path; they do not constitute a capability-accumulation test proving that old text/surface/kernel tools still work on new morphologies.

## Root cause

The principal architectural problem is not deletion of previous work. It is **capability fragmentation plus pipeline replacement without a universal composition contract**.

Each generation improved one axis:
- early engine: useful product features;
- Kernel v2: general CAD operations;
- surface stack: mapped decoration;
- organic engine: complex implicit geometry;
- design interpreter: semantic/morphological orchestration;
- B/C: manufacturing and packaging.

But the active pipeline became centered on the newer organic hierarchy backend instead of using older capabilities as composable operators. As a result, architecture accumulated in the repository while visible product capability did not accumulate proportionally.

## What should be kept

KEEP as canonical or reusable:
- semantic contract/interpreter/repair/grammar;
- structural vocabulary and morphogenesis;
- `organic_shapes` implicit/hierarchy engine;
- Kernel v2 generic operations (boolean/extrude/revolve/loft/sweep/shell);
- surface mapping + topology-aware emboss/deboss concepts;
- legacy text implementation as a capability source to migrate/adapt;
- manufacturability and production package;
- current 3MF pipeline.

## What should not remain as parallel product engines

DEPRECATE AS PRIMARY EXECUTION PATHS after migration:
- standalone legacy `app/engine` pipeline;
- product-specific/preset pipelines as alternate engines;
- duplicate surface execution paths once their strongest operators are migrated behind one interface.

Do not delete these before parity tests exist.

## Consolidation architecture

Target execution model:

`Design DNA / semantic program`
-> `Structural / Morphological Graph`
-> `Geometry Composer`
   - implicit organic operators
   - Kernel v2 CAD operators
   - mapped surface operators
   - text operator
   - negative-volume operator
-> `Unified final solid / material regions`
-> `Manufacturability + repair`
-> `3MF/STL`
-> `Render/package`

The new element is not another engine. It is a **Geometry Composer / capability adapter layer** that exposes existing engines as operators under one execution contract.

## Mandatory parity tests before D3

Create a `Capability Accumulation Matrix` proving on the same modern non-cylindrical body that the pipeline can simultaneously:

1. generate an organic/asymmetric body;
2. add embossed curved text;
3. add engraved text;
4. apply mapped relief;
5. perform a negative boolean/perforation;
6. add a decoration/vector feature;
7. preserve cavity/drainage/wall thickness;
8. export valid STL and multicolor 3MF;
9. pass manufacturability;
10. render the final geometry.

No future macroblock should be accepted if a previously accepted capability disappears from this matrix.

## Immediate recommendation

Freeze D2. Do not start D3 form expansion yet.

Next macroblock: `DOBO Consolidation C0 — Capability Reconnection`.

Sequence:
1. create a machine-readable capability inventory;
2. define one `GeometryOperator` contract;
3. adapt Kernel v2 operations rather than rewriting them;
4. migrate/adapt legacy text into the modern body/surface coordinate system;
5. reconnect mapped surface emboss/deboss;
6. connect negative volumes through a single boolean interface;
7. execute the capability-accumulation matrix on an organic body;
8. only after green parity, resume visual D3/D4 work.

This converts existing repository architecture into cumulative product capability instead of adding another parallel generation stack.
