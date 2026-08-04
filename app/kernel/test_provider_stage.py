from kernel.providers.circle_provider import CircleProvider
from kernel.providers.polygon_provider import PolygonProvider
from kernel.providers.registry import ProviderRegistry
from kernel.providers.svg_provider import SVGProvider
from kernel.stages.provider_stage import ProviderStage


def main() -> None:
    registry = ProviderRegistry()

    registry.register_provider(CircleProvider())

    registry.register_provider(PolygonProvider())

    registry.register_provider(SVGProvider())

    stage = ProviderStage(registry=registry)

    result = stage.execute(
        provider_name="circle",
        parameters={
            "radius": 20.0,
        },
        metadata={
            "test": True,
        },
    )

    print()
    print("DOBO Provider Stage")
    print("-------------------")
    print(
        "Provider:",
        result.request.provider,
    )
    print(
        "Contours:",
        result.contours.count,
    )
    print(
        "Valid:",
        result.contours.validate(),
    )
    print(
        "Registered:",
        registry.names(),
    )
    print()


if __name__ == "__main__":
    main()
