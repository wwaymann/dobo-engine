from kernel.contracts.provider_request import ProviderRequest
from kernel.providers.circle_provider import CircleProvider
from kernel.providers.registry import ProviderRegistry


def main() -> None:
    registry = ProviderRegistry()

    registry.register_provider(
        CircleProvider()
    )

    request = ProviderRequest(
        provider="circle",
        parameters={
            "radius": 20,
        },
    )

    contour_set = registry.execute(
        name="circle",
        request=request,
    )

    print()
    print("Registered:", registry.names())
    print("Contours:", contour_set.count)
    print("Valid:", contour_set.validate())
    print()


if __name__ == "__main__":
    main()