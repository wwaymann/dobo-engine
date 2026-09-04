# C0 Accumulated Baseline Execution

Purpose: trigger the existing Macroblock B autonomous regression workflow without modifying engine behavior.

Candidate baseline source: accepted Macroblock B checkpoint 3a87788ec8e9ec4c1a6d12647ddc3e8f662129a6.

Acceptance rule: this tree is eligible to become C0_BASELINE only if the existing Macroblock B autonomous workflow passes unchanged, including Macroblock A regressions, consolidated manufacturing contract, final geometry, repair controller, production orientation, planned 3MF export, physical 3MF placement, real product validation, repair audit, production handoff, and production evidence upload.

No engine, geometry, text, decoration, boolean, manufacturing, or export code is changed by this marker.
