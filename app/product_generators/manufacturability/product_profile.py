from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProductManufacturingProfile:
    product_type: str = "planter"
    expected_final_solid_count: int = 1
    min_internal_volume: float = 1000.0
    required_drainage_count: int = 1
    allow_closed_cavities: bool = False

    def validate(self) -> None:
        if not self.product_type.strip():
            raise ValueError("product_type must not be empty.")

        if self.expected_final_solid_count < 1:
            raise ValueError(
                "expected_final_solid_count must be >= 1."
            )

        if self.min_internal_volume <= 0.0:
            raise ValueError(
                "min_internal_volume must be positive."
            )

        if self.required_drainage_count < 0:
            raise ValueError(
                "required_drainage_count must be >= 0."
            )
