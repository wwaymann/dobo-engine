# DOBO Technical Verdict 1.0

Date: 2026-08-16
Branch: `consolidation-c0-capability-reconnection`
Status: EVIDENCE-ONLY BASELINE

## 1. Scope and rule of evidence

This verdict records only facts demonstrated by repository code, Git history, or executable tests. It does not prescribe a new architecture and does not assume that a capability is integrated merely because code for it exists.

Classification used in this document:

- **ACTIVE_CURRENT_PATH** — executed by the current structural/production path and protected by a passing test.
- **VALIDATED_SEPARATE_PATH** — executable and protected by a passing test, but not called by the current structural path.
- **PRESENT_NOT_C0_EXECUTED** — implementation exists in the repository/history, but C0 #1 did not execute it directly.
- **REPLACED_OR_DUPLICATED** — a newer path performs the same broad responsibility; no claim is made that behavior is equivalent.
- **BROKEN** — a directly executed current test fails.
- **UNKNOWN** — evidence is insufficient.

No capability may be called ACTIVE unless there is direct execution evidence.

## 2. Foundational requirements being checked

The DOBO Platform V1/V2 specifications define the intended system as cumulative and modular:

- structured input must become printable geometry;
- geometry, decorations, text, color, validation and export are separate responsibilities;
- text, drainage, manufacturability and multicolor are required product capabilities;
- modules are intended to evolve independently;
- existing modules must not be broken by later changes.

This verdict checks the repository against that intended cumulative behavior.

## 3. Current executable pipeline — fact

`DoboStructuralPipeline.generate_from_semantic()` currently performs:

1. semantic repair;
2. structural vocabulary resolution;
3. structural semantic compilation;
4. intelligent-surface program compilation;
5. parse motor program with `HierarchicalFeatureParser`;
6. preflight with `HierarchicalFeatureVesselEngine`;
7. physical generation through `HierarchicalFeatureVesselEngine` / `DoboDesignPipeline._generate_with_retry()`;
8. output as mesh;
9. export with `ThreeMFMeshExporter`.

The current function directly imports the hierarchy engine from `product_generators.organic_shapes` and passes the resulting mesh to the newer 3MF exporter.

Within this physical generation function there is no call to:

- `product_generators.surface_designer`;
- legacy `engine` text/decorative stages;
- Kernel v2 as a general post-body CAD pipeline;
- the older hybrid BRep product composer.

Therefore those systems are not automatically accumulated by the current structural generation path.

## 4. C0 #1 executable evidence

GitHub Actions run `31975969738` completed with conclusion **success**.

The following steps all completed successfully:

- executable capability inventory;
- native surface text capability;
- hybrid BRep composition;
- JSON product composition;
- text + decoration + multicolor 3MF accumulation;
- modern structural morphogenesis;
- advanced visual geometry;
- manufacturability validation.

This proves that old and new capability families are still executable in the same repository revision. It does **not** prove that they execute on the same generated object.

## 5. Capability status matrix

| Capability | Direct evidence | Status | Current structural path? |
|---|---|---|---|
| Semantic program / repair / structural compile | `structural_pipeline.py`; modern morphology tests in C0 | ACTIVE_CURRENT_PATH | yes |
| Modern implicit/hierarchical morphology | `HierarchicalFeatureVesselEngine`; modern morphology tests pass in C0 | ACTIVE_CURRENT_PATH | yes |
| Negative volumes in modern structural program | structural trace includes `negative_volumes`; hierarchy engine executes current path | ACTIVE_CURRENT_PATH | yes |
| STL from modern morphology | structural result exposes generated STL and validates artifact | ACTIVE_CURRENT_PATH | yes |
| Modern 3MF export | `ThreeMFMeshExporter` called directly by structural pipeline | ACTIVE_CURRENT_PATH | yes |
| Manufacturability | C0 executes real product manufacturability test successfully | ACTIVE_CURRENT_PATH / DOWNSTREAM | yes downstream |
| Native projected surface text | `test_native_surface_text_capability` creates projected and thickened native text and exports STEP; C0 pass | VALIDATED_SEPARATE_PATH | no |
| Hybrid BRep primitive fusion | `test_phase_4_hybrid`; C0 pass | VALIDATED_SEPARATE_PATH | no |
| Subtractive BRep booleans | `test_phase_4_hybrid` verifies volume decrease; C0 pass | VALIDATED_SEPARATE_PATH | no |
| Geometric BRep decoration | `test_phase_4_hybrid` verifies volume increase; C0 pass | VALIDATED_SEPARATE_PATH | no |
| Text emboss on hybrid BRep object | `test_phase_4_hybrid` verifies volume increase; C0 pass | VALIDATED_SEPARATE_PATH | no |
| SVG deboss on hybrid BRep object | `test_phase_4_hybrid` verifies volume decrease; C0 pass | VALIDATED_SEPARATE_PATH | no |
| JSON product composition | dedicated Phase 5 JSON composition test passes in C0 | VALIDATED_SEPARATE_PATH | no |
| Multicolor 3MF with material regions | `test_phase_6_multicolor_3mf`; 1 compound printable object, 3 components/filaments; C0 pass | VALIDATED_SEPARATE_PATH | no for D body path |
| Legacy advanced text engine | implementation/history exists | PRESENT_NOT_C0_EXECUTED | no |
| Kernel v2 extrude | implementation/history exists | PRESENT_NOT_C0_EXECUTED | no general D stage |
| Kernel v2 boolean | implementation/history exists | PRESENT_NOT_C0_EXECUTED | no general D stage |
| Kernel v2 revolve | implementation/history exists | PRESENT_NOT_C0_EXECUTED | no |
| Kernel v2 loft | implementation/history exists | PRESENT_NOT_C0_EXECUTED | no |
| Kernel v2 sweep | implementation/history exists | PRESENT_NOT_C0_EXECUTED | no |
| Kernel v2 shell | implementation/history exists | PRESENT_NOT_C0_EXECUTED | no |
| Decorative pattern engines | implementation/history exists | PRESENT_NOT_C0_EXECUTED | no current D proof |
| Production render/package | prior Macroblock C implementation exists; not executed by C0 #1 workflow | PRESENT_NOT_C0_EXECUTED in C0 | downstream in C branch/history |

