"""Create per-asset contact sheets for scalp-hair static pressure."""

import argparse
import json
import os

from PIL import Image, ImageDraw, ImageFont


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SUMMARY = os.path.join(
    SCRIPT_DIR, "cc_scalp_hair_static_pressure_summary_v1.json"
)
VIEWS = (
    ("face_front_preview", "Front"),
    ("face_three_quarter_preview", "3/4"),
    ("face_profile_preview", "Profile"),
    ("hair_rear_three_quarter_preview", "Rear 3/4"),
    ("hair_rear_preview", "Rear"),
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


def render_asset(asset_id, cases, output_path):
    if len(cases) != 4:
        raise RuntimeError(
            "{} expected four extreme faces, found {}".format(
                asset_id,
                len(cases),
            )
        )
    cell_width = 220
    cell_height = 295
    label_width = 160
    title_height = 68
    view_label_height = 30
    columns = len(VIEWS)
    rows = len(cases)
    sheet = Image.new(
        "RGB",
        (
            label_width + columns * cell_width,
            title_height + view_label_height + rows * cell_height,
        ),
        (19, 22, 27),
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    title = "{} | {} | {}".format(
        cases[0]["display_name"],
        asset_id,
        cases[0].get("silhouette_family"),
    )
    draw.text((12, 12), title, fill=(242, 244, 247), font=font)
    for column, unused_view in enumerate(VIEWS):
        draw.text(
            (
                label_width + column * cell_width + 8,
                title_height + 8,
            ),
            unused_view[1],
            fill=(207, 211, 218),
            font=font,
        )
    y = title_height + view_label_height
    for case in sorted(cases, key=lambda item: item["face_index"]):
        draw.text(
            (12, y + 118),
            case["primary_seed_id"],
            fill=(242, 244, 247),
            font=font,
        )
        draw.text(
            (12, y + 138),
            case["sex"],
            fill=(171, 178, 188),
            font=font,
        )
        for column, (artifact_key, unused_label) in enumerate(VIEWS):
            path = case["artifact_paths"][artifact_key]
            if not os.path.isfile(path):
                raise RuntimeError(
                    "Review image is missing: {}".format(path)
                )
            x = label_width + column * cell_width
            sheet.paste(
                fitted_image(path, cell_width, cell_height),
                (x, y),
            )
        y += cell_height
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=True)


def main():
    parser = argparse.ArgumentParser(
        description="Create CC5 scalp-hair static pressure sheets."
    )
    parser.add_argument("--summary", default=DEFAULT_SUMMARY)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    summary_path = os.path.realpath(os.path.abspath(args.summary))
    output_dir = os.path.realpath(os.path.abspath(args.output_dir))
    summary = read_json(summary_path)
    by_asset = {}
    for item in summary.get("cases") or []:
        if item.get("structural_pass") is not True:
            continue
        by_asset.setdefault(item["asset_id"], []).append(item)
    records = []
    for asset_id, cases in sorted(by_asset.items()):
        output_path = os.path.join(output_dir, asset_id + ".png")
        render_asset(asset_id, cases, output_path)
        records.append(
            {
                "asset_id": asset_id,
                "case_count": len(cases),
                "contact_sheet": output_path,
                "display_name": cases[0]["display_name"],
                "visual_review_status": "pending",
            }
        )
    index_path = os.path.join(output_dir, "index.json")
    write_json(
        {
            "asset_count": len(records),
            "assets": records,
            "schema_version": 1,
            "source_summary": summary_path,
        },
        index_path,
    )
    print(
        "Created {} static pressure sheets -> {}".format(
            len(records),
            output_dir,
        )
    )


if __name__ == "__main__":
    main()
