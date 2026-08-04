"""
DOBO CAD Kernel

Boolean Engine

Combines Solid geometry with the current ModelState.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import cadquery as cq

from kernel.contracts.boolean_request import (
    BooleanOperation,
    BooleanRequest,
)
from kernel.contracts.model_state import ModelState
from kernel.contracts.solid import (
    BoundingBox,
    Solid,
    SolidValidation,
)


class BooleanEngineInterface(ABC):
    """
    Public interface implemented by Boolean Engines.
    """

    @abstractmethod
    def apply(
        self,
        model: ModelState,
        request: BooleanRequest,
    ) -> ModelState:
        """
        Applies one boolean operation and returns
        a new immutable ModelState.
        """


class BooleanEngine(BooleanEngineInterface):
    """
    Initial Boolean Engine implementation.

    Supports:

    - union
    - cut
    - intersect
    """

    def apply(
        self,
        model: ModelState,
        request: BooleanRequest,
    ) -> ModelState:
        """
        Applies a BooleanRequest to ModelState.
        """

        model.validate()
        request.validate()

        operand = request.operand

        if operand is None:
            raise ValueError(
                "BooleanRequest requires an operand."
            )

        if model.is_empty:
            return self._apply_to_empty_model(
                model=model,
                request=request,
                operand=operand,
            )

        base_solid = model.solid

        if base_solid is None:
            raise RuntimeError(
                "Non-empty ModelState requires a Solid."
            )

        base_geometry = base_solid.geometry
        operand_geometry = operand.geometry

        if not isinstance(
            base_geometry,
            cq.Shape,
        ):
            raise TypeError(
                "BooleanEngine requires the current "
                "ModelState geometry to be a CadQuery Shape."
            )

        if not isinstance(
            operand_geometry,
            cq.Shape,
        ):
            raise TypeError(
                "BooleanEngine requires the operand "
                "geometry to be a CadQuery Shape."
            )

        try:
            if (
                request.operation
                == BooleanOperation.UNION
            ):
                result_geometry = (
                    base_geometry.fuse(
                        operand_geometry,
                        tol=request.tolerance,
                    )
                )

            elif (
                request.operation
                == BooleanOperation.CUT
            ):
                result_geometry = (
                    base_geometry.cut(
                        operand_geometry,
                        tol=request.tolerance,
                    )
                )

            elif (
                request.operation
                == BooleanOperation.INTERSECT
            ):
                result_geometry = (
                    base_geometry.intersect(
                        operand_geometry,
                    )
                )

            else:
                raise ValueError(
                    "Unsupported boolean operation: "
                    f"{request.operation}"
                )

        except Exception as error:
            raise RuntimeError(
                "BooleanEngine could not apply "
                f"operation '{request.operation.value}'."
            ) from error

        result_solid = self._build_solid(
            geometry=result_geometry,
            source=(
                "boolean_engine:"
                f"{request.operation.value}"
            ),
            metadata={
                "request_id": request.id,
                "operation": (
                    request.operation.value
                ),
                "operand_id": operand.id,
                "tolerance": request.tolerance,
                **request.metadata,
            },
        )

        return model.with_solid(
            solid=result_solid,
            operation=request.operation.value,
            source_id=request.id,
            label=request.label,
            metadata={
                "operand_id": operand.id,
                "priority": request.priority,
            },
        )

    def _apply_to_empty_model(
        self,
        model: ModelState,
        request: BooleanRequest,
        operand: Solid,
    ) -> ModelState:
        """
        Handles operations against an empty ModelState.

        Union initializes the model.

        Cut and intersect require an existing base solid.
        """

        if (
            request.operation
            != BooleanOperation.UNION
        ):
            raise ValueError(
                "An empty ModelState can only be "
                "initialized with a union operation."
            )

        operand.validate()

        return model.with_solid(
            solid=operand,
            operation=request.operation.value,
            source_id=request.id,
            label=request.label,
            metadata={
                "initialized_model": True,
                "operand_id": operand.id,
            },
        )

    @staticmethod
    def _build_solid(
        geometry: cq.Shape,
        source: str,
        metadata: dict[str, object],
    ) -> Solid:
        """
        Converts backend geometry into a validated
        Solid contract.
        """

        if not isinstance(
            geometry,
            cq.Shape,
        ):
            raise TypeError(
                "Boolean result must be "
                "a CadQuery Shape."
            )

        is_valid = bool(
            geometry.isValid()
        )

        volume = float(
            geometry.Volume()
        )

        if volume <= 0:
            raise RuntimeError(
                "Boolean operation produced "
                "zero-volume geometry."
            )

        center = geometry.Center()
        box = geometry.BoundingBox()

        errors: tuple[str, ...] = ()

        if not is_valid:
            errors = (
                "CAD backend reports invalid geometry.",
            )

        solid = Solid(
            geometry=geometry,
            volume=volume,
            center_of_mass=(
                float(center.x),
                float(center.y),
                float(center.z),
            ),
            bounding_box=BoundingBox(
                minimum=(
                    float(box.xmin),
                    float(box.ymin),
                    float(box.zmin),
                ),
                maximum=(
                    float(box.xmax),
                    float(box.ymax),
                    float(box.zmax),
                ),
            ),
            validation=SolidValidation(
                is_valid=is_valid,
                is_closed=is_valid,
                is_manifold=is_valid,
                is_watertight=is_valid,
                errors=errors,
                warnings=(),
            ),
            source=source,
            metadata=dict(metadata),
        )

        solid.validate()

        return solid