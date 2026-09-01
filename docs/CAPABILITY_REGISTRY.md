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
| General body family expansion | `app/product_generators/design_interpreter/body_family_expansion.py` | Structural/hierarchy | ACTIVE | Called before capability routing | Audit family coverage and historical branches |
| Historical parametric planter body | `app/engine/body.py` | CadQuery analytic/parametric CAD | CANDIDATE | Reconnected for compatible cylindrical planters; exact cylinders now remain analytic instead of equal-radius lofts | Await canonical PAZ/WALTER visual gate |
| Historical planter drain | `app/engine/drain.py` | CadQuery Boolean CAD | CANDIDATE | Reconnected in analytic cylindrical route before native text | Validate physical drain in final artifact |
| Hierarchical vessel generation | `app/product_generators/organic_shapes/hierarchy_engine.py` | Volumetric/mesh | ACTIVE | Remains route for organic/unsupported compositions | Must not become universal representation |
| Cylindrical surface mapping | `app/product_generators/surface_mapping/cylinder_mapper.py` | Analytic surface frame | CANDIDATE | Reused directly by analytic native-text route | Must pass canonical visual gates |
| Native CAD surface text | `app/product_generators/surface_designer/native_text.py` | CadQuery/OCC analytic CAD | CANDIDATE | Applied directly to analytic cylindrical body before tessellation | Await PAZ/WALTER/long/multiline visual acceptance |
| Advanced mesh-to-CAD adapter | `app/product_generators/surface_designer/advanced_body_adapter.py` | STL boundary -> OCC/CadQuery | CANDIDATE | Retained only as fallback for cylindrical text cases not eligible for analytic routing | No longer preferred for simple cylindrical text because of excessive cost |
| Structural/native capability router | `app/product_generators/design_interpreter/native_text_pipeline_adapter.py` | Orchestration | CANDIDATE | Compatible cylindrical body -> historical CAD body -> drain -> native CAD text -> final STL/3MF; unsupported compositions remain on existing structural route | Must demonstrate routing, speed and visual quality before ACTIVE |
| Multiline text semantics/layout | `app/product_generators/design_interpreter/text_surface_consolidation.py` parsing contract + native adapter layout | Semantic/layout | CANDIDATE | Explicit line extraction reused; native CAD owns glyph geometry | Validate 2-line and 3-line output order/spacing |
| Voxel/SDF glyph geometry | `core_capability_reconnection.py`, `text_surface_consolidation.py` | SDF/voxel | CANDIDATE | Not selected for compatible cylindrical text | Retain until analytic native route passes; then supersede only for covered cases |
| Intelligent surfaces | `app/product_generators/design_interpreter/intelligent_surfaces.py` | Surface intent/program | ACTIVE | Compiled in structural pipeline | Audit how additional decorations route by representation |
| 3MF export | `app/product_generators/design_interpreter/three_mf_export.py` | Mesh/3MF | ACTIVE | Tessellation occurs after analytic body/drain/text for compatible cylindrical route | Validate final decorated 3MF |
| Manufacturability preflight | hierarchy engine/specification reports | Structural validation | ACTIVE | Existing preflight remains before generation | Add final analytic-body checks as acceptance evidence |

## Current cylindrical routing decision

For a compatible cylindrical planter with text, the selected route is now:

semantic contract -> structural/body-family normalization -> historical CadQuery planter body -> historical CadQuery drain -> native CadQuery cylindrical text -> final STL tessellation -> existing 3MF export.

The expensive `voxel -> STL -> OCC reconstruction -> native text` bridge is not the preferred route for this case. It remains only as a fallback while broader surface/body combinations are audited.

A cylindrical request containing unsupported non-text structural decorations must not silently use the analytic route and lose those features; it stays on the existing structural route until those capabilities are explicitly connected.

## Current text consolidation gate

The implementation remains CANDIDATE. Acceptance requires:

1. `PAZ`: crisp native glyphs, no plaque, one watertight body.
2. `WALTER`: correct curvature/contact across the full word.
3. Long text: requested angular span remains usable.
4. Two lines: content and order preserved.
5. Three lines: content and order preserved.
6. Opening/cavity unobstructed.
7. Drain physically present.
8. Final STL and 3MF contain the decorated final geometry.
9. Compatible cylindrical cases report/use the analytic CAD route rather than voxel glyphs or STL->OCC reconstruction.
10. Generation time is suitable for the interactive Capability Lab and does not depend on increasing HTTP timeout.

Only after these gates pass may the analytic/native cylindrical route be marked ACTIVE and the voxel glyph route be marked SUPERSEDED for the covered cylindrical cases.

## Registry update rule

Any consolidation commit that changes capability routing must update this registry in the same change or immediately following documentation commit. No new capability implementation should be added before consulting this registry and the charter.
