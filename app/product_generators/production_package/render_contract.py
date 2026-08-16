from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RenderIntent(str, Enum):
    COMMERCIAL = "commercial"
    PRODUCTION = "production"
    THUMBNAIL = "thumbnail"


@dataclass(frozen=True, slots=True)
class RenderView:
    name: str
    direction: tuple[float, float, float]
    width_px: int
    height_px: int
    transparent_background: bool = False

    def validate(self) -> None:
        if not self.name:
            raise ValueError("Render view name is required.")
        if self.width_px <= 0 or self.height_px <= 0:
            raise ValueError("Render dimensions must be positive.")
        if len(self.direction) != 3 or not any(abs(value) > 1.0e-9 for value in self.direction):
            raise ValueError("Render direction must be a non-zero 3D vector.")


@dataclass(frozen=True, slots=True)
class RenderContract:
    schema_version: str
    intent: RenderIntent
    views: tuple[RenderView, ...]

    SCHEMA_VERSION = "dobo.render-contract.v1"

    def validate(self) -> None:
        if self.schema_version != self.SCHEMA_VERSION:
            raise ValueError(f"Unsupported render contract: {self.schema_version}")
        if not self.views:
            raise ValueError("Render contract requires at least one view.")
        names: set[str] = set()
        for view in self.views:
            view.validate()
            if view.name in names:
                raise ValueError(f"Duplicate render view: {view.name}")
            names.add(view.name)

    @classmethod
    def standard(cls, intent: RenderIntent) -> "RenderContract":
        if intent is RenderIntent.COMMERCIAL:
            views = (
                RenderView("hero_iso", (1.0, -1.0, 0.72), 1600, 1600),
                RenderView("front", (0.0, -1.0, 0.18), 1400, 1400),
            )
        elif intent is RenderIntent.PRODUCTION:
            views = (
                RenderView("front", (0.0, -1.0, 0.0), 1200, 1200, True),
                RenderView("side", (1.0, 0.0, 0.0), 1200, 1200, True),
                RenderView("top", (0.0, 0.0, 1.0), 1200, 1200, True),
                RenderView("iso", (1.0, -1.0, 0.75), 1200, 1200, True),
            )
        elif intent is RenderIntent.THUMBNAIL:
            views = (RenderView("thumbnail", (1.0, -1.0, 0.72), 512, 512),)
        else:
            raise ValueError(f"Unsupported render intent: {intent!r}")
        contract = cls(schema_version=cls.SCHEMA_VERSION, intent=intent, views=views)
        contract.validate()
        return contract
