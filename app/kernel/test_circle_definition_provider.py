from kernel.contracts.provider_request import ProviderRequest
from kernel.providers.circle_definition_provider import (
    CircleDefinitionProvider,
)


def main() -> None:
    provider = CircleDefinitionProvider()

    result = provider.execute(
        ProviderRequest(
            provider="circle_definition",
            parameters={
                "radius": 20.0,
                "samples": 64,
            },
        )
    )

    contour = result.contours[0]

    print()
    print("DOBO Circle Definition Provider")
    print("-------------------------------")
    print("Contours:", result.count)
    print("Points:", contour.count)
    print("Bounds:", contour.bounds)
    print("Valid: OK")
    print()


if __name__ == "__main__":
    main()