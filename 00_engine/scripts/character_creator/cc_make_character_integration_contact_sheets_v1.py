"""Create per-character contact sheets for canonical CC5 integration."""

import argparse
import json
import os

from PIL import Image, ImageDraw, ImageFont, ImageOps


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SUMMARY = os.path.join(
    SCRIPT_DIR, "cc_character_integration_automation_summary_v1.json"
)
VIEWS = (
    ("face_front_preview", "Front"),
    ("face_three_quarter_preview", "3/4"),
    ("face_profile_preview", "Profile"),
    ("hair_rear_three_quarter_preview", "Rear 3/4"),
    ("hair_rear_preview", "Rear"),
    ("face_blink_bilateral_preview", "Blink"),
    ("face_look_left_preview", "Look L"),
    ("face_look_right_preview", "Look R"),
    ("face_squint_preview", "Squint"),
    ("face_widen_preview", "Widen"),
    ("face_brow_raise_preview", "Brow Up"),
    ("face_brow_down_preview", "Brow Down"),
    ("face_smile_preview", "Smile"),
    ("face_jaw_open_preview", "Jaw"),
    ("face_jaw_open_three_quarter_preview", "Jaw 3/4"),
    ("reconstructed_preview", "Full"),
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


def fitted_image(path, size):
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, (27, 31, 37))
    x = (size[0] - image.width) // 2
    y = (size[1] - image.height) // 2
    canvas.paste(image, (x, y))
    return canvas


def render_case(case, output_path):
    columns = 4
    rows = 4
    image_size = (300, 300)
    label_height = 34
    header_height = 92
    width = columns * image_size[0]
    height = header_height + rows * (image_size[1] + label_height)
    sheet = Image.new("RGB", (width, height), (22, 25, 30))
    draw = ImageDraw.Draw(sheet)
    title_font = font(24, bold=True)
    detail_font = font(15)
    label_font = font(16, bold=True)
    draw.text(
        (16, 12),
        "{} | {} | {} | {}".format(
            case["preset_id"],
            case["sex"],
            case["bodyfit_id"],
            case["age_label"],
        ),
        fill=(240, 242, 245),
        font=title_font,
    )
    draw.text(
        (16, 50),
        "{} | {} | {}".format(
            case["face_recipe_id"],
            case.get("scalp_hair_display_name") or "Hair",
            case["hair_presentation_mode"],
        ),
        fill=(171, 178, 188),
        font=detail_font,
    )
    for index, (artifact_key, label) in enumerate(VIEWS):
        path = case["artifact_paths"][artifact_key]
        if not os.path.isfile(path):
            raise RuntimeError(
                "Review image is missing: {}".format(path)
            )
        column = index % columns
        row = index // columns
        x = column * image_size[0]
        y = header_height + row * (image_size[1] + label_height)
        sheet.paste(fitted_image(path, image_size), (x, y))
        draw.text(
            (x + 10, y + image_size[1] + 7),
            label,
            fill=(207, 211, 218),
            font=label_font,
        )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=True)


def main():
    parser = argparse.ArgumentParser(
        description="Create CC5 character-integration contact sheets."
    )
    parser.add_argument("--summary", default=DEFAULT_SUMMARY)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    summary_path = os.path.realpath(os.path.abspath(args.summary))
    output_dir = os.path.realpath(os.path.abspath(args.output_dir))
    summary = read_json(summary_path)
    records = []
    for case in summary.get("cases") or []:
        if case.get("structural_pass") is not True:
            continue
        output_path = os.path.join(
            output_dir, case["preset_id"] + ".png"
        )
        render_case(case, output_path)
        records.append(
            {
                "contact_sheet": output_path,
                "preset_id": case["preset_id"],
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
        "Created {} integration contact sheets -> {}".format(
            len(records),
            output_dir,
        )
    )


if __name__ == "__main__":
    main()
