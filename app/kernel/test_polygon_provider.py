from kernel.contracts.provider_request import ProviderRequest
from kernel.providers.polygon_provider import PolygonProvider


def main() -> None:
    provider = PolygonProvider()

    request = ProviderRequest(
        provider="polygon",
        parameters={
            "sides": 6,
            "diameter": 30,
            "rotation_degrees": 30,
        },
    )

    contour_set = provider.execute(request)

    print()
    print("Provider:", provider.name)
    print("Contours:", contour_set.count)
    print("Valid:", contour_set.validate())
    print(
        "Metadata:",
        contour_set.contours[0].metadata,
    )
    print()


if __name__ == "__main__":
    main()
