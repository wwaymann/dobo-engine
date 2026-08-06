"""
DOBO Features

Feature Builder Registry

Registers FeatureOperationBuilder implementations and
resolves the correct builder for each FeatureDefinition.
"""

from __future__ import annotations

from features.contracts import (
    FeatureContext,
    FeatureDefinition,
    FeaturePlan,
)

from .feature_operation_builder import (
    FeatureOperationBuilder,
)


class FeatureBuilderRegistry:
    """
    Registry of FeatureOperationBuilder implementations.

    One builder may be registered for each concrete
    FeatureDefinition class.
    """

    def __init__(self) -> None:
        self._builders: dict[
            type[FeatureDefinition],
            FeatureOperationBuilder[
                FeatureDefinition
            ],
        ] = {}

    def register(
        self,
        builder: FeatureOperationBuilder[
            FeatureDefinition
        ],
    ) -> None:
        """
        Registers one Feature operation builder.
        """

        if not isinstance(
            builder,
            FeatureOperationBuilder,
        ):
            raise TypeError(
                "FeatureBuilderRegistry requires "
                "FeatureOperationBuilder instances."
            )

        feature_class = builder.feature_type

        if not isinstance(
            feature_class,
            type,
        ):
            raise TypeError(
                "FeatureOperationBuilder feature_type "
                "must return a class."
            )

        if not issubclass(
            feature_class,
            FeatureDefinition,
        ):
            raise TypeError(
                "FeatureOperationBuilder feature_type "
                "must inherit FeatureDefinition."
            )

        if feature_class in self._builders:
            raise ValueError(
                "A FeatureOperationBuilder is already "
                f"registered for "
                f"'{feature_class.__name__}'."
            )

        self._builders[
            feature_class
        ] = builder

    def unregister(
        self,
        feature_class: type[
            FeatureDefinition
        ],
    ) -> FeatureOperationBuilder[
        FeatureDefinition
    ]:
        """
        Removes and returns one registered builder.
        """

        self._validate_feature_class(
            feature_class
        )

        try:
            return self._builders.pop(
                feature_class
            )

        except KeyError as error:
            raise LookupError(
                "No FeatureOperationBuilder is "
                f"registered for "
                f"'{feature_class.__name__}'."
            ) from error

    def resolve(
        self,
        feature: FeatureDefinition,
    ) -> FeatureOperationBuilder[
        FeatureDefinition
    ]:
        """
        Resolves the builder for one FeatureDefinition.
        """

        if not isinstance(
            feature,
            FeatureDefinition,
        ):
            raise TypeError(
                "FeatureBuilderRegistry.resolve "
                "requires FeatureDefinition."
            )

        feature.validate()

        feature_class = type(
            feature
        )

        try:
            return self._builders[
                feature_class
            ]

        except KeyError as error:
            available = ", ".join(
                item.__name__
                for item in self._builders
            )

            raise LookupError(
                "No FeatureOperationBuilder is "
                f"registered for "
                f"'{feature_class.__name__}'. "
                f"Available: "
                f"{available or '<none>'}"
            ) from error

    def build(
        self,
        feature: FeatureDefinition,
        context: FeatureContext,
    ) -> FeaturePlan:
        """
        Resolves the correct builder and creates
        one validated FeaturePlan.
        """

        if not isinstance(
            feature,
            FeatureDefinition,
        ):
            raise TypeError(
                "FeatureBuilderRegistry.build "
                "requires FeatureDefinition."
            )

        if not isinstance(
            context,
            FeatureContext,
        ):
            raise TypeError(
                "FeatureBuilderRegistry.build "
                "requires FeatureContext."
            )

        feature.validate()
        context.validate()

        builder = self.resolve(
            feature
        )

        plan = builder.build(
            feature,
            context,
        )

        if not isinstance(
            plan,
            FeaturePlan,
        ):
            raise TypeError(
                "FeatureOperationBuilder must "
                "return FeaturePlan."
            )

        plan.validate()

        if plan.feature is not feature:
            raise ValueError(
                "FeaturePlan must reference "
                "the source FeatureDefinition."
            )

        return plan

    def contains(
        self,
        feature_class: type[
            FeatureDefinition
        ],
    ) -> bool:
        """
        Returns whether a builder is registered
        for the supplied Feature class.
        """

        if not isinstance(
            feature_class,
            type,
        ):
            return False

        if not issubclass(
            feature_class,
            FeatureDefinition,
        ):
            return False

        return (
            feature_class
            in self._builders
        )

    def clear(self) -> None:
        """
        Removes every registered builder.
        """

        self._builders.clear()

    def validate(self) -> None:
        """
        Validates the complete registry.
        """

        for feature_class, builder in (
            self._builders.items()
        ):
            self._validate_feature_class(
                feature_class
            )

            if not isinstance(
                builder,
                FeatureOperationBuilder,
            ):
                raise TypeError(
                    "FeatureBuilderRegistry contains "
                    "an invalid builder."
                )

            if (
                builder.feature_type
                is not feature_class
            ):
                raise ValueError(
                    "Registered builder feature_type "
                    "does not match its registry key."
                )

    @property
    def count(self) -> int:
        """
        Number of registered builders.
        """

        return len(
            self._builders
        )

    @property
    def supported_feature_classes(
        self,
    ) -> tuple[
        type[FeatureDefinition],
        ...,
    ]:
        """
        Returns the registered Feature classes.
        """

        return tuple(
            self._builders.keys()
        )

    @property
    def supported_feature_types(
        self,
    ) -> tuple[
        str,
        ...,
    ]:
        """
        Returns the stable Feature type identifiers.

        The identifiers are resolved from each registered
        builder's concrete FeatureDefinition class.
        """

        feature_types: list[str] = []

        for feature_class in self._builders:
            feature_type_property = getattr(
                feature_class,
                "feature_type",
                None,
            )

            if not isinstance(
                feature_type_property,
                property,
            ):
                feature_types.append(
                    feature_class.__name__
                )
                continue

            feature_types.append(
                feature_class.__name__
            )

        return tuple(
            feature_types
        )

    @property
    def builders(
        self,
    ) -> tuple[
        FeatureOperationBuilder[
            FeatureDefinition
        ],
        ...,
    ]:
        """
        Returns all registered builders.
        """

        return tuple(
            self._builders.values()
        )

    @staticmethod
    def _validate_feature_class(
        feature_class: type[
            FeatureDefinition
        ],
    ) -> None:
        """
        Validates one FeatureDefinition class.
        """

        if not isinstance(
            feature_class,
            type,
        ):
            raise TypeError(
                "feature_class must be a class."
            )

        if not issubclass(
            feature_class,
            FeatureDefinition,
        ):
            raise TypeError(
                "feature_class must inherit "
                "FeatureDefinition."
            )