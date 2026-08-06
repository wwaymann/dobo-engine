"""
DOBO CAD Kernel

Solid Factory

Converts validated backend geometry into the public
Kernel Solid contract.
"""

from __future__ import annotations

from typing import Any

import cadquery as cq

from kernel.contracts.solid import (
    BoundingBox,
    Solid,
    SolidValidation,
)


class SolidFactory:
    """
    Builds Kernel Solid contracts from CadQuery shapes.
    """

    @staticmethod
    def from_shape(
        *,
        geometry: cq.Shape,
        source: str,
        metadata: dict[str, Any] | None = None,
    ) -> Solid:
        """
        Builds and validates one Solid contract.
        """

        if not isinstance(
            geometry,
            cq.Shape,
        ):
            raise TypeError(
                "SolidFactory geometry must be "
                "a CadQuery Shape."
            )

        if not geometry.isValid():
            raise ValueError(
                "SolidFactory cannot use invalid "
                "CadQuery geometry."
            )

        if not isinstance(
            source,
            str,
        ) or not source.strip():
            raise ValueError(
                "SolidFactory source cannot be empty."
            )

        if (
            metadata is not None
            and not isinstance(
                metadata,
                dict,
            )
        ):
            raise TypeError(
                "SolidFactory metadata must be "
                "a dictionary."
            )

        volume = float(
            geometry.Volume()
        )

        if volume <= 0.0:
            raise ValueError(
                "SolidFactory geometry volume must "
                "be greater than zero."
            )

        center = geometry.Center()

        backend_bounds = (
            geometry.BoundingBox()
        )

        bounding_box = BoundingBox(
            minimum=(
                float(
                    backend_bounds.xmin
                ),
                float(
                    backend_bounds.ymin
                ),
                float(
                    backend_bounds.zmin
                ),
            ),
            maximum=(
                float(
                    backend_bounds.xmax
                ),
                float(
                    backend_bounds.ymax
                ),
                float(
                    backend_bounds.zmax
                ),
            ),
        )

        bounding_box.validate()

        solid = Solid(
            geometry=geometry,
            volume=volume,
            center_of_mass=(
                float(
                    center.x
                ),
                float(
                    center.y
                ),
                float(
                    center.z
                ),
            ),
            bounding_box=bounding_box,
            validation=SolidValidation(
                is_valid=True,
                is_closed=True,
                is_manifold=True,
                is_watertight=True,
                errors=(),
                warnings=(),
            ),
            source=source,
            metadata=dict(
                metadata
                if metadata is not None
                else {}
            ),
        )

        solid.validate()

        return solid