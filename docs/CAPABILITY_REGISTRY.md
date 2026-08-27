# DOBO Capability Registry

This registry is required by `CONSOLIDATION_CHARTER.md`. It is a living architectural index, not a claim that every listed capability is currently connected end-to-end.

Status meanings:
- ACTIVE: connected and demonstrated in the consolidated route.
- CANDIDATE: existing implementation identified or connected but still awaiting acceptance gates.
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
| Cylindrical surface mapping | `app/product_generators/surface_mapping/cylinder_mapper.py` | Analytic surface frame | CANDIDATE | Reused by native text pipeline adapter as mapping contract | Must pass canonical visual gates |
| Native CAD surface text | `app/product_generators/surface_designer/native_text.py` | CadQuery/OCC analytic CAD | CANDIDATE | Reconnected after structural body generation through `native_text_pipeline_adapter.py` | Await PAZ/WALTER/long/multiline visual acceptance |
| Surface designer text orchestration | `app/product_generators/surface_designer/designer.py` | CadQuery/OCC | CANDIDATE | Existing native text implementation remains source capability; structural adapter reuses its builder | Full `SurfaceDesigner` routing can be generalized after cylindrical gate passes |
| Advanced mesh-to-CAD adapter | `app/product_generators/surface_designer/advanced_body_adapter.py` | STL boundary -> OCC/CadQuery | CANDIDATE | Reconnected between structural STL and native CAD text boolean | Validate robustness on generated vessel variants |
| Structural/native text bridge | `app/product_generators/design_interpreter/native_text_pipeline_adapter.py` | Orchestration adapter | CANDIDATE | Removes cylindrical text from voxel body generation, then decorates the same generated body with existing CAD text | New connection, not accepted until gates pass |
| Multiline text semantics/layout | `app/product_generators/design_interpreter/text_surface_consolidation.py` parsing contract + native adapter layout | Semantic/layout | CANDIDATE | Explicit line extraction is reused; each line delegates glyph generation to native CAD text | Validate 2-line and 3-line output order/spacing |
| Voxel/SDF glyph geometry | `core_capability_reconnection.py`, `text_surface_consolidation.py` | SDF/voxel | CANDIDATE | No longer selected by the structural pipeline for cylindrical text when native routing applies | Retain until native route passes; then mark SUPERSEDED for cylindrical text only |
| Intelligent surfaces | `app/product_generators/design_interpreter/intelligent_surfaces.py` | Surface intent/program | ACTIVE | Compiled in structural pipeline | Audit how geometric decorations connect to actual surface operators |
| 3MF export | `app/product_generators/design_interpreter/three_mf_export.py` | Mesh/3MF | ACTIVE | Structural pipeline now receives post-decoration mesh before export | Validate decorated final mesh in 3MF |
| Manufacturability preflight | hierarchy engine/specification reports | Structural validation | ACTIVE | Preflight before generation | Native decoration needs downstream final-body validation as acceptance gate |

## Current text consolidation gate

The implementation is now connected but intentionally remains CANDIDATE. Acceptance requires all of the following on the same routing:

1. `PAZ`: crisp native glyphs, no plaque, one watertight body.
2. `WALTER`: correct curvature/contact across the full word.
3. Long text: no forced small centered fraction; text may occupy the requested angular span.
4. Two lines: content and order preserved.
5. Three lines: content and order preserved.
6. Opening/cavity remain unobstructed.
7. Drain remains physically present and validated.
8. Final STL and 3MF contain the decorated final geometry.
9. No fallback to voxel glyph generation is silently selected for the cylindrical cases above.

Only after these gates pass may the native cylindrical text route be marked ACTIVE and the voxel glyph route be marked SUPERSEDED for cylindrical text.

## Registry update rule

Any consolidation commit that changes capability routing must update this registry in the same change or immediately following documentation commit. No new capability implementation should be added before consulting this registry and the charter.
