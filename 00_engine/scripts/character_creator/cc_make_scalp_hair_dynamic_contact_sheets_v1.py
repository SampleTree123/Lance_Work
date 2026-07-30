"""Create contact sheets for completed scalp-hair dynamic cases."""

import argparse
import json
import os

from PIL import Image, ImageDraw, ImageFont


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SUMMARY = os.path.join(
    SCRIPT_DIR, "cc_scalp_hair_dynamic_automation_summary_v1.json"
)


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(data, path):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(
            data,
            handle,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
        handle.write("\n")
    os.replace(temporary, path)


def fitted_image(path, width, height):
    with Image.open(path) as source:
        image = source.convert("RGB")
    image.thumbnail((width, height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (width, height), (28, 31, 36))
    x = (width - image.width) // 2
    y = (height - image.height) // 2
    canvas.paste(image, (x, y))
    return canvas


def case_images(item):
    paths = item["artifact_paths"]
    static = [
        ("front", paths["face_front"]),
        ("profile", paths["face_profile"]),
        ("rear", paths["hair_rear"]),
    ]
    dynamic = [
        (
            "motion_{:02d}".format(index),
            path,
        )
        for index, path in enumerate(
            paths.get("motion_images") or [],
            1,
        )
    ]
    return static + dynamic


def render_case(item, output_path):
    images = case_images(item)
    if len(images) != 8:
        raise RuntimeError(
            "{} expected 8 review images, found {}".format(
                item["preset_id"],
                len(images),
            )
        )
    cell_width = 240
    cell_height = 330
    label_height = 28
    header_height = 72
    columns = 4
    rows = 2
    sheet = Image.new(
        "RGB",
        (
            cell_width * columns,
            header_height + (cell_height + label_height) * rows,
        ),
        (19, 22, 27),
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    header = "{} | {} | {} | {} | {}".format(
        item["preset_id"],
        item["display_name"],
        item["sex"],
        item["case_phase"],
        item["motion_id"],
    )
    draw.text((12, 10), header, fill=(242, 244, 247), font=font)
    detail = "auto={} active={} max_active_delta={:.3f}".format(
        item["automation_status"],
        item["physics"].get("physics_active_count"),
        item["displacement"][
            "active_part_max_center_displacement"
        ],
    )
    draw.text((12, 34), detail, fill=(171, 178, 188), font=font)
    for index, (label, path) in enumerate(images):
        if not os.path.isfile(path):
            raise RuntimeError("Review image is missing: {}".format(path))
        column = index % columns
        row = index // columns
        x = column * cell_width
        y = header_height + row * (cell_height + label_height)
        sheet.paste(
            fitted_image(path, cell_width, cell_height),
            (x, y),
        )
        draw.text(
            (x + 8, y + cell_height + 7),
            label,
            fill=(207, 211, 218),
            font=font,
        )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=True)


def main():
    parser = argparse.ArgumentParser(
        description="Create CC5 scalp-hair dynamic contact sheets."
    )
    parser.add_argument("--summary", default=DEFAULT_SUMMARY)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    summary_path = os.path.realpath(os.path.abspath(args.summary))
    output_dir = os.path.realpath(os.path.abspath(args.output_dir))
    summary = read_json(summary_path)
    records = []
    for item in summary.get("cases") or []:
        if not item.get("images_complete"):
            continue
        output_path = os.path.join(
            output_dir,
            item["preset_id"] + ".png",
        )
        render_case(item, output_path)
        records.append(
            {
                "asset_id": item["asset_id"],
                "contact_sheet": output_path,
                "preset_id": item["preset_id"],
                "visual_review_status": "pending",
            }
        )
    index_path = os.path.join(output_dir, "index.json")
    write_json(
        {
            "case_count": len(records),
            "cases": records,
            "schema_version": 1,
            "source_summary": summary_path,
        },
        index_path,
    )
    print(
        "Created {} contact sheets -> {}".format(
            len(records),
            output_dir,
        )
    )


if __name__ == "__main__":
    main()
