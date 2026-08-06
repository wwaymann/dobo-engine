"""
DOBO CAD Kernel

Modeling Operation Executor

Executes transformations, detail operations and patterns
over an existing Kernel Solid.
"""

from __future__ import annotations

import math
from typing import Any

import cadquery as cq

from kernel.contracts.operations.modeling_operation import (
    ModelingOperation,
    ModelingTool,
)
from kernel.core.execution_context import (
    KernelExecutionContext,
)
from kernel.core.operation_executor import (
    OperationExecutor,
    OperationExecutorPayload,
)
from kernel.geometry.solid_factory import (
    SolidFactory,
)


Vector3 = tuple[
    float,
    float,
    float,
]


class ModelingOperationExecutor(
    OperationExecutor[ModelingOperation],
):
    """
    Executes general modeling operations over
    existing CadQuery geometry.
    """

    @property
    def operation_class(
        self,
    ) -> type[ModelingOperation]:
        """
        Returns the supported operation contract.
        """

        return ModelingOperation

    def _execute(
        self,
        operation: ModelingOperation,
        context: KernelExecutionContext,
    ) -> OperationExecutorPayload:
        """
        Executes one ModelingOperation.
        """

        operation.validate()
        context.validate()

        source = context.solids.get(
            operation.source_id
        )

        source.validate()

        geometry = source.geometry

        if not isinstance(
            geometry,
            cq.Shape,
        ):
            raise TypeError(
                "ModelingOperation source geometry "
                "must be a CadQuery Shape."
            )

        result_shape = self._apply(
            geometry=geometry,
            tool=operation.tool,
            parameters=operation.parameters,
        )

        if not isinstance(
            result_shape,
            cq.Shape,
        ):
            raise RuntimeError(
                "Modeling operation did not produce "
                "a CadQuery Shape."
            )

        try:
            result_shape = (
                result_shape.clean()
            )

        except Exception as error:
            raise RuntimeError(
                "Modeling operation could not clean "
                "the resulting geometry."
            ) from error

        if not result_shape.isValid():
            raise RuntimeError(
                f"{operation.tool.value} generated "
                "invalid geometry."
            )

        solid = SolidFactory.from_shape(
            geometry=result_shape,
            source="modeling_operation_executor",
            metadata={
                "source_id": (
                    operation.source_id
                ),
                "output_id": (
                    operation.output_id
                ),
                "tool": (
                    operation.tool.value
                ),
                "parameters": dict(
                    operation.parameters
                ),
                **operation.metadata,
            },
        )

        solid.validate()

        context.log(
            level="info",
            message=(
                "Modeling operation "
                f"'{operation.tool.value}' generated "
                f"'{operation.output_id}'."
            ),
            operation_id=operation.id,
            metadata={
                "source_id": (
                    operation.source_id
                ),
                "output_id": (
                    operation.output_id
                ),
                "tool": (
                    operation.tool.value
                ),
                "volume": solid.volume,
            },
        )

        return OperationExecutorPayload(
            output_id=operation.output_id,
            solid=solid,
            metadata={
                "executor": (
                    "modeling_operation_executor"
                ),
                "tool": (
                    operation.tool.value
                ),
                "source_id": (
                    operation.source_id
                ),
                "output_id": (
                    operation.output_id
                ),
                "volume": solid.volume,
            },
        )

    def _apply(
        self,
        *,
        geometry: cq.Shape,
        tool: ModelingTool,
        parameters: dict[
            str,
            Any,
        ],
    ) -> cq.Shape:
        """
        Applies one concrete modeling tool.
        """

        if tool is ModelingTool.MOVE:
            return self._apply_move(
                geometry,
                parameters,
            )

        if tool is ModelingTool.ROTATE:
            return self._apply_rotate(
                geometry,
                parameters,
            )

        if tool is ModelingTool.SCALE:
            return self._apply_scale(
                geometry,
                parameters,
            )

        if tool is ModelingTool.MIRROR:
            return self._apply_mirror(
                geometry,
                parameters,
            )

        if tool is ModelingTool.FILLET:
            return self._apply_fillet(
                geometry,
                parameters,
            )

        if tool is ModelingTool.CHAMFER:
            return self._apply_chamfer(
                geometry,
                parameters,
            )

        if tool is ModelingTool.DRAFT:
            return self._apply_draft(
                geometry,
                parameters,
            )

        if tool is ModelingTool.LINEAR_PATTERN:
            return self._apply_linear_pattern(
                geometry,
                parameters,
            )

        if tool is ModelingTool.CIRCULAR_PATTERN:
            return self._apply_circular_pattern(
                geometry,
                parameters,
            )

        raise ValueError(
            "Unsupported ModelingTool: "
            f"'{tool.value}'."
        )

    def _apply_move(
        self,
        geometry: cq.Shape,
        parameters: dict[
            str,
            Any,
        ],
    ) -> cq.Shape:
        """
        Translates geometry by one vector.
        """

        vector = self._vector3(
            parameters.get(
                "vector"
            ),
            "vector",
        )

        try:
            translated = geometry.translate(
                cq.Vector(
                    vector[0],
                    vector[1],
                    vector[2],
                )
            )

        except Exception as error:
            raise RuntimeError(
                "Move operation could not translate "
                "the source geometry."
            ) from error

        if not isinstance(
            translated,
            cq.Shape,
        ):
            raise RuntimeError(
                "Move operation did not produce "
                "a CadQuery Shape."
            )

        return translated

    def _apply_rotate(
        self,
        geometry: cq.Shape,
        parameters: dict[
            str,
            Any,
        ],
    ) -> cq.Shape:
        """
        Rotates geometry around one axis.
        """

        origin = self._vector3(
            parameters.get(
                "axis_origin",
                (
                    0.0,
                    0.0,
                    0.0,
                ),
            ),
            "axis_origin",
        )

        direction = self._vector3(
            parameters.get(
                "axis_direction"
            ),
            "axis_direction",
        )

        self._require_nonzero_vector(
            direction,
            "axis_direction",
        )

        angle = self._number(
            parameters.get(
                "angle"
            ),
            "angle",
        )

        axis_end = (
            origin[0]
            + direction[0],
            origin[1]
            + direction[1],
            origin[2]
            + direction[2],
        )

        try:
            rotated = geometry.rotate(
                cq.Vector(
                    origin[0],
                    origin[1],
                    origin[2],
                ),
                cq.Vector(
                    axis_end[0],
                    axis_end[1],
                    axis_end[2],
                ),
                angle,
            )

        except Exception as error:
            raise RuntimeError(
                "Rotate operation could not rotate "
                "the source geometry."
            ) from error

        if not isinstance(
            rotated,
            cq.Shape,
        ):
            raise RuntimeError(
                "Rotate operation did not produce "
                "a CadQuery Shape."
            )

        return rotated

    def _apply_scale(
        self,
        geometry: cq.Shape,
        parameters: dict[
            str,
            Any,
        ],
    ) -> cq.Shape:
        """
        Applies uniform scaling.
        """

        factor = self._number(
            parameters.get(
                "factor"
            ),
            "factor",
        )

        if factor <= 0.0:
            raise ValueError(
                "Scale factor must be greater "
                "than zero."
            )

        try:
            scaled = geometry.scale(
                factor
            )

        except Exception as error:
            raise RuntimeError(
                "Scale operation could not scale "
                "the source geometry."
            ) from error

        if not isinstance(
            scaled,
            cq.Shape,
        ):
            raise RuntimeError(
                "Scale operation did not produce "
                "a CadQuery Shape."
            )

        return scaled

    def _apply_mirror(
        self,
        geometry: cq.Shape,
        parameters: dict[
            str,
            Any,
        ],
    ) -> cq.Shape:
        """
        Mirrors geometry across a principal plane.
        """

        plane = parameters.get(
            "plane",
            "YZ",
        )

        if not isinstance(
            plane,
            str,
        ):
            raise TypeError(
                "Mirror plane must be a string."
            )

        normalized_plane = (
            plane.upper()
        )

        if normalized_plane not in (
            "XY",
            "XZ",
            "YZ",
        ):
            raise ValueError(
                "Mirror plane must be XY, XZ or YZ."
            )

        base_point = self._vector3(
            parameters.get(
                "base_point",
                (
                    0.0,
                    0.0,
                    0.0,
                ),
            ),
            "base_point",
        )

        try:
            workplane = cq.Workplane(
                obj=geometry
            )

            mirrored_workplane = (
                workplane.mirror(
                    mirrorPlane=(
                        normalized_plane
                    ),
                    basePointVector=(
                        base_point
                    ),
                    union=False,
                )
            )

            mirrored_value = (
                mirrored_workplane.val()
            )

        except Exception as error:
            raise RuntimeError(
                "Mirror operation could not mirror "
                "the source geometry."
            ) from error

        if not isinstance(
            mirrored_value,
            cq.Shape,
        ):
            raise RuntimeError(
                "Mirror operation did not produce "
                "a CadQuery Shape."
            )

        return mirrored_value

    def _apply_fillet(
        self,
        geometry: cq.Shape,
        parameters: dict[
            str,
            Any,
        ],
    ) -> cq.Shape:
        """
        Applies a fillet to selected edges.
        """

        radius = self._number(
            parameters.get(
                "radius"
            ),
            "radius",
        )

        if radius <= 0.0:
            raise ValueError(
                "Fillet radius must be greater "
                "than zero."
            )

        edges = self._selected_edges(
            geometry,
            parameters.get(
                "edge_indices",
                (),
            ),
        )

        if not edges:
            raise ValueError(
                "Fillet operation requires at least "
                "one selected edge."
            )

        try:
            workplane = cq.Workplane(
                obj=geometry
            )

            selected_edges = (
                workplane.newObject(
                    edges
                )
            )

            filleted_workplane = (
                selected_edges.fillet(
                    radius
                )
            )

            filleted_value = (
                filleted_workplane.val()
            )

        except Exception as error:
            raise RuntimeError(
                "Fillet operation could not modify "
                "the selected edges."
            ) from error

        if not isinstance(
            filleted_value,
            cq.Shape,
        ):
            raise RuntimeError(
                "Fillet operation did not produce "
                "a CadQuery Shape."
            )

        return filleted_value

    def _apply_chamfer(
        self,
        geometry: cq.Shape,
        parameters: dict[
            str,
            Any,
        ],
    ) -> cq.Shape:
        """
        Applies a chamfer to selected edges.
        """

        length = self._number(
            parameters.get(
                "length"
            ),
            "length",
        )

        if length <= 0.0:
            raise ValueError(
                "Chamfer length must be greater "
                "than zero."
            )

        edges = self._selected_edges(
            geometry,
            parameters.get(
                "edge_indices",
                (),
            ),
        )

        if not edges:
            raise ValueError(
                "Chamfer operation requires at least "
                "one selected edge."
            )

        try:
            workplane = cq.Workplane(
                obj=geometry
            )

            selected_edges = (
                workplane.newObject(
                    edges
                )
            )

            chamfered_workplane = (
                selected_edges.chamfer(
                    length
                )
            )

            chamfered_value = (
                chamfered_workplane.val()
            )

        except Exception as error:
            raise RuntimeError(
                "Chamfer operation could not modify "
                "the selected edges."
            ) from error

        if not isinstance(
            chamfered_value,
            cq.Shape,
        ):
            raise RuntimeError(
                "Chamfer operation did not produce "
                "a CadQuery Shape."
            )

        return chamfered_value

    def _apply_draft(
        self,
        geometry: cq.Shape,
        parameters: dict[
            str,
            Any,
        ],
    ) -> cq.Shape:
        """
        Applies draft to selected faces.
        """

        angle = self._number(
            parameters.get(
                "angle"
            ),
            "angle",
        )

        if not (
            -89.0
            < angle
            < 89.0
        ):
            raise ValueError(
                "Draft angle must be between "
                "-89 and 89 degrees."
            )

        direction = self._vector3(
            parameters.get(
                "direction",
                (
                    0.0,
                    0.0,
                    1.0,
                ),
            ),
            "direction",
        )

        self._require_nonzero_vector(
            direction,
            "direction",
        )

        face_indices = parameters.get(
            "face_indices",
            (),
        )

        faces = self._selected_faces(
            geometry,
            face_indices,
        )

        if not faces:
            raise ValueError(
                "Draft operation requires at least "
                "one selected face."
            )

        neutral_plane_index = (
            parameters.get(
                "neutral_plane_index",
                0,
            )
        )

        if isinstance(
            neutral_plane_index,
            bool,
        ) or not isinstance(
            neutral_plane_index,
            int,
        ):
            raise TypeError(
                "neutral_plane_index must be "
                "an integer."
            )

        all_faces = list(
            geometry.Faces()
        )

        try:
            neutral_plane = all_faces[
                neutral_plane_index
            ]

        except IndexError as error:
            raise IndexError(
                "Draft neutral_plane_index is "
                "outside the available face range."
            ) from error

        make_draft = getattr(
            geometry,
            "makeDraft",
            None,
        )

        if not callable(
            make_draft
        ):
            raise NotImplementedError(
                "The installed CadQuery version does "
                "not expose Shape.makeDraft()."
            )

        try:
            drafted = make_draft(
                faces,
                cq.Vector(
                    direction[0],
                    direction[1],
                    direction[2],
                ),
                math.radians(
                    angle
                ),
                neutral_plane,
            )

        except Exception as error:
            raise RuntimeError(
                "Draft operation could not modify "
                "the selected faces."
            ) from error

        if not isinstance(
            drafted,
            cq.Shape,
        ):
            raise RuntimeError(
                "Draft operation did not produce "
                "a CadQuery Shape."
            )

        return drafted

    def _apply_linear_pattern(
        self,
        geometry: cq.Shape,
        parameters: dict[
            str,
            Any,
        ],
    ) -> cq.Shape:
        """
        Creates a linear pattern.
        """

        direction = self._vector3(
            parameters.get(
                "direction"
            ),
            "direction",
        )

        self._require_nonzero_vector(
            direction,
            "direction",
        )

        spacing = self._number(
            parameters.get(
                "spacing"
            ),
            "spacing",
        )

        if spacing <= 0.0:
            raise ValueError(
                "Linear pattern spacing must be "
                "greater than zero."
            )

        count = self._positive_int(
            parameters.get(
                "count"
            ),
            "count",
        )

        copies: list[
            cq.Shape
        ] = []

        for index in range(
            count
        ):
            offset = cq.Vector(
                direction[0]
                * spacing
                * index,
                direction[1]
                * spacing
                * index,
                direction[2]
                * spacing
                * index,
            )

            translated = (
                geometry.translate(
                    offset
                )
            )

            if not isinstance(
                translated,
                cq.Shape,
            ):
                raise RuntimeError(
                    "Linear pattern copy did not "
                    "produce a CadQuery Shape."
                )

            copies.append(
                translated
            )

        return self._combine(
            copies
        )

    def _apply_circular_pattern(
        self,
        geometry: cq.Shape,
        parameters: dict[
            str,
            Any,
        ],
    ) -> cq.Shape:
        """
        Creates a circular pattern.
        """

        origin = self._vector3(
            parameters.get(
                "axis_origin",
                (
                    0.0,
                    0.0,
                    0.0,
                ),
            ),
            "axis_origin",
        )

        direction = self._vector3(
            parameters.get(
                "axis_direction",
                (
                    0.0,
                    0.0,
                    1.0,
                ),
            ),
            "axis_direction",
        )

        self._require_nonzero_vector(
            direction,
            "axis_direction",
        )

        total_angle = self._number(
            parameters.get(
                "total_angle",
                360.0,
            ),
            "total_angle",
        )

        if total_angle == 0.0:
            raise ValueError(
                "Circular pattern total_angle "
                "cannot be zero."
            )

        count = self._positive_int(
            parameters.get(
                "count"
            ),
            "count",
        )

        axis_end = (
            origin[0]
            + direction[0],
            origin[1]
            + direction[1],
            origin[2]
            + direction[2],
        )

        step = (
            total_angle
            / count
        )

        copies: list[
            cq.Shape
        ] = []

        for index in range(
            count
        ):
            rotated = geometry.rotate(
                cq.Vector(
                    origin[0],
                    origin[1],
                    origin[2],
                ),
                cq.Vector(
                    axis_end[0],
                    axis_end[1],
                    axis_end[2],
                ),
                step
                * index,
            )

            if not isinstance(
                rotated,
                cq.Shape,
            ):
                raise RuntimeError(
                    "Circular pattern copy did not "
                    "produce a CadQuery Shape."
                )

            copies.append(
                rotated
            )

        return self._combine(
            copies
        )

    @staticmethod
    def _selected_edges(
        geometry: cq.Shape,
        indices: Any,
    ) -> list[cq.Edge]:
        """
        Resolves selected edge indices.

        An empty tuple selects every edge.
        """

        edges = list(
            geometry.Edges()
        )

        if indices == ():
            return edges

        if not isinstance(
            indices,
            tuple,
        ):
            raise TypeError(
                "edge_indices must be a tuple."
            )

        selected: list[
            cq.Edge
        ] = []

        for index in indices:
            if isinstance(
                index,
                bool,
            ) or not isinstance(
                index,
                int,
            ):
                raise TypeError(
                    "edge_indices must contain "
                    "integers."
                )

            if index < 0:
                raise ValueError(
                    "edge_indices cannot contain "
                    "negative values."
                )

            try:
                edge = edges[
                    index
                ]

            except IndexError as error:
                raise IndexError(
                    f"Edge index {index} is outside "
                    f"the available range of {len(edges)}."
                ) from error

            selected.append(
                edge
            )

        return selected

    @staticmethod
    def _selected_faces(
        geometry: cq.Shape,
        indices: Any,
    ) -> list[cq.Face]:
        """
        Resolves selected face indices.

        An empty tuple selects every face.
        """

        faces = list(
            geometry.Faces()
        )

        if indices == ():
            return faces

        if not isinstance(
            indices,
            tuple,
        ):
            raise TypeError(
                "face_indices must be a tuple."
            )

        selected: list[
            cq.Face
        ] = []

        for index in indices:
            if isinstance(
                index,
                bool,
            ) or not isinstance(
                index,
                int,
            ):
                raise TypeError(
                    "face_indices must contain "
                    "integers."
                )

            if index < 0:
                raise ValueError(
                    "face_indices cannot contain "
                    "negative values."
                )

            try:
                face = faces[
                    index
                ]

            except IndexError as error:
                raise IndexError(
                    f"Face index {index} is outside "
                    f"the available range of {len(faces)}."
                ) from error

            selected.append(
                face
            )

        return selected

    @staticmethod
    def _combine(
        shapes: list[
            cq.Shape
        ],
    ) -> cq.Shape:
        """
        Combines multiple shapes into one Compound.
        """

        if not shapes:
            raise RuntimeError(
                "Pattern generated no copies."
            )

        if len(
            shapes
        ) == 1:
            return shapes[0]

        try:
            compound = (
                cq.Compound.makeCompound(
                    shapes
                )
            )

        except Exception as error:
            raise RuntimeError(
                "Pattern copies could not be "
                "combined into a Compound."
            ) from error

        if not isinstance(
            compound,
            cq.Shape,
        ):
            raise RuntimeError(
                "Pattern did not produce a "
                "CadQuery Shape."
            )

        return compound

    @staticmethod
    def _vector3(
        value: Any,
        name: str,
    ) -> Vector3:
        """
        Validates a numeric three-dimensional vector.
        """

        if not isinstance(
            value,
            tuple,
        ) or len(
            value
        ) != 3:
            raise TypeError(
                f"{name} must be a 3-value tuple."
            )

        result: list[
            float
        ] = []

        for item in value:
            if isinstance(
                item,
                bool,
            ) or not isinstance(
                item,
                (
                    int,
                    float,
                ),
            ):
                raise TypeError(
                    f"{name} values must be numeric."
                )

            numeric = float(
                item
            )

            if not math.isfinite(
                numeric
            ):
                raise ValueError(
                    f"{name} values must be finite."
                )

            result.append(
                numeric
            )

        return (
            result[0],
            result[1],
            result[2],
        )

    @staticmethod
    def _require_nonzero_vector(
        value: Vector3,
        name: str,
    ) -> None:
        """
        Ensures a vector has nonzero length.
        """

        length = math.sqrt(
            value[0]
            * value[0]
            + value[1]
            * value[1]
            + value[2]
            * value[2]
        )

        if length <= 1e-12:
            raise ValueError(
                f"{name} cannot be zero."
            )

    @staticmethod
    def _number(
        value: Any,
        name: str,
    ) -> float:
        """
        Validates one finite numeric parameter.
        """

        if isinstance(
            value,
            bool,
        ) or not isinstance(
            value,
            (
                int,
                float,
            ),
        ):
            raise TypeError(
                f"{name} must be numeric."
            )

        result = float(
            value
        )

        if not math.isfinite(
            result
        ):
            raise ValueError(
                f"{name} must be finite."
            )

        return result

    @staticmethod
    def _positive_int(
        value: Any,
        name: str,
    ) -> int:
        """
        Validates one positive integer.
        """

        if isinstance(
            value,
            bool,
        ) or not isinstance(
            value,
            int,
        ):
            raise TypeError(
                f"{name} must be an integer."
            )

        if value < 1:
            raise ValueError(
                f"{name} must be at least one."
            )

        return value