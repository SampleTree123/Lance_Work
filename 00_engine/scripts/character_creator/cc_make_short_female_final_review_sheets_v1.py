"""Create labeled comparison sheets for the final F05 refinement review."""

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


REVIEW_ID = "selected_shoulder_top_height_b"


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def collect(summary_path):
    summary_path = os.path.realpath(os.path.abspath(summary_path))
    summary = read_json(summary_path)
    if summary.get("success") is not True:
        raise RuntimeError("Review summary is not successful")
    results = summary.get("results") or []
    if len(results) != 1 or results[0].get("success") is not True:
        raise RuntimeError("Expected one successful review result")
    review = results[0].get("neck_morph_review") or {}
    matching = [
        item
        for item in review.get("morphs") or []
        if item.get("review_id") == REVIEW_ID
    ]
    if len(matching) != 1:
        raise RuntimeError("Expected one Shoulder Top Height B review")
    candidates = []
    for candidate in matching[0].get("candidates") or []:
        candidates.append(
            {
                "value": float(candidate["value"]),
                "views": {
                    key: os.path.realpath(os.path.abspath(value))
                    for key, value in (candidate.get("views") or {}).items()
                },
            }
        )
    candidates.sort(key=lambda item: item["value"])
    return summary_path, candidates


def crop(source, crop_kind):
    if crop_kind == "full_body":
        return source
    width, height = source.size
    if crop_kind == "head_shoulders":
        return source.crop(
            (
                int(width * 0.25),
                int(height * 0.13),
                int(width * 0.75),
                int(height * 0.52),
            )
        )
    raise ValueError("Unsupported crop kind: " + crop_kind)


def value_label(value):
    return str(int(round(float(value) * 100.0)))


def render_sheet(candidates, view_id, crop_kind, output_path):
    columns = 3
    rows = int(math.ceil(len(candidates) / float(columns)))
    tile_width = 430
    tile_height = 500 if crop_kind == "full_body" else 440
    header_height = 100
    panel_size = (390, tile_height - 70)
    sheet = Image.new(
        "RGB",
        (columns * tile_width, header_height + rows * tile_height),
        BACKGROUND,
    )
    draw = ImageDraw.Draw(sheet)
    draw.text(
        (18, 12),
        "F05 final refinement | {} | {}".format(view_id, crop_kind),
        fill=TEXT,
        font=font(24, bold=True),
    )
    draw.text(
        (18, 52),
        "Head Scale -10 | Plump Body Shape 30 | Shoulder Top Height B varies",
        fill=MUTED,
        font=font(16),
    )
    for index, candidate in enumerate(candidates):
        column = index % columns
        row = index // columns
        x = column * tile_width
        y = header_height + row * tile_height
        image_path = candidate["views"].get(view_id)
        if not image_path or not os.path.isfile(image_path):
            raise RuntimeError("Missing {} image".format(view_id))
        source = crop(load_rgb(image_path), crop_kind)
        panel = contain(source, panel_size)
        sheet.paste(panel, (x + 20, y + 52))
        draw.text(
            (x + 20, y + 14),
            "Shoulder B {}".format(value_label(candidate["value"])),
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


def build(summary_path, output_dir):
    output_dir = Path(os.path.realpath(os.path.abspath(output_dir)))
    source_summary, candidates = collect(summary_path)
    requested = (
        ("yaw_000", "full_body", "f05_final_full_body.png"),
        ("yaw_000", "head_shoulders", "f05_final_head_shoulders.png"),
        (
            "yaw_045",
            "head_shoulders",
            "f05_final_head_shoulders_yaw045.png",
        ),
    )
    files = []
    for view_id, crop_kind, filename in requested:
        render_sheet(
            candidates,
            view_id,
            crop_kind,
            output_dir / filename,
        )
        files.append(filename)
    manifest = {
        "candidate_values": [item["value"] for item in candidates],
        "files": files,
        "schema_version": 1,
        "source_summary": source_summary,
    }
    write_json(manifest, output_dir / "index.json")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    manifest = build(args.summary, args.output_dir)
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
