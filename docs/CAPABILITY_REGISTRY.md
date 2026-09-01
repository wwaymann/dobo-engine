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
| Historical parametric planter body | `app/engine/body.py` | CadQuery analytic/parametric CAD | ACTIVE | Reconnected and demonstrated in the compatible cylindrical route; exact cylinders remain analytic; final artifact remained one valid watertight component | Broader non-cylindrical reuse still requires separate audit |
| Historical planter drain | `app/engine/drain.py` | CadQuery Boolean CAD | ACTIVE | Reconnected before native text; physical `drain_is_clear` passed in the multiline regression and Capability Lab diagnostics | Validate additional drain variants separately |
| Hierarchical vessel generation | `app/product_generators/organic_shapes/hierarchy_engine.py` | Volumetric/mesh | ACTIVE | Remains route for organic/unsupported compositions | Must not become universal representation |
| Cylindrical surface mapping | `app/product_generators/surface_mapping/cylinder_mapper.py` | Analytic surface frame | ACTIVE | Reused by native CAD cylindrical text; frontal multiline placement is now measured and centered on the actual projected glyph bounds | Audit non-frontal and broader angular placement separately |
| Native CAD surface text | `app/product_generators/surface_designer/native_text.py` | CadQuery/OCC analytic CAD | ACTIVE | Demonstrated for frontal cylindrical emboss, including explicit 3-line `PLANTA\\nUNA\\nIDEA`; native glyphs, 1.5 mm relief cap, measured angular centering, one watertight solid | WALTER, long-text envelope, 2-line and deboss remain separate coverage gates |
| Advanced mesh-to-CAD adapter | `app/product_generators/surface_designer/advanced_body_adapter.py` | STL boundary -> OCC/CadQuery | CANDIDATE | Retained only as fallback for cylindrical text cases not eligible for analytic routing | No longer preferred for simple cylindrical text because of excessive cost |
| Structural/native capability router | `app/product_generators/design_interpreter/native_text_pipeline_adapter.py` | Orchestration | CANDIDATE | Compatible cylindrical body -> historical CAD body -> drain -> native CAD text -> final STL/3MF. The 3-line frontal emboss route is demonstrated and regression-locked. Unsupported compositions remain on the existing structural route. | Broader text cases and additional decorated combinations must pass before the whole router is ACTIVE |
| Multiline text semantics/layout | lightweight prompt-line parsing + native adapter layout | Semantic/layout | ACTIVE | Explicit 3-line content/order/scale/spacing demonstrated by `PLANTA\\nUNA\\nIDEA`; regression test passes end-to-end | Add explicit 2-line coverage and alternate line lengths |
| Voxel/SDF glyph geometry | `core_capability_reconnection.py`, `text_surface_consolidation.py` | SDF/voxel | SUPERSEDED | Superseded for the covered compatible cylindrical frontal text cases by the validated native CAD route | Retain only for uncovered representations until separately audited |
| Intelligent surfaces | `app/product_generators/design_interpreter/intelligent_surfaces.py` | Surface intent/program | ACTIVE | Compiled in structural pipeline | Audit how additional decorations route by representation |
| 3MF export | `app/product_generators/design_interpreter/three_mf_export.py` | Mesh/3MF | ACTIVE | Tessellation occurs after analytic body/drain/text for compatible cylindrical route | Add direct decorated-3MF content gate |
| Manufacturability preflight | hierarchy engine/specification reports | Structural validation | ACTIVE | Existing preflight remains before generation; final analytic route also demonstrates watertightness, winding consistency, one component, cavity/opening/drain semantic checks | Extend final analytic acceptance checks to additional routes |

## Current cylindrical routing decision

For a compatible cylindrical planter with text, the selected route is:

semantic contract -> structural/body-family normalization -> historical CadQuery planter body -> historical CadQuery drain -> native CadQuery cylindrical text -> final STL tessellation -> existing 3MF export.

The expensive `voxel -> STL -> OCC reconstruction -> native text` bridge is not the preferred route for this case. It remains only as a fallback while broader surface/body combinations are audited.

A cylindrical request containing unsupported non-text structural decorations must not silently use the analytic route and lose those features; it stays on the existing structural route until those capabilities are explicitly connected.

## Validated cylindrical multiline checkpoint

The frontal cylindrical 3-line emboss case is now demonstrated and regression-locked.

Canonical validated prompt content:

`PLANTA\\nUNA\\nIDEA`

Evidence:

- Capability Lab generated a valid cylindrical artifact with interpretation, geometry, cavity, drain and fabrication all reporting PASS.
- Final mesh was watertight, winding-consistent and contained exactly one component.
- The analytic CAD route was used rather than voxel glyphs or STL->OCC reconstruction.
- Native CAD text remained readable, vertically distributed as three explicit lines and visually centered on the frontal meridian.
- `app/product_generators/design_interpreter/test_native_cylindrical_multiline_regression.py` completed with `Native cylindrical multiline regression: PASS`.
- The regression checks the analytic route, one component, watertightness, winding consistency, cavity, opening, drain, measurable relief, frontal angular bounds and a real multiline vertical span.

This closes the covered capability: **compatible cylindrical planter + frontal native CAD emboss + explicit 3-line text + cavity + drain + final STL geometry**.

It does not imply that every cylindrical text variant is already validated.

## Remaining cylindrical text gates

1. `WALTER`: verify full-word curvature/contact at the validated frontal centering contract.
2. Long text: establish the safe angular/size envelope without null OCC projection or unacceptable shrinking.
3. Two lines: verify content, order, scale and spacing.
4. Deboss/recessed text: validate inward text operation independently.
5. Final decorated 3MF: inspect/export gate proving the decorated geometry is preserved in the manufacturing artifact.
6. Non-frontal placement: validate semantic circumferential offsets after measured centering.

Only when those broader gates pass should the complete structural/native text router be marked ACTIVE without a scope qualification.

## Registry update rule

Any consolidation commit that changes capability routing must update this registry in the same change or immediately following documentation commit. No new capability implementation should be added before consulting this registry and the charter.
