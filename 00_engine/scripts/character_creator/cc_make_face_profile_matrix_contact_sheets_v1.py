"""Create per-seed contact sheets for the CC5 face profile matrix."""

import argparse
import json
import os

from PIL import Image, ImageDraw, ImageFont, ImageOps


VIEWS = (
    ("face_front_preview", "Front"),
    ("face_three_quarter_preview", "3/4"),
    ("face_profile_preview", "Profile"),
    ("face_blink_bilateral_preview", "Blink"),
    ("face_blink_left_preview", "Blink L"),
    ("face_blink_right_preview", "Blink R"),
    ("face_look_up_preview", "Look Up"),
    ("face_look_down_preview", "Look Down"),
    ("face_look_left_preview", "Look L"),
    ("face_look_right_preview", "Look R"),
    ("face_squint_preview", "Squint"),
    ("face_widen_preview", "Widen"),
    ("face_brow_raise_preview", "Brow Up"),
    ("face_smile_preview", "Smile"),
    ("face_jaw_open_preview", "Jaw"),
    ("face_jaw_open_three_quarter_preview", "Jaw 3/4"),
)


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True, ensure_ascii=True)
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
    canvas.paste(
        image,
        (
            (size[0] - image.width) // 2,
            (size[1] - image.height) // 2,
        ),
    )
    return canvas


def validation_results(result_data):
    validation = (result_data.get("result") or {}).get("validation")
    if validation is None:
        validation = result_data.get("validation")
    if validation is None:
        raise RuntimeError("Result JSON has no validation object.")
    return validation.get("results") or []


def render_case(case, output_path):
    columns = 4
    rows = 4
    image_size = (260, 260)
    label_height = 30
    header_height = 68
    width = columns * image_size[0]
    height = header_height + rows * (image_size[1] + label_height)
    sheet = Image.new("RGB", (width, height), (22, 25, 30))
    draw = ImageDraw.Draw(sheet)
    draw.text(
        (16, 11),
        "{} | {}".format(case["preset_id"], case.get("sex") or "unknown"),
        fill=(240, 242, 245),
        font=font(23, bold=True),
    )
    draw.text(
        (16, 41),
        "CC5 face profile dynamic validation",
        fill=(171, 178, 188),
        font=font(14),
    )
    artifacts = case.get("artifacts") or {}
    for index, (artifact_key, label) in enumerate(VIEWS):
        path = artifacts.get(artifact_key)
        if not path or not os.path.isfile(path):
            raise RuntimeError(
                "{} is missing {}".format(case["preset_id"], artifact_key)
            )
        column = index % columns
        row = index // columns
        x = column * image_size[0]
        y = header_height + row * (image_size[1] + label_height)
        sheet.paste(fitted_image(path, image_size), (x, y))
        draw.text(
            (x + 9, y + image_size[1] + 5),
            label,
            fill=(207, 211, 218),
            font=font(15, bold=True),
        )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=True)


def create_contact_sheets(
    result_paths,
    output_dir,
    visual_review_status="pending",
):
    records = []
    seen = set()
    for result_path in result_paths:
        for case in validation_results(read_json(result_path)):
            preset_id = case.get("preset_id")
            if not preset_id or preset_id in seen or case.get("success") is not True:
                continue
            seen.add(preset_id)
            output_path = os.path.join(output_dir, preset_id + ".png")
            render_case(case, output_path)
            records.append(
                {
                    "contact_sheet": output_path,
                    "preset_id": preset_id,
                    "source_result": result_path,
                    "visual_review_status": visual_review_status,
                }
            )
    records.sort(key=lambda item: item["preset_id"])
    write_json(
        {
            "case_count": len(records),
            "cases": records,
            "schema_version": 1,
        },
        os.path.join(output_dir, "index.json"),
    )
    return records


def main():
    parser = argparse.ArgumentParser(
        description="Create CC5 face profile matrix contact sheets."
    )
    parser.add_argument("--result", action="append", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--visual-review-status",
        choices=("failed", "passed", "pending"),
        default="pending",
    )
    args = parser.parse_args()
    result_paths = [
        os.path.realpath(os.path.abspath(path)) for path in args.result
    ]
    output_dir = os.path.realpath(os.path.abspath(args.output_dir))
    records = create_contact_sheets(
        result_paths,
        output_dir,
        args.visual_review_status,
    )
    print(
        "Created {} face profile contact sheets -> {}".format(
            len(records),
            output_dir,
        )
    )


if __name__ == "__main__":
    main()
