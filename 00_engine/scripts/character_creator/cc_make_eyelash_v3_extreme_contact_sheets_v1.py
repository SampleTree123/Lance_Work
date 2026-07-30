"""Create per-asset eye contact sheets for the V3 eyelash matrix."""

import argparse
import json
import os

from PIL import Image, ImageDraw, ImageFont, ImageOps


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SUMMARY = os.path.join(
    SCRIPT_DIR, "cc_eyelash_v3_extreme_automation_summary_v1.json"
)
POSES = (
    ("face_front_preview", "Neutral"),
    ("eyelash_blink_preview", "Blink"),
    ("eyelash_asymmetric_preview", "Left Blink"),
    ("eyelash_wide_preview", "Wide"),
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


def font(size, bold=False):
    candidates = (
        (
            r"C:\Windows\Fonts\segoeuib.ttf"
            if bold
            else r"C:\Windows\Fonts\segoeui.ttf"
        ),
        (
            r"C:\Windows\Fonts\arialbd.ttf"
            if bold
            else r"C:\Windows\Fonts\arial.ttf"
        ),
    )
    for path in candidates:
        if os.path.isfile(path):
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def eye_crop(path, size):
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    width, height = image.size
    image = image.crop(
        (
            int(width * 0.08),
            int(height * 0.42),
            int(width * 0.56),
            int(height * 0.78),
        )
    )
    image.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, (27, 31, 37))
    x = (size[0] - image.width) // 2
    y = (size[1] - image.height) // 2
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
    columns = len(POSES)
    rows = len(cases)
    image_size = (300, 190)
    row_label_width = 180
    column_label_height = 42
    title_height = 68
    width = row_label_width + columns * image_size[0]
    height = title_height + column_label_height + rows * image_size[1]
    sheet = Image.new("RGB", (width, height), (22, 25, 30))
    draw = ImageDraw.Draw(sheet)
    title_font = font(24, bold=True)
    label_font = font(17, bold=True)
    detail_font = font(14)
    draw.text(
        (16, 12),
        "{} | {}".format(cases[0]["display_name"], asset_id),
        fill=(240, 242, 245),
        font=title_font,
    )
    for column, unused_pose in enumerate(POSES):
        draw.text(
            (
                row_label_width + column * image_size[0] + 10,
                title_height + 9,
            ),
            unused_pose[1],
            fill=(194, 200, 208),
            font=label_font,
        )
    y = title_height + column_label_height
    for case in sorted(cases, key=lambda item: item["face_index"]):
        draw.text(
            (14, y + 54),
            case["primary_seed_id"],
            fill=(235, 238, 242),
            font=label_font,
        )
        draw.text(
            (14, y + 82),
            case["sex"],
            fill=(153, 162, 174),
            font=detail_font,
        )
        for column, (artifact_key, unused_label) in enumerate(POSES):
            path = case["artifact_paths"][artifact_key]
            if not os.path.isfile(path):
                raise RuntimeError(
                    "Review image is missing: {}".format(path)
                )
            preview = eye_crop(path, image_size)
            x = row_label_width + column * image_size[0]
            sheet.paste(preview, (x, y))
        y += image_size[1]
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=True)


def main():
    parser = argparse.ArgumentParser(
        description="Create CC5 V3 eyelash eye contact sheets."
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
        "Created {} eyelash contact sheets -> {}".format(
            len(records),
            output_dir,
        )
    )


if __name__ == "__main__":
    main()
