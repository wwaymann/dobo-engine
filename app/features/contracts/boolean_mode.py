"""
DOBO Features

Boolean Mode

Defines how a Feature interacts with the existing model.
"""

from __future__ import annotations

from enum import Enum


class BooleanMode(Enum):
    """
    Defines the boolean behavior of a Feature.
    """

    NEW_BODY = "new_body"

    JOIN = "join"

    CUT = "cut"

    INTERSECT = "intersect"

    @property
    def requires_target_body(
        self,
    ) -> bool:
        """
        Returns whether the operation requires
        an existing target body.
        """

        return self in (
            BooleanMode.JOIN,
            BooleanMode.CUT,
            BooleanMode.INTERSECT,
        )

    @property
    def creates_new_body(
        self,
    ) -> bool:
        """
        Returns whether the operation creates
        a new independent body.
        """

        return self is BooleanMode.NEW_BODY

    @property
    def performs_boolean(
        self,
    ) -> bool:
        """
        Returns whether the operation performs
        a boolean operation.
        """

        return self is not BooleanMode.NEW_BODY

    @property
    def is_join(
        self,
    ) -> bool:
        """
        Returns whether the mode performs a Join.
        """

        return self is BooleanMode.JOIN

    @property
    def is_cut(
        self,
    ) -> bool:
        """
        Returns whether the mode performs a Cut.
        """

        return self is BooleanMode.CUT

    @property
    def is_intersect(
        self,
    ) -> bool:
        """
        Returns whether the mode performs an Intersect.
        """

        return self is BooleanMode.INTERSECT

    @classmethod
    def default(
        cls,
    ) -> "BooleanMode":
        """
        Returns the default boolean mode.
        """

        return cls.NEW_BODY