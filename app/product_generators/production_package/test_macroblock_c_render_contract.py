from __future__ import annotations

from .render_contract import RenderContract, RenderIntent


def main() -> None:
    commercial = RenderContract.standard(RenderIntent.COMMERCIAL)
    production = RenderContract.standard(RenderIntent.PRODUCTION)
    thumbnail = RenderContract.standard(RenderIntent.THUMBNAIL)

    if tuple(view.name for view in commercial.views) != ("hero_iso", "front"):
        raise RuntimeError("Commercial render contract changed unexpectedly.")
    if tuple(view.name for view in production.views) != (
        "front",
        "side",
        "top",
        "iso",
    ):
        raise RuntimeError("Production render contract must preserve four QA views.")
    if len(thumbnail.views) != 1 or thumbnail.views[0].width_px != 512:
        raise RuntimeError("Thumbnail render contract is invalid.")
    if not all(view.transparent_background for view in production.views):
        raise RuntimeError("Production QA renders must use transparent backgrounds.")

    print("DOBO Macroblock C - Render Contract")
    print("-----------------------------------")
    print("commercial views", len(commercial.views), "OK")
    print("production views", len(production.views), "OK")
    print("thumbnail views", len(thumbnail.views), "OK")
    print("schema", RenderContract.SCHEMA_VERSION, "OK")
    print("-----------------------------------")
    print("Macroblock C Render Contract: Valid OK")


if __name__ == "__main__":
    main()
