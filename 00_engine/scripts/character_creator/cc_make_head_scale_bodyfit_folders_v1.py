"""Arrange CC5 head-scale review sheets into one folder per bodyfit."""

import argparse
import json
import os
import re
from pathlib import Path

from PIL import Image, ImageDraw

from cc_make_head_bodyfit_scale_review_sheets_v1 import (
    BACKGROUND,
    GRID,
    MUTED,
    PANEL,
    REFERENCE,
    TEXT,
    case_title,
    collect_cases,
    contain,
    font,
    head_shoulders_crop,
    is_previous_reference,
    load_rgb,
    matrix_sort_key,
    slider_label,
    write_json,
)


def safe_filename(value):
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value)).strip("._")
    return value or "unnamed"


def render_case_view(case, view, output_path):
    columns = 5
    rows = 2
    tile_width = 432
    tile_height = 458
    header_height = 92
    image_size = (400, 400)
    width = columns * tile_width
    height = header_height + rows * tile_height
    sheet = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    view_title = "Full Body" if view == "full_body" else "Head and Shoulders"
    draw.text(
        (18, 12),
        "{} | {}".format(case_title(case), view_title),
        fill=TEXT,
        font=font(26, bold=True),
    )
    draw.text(
        (18, 52),
        "Ten fixed-camera candidates. Slider labels use the Character Creator display scale.",
        fill=MUTED,
        font=font(16),
    )

    for index, candidate in enumerate(case["candidates"]):
        column = index % columns
        row = index // columns
        x = column * tile_width
        y = header_height + row * tile_height
        image = load_rgb(candidate["image"])
        if view == "head_shoulders":
            image = head_shoulders_crop(image)
        panel = contain(image, image_size)
        sheet.paste(panel, (x + 16, y + 42))

        highlighted = is_previous_reference(case, candidate["value"])
        label_color = REFERENCE if highlighted else TEXT
        draw.text(
            (x + 16, y + 10),
            "Head Scale {}".format(slider_label(candidate["value"])),
            fill=label_color,
            font=font(19, bold=True),
        )
        draw.rectangle(
            (x + 7, y + 3, x + tile_width - 8, y + tile_height - 7),
            outline=REFERENCE if highlighted else GRID,
            width=3 if highlighted else 1,
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=True)


def bodyfit_order(case):
    return matrix_sort_key(case, "bodyfit_matrix")


def build_bodyfit_folders(summary_path, output_dir):
    summary_path = os.path.realpath(os.path.abspath(summary_path))
    output_dir = Path(os.path.realpath(os.path.abspath(output_dir)))
    summary, all_cases = collect_cases(summary_path)
    cases = [case for case in all_cases if "bodyfit_matrix" in case["review_groups"]]
    face_cases = [case for case in all_cases if "face_variation" in case["review_groups"]]

    average_m04 = next(
        case for case in cases if case["preset_id"] == "HBS_FACE_M04_AVERAGE"
    )
    m04_variants = sorted(
        face_cases,
        key=lambda case: matrix_sort_key(case, "face_variation"),
    )
    expanded_cases = []
    for case in sorted(cases, key=bodyfit_order):
        if case is average_m04:
            expanded_cases.extend(m04_variants)
        else:
            expanded_cases.append(case)

    manifest = {
        "bodyfit_count": 8,
        "case_count": len(expanded_cases),
        "folders": {},
        "matrix_restored_exactly": summary.get("scene_restoration", {}).get("restored_exactly") is True,
        "schema_version": 1,
        "sheet_count": 0,
        "source_summary": summary_path,
    }
    output_dir.mkdir(parents=True, exist_ok=True)

    bodyfit_case_numbers = {}
    for case in expanded_cases:
        bodyfit_id = case["bodyfit_id"]
        bodyfit_case_numbers[bodyfit_id] = bodyfit_case_numbers.get(bodyfit_id, 0) + 1
        case_number = bodyfit_case_numbers[bodyfit_id]
        bodyfit_dir = output_dir / safe_filename(bodyfit_id)
        stem = "{:02d}_{}_{}".format(
            case_number,
            safe_filename(case["face_recipe_id"]),
            safe_filename(case["face_shape_role"]),
        )
        full_path = bodyfit_dir / (stem + "_full_body.png")
        close_path = bodyfit_dir / (stem + "_head_shoulders.png")
        render_case_view(case, "full_body", full_path)
        render_case_view(case, "head_shoulders", close_path)

        record = {
            "face_recipe_id": case["face_recipe_id"],
            "face_shape_role": case["face_shape_role"],
            "full_body": full_path.relative_to(output_dir).as_posix(),
            "head_shoulders": close_path.relative_to(output_dir).as_posix(),
            "preset_id": case["preset_id"],
        }
        manifest["folders"].setdefault(bodyfit_id, []).append(record)
        manifest["sheet_count"] += 2

    write_json(manifest, output_dir / "index.json")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    manifest = build_bodyfit_folders(args.summary, args.output_dir)
    print("Bodyfit folders created: {}".format(os.path.realpath(args.output_dir)))
    print("Bodyfits: {}".format(manifest["bodyfit_count"]))
    print("Character cases: {}".format(manifest["case_count"]))
    print("Review sheets: {}".format(manifest["sheet_count"]))


if __name__ == "__main__":
    main()
