# DOBO Macroblock B Autopilot

Status: Active

Macroblock B combines Blocks 9 and 10:

- manufacturability and bounded self-repair
- advanced production validation

The autonomous battery preserves the complete Macroblock A regression suite,
then validates the 24-rule manufacturing contract, bounded repair behavior,
and the current real-product manufacturing baseline.

Repair policy is conservative: every candidate is followed by full 24-rule
revalidation and is accepted only when it improves the targeted failure without
introducing a new blocking regression. SOURCE_PENDING and NOT_AVAILABLE are not
invented into geometry failures.

Next integration targets are real geometric sources for CLEARANCE, OVERHANG and
TEXT_PRINTABLE_STROKE, followed by deterministic repair strategies and repeated
production revalidation.
