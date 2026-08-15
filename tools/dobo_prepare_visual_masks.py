from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize Blender Workbench backgrounds into alpha masks."
    )
    parser.add_argument("--render-root", required=True)
    parser.add_argument("--threshold", type=float, default=10.0)
    return parser.parse_args()


def _border_pixels(rgb: np.ndarray) -> np.ndarray:
    return np.concatenate(
        (
            rgb[0, :, :],
            rgb[-1, :, :],
            rgb[:, 0, :],
            rgb[:, -1, :],
        ),
        axis=0,
    )


def _prepare(path: Path, threshold: float) -> tuple[int, int]:
    image = Image.open(path).convert("RGBA")
    rgba = np.asarray(image, dtype=np.uint8).copy()
    alpha = rgba[:, :, 3]

    # If Blender already produced meaningful transparency, preserve it.
    if int(alpha.min()) < 240:
        mask = alpha >= 8
    else:
        rgb = rgba[:, :, :3].astype(np.float32)
        background = np.median(_border_pixels(rgb), axis=0)
        distance = np.linalg.norm(rgb - background, axis=2)
        mask = distance >= threshold
        rgba[:, :, 3] = np.where(mask, 255, 0).astype(np.uint8)
        Image.fromarray(rgba, mode="RGBA").save(path)

    foreground = int(mask.sum())
    total = int(mask.size)
    ratio = foreground / total
    if foreground == 0 or ratio >= 0.95:
        raise RuntimeError(
            f"Invalid visual mask for {path}: foreground={foreground}, ratio={ratio:.4f}."
        )
    return foreground, total


def main() -> None:
    args = _arguments()
    root = Path(args.render_root).resolve()
    paths = sorted(root.rglob("*.png"))
    if not paths:
        raise RuntimeError(f"No PNG renders found under {root}.")

    print("DOBO Workbench alpha normalization")
    for path in paths:
        foreground, total = _prepare(path, args.threshold)
        print(path.relative_to(root), f"foreground={foreground}/{total}", "OK")
    print("DOBO Workbench alpha normalization: Valid OK")


if __name__ == "__main__":
    main()
