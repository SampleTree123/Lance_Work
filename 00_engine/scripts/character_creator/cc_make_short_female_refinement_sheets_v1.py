"""Create labeled close-up sheets for the F05 refinement reviews."""

import argparse
import json
import math
import os
from pathlib import Path

from PIL import Image, ImageDraw

from cc_make_head_bodyfit_scale_review_sheets_v1 import (
    BACKGROUND,
    GRID,
    MUTED,
    TEXT,
    contain,
    font,
    load_rgb,
    write_json,
)


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def collect(summary_path):
    summary_path = os.path.realpath(os.path.abspath(summary_path))
    summary = read_json(summary_path)
    if summary.get("success") is not True:
        raise RuntimeError("Review summary is not successful: " + summary_path)
    results = summary.get("results") or []
    if len(results) != 1 or results[0].get("success") is not True:
        raise RuntimeError("Expected one successful review result")
    review = results[0].get("neck_morph_review") or {}
    morphs = {}
    for morph in review.get("morphs") or []:
        review_id = morph.get("review_id")
        candidates = []
        for candidate in morph.get("candidates") or []:
            views = candidate.get("views") or {}
            candidates.append(
                {
                    "value": float(candidate["value"]),
                    "views": {
                        key: os.path.realpath(os.path.abspath(value))
                        for key, value in views.items()
                    },
                }
            )
        candidates.sort(key=lambda item: item["value"])
        morphs[review_id] = candidates
    return summary_path, morphs


def value_label(value):
    number = int(round(float(value) * 100.0))
    return "{:+d}".format(number) if number else "0"


def crop(source, crop_kind):
    width, height = source.size
    if crop_kind == "torso":
        box = (
            int(width * 0.27),
            int(height * 0.25),
            int(width * 0.73),
            int(height * 0.66),
        )
    elif crop_kind == "head_shoulders":
        box = (
            int(width * 0.25),
            int(height * 0.16),
            int(width * 0.75),
            int(height * 0.51),
        )
    else:
        raise ValueError("Unsupported crop kind: " + crop_kind)
    return source.crop(box)


def render_sheet(review_id, candidates, crop_kind, output_path):
    columns = 3
    rows = int(math.ceil(len(candidates) / float(columns)))
    tile_width = 420
    tile_height = 430
    header_height = 92
    panel_size = (380, 350)
    sheet = Image.new(
        "RGB",
        (columns * tile_width, header_height + rows * tile_height),
        BACKGROUND,
    )
    draw = ImageDraw.Draw(sheet)
    draw.text(
        (18, 12),
        "F05 | {} | {}".format(review_id, crop_kind.replace("_", " ")),
        fill=TEXT,
        font=font(24, bold=True),
    )
    draw.text(
        (18, 52),
        "Head Scale fixed at -10. Only the labeled Morph changes.",
        fill=MUTED,
        font=font(16),
    )
    for index, candidate in enumerate(candidates):
        column = index % columns
        row = index // columns
        x = column * tile_width
        y = header_height + row * tile_height
        image_path = candidate["views"].get("yaw_000")
        if not image_path or not os.path.isfile(image_path):
            raise RuntimeError("Missing yaw_000 image for " + review_id)
        source = crop(load_rgb(image_path), crop_kind)
        panel = contain(source, panel_size)
        sheet.paste(panel, (x + 20, y + 52))
        draw.text(
            (x + 20, y + 14),
            "Value {}".format(value_label(candidate["value"])),
            fill=TEXT,
            font=font(20, bold=True),
        )
        draw.rectangle(
            (x + 8, y + 5, x + tile_width - 9, y + tile_height - 8),
            outline=GRID,
            width=1,
        )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=True)


def build(shape_summary, shoulder_summary, output_dir):
    output_dir = Path(os.path.realpath(os.path.abspath(output_dir)))
    shape_path, shape = collect(shape_summary)
    shoulder_path, shoulder = collect(shoulder_summary)
    requested = (
        (shape, "plump_shape_reduction", "torso"),
        (shape, "fit_shape_increase", "torso"),
        (shoulder, "shoulder_top_height_a", "head_shoulders"),
        (shoulder, "shoulder_top_height_b", "head_shoulders"),
    )
    files = {}
    for source, review_id, crop_kind in requested:
        if review_id not in source:
            raise RuntimeError("Missing review: " + review_id)
        output_path = output_dir / (review_id + "_" + crop_kind + ".png")
        render_sheet(review_id, source[review_id], crop_kind, output_path)
        files[review_id] = output_path.name
    manifest = {
        "schema_version": 1,
        "shape_summary": shape_path,
        "shoulder_summary": shoulder_path,
        "files": files,
    }
    write_json(manifest, output_dir / "index.json")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shape-summary", required=True)
    parser.add_argument("--shoulder-summary", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    manifest = build(
        args.shape_summary,
        args.shoulder_summary,
        args.output_dir,
    )
    print(
        json.dumps(
            {
                "file_count": len(manifest["files"]),
                "output_dir": os.path.realpath(args.output_dir),
                "success": True,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
