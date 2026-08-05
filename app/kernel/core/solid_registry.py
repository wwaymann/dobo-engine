"""DOBO CAD Kernel - Solid Registry."""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from kernel.contracts.solid import Solid


@dataclass(slots=True)
class SolidRegistry:
    """Stores validated Solid contracts by stable output identifiers."""

    _solids: dict[str, Solid] = field(default_factory=dict, init=False, repr=False)

    def register(self, output_id: str, solid: Solid, *, overwrite: bool = False) -> None:
        key = self._normalize_identifier(output_id)
        if not isinstance(solid, Solid):
            raise TypeError("SolidRegistry accepts Solid contracts only.")
        solid.validate()
        if key in self._solids and not overwrite:
            raise ValueError(f"SolidRegistry already contains '{key}'.")
        self._solids[key] = solid

    def get(self, output_id: str) -> Solid:
        key = self._normalize_identifier(output_id)
        try:
            return self._solids[key]
        except KeyError as error:
            available = ", ".join(self.ids) or "<none>"
            raise KeyError(
                f"SolidRegistry does not contain '{key}'. Available: {available}"
            ) from error

    def require_many(self, *output_ids: str) -> tuple[Solid, ...]:
        return tuple(self.get(output_id) for output_id in output_ids)

    def remove(self, output_id: str) -> Solid:
        key = self._normalize_identifier(output_id)
        try:
            return self._solids.pop(key)
        except KeyError as error:
            raise KeyError(f"SolidRegistry does not contain '{key}'.") from error

    def contains(self, output_id: str) -> bool:
        return self._normalize_identifier(output_id) in self._solids

    def clear(self) -> None:
        self._solids.clear()

    def snapshot(self) -> dict[str, Solid]:
        return dict(self._solids)

    def validate(self) -> None:
        for output_id, solid in self._solids.items():
            self._normalize_identifier(output_id)
            if not isinstance(solid, Solid):
                raise TypeError("SolidRegistry contains a non-Solid value.")
            solid.validate()

    @property
    def count(self) -> int:
        return len(self._solids)

    @property
    def is_empty(self) -> bool:
        return self.count == 0

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(self._solids.keys())

    @property
    def solids(self) -> tuple[Solid, ...]:
        return tuple(self._solids.values())

    @property
    def latest_id(self) -> str | None:
        return None if self.is_empty else self.ids[-1]

    @property
    def latest(self) -> Solid | None:
        latest_id = self.latest_id
        return None if latest_id is None else self._solids[latest_id]

    def __len__(self) -> int:
        return self.count

    def __contains__(self, output_id: object) -> bool:
        return isinstance(output_id, str) and self.contains(output_id)

    def __iter__(self) -> Iterator[tuple[str, Solid]]:
        return iter(self._solids.items())

    @staticmethod
    def _normalize_identifier(value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("SolidRegistry identifier must be a string.")
        normalized = value.strip()
        if not normalized:
            raise ValueError("SolidRegistry identifier cannot be empty.")
        return normalized