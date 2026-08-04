from kernel.contracts.provider_request import (
    ProviderRequest,
)
from kernel.providers.svg_provider import (
    SVGProvider,
)


def main() -> None:
    provider = SVGProvider()

    contour_set = provider.execute(
        ProviderRequest(
            provider="svg",
            parameters={
                "file": (
                    "assets/svg/test.svg"
                ),
                "width": 30.0,
                "samples_per_path": 128,
                "flip_y": True,
            },
        )
    )

    print()
    print("DOBO SVG Provider")
    print("-----------------")
    print(
        "Provider:",
        provider.name,
    )
    print(
        "Contours:",
        contour_set.count,
    )
    print(
        "Valid:",
        contour_set.validate(),
    )
    print(
        "Target width:",
        contour_set.metadata[
            "target_width"
        ],
    )
    print(
        "Skipped open paths:",
        contour_set.metadata[
            "skipped_open_paths"
        ],
    )
    print()


if __name__ == "__main__":
    main()