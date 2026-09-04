# DOBO Consolidation Charter

Status: BINDING for `integration-consolidation-core`

## 1. Purpose

`integration-consolidation-core` exists to CONSOLIDATE the capabilities already built in DOBO into one coherent end-to-end engine. Its default purpose is not to invent replacement capabilities.

The target is a single orchestrated path from intent to manufacturable artifact that reuses the strongest existing implementation for each responsibility.

## 2. Non-negotiable rule: reuse before creation

Before writing a new implementation for any capability, the consolidation work MUST:

1. Search the repository and relevant historical branches for existing implementations.
2. Identify the existing candidates by module/path and behavior.
3. Test or inspect whether each candidate satisfies the required contract.
4. Prefer reconnection/adaptation/orchestration of an existing candidate.
5. Create a new capability only when the existing candidates are demonstrably absent or unsuitable.
6. Record the evidence for that exception.

A new implementation without this evidence is a consolidation failure.

## 3. No technology dogma

DOBO is not a voxel-only, primitive-only, CAD-only, SDF-only, mesh-only, or AI-only engine.

The pipeline MUST select the existing representation best suited to the operation while preserving conversion boundaries explicitly.

Examples:
- Analytic/CAD primitives should remain analytic when that preserves exact mechanical geometry.
- Native CAD surface text should be preferred for crisp text when available.
- Volumetric/SDF processing may be used for morphology where it is advantageous.
- Mesh conversion should occur when required for downstream fabrication/export, not automatically at the earliest stage.

No representation may become the universal route merely because it is convenient for one subsystem.

## 4. Capability preservation

A consolidation change MUST NOT silently replace, disable, bypass, or regress an already demonstrated capability.

Every change must state:
- capability being connected or repaired;
- existing implementation being reused;
- pipeline entry and exit points;
- capabilities that must remain unchanged;
- acceptance tests used before and after the change.

If a change improves one capability but regresses another accepted capability, the change is NOT accepted as consolidated.

## 5. Pipeline orchestration rule

The consolidated pipeline is an ORCHESTRATOR of capabilities.

Intent -> semantic contract -> capability routing -> geometry/surface operations -> manufacturability -> artifact/export.

Each stage should call a registered existing capability through an explicit contract. Stages must not recreate downstream functionality locally merely to make one test pass.

## 6. Capability decision protocol

Before implementation, use this decision sequence:

A. What capability is requested?
B. Where does that capability already exist?
C. Which implementation is authoritative/best evidenced?
D. Can it be connected to the current pipeline through an adapter or existing contract?
E. What conversions are required, and do they lose fidelity?
F. What existing capabilities could regress?
G. What tests prove preservation and end-to-end operation?

Only if B-D fail with evidence may a new implementation be proposed.

## 7. Representation and fidelity rule

Conversions are architectural boundaries and must be justified.

In particular:
- Do not voxelize exact geometry merely because another feature uses voxels.
- Do not rasterize/vectorize repeatedly when an existing vector/CAD representation is available.
- Do not remesh before an operation that benefits from analytic surfaces unless required.
- Preserve semantic parameters across conversions so later capabilities can still operate on intent, not reverse-engineer geometry.

## 8. Source of truth and capability registry

`docs/CAPABILITY_REGISTRY.md` is the living map of reusable DOBO capabilities.

For each capability it records:
- capability name;
- implementation path(s);
- representation/technology;
- status: ACTIVE, CANDIDATE, LEGACY, SUPERSEDED, or UNKNOWN;
- known tests/evidence;
- current pipeline connection;
- known limitations.

The registry must be consulted before adding implementation code.

## 9. Change gate

A consolidation commit is acceptable only when:

- Existing-capability search was performed.
- Reuse decision is documented.
- No accepted capability is knowingly regressed.
- Relevant unit/integration gates pass, or failures are explicitly reported as blockers.
- Visual/physical evidence is used where geometry quality cannot be proven by unit tests alone.
- The commit does not claim success merely because code was written or CI started.

`PASS` means behavior was demonstrated. `IMPLEMENTED` is not equivalent to `PASS`.

## 10. Failed experiments

Failed experiments are evidence, not new architecture.

A failed experimental route must not become the default pipeline merely because it exists in the latest commit. It should be reverted, disabled, or marked SUPERSEDED once a better existing capability is selected.

## 11. Current text case: binding architectural decision

The recent text tests demonstrate that voxel/SDF text in the structural field does not provide acceptable typographic fidelity at reasonable cost.

The repository already contains native CAD surface-text capabilities under `app/product_generators/surface_designer/`, including native cylindrical text projection. Therefore the consolidation direction for cylindrical text is to RECONNECT and validate that existing capability, not continue inventing voxel-text variants.

Multiline semantic/layout behavior that has already been demonstrated must be preserved while reconnecting the native surface-text implementation.

## 12. Working discipline

For every future consolidation task, the work report must use these headings:

- Requested capability
- Existing capability candidates
- Selected existing implementation
- Why it is selected
- Pipeline connection point
- Preserved capabilities
- Tests/gates
- Result: PASS / FAIL / BLOCKED

If the selected route changes, the reason must be stated BEFORE implementing the new route.

## 13. Deletion and cleanup

DOBO should not accumulate indefinite parallel implementations.

After a capability is consolidated and validated:
1. identify redundant/superseded routes;
2. verify no callers still require them;
3. mark or remove them in a separate cleanup change;
4. update the capability registry.

Deletion is evidence-driven; old code is not removed merely because it looks unused.

## 14. Authority

For work on `integration-consolidation-core`, this charter overrides ad-hoc implementation convenience. When a proposed code change conflicts with this charter, stop and resolve the architectural conflict first.
