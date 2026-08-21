from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image, ImageDraw, ImageFont


CASES = ("architectural", "branching", "perforated")
VIEWS = ("front", "side", "top", "iso")
BACKGROUND = (39, 41, 45, 255)
PANEL_BACKGROUND = (48, 50, 55, 255)
TEXT = (238, 239, 241, 255)
BASELINE_ONLY = (238, 155, 77, 255)
CANDIDATE_ONLY = (69, 199, 190, 255)
SHARED = (121, 125, 132, 255)


@dataclass(frozen=True, slots=True)
class ViewMetrics:
    case: str
    view: str
    baseline_area_px: int
    candidate_area_px: int
    area_ratio: float
    silhouette_iou: float
    silhouette_delta: float
    centroid_shift_normalized: float
    baseline_bbox_fill: float
    candidate_bbox_fill: float
    catastrophic_guard: bool


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build DOBO A/B visual regression evidence.")
    parser.add_argument("--render-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--baseline-label", required=True)
    parser.add_argument("--candidate-label", required=True)
    parser.add_argument("--baseline-commit", default="")
    parser.add_argument("--candidate-commit", default="")
    return parser.parse_args()


def _rgba(path: Path) -> Image.Image:
    image = Image.open(path).convert("RGBA")
    if image.getbbox() is None:
        raise RuntimeError(f"Empty render: {path}")
    return image


def _mask(image: Image.Image) -> np.ndarray:
    alpha = np.asarray(image.getchannel("A"), dtype=np.uint8)
    return alpha >= 8


def _centroid(mask: np.ndarray) -> tuple[float, float]:
    y, x = np.nonzero(mask)
    if len(x) == 0:
        raise RuntimeError("Cannot calculate centroid of an empty silhouette.")
    return float(x.mean()), float(y.mean())


def _bbox_fill(mask: np.ndarray) -> float:
    y, x = np.nonzero(mask)
    if len(x) == 0:
        return 0.0
    width = int(x.max() - x.min() + 1)
    height = int(y.max() - y.min() + 1)
    return float(mask.sum()) / float(width * height)


def _metrics(case: str, view: str, baseline: Image.Image, candidate: Image.Image) -> ViewMetrics:
    a = _mask(baseline)
    b = _mask(candidate)
    if a.shape != b.shape:
        raise RuntimeError(f"Render size mismatch for {case}/{view}.")
    area_a = int(a.sum())
    area_b = int(b.sum())
    if min(area_a, area_b) <= 0:
        raise RuntimeError(f"Empty silhouette for {case}/{view}.")
    intersection = int(np.logical_and(a, b).sum())
    union = int(np.logical_or(a, b).sum())
    xor = int(np.logical_xor(a, b).sum())
    iou = intersection / union
    delta = xor / union
    area_ratio = area_b / area_a
    ca = _centroid(a)
    cb = _centroid(b)
    diagonal = float(np.hypot(a.shape[1], a.shape[0]))
    centroid_shift = float(np.hypot(cb[0] - ca[0], cb[1] - ca[1]) / diagonal)
    # Broad safety rails: they catch explosions, disappearances, extreme drift,
    # or a gross scale change. They do not claim subjective design quality.
    catastrophic_guard = (
        0.55 <= area_ratio <= 1.65
        and iou >= 0.50
        and centroid_shift <= 0.18
    )
    return ViewMetrics(
        case=case,
        view=view,
        baseline_area_px=area_a,
        candidate_area_px=area_b,
        area_ratio=round(area_ratio, 6),
        silhouette_iou=round(iou, 6),
        silhouette_delta=round(delta, 6),
        centroid_shift_normalized=round(centroid_shift, 6),
        baseline_bbox_fill=round(_bbox_fill(a), 6),
        candidate_bbox_fill=round(_bbox_fill(b), 6),
        catastrophic_guard=catastrophic_guard,
    )


def _font(size: int) -> ImageFont.ImageFont:
    candidates = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    )
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _composite(image: Image.Image, background=BACKGROUND) -> Image.Image:
    canvas = Image.new("RGBA", image.size, background)
    canvas.alpha_composite(image)
    return canvas


def _difference_panel(baseline: Image.Image, candidate: Image.Image) -> Image.Image:
    a = _mask(baseline)
    b = _mask(candidate)
    output = np.empty((a.shape[0], a.shape[1], 4), dtype=np.uint8)
    output[:, :] = BACKGROUND
    shared = np.logical_and(a, b)
    only_a = np.logical_and(a, ~b)
    only_b = np.logical_and(~a, b)
    output[shared] = SHARED
    output[only_a] = BASELINE_ONLY
    output[only_b] = CANDIDATE_ONLY
    return Image.fromarray(output, mode="RGBA")


def _labeled_panel(image: Image.Image, label: str, font: ImageFont.ImageFont) -> Image.Image:
    image = _composite(image)
    header = 38
    panel = Image.new("RGBA", (image.width, image.height + header), PANEL_BACKGROUND)
    panel.alpha_composite(image, (0, header))
    draw = ImageDraw.Draw(panel)
    draw.text((12, 9), label, fill=TEXT, font=font)
    return panel


