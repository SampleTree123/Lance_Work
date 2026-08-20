"""Build full-body and head-shoulders sheets for a CC5 neck review."""

import argparse
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


BACKGROUND = (22, 25, 30)
PANEL = (31, 35, 41)
TEXT = (240, 242, 245)
MUTED = (177, 184, 194)
GRID = (65, 71, 80)
BASELINE = (218, 174, 72)


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(data, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True, ensure_ascii=True)
        handle.write("\n")
    os.replace(str(temporary), str(path))


def font(size, bold=False):
    candidates = (
        r"C:\Windows\Fonts\segoeuib.ttf"
        if bold
        else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf"
        if bold
        else r"C:\Windows\Fonts\arial.ttf",
    )
    for path in candidates:
        if os.path.isfile(path):
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def load_rgb(path):
    with Image.open(path) as source:
        return ImageOps.exif_transpose(source).convert("RGB")


def contain(image, size):
    canvas = Image.new("RGB", size, PANEL)
    fitted = ImageOps.contain(image, size, method=Image.Resampling.LANCZOS)
    canvas.paste(
        fitted,
        ((size[0] - fitted.width) // 2, (size[1] - fitted.height) // 2),
    )
    return canvas


def head_shoulders_crop(image):
    width, height = image.size
    return image.crop(
        (
            int(round(width * 0.25)),
            int(round(height * 0.01)),
            int(round(width * 0.75)),
            int(round(height * 0.51)),
        )
    )


def slider_label(value):
    slider_value = int(round(float(value) * 100.0))
    return "{:+d}".format(slider_value) if slider_value else "0"


def collect_case(summary_path):
    summary = read_json(summary_path)
    if summary.get("success") is not True:
        raise RuntimeError("Neck review summary is not successful")
    results = summary.get("results") or []
    if len(results) != 1 or results[0].get("success") is not True:
        raise RuntimeError("Expected one successful neck review case")
    result = results[0]
    review = result.get("neck_morph_review") or {}
    morphs = review.get("morphs") or []
    if len(morphs) != 1:
        raise RuntimeError("Expected one reviewed neck Morph")
    candidates = sorted(
        morphs[0].get("candidates") or [],
        key=lambda item: float(item["value"]),
        reverse=True,
    )
    if not candidates:
        raise RuntimeError("Neck review has no candidates")
    baseline = next(
        (item for item in candidates if abs(float(item["value"])) <= 1e-7),
        None,
    )
    if baseline is None:
        raise RuntimeError("Neck review has no zero baseline")
    baseline_height = (
        float(baseline["avatar_bounds"]["maximum"][2])
        - float(baseline["avatar_bounds"]["minimum"][2])
    )
    for candidate in candidates:
        height = (
            float(candidate["avatar_bounds"]["maximum"][2])
            - float(candidate["avatar_bounds"]["minimum"][2])
        )
        candidate["height_cm"] = height
        candidate["height_delta_cm"] = height - baseline_height
        for image_path in candidate.get("views", {}).values():
            if not os.path.isfile(image_path):
                raise RuntimeError("Missing review image: {}".format(image_path))
    return summary, result, review, morphs[0], candidates


def render_sheet(
    candidates,
    views,
    crop_mode,
    output_path,
    bodyfit_id="F01_Lean",
):
    label_width = 150
    cell_width = 238
    cell_height = 252
    header_height = 150
    width = label_width + cell_width * len(candidates)
    height = header_height + cell_height * len(views)
    sheet = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    title = "{} | Neck Height | {}".format(
        bodyfit_id,
        "Head and Shoulders" if crop_mode else "Full Body"
    )
    draw.text((16, 12), title, fill=TEXT, font=font(25, bold=True))
    draw.text(
        (16, 49),
        "Head Scale fixed at -20. Height delta is measured against Neck Height 0.",
        fill=MUTED,
        font=font(15),
    )
    for column, candidate in enumerate(candidates):
        x = label_width + column * cell_width
        value = float(candidate["value"])
        color = BASELINE if abs(value) <= 1e-7 else TEXT
        draw.text(
            (x + 10, 86),
            "Neck {}".format(slider_label(value)),
            fill=color,
            font=font(18, bold=True),
        )
        draw.text(
            (x + 10, 118),
            "height {:+.2f} cm".format(candidate["height_delta_cm"]),
            fill=MUTED,
            font=font(14),
        )
    for row, view in enumerate(views):
        view_id = view["view_id"]
        y = header_height + row * cell_height
        draw.text(
            (16, y + 16),
            "Yaw {:g} deg".format(float(view["yaw_degrees"])),
            fill=TEXT,
            font=font(17, bold=True),
        )
        for column, candidate in enumerate(candidates):
            x = label_width + column * cell_width
            image = load_rgb(candidate["views"][view_id])
            if crop_mode:
                image = head_shoulders_crop(image)
            panel = contain(image, (226, 226))
            sheet.paste(panel, (x + 6, y + 6))
            color = (
                BASELINE
                if abs(float(candidate["value"])) <= 1e-7
                else GRID
            )
            draw.rectangle(
                (x + 4, y + 4, x + cell_width - 5, y + 233),
                outline=color,
                width=3 if color == BASELINE else 1,
            )
        draw.line(
            (0, y + cell_height - 1, width, y + cell_height - 1),
            fill=GRID,
            width=1,
        )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=True)


def build_review(summary_path, output_dir):
    summary_path = os.path.realpath(os.path.abspath(summary_path))
    output_dir = Path(os.path.realpath(os.path.abspath(output_dir)))
    summary, result, review, morph, candidates = collect_case(summary_path)
    full_path = output_dir / "overview_full_body.png"
    close_path = output_dir / "overview_head_shoulders.png"
    views = review.get("views") or []
    if not views:
        raise RuntimeError("Neck review has no view definitions")
    render_sheet(candidates, views, False, full_path, bodyfit_id="F01_Lean")
    render_sheet(candidates, views, True, close_path, bodyfit_id="F01_Lean")
    index = {
        "bodyfit_id": "F01_Lean",
        "candidate_count": len(candidates),
        "head_scale": review.get("head_scale", {}).get("target"),
        "morph_id": morph.get("morph", {}).get("id"),
        "morph_review_id": morph.get("review_id"),
        "review_restored_exactly": review.get("restored_exactly") is True,
        "scene_restored_exactly": (
            summary.get("scene_restoration", {}).get("restored_exactly") is True
        ),
        "schema_version": 1,
        "sheets": {
            "full_body": full_path.name,
            "head_shoulders": close_path.name,
        },
        "source_summary": summary_path,
        "values": [
            {
                "height_cm": item["height_cm"],
                "height_delta_cm": item["height_delta_cm"],
                "slider": int(round(float(item["value"]) * 100.0)),
                "value": float(item["value"]),
            }
            for item in candidates
        ],
        "yaw_restored_exactly": review.get("yaw_restored_exactly") is True,
    }
    write_json(index, output_dir / "index.json")
    return output_dir / "index.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    index_path = build_review(args.summary, args.output_dir)
    print("Neck review sheets created: {}".format(index_path.parent))
    print("Review index: {}".format(index_path))


if __name__ == "__main__":
    main()
