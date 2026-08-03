from kernel.contracts.provider_request import ProviderRequest
from kernel.providers.circle_provider import CircleProvider


def main():

    provider = CircleProvider()

    request = ProviderRequest(
        provider="circle",
        parameters={
            "radius": 20,
        },
    )

    contour_set = provider.execute(
        request
    )

    print()

    print("Provider:", provider.name)

    print("Contours:", contour_set.count)

    print(
        "Valid:",
        contour_set.validate(),
    )

    print()


if __name__ == "__main__":
    main()