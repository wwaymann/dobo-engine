from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RuleSeverity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"


class RuleGroup(str, Enum):
    FINAL_PRODUCT = "final_product"
    STRUCTURAL_BODY = "structural_body"
    TEXT = "text"
    DECORATION = "decoration"
    COLOR = "color"
    PRODUCTION = "production"


@dataclass(frozen=True, slots=True)
class ManufacturingRule:
    code: str
    group: RuleGroup
    severity: RuleSeverity


RULES: tuple[ManufacturingRule, ...] = (
    ManufacturingRule("CAD_VALID", RuleGroup.FINAL_PRODUCT, RuleSeverity.ERROR),
    ManufacturingRule("CONNECTED_FINAL_PRODUCT", RuleGroup.FINAL_PRODUCT, RuleSeverity.ERROR),
    ManufacturingRule("NO_DEGENERATE_GEOMETRY", RuleGroup.FINAL_PRODUCT, RuleSeverity.ERROR),
    ManufacturingRule("CLEARANCE", RuleGroup.FINAL_PRODUCT, RuleSeverity.WARNING),
    ManufacturingRule("OVERHANG", RuleGroup.FINAL_PRODUCT, RuleSeverity.WARNING),

    ManufacturingRule("STRUCTURAL_WALL_THICKNESS", RuleGroup.STRUCTURAL_BODY, RuleSeverity.ERROR),
    ManufacturingRule("BASE_CONTACT_AREA", RuleGroup.STRUCTURAL_BODY, RuleSeverity.WARNING),
    ManufacturingRule("BASE_STABILITY", RuleGroup.STRUCTURAL_BODY, RuleSeverity.ERROR),
    ManufacturingRule("INTERNAL_VOLUME", RuleGroup.STRUCTURAL_BODY, RuleSeverity.ERROR),
    ManufacturingRule("DRAINAGE_PATH", RuleGroup.STRUCTURAL_BODY, RuleSeverity.ERROR),
    ManufacturingRule("NO_UNINTENDED_CLOSED_CAVITIES", RuleGroup.STRUCTURAL_BODY, RuleSeverity.WARNING),

    ManufacturingRule("TEXT_PRINTABLE_STROKE", RuleGroup.TEXT, RuleSeverity.WARNING),
    ManufacturingRule("TEXT_DEPTH", RuleGroup.TEXT, RuleSeverity.WARNING),
    ManufacturingRule("TEXT_REGION_VOLUME", RuleGroup.TEXT, RuleSeverity.WARNING),

    ManufacturingRule("DECORATION_FEATURE_SIZE", RuleGroup.DECORATION, RuleSeverity.WARNING),
    ManufacturingRule("DECORATION_REGION_VOLUME", RuleGroup.DECORATION, RuleSeverity.WARNING),

    ManufacturingRule("COLOR_REGIONS_VALID", RuleGroup.COLOR, RuleSeverity.ERROR),
    ManufacturingRule("COLOR_REGION_MIN_VOLUME", RuleGroup.COLOR, RuleSeverity.WARNING),
    ManufacturingRule("COLOR_REGION_CONNECTIVITY", RuleGroup.COLOR, RuleSeverity.WARNING),
    ManufacturingRule("COLOR_INTERFACE_INTEGRITY", RuleGroup.COLOR, RuleSeverity.ERROR),

    ManufacturingRule("PHYSICAL_SIZE_LIMITS", RuleGroup.PRODUCTION, RuleSeverity.ERROR),
    ManufacturingRule("ORIENTATION_ON_BED", RuleGroup.PRODUCTION, RuleSeverity.ERROR),
    ManufacturingRule("MULTICOLOR_3MF_INTEGRITY", RuleGroup.PRODUCTION, RuleSeverity.ERROR),
    ManufacturingRule("FILAMENT_ASSIGNMENT", RuleGroup.PRODUCTION, RuleSeverity.ERROR),
)

RULE_BY_CODE = {rule.code: rule for rule in RULES}
