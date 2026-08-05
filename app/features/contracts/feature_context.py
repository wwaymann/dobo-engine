"""
DOBO Features

Feature Context

Shared execution state for Feature evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any

from kernel.contracts.model_state import (
    ModelState,
)

from sketch.sketch import Sketch
from sketch.topology import RegionSet


@dataclass(
    slots=True,
)
class FeatureContext:
    """
    Mutable CAD model state used during
    Feature execution.
    """

    model: ModelState

    sketches: dict[
        str,
        Sketch,
    ] = field(
        default_factory=dict
    )

    regions: dict[
        str,
        RegionSet,
    ] = field(
        default_factory=dict
    )

    variables: dict[
        str,
        float,
    ] = field(
        default_factory=dict
    )

    metadata: dict[
        str,
        Any,
    ] = field(
        default_factory=dict
    )

    def validate(
        self,
    ) -> None:

        if not isinstance(
            self.model,
            ModelState,
        ):
            raise TypeError(
                "FeatureContext model "
                "must be ModelState."
            )

        self.model.validate()

        if not isinstance(
            self.sketches,
            dict,
        ):
            raise TypeError(
                "FeatureContext sketches "
                "must be a dictionary."
            )

        for key, sketch in self.sketches.items():

            if (
                not isinstance(
                    key,
                    str,
                )
                or not key.strip()
            ):
                raise ValueError(
                    "Sketch ids cannot be empty."
                )

            if not isinstance(
                sketch,
                Sketch,
            ):
                raise TypeError(
                    "FeatureContext sketches "
                    "must contain Sketch objects."
                )

            sketch.validate()

        if not isinstance(
            self.regions,
            dict,
        ):
            raise TypeError(
                "FeatureContext regions "
                "must be a dictionary."
            )

        for key, region_set in self.regions.items():

            if (
                not isinstance(
                    key,
                    str,
                )
                or not key.strip()
            ):
                raise ValueError(
                    "Region ids cannot be empty."
                )

            if not isinstance(
                region_set,
                RegionSet,
            ):
                raise TypeError(
                    "FeatureContext regions "
                    "must contain RegionSet objects."
                )

            region_set.validate()

        if not isinstance(
            self.variables,
            dict,
        ):
            raise TypeError(
                "FeatureContext variables "
                "must be a dictionary."
            )

        for key, value in self.variables.items():

            if (
                not isinstance(
                    key,
                    str,
                )
                or not key.strip()
            ):
                raise ValueError(
                    "Variable names cannot be empty."
                )

            if not isinstance(
                value,
                (
                    int,
                    float,
                ),
            ):
                raise TypeError(
                    "Variables must be numeric."
                )

        if not isinstance(
            self.metadata,
            dict,
        ):
            raise TypeError(
                "FeatureContext metadata "
                "must be a dictionary."
            )

    @property
    def sketch_count(
        self,
    ) -> int:

        return len(
            self.sketches
        )

    @property
    def region_count(
        self,
    ) -> int:

        return len(
            self.regions
        )

    @property
    def variable_count(
        self,
    ) -> int:

        return len(
            self.variables
        )

    def register_sketch(
        self,
        sketch: Sketch,
    ) -> None:

        sketch.validate()

        self.sketches[
            sketch.id
        ] = sketch

    def register_regions(
        self,
        sketch_id: str,
        regions: RegionSet,
    ) -> None:

        if (
            not isinstance(
                sketch_id,
                str,
            )
            or not sketch_id.strip()
        ):
            raise ValueError(
                "Sketch id cannot be empty."
            )

        regions.validate()

        self.regions[
            sketch_id
        ] = regions