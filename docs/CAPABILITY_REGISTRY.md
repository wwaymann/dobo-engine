# DOBO Capability Registry

This registry is required by `CONSOLIDATION_CHARTER.md`. It is a living architectural index, not a claim that every listed capability is currently connected end-to-end.

Status meanings:
- ACTIVE: connected and demonstrated in the consolidated route.
- CANDIDATE: existing implementation identified for reconnection/validation.
- LEGACY: historical implementation retained pending audit.
- SUPERSEDED: replaced by a validated better route; candidate for cleanup.
- UNKNOWN: existence known but behavior/connection not yet audited.

| Capability | Existing implementation | Representation | Status | Current connection / evidence | Known limitation / next gate |
|---|---|---|---|---|---|
| Prompt semantic interpretation | `app/product_generators/design_interpreter/prompt_interpreter.py` | Semantic program | ACTIVE | Structural prompt pipeline invokes it | Preserve semantic intent through routing |
| Semantic repair | `app/product_generators/design_interpreter/proposal_repair.py` | Semantic program | ACTIVE | Called by structural pipeline | Must not silently rewrite valid intent |
| Structural compilation | `app/product_generators/design_interpreter/structural_compiler.py` | Motor/hierarchy program | ACTIVE | Called by structural pipeline | Capability routing must not be recreated here |
| General body family expansion | `app/product_generators/design_interpreter/body_family_expansion.py` | Structural/hierarchy | ACTIVE | Called before motor generation | Audit family coverage and historical branches |
| Hierarchical vessel generation | `app/product_generators/organic_shapes/hierarchy_engine.py` | Volumetric/mesh | ACTIVE | `_generate_with_retry()` | Appropriate for morphology; not universal representation |
| Cylindrical surface mapping | `app/product_generators/surface_mapping/cylinder_mapper.py` | Analytic surface frame | CANDIDATE | Existing reusable mapper | Reconnect to consolidated surface operations |
| Native CAD surface text | `app/product_generators/surface_designer/native_text.py` | CadQuery/OCC analytic CAD | CANDIDATE | Existing cylinder projection uses native text + offset | Must reconnect after structural body generation and validate boolean/fidelity |
| Surface designer text orchestration | `app/product_generators/surface_designer/designer.py` | CadQuery/OCC | CANDIDATE | Existing `add_text()` routes to native surface/face text | Connect without duplicating semantic text implementation |
| Advanced mesh-to-CAD adapter | `app/product_generators/surface_designer/advanced_body_adapter.py` | STL boundary -> OCC/CadQuery | CANDIDATE | Existing adapter promotes generated STL to Boolean-capable shape | Validate robustness and avoid unnecessary remeshing |
| Multiline text semantics/layout | `app/product_generators/design_interpreter/text_surface_consolidation.py` | Semantic/layout + current SDF route | CANDIDATE | 3-line order/content visually demonstrated | Preserve layout semantics; replace/supersede voxel glyph geometry after native CAD reconnection |
| Voxel/SDF glyph geometry | `core_capability_reconnection.py`, `text_surface_consolidation.py` | SDF/voxel | SUPERSEDED-CANDIDATE | Produced text but unacceptable faceting/cost in current tests | Do not continue tuning as default cylindrical text route; retain until native route passes |
| Intelligent surfaces | `app/product_generators/design_interpreter/intelligent_surfaces.py` | Surface intent/program | ACTIVE | Compiled in structural pipeline | Audit how geometric decorations connect to actual surface operators |
| 3MF export | `app/product_generators/design_interpreter/three_mf_export.py` | Mesh/3MF | ACTIVE | Structural pipeline exports after generation | Must consume final decorated geometry once surface reconnection is active |
| Manufacturability preflight | hierarchy engine/specification reports | Structural validation | ACTIVE | Preflight before generation | Must remain valid after capability routing changes |

## Required next audit

Before implementing more text geometry:

1. Trace the exact output contract of `HierarchicalFeatureVesselEngine` / `mesh_result`.
2. Validate `advanced_body_adapter` on that generated STL.
3. Reconnect `SurfaceDesigner` / `NativeSurfaceTextBuilder` for cylindrical text.
4. Preserve multiline semantic extraction/layout while delegating each line to the native CAD text capability.
5. Export the decorated final body through the existing STL/3MF/fabrication path.
6. Run canonical visual gates: `PAZ`, `WALTER`, long text, two lines, three lines, cavity, opening, drain.
7. Only after PASS, mark the voxel glyph route SUPERSEDED and clean it up separately.

## Registry update rule

Any consolidation commit that changes capability routing must update this registry in the same change or immediately following documentation commit. No new capability implementation should be added before consulting this registry and the charter.