## 6. What C0 #1 proves

C0 #1 proves all of the following simultaneously:

1. modern morphology still executes;
2. native surface text still executes;
3. hybrid BRep composition still executes;
4. subtractive boolean, geometric decoration, text emboss and SVG deboss still execute together on one BRep hybrid object;
5. JSON composition still executes;
6. multicolor 3MF still executes with one printable compound object and three material components;
7. manufacturability still executes;
8. these capability families coexist without test failure in the same branch.

## 7. What C0 #1 does NOT prove

C0 #1 does not prove:

1. that the modern D morphology output can receive the validated BRep text operation;
2. that the modern D morphology output can receive the validated Phase 4 hybrid BRep operations;
3. that Kernel v2 operations are currently called on D morphology output;
4. that the eight visual benchmark objects accumulate text, relief, boolean decoration and multicolor physically on the same bodies;
5. that any mesh/BRep conversion or bridge is required. The repository currently only proves that the paths use different representations and are not composed by `DoboStructuralPipeline`.

The last point is important: **this verdict does not authorize building a bridge yet**. It records only the integration gap.

## 8. First proven point of capability loss

The first proven integration cut is the output boundary of the current structural generator:

`semantic/structural program -> HierarchicalFeatureVesselEngine -> mesh`

After this point the function proceeds directly to `ThreeMFMeshExporter`.

The validated `surface_designer` hybrid/text composition path is not invoked between generated body and export.

Therefore the first proven problem is:

> A modern morphology can be generated, and the repository can separately execute text/boolean/decoration/multicolor composition, but there is no direct execution evidence showing those validated composition operations being applied to the modern morphology result before export.

This statement is demonstrated by code flow plus C0 passing tests; it is not an architectural hypothesis.

## 9. No-build decision gate

Before any new adapter, bridge, engine, composer, refactor or geometry representation is implemented, the next technical action must answer one binary question using executable evidence:

> Can an existing validated composition path accept or reuse the current modern morphology result without adding a new geometry subsystem?

Allowed outcomes:

- **YES** — reconnect using the existing path and protect it with an integration test.
- **NO** — record the exact failing API/representation contract and only then authorize the smallest missing compatibility change.

No other architectural work is authorized by this verdict.

## 10. Permanent accumulation rule

From this verdict onward, a capability is considered part of DOBO only when both conditions are true:

1. its own capability test passes;
2. at least one cumulative integration test proves it still operates with all previously accepted capabilities relevant to that product path.

A future change that removes an accepted capability from the cumulative path is a regression, regardless of whether its isolated unit test still passes.

## 11. Final verdict

**There is no evidence that DOBO needs another geometry engine at this stage.**

There is direct evidence that:

- multiple valuable capability stacks exist and still execute;
- the modern D structural path uses only a subset of them;
- the old BRep hybrid stack already combines several features that D1/D2 visually failed to show;
- the current structural path bypasses that validated composition stack before final mesh/3MF export.

Therefore the next action is not new architecture. It is an executable compatibility test at this exact boundary. Only the result of that test may determine whether any compatibility code is actually necessary.
