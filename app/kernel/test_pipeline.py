from kernel.pipeline.pipeline import KernelPipeline
from kernel.providers.circle_provider import CircleProvider
from kernel.providers.polygon_provider import PolygonProvider
from kernel.providers.registry import ProviderRegistry


def main() -> None:
    registry = ProviderRegistry()

    registry.register_provider(CircleProvider())

    registry.register_provider(PolygonProvider())

    pipeline = KernelPipeline(provider_registry=registry)

    circle_result = pipeline.execute(
        provider_name="circle",
        parameters={
            "radius": 20,
        },
    )

    polygon_result = pipeline.execute(
        provider_name="polygon",
        parameters={
            "sides": 6,
            "diameter": 30,
            "rotation_degrees": 30,
        },
    )

    print()
    print("DOBO Kernel Pipeline")
    print("--------------------")
    print(
        "Circle contours:",
        circle_result.contours.count,
    )
    print(
        "Polygon contours:",
        polygon_result.contours.count,
    )
    print(
        "Registered providers:",
        registry.names(),
    )
    print()


if __name__ == "__main__":
    main()
