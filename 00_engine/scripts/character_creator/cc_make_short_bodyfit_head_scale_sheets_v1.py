"""Create two review sheets per short BodyFit: full body and head/shoulders."""

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
    PANEL,
    TEXT,
    contain,
    font,
    head_shoulders_crop,
    load_rgb,
    slider_label,
    write_json,
)


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def bodyfit_id(result):
    source = (result.get("application") or {}).get("source_project")
    if source:
        name = Path(source).stem
        if name.endswith("_candidate"):
            name = name[: -len("_candidate")]
        return name
    token = result.get("preset_id", "UNKNOWN")
    return token.replace("SHORT_HEAD_SCALE_", "")


def collect(summary_path):
    summary = read_json(summary_path)
    if summary.get("success") is not True:
        raise RuntimeError("Head Scale review summary is not successful")
    cases = []
    for result in summary.get("results") or []:
        if result.get("success") is not True:
            raise RuntimeError(
                "Failed Head Scale case: {}".format(result.get("preset_id"))
            )
        review = result.get("head_scale_review") or {}
        candidates = []
        for item in review.get("candidates") or []:
            image_path = os.path.realpath(os.path.abspath(item["image"]))
            if not os.path.isfile(image_path):
                raise RuntimeError(
                    "Missing Head Scale image: {}".format(image_path)
                )
            candidates.append(
                {
                    "image": image_path,
                    "value": float(item["value"]),
                }
            )
        candidates.sort(key=lambda item: item["value"])
        if len(candidates) != 9:
            raise RuntimeError(
                "Expected 9 Head Scale candidates for {}".format(
                    result.get("preset_id")
                )
            )
        cases.append(
            {
                "bodyfit_id": bodyfit_id(result),
                "candidates": candidates,
                "face_recipe_id": result.get("face_recipe_id"),
                "preset_id": result.get("preset_id"),
                "sex": result.get("sex"),
            }
        )
    if len(cases) != 2:
        raise RuntimeError("Expected two short BodyFit review cases")
    return summary, sorted(cases, key=lambda item: item["bodyfit_id"])


def render_sheet(case, view, output_path):
    columns = 5
    rows = int(math.ceil(len(case["candidates"]) / float(columns)))
    tile_width = 380
    tile_height = 420
    header_height = 92
    panel_size = (344, 344)
    sheet = Image.new(
        "RGB",
        (columns * tile_width, header_height + rows * tile_height),
        BACKGROUND,
    )
    draw = ImageDraw.Draw(sheet)
    view_title = "Full Body" if view == "full_body" else "Head and Shoulders"
    draw.text(
        (18, 12),
        "{} | Head Scale | {}".format(case["bodyfit_id"], view_title),
        fill=TEXT,
        font=font(25, bold=True),
    )
    draw.text(
        (18, 51),
        "Fixed body, face, camera, and pose. Only Head Scale changes.",
        fill=MUTED,
        font=font(16),
    )

    for index, candidate in enumerate(case["candidates"]):
        column = index % columns
        row = index // columns
        x = column * tile_width
        y = header_height + row * tile_height
        source = load_rgb(candidate["image"])
        if view == "head_shoulders":
            source = head_shoulders_crop(source)
        panel = contain(source, panel_size)
        sheet.paste(panel, (x + 18, y + 48))
        draw.text(
            (x + 18, y + 13),
            "Head Scale {}".format(slider_label(candidate["value"])),
            fill=TEXT,
            font=font(19, bold=True),
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
    summary_path = os.path.realpath(os.path.abspath(summary_path))
    output_dir = Path(os.path.realpath(os.path.abspath(output_dir)))
    summary, cases = collect(summary_path)
    manifest = {
        "schema_version": 1,
        "source_summary": summary_path,
        "matrix_restored_exactly": (
            (summary.get("scene_restoration") or {}).get("restored_exactly")
            is True
        ),
        "bodyfit_count": len(cases),
        "candidate_values": [
            item["value"] for item in cases[0]["candidates"]
        ],
        "folders": {},
    }
    for case in cases:
        body_dir = output_dir / case["bodyfit_id"]
        full_path = body_dir / "head_scale_full_body.png"
        close_path = body_dir / "head_scale_head_shoulders.png"
        render_sheet(case, "full_body", full_path)
        render_sheet(case, "head_shoulders", close_path)
        manifest["folders"][case["bodyfit_id"]] = {
            "full_body": full_path.relative_to(output_dir).as_posix(),
            "head_shoulders": close_path.relative_to(output_dir).as_posix(),
            "preset_id": case["preset_id"],
            "sex": case["sex"],
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
                "bodyfit_count": manifest["bodyfit_count"],
                "output_dir": os.path.realpath(args.output_dir),
                "success": True,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