def _case_sheet(
    render_root: Path,
    case: str,
    baseline_label: str,
    candidate_label: str,
    output_path: Path,
) -> None:
    title_font = _font(19)
    panel_font = _font(15)
    rows: list[Image.Image] = []
    for view in VIEWS:
        baseline = _rgba(render_root / case / f"{baseline_label}_{view}.png")
        candidate = _rgba(render_root / case / f"{candidate_label}_{view}.png")
        diff = _difference_panel(baseline, candidate)
        panels = (
            _labeled_panel(baseline, f"{baseline_label} · {view}", panel_font),
            _labeled_panel(candidate, f"{candidate_label} · {view}", panel_font),
            _labeled_panel(diff, f"delta · {view}", panel_font),
        )
        row = Image.new(
            "RGBA",
            (sum(panel.width for panel in panels), max(panel.height for panel in panels)),
            BACKGROUND,
        )
        x = 0
        for panel in panels:
            row.alpha_composite(panel, (x, 0))
            x += panel.width
        rows.append(row)

    title_height = 48
    sheet = Image.new(
        "RGBA",
        (max(row.width for row in rows), title_height + sum(row.height for row in rows)),
        BACKGROUND,
    )
    draw = ImageDraw.Draw(sheet)
    draw.text((14, 12), f"DOBO visual regression · {case}", fill=TEXT, font=title_font)
    y = title_height
    for row in rows:
        sheet.alpha_composite(row, (0, y))
        y += row.height
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(output_path, quality=95)


def _master_sheet(case_paths: Iterable[Path], output_path: Path) -> None:
    images = [Image.open(path).convert("RGB") for path in case_paths]
    width = max(image.width for image in images)
    height = sum(image.height for image in images)
    master = Image.new("RGB", (width, height), BACKGROUND[:3])
    y = 0
    for image in images:
        master.paste(image, (0, y))
        y += image.height
    master.save(output_path, quality=95)


def main() -> None:
    args = _arguments()
    render_root = Path(args.render_root).resolve()
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    metrics: list[ViewMetrics] = []
    case_sheets: list[Path] = []
    for case in CASES:
        for view in VIEWS:
            baseline = _rgba(render_root / case / f"{args.baseline_label}_{view}.png")
            candidate = _rgba(render_root / case / f"{args.candidate_label}_{view}.png")
            metrics.append(_metrics(case, view, baseline, candidate))
        sheet_path = output_root / f"{case}_comparison.png"
        _case_sheet(render_root, case, args.baseline_label, args.candidate_label, sheet_path)
        case_sheets.append(sheet_path)

    _master_sheet(case_sheets, output_root / "visual_regression_master.png")

    all_safe = all(item.catastrophic_guard for item in metrics)
    average_iou = float(np.mean([item.silhouette_iou for item in metrics]))
    average_delta = float(np.mean([item.silhouette_delta for item in metrics]))
    maximum_delta = float(np.max([item.silhouette_delta for item in metrics]))
    report = {
        "schema": "dobo.visual_regression.1",
        "baseline": {"label": args.baseline_label, "commit": args.baseline_commit},
        "candidate": {"label": args.candidate_label, "commit": args.candidate_commit},
        "views": [asdict(item) for item in metrics],
        "summary": {
            "catastrophic_guard": all_safe,
            "average_silhouette_iou": round(average_iou, 6),
            "average_silhouette_delta": round(average_delta, 6),
            "maximum_silhouette_delta": round(maximum_delta, 6),
            "nontrivial_visual_delta": average_delta >= 0.001,
        },
    }
    (output_root / "visual_regression_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# DOBO Visual Regression",
        "",
        f"Baseline: **{args.baseline_label}** `{args.baseline_commit}`",
        f"Candidate: **{args.candidate_label}** `{args.candidate_commit}`",
        "",
        f"Catastrophic guard: **{'PASS' if all_safe else 'FAIL'}**",
        f"Average silhouette IoU: **{average_iou:.4f}**",
        f"Average silhouette delta: **{average_delta:.4f}**",
        f"Maximum silhouette delta: **{maximum_delta:.4f}**",
        "",
        "The guard is deliberately broad: it detects catastrophic scale, drift, or silhouette loss; it does not claim subjective design quality.",
        "",
        "| Case | View | IoU | Delta | Area ratio | Centroid shift | Guard |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in metrics:
        lines.append(
            f"| {item.case} | {item.view} | {item.silhouette_iou:.4f} | "
            f"{item.silhouette_delta:.4f} | {item.area_ratio:.4f} | "
            f"{item.centroid_shift_normalized:.4f} | "
            f"{'PASS' if item.catastrophic_guard else 'FAIL'} |"
        )
    (output_root / "visual_regression_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("DOBO Visual Regression")
    print("baseline", args.baseline_label, args.baseline_commit)
    print("candidate", args.candidate_label, args.candidate_commit)
    print("average silhouette IoU", f"{average_iou:.4f}")
    print("average silhouette delta", f"{average_delta:.4f}")
    print("maximum silhouette delta", f"{maximum_delta:.4f}")
    print("catastrophic guard", all_safe, "OK" if all_safe else "FAILED")
    if not all_safe:
        raise SystemExit(2)
    print("DOBO Visual Regression: Valid OK")


if __name__ == "__main__":
    main()
