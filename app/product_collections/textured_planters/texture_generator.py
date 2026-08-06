from __future__ import annotations

from dataclasses import dataclass

from kernel.contracts.contour_definition import ContourDefinition
from kernel.contracts.geometry_definition import GeometryDefinition


@dataclass(frozen=True, slots=True)
class TextureProfile:
    id: str
    points: tuple[tuple[float, float], ...]


class TexturedPlanterTextureGenerator:
    """
    Generates independent vertical texture profiles.

    Each profile is executed and joined independently by the
    product collection. This avoids passing disconnected texture
    compounds to the Kernel Boolean engine.
    """

    def generate_definitions(
        self,
        *,
        product_id: str,
        width: float,
        depth: float,
        texture: str,
        count: int,
        rib_width: float,
        rib_depth: float,
    ) -> tuple[GeometryDefinition, ...]:
        profiles = self._profiles(
            width=float(width),
            depth=float(depth),
            texture=texture,
            count=count,
            rib_width=float(rib_width),
            rib_depth=float(rib_depth),
        )

        definitions: list[GeometryDefinition] = []

        for index, profile in enumerate(profiles):
            contour = ContourDefinition(
                id=f"{product_id}:texture-contour:{index}",
                points=profile.points,
                closed=True,
                source="textured_planters",
                metadata={
                    "texture": texture,
                    "texture_index": index,
                },
            )
            contour.validate()

            definition = GeometryDefinition(
                id=f"{product_id}:texture-definition:{index}",
                outer_contour=contour,
                source="textured_planters",
                metadata={
                    "texture": texture,
                    "texture_index": index,
                },
            )
            definition.validate()
            definitions.append(definition)

        if not definitions:
            raise RuntimeError(
                "Texture generator produced no definitions."
            )

        return tuple(definitions)

    def _profiles(
        self,
        *,
        width: float,
        depth: float,
        texture: str,
        count: int,
        rib_width: float,
        rib_depth: float,
    ) -> tuple[TextureProfile, ...]:
        if texture == "corner_ribs":
            return self._corner_profiles(
                width,
                depth,
                rib_width,
                rib_depth,
            )

        if texture == "front_panels":
            return self._front_profiles(
                width,
                depth,
                count,
                rib_width,
                rib_depth,
            )

        if texture in {
            "vertical_ribs",
            "wide_ribs",
            "fine_fluting",
            "alternating_ribs",
        }:
            return self._perimeter_profiles(
                width,
                depth,
                count,
                rib_width,
                rib_depth,
                alternating=(
                    texture == "alternating_ribs"
                ),
            )

        raise ValueError(
            f"Unsupported texture '{texture}'."
        )

    @staticmethod
    def _rect(
        id_: str,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
    ) -> TextureProfile:
        return TextureProfile(
            id=id_,
            points=(
                (x0, y0),
                (x1, y0),
                (x1, y1),
                (x0, y1),
            ),
        )

    def _perimeter_profiles(
        self,
        width: float,
        depth: float,
        count: int,
        rib_width: float,
        rib_depth: float,
        *,
        alternating: bool,
    ) -> tuple[TextureProfile, ...]:
        profiles: list[TextureProfile] = []
        per_side = max(1, count // 4)

        for side in range(4):
            length = (
                width
                if side in (0, 2)
                else depth
            )
            step = length / (per_side + 1)

            for i in range(per_side):
                center = step * (i + 1)

                depth_value = (
                    rib_depth
                    * (
                        0.55
                        if alternating and i % 2
                        else 1.0
                    )
                )

                overlap = min(
                    depth_value * 0.75,
                    2.0,
                )

                if side == 0:
                    profiles.append(
                        self._rect(
                            f"front:{i}",
                            center - rib_width / 2,
                            -depth_value,
                            center + rib_width / 2,
                            overlap,
                        )
                    )

                elif side == 1:
                    profiles.append(
                        self._rect(
                            f"right:{i}",
                            width - overlap,
                            center - rib_width / 2,
                            width + depth_value,
                            center + rib_width / 2,
                        )
                    )

                elif side == 2:
                    profiles.append(
                        self._rect(
                            f"back:{i}",
                            center - rib_width / 2,
                            depth - overlap,
                            center + rib_width / 2,
                            depth + depth_value,
                        )
                    )

                else:
                    profiles.append(
                        self._rect(
                            f"left:{i}",
                            -depth_value,
                            center - rib_width / 2,
                            overlap,
                            center + rib_width / 2,
                        )
                    )

        return tuple(profiles)

    def _corner_profiles(
        self,
        width: float,
        depth: float,
        rib_width: float,
        rib_depth: float,
    ) -> tuple[TextureProfile, ...]:
        half = rib_width / 2.0
        overlap = min(rib_depth * 0.75, 2.0)

        return (
            self._rect(
                "c0",
                -rib_depth,
                -rib_depth,
                half + overlap,
                half + overlap,
            ),
            self._rect(
                "c1",
                width - half - overlap,
                -rib_depth,
                width + rib_depth,
                half + overlap,
            ),
            self._rect(
                "c2",
                width - half - overlap,
                depth - half - overlap,
                width + rib_depth,
                depth + rib_depth,
            ),
            self._rect(
                "c3",
                -rib_depth,
                depth - half - overlap,
                half + overlap,
                depth + rib_depth,
            ),
        )

    def _front_profiles(
        self,
        width: float,
        depth: float,
        count: int,
        rib_width: float,
        rib_depth: float,
    ) -> tuple[TextureProfile, ...]:
        step = width / (count + 1)
        overlap = min(rib_depth * 0.75, 2.0)

        return tuple(
            self._rect(
                f"panel:{i}",
                step * (i + 1) - rib_width / 2,
                -rib_depth,
                step * (i + 1) + rib_width / 2,
                overlap,
            )
            for i in range(count)
        )
