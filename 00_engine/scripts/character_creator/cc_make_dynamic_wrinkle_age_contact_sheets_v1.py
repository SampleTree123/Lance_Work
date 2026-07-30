"""Create male and female dynamic-wrinkle age contact sheets."""

import argparse
import json
import os

from PIL import Image, ImageDraw, ImageFont, ImageOps


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SUMMARY = os.path.join(
    SCRIPT_DIR, "cc_dynamic_wrinkle_age_automation_summary_v1.json"
)
POSE_LABELS = {
    "neutral_front": "Neutral",
    "blink_bilateral_front": "Blink",
    "brow_raise_front": "Brow Raise",
    "brow_down_front": "Brow Down",
    "squint_bilateral_front": "Squint",
    "smile_front": "Smile",
}


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


def face_crop(path, size):
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    width, height = image.size
    image = image.crop(
        (
            int(width * 0.08),
            int(height * 0.18),
            int(width * 0.92),
            int(height * 0.92),
        )
    )
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


def pair_cell(pair, size):
    half_width = size[0] // 2
    baseline = face_crop(
        pair["baseline_image"],
        (half_width, size[1]),
    )
    target = face_crop(
        pair["target_image"],
        (size[0] - half_width, size[1]),
    )
    cell = Image.new("RGB", size, (27, 31, 37))
    cell.paste(baseline, (0, 0))
    cell.paste(target, (half_width, 0))
    draw = ImageDraw.Draw(cell)
    small_font = font(13, bold=True)
    draw.rectangle((0, 0, 27, 20), fill=(22, 25, 30))
    draw.text((6, 2), "0", fill=(190, 198, 208), font=small_font)
    draw.rectangle(
        (half_width, 0, half_width + 27, 20),
        fill=(22, 25, 30),
    )
    draw.text(
        (half_width + 6, 2),
        "1",
        fill=(240, 242, 245),
        font=small_font,
    )
    return cell


def render_sex(sex, cases, output_path):
    if len(cases) != 3:
        raise RuntimeError(
            "{} expected three age cases, found {}".format(
                sex,
                len(cases),
            )
        )
    pose_ids = list(POSE_LABELS)
    cell_size = (280, 250)
    row_label_width = 155
    title_height = 66
    column_label_height = 42
    width = row_label_width + len(pose_ids) * cell_size[0]
    height = title_height + column_label_height + 3 * cell_size[1]
    sheet = Image.new("RGB", (width, height), (22, 25, 30))
    draw = ImageDraw.Draw(sheet)
    title_font = font(25, bold=True)
    label_font = font(17, bold=True)
    detail_font = font(14)
    draw.text(
        (16, 14),
        "{} dynamic wrinkles | left=0 right=1".format(sex.title()),
        fill=(240, 242, 245),
        font=title_font,
    )
    for column, pose_id in enumerate(pose_ids):
        draw.text(
            (
                row_label_width + column * cell_size[0] + 8,
                title_height + 9,
            ),
            POSE_LABELS[pose_id],
            fill=(194, 200, 208),
            font=label_font,
        )
    age_order = {"young": 0, "middle": 1, "older": 2}
    y = title_height + column_label_height
    for case in sorted(cases, key=lambda item: age_order[item["age_label"]]):
        draw.text(
            (14, y + 86),
            case["age_label"].title(),
            fill=(235, 238, 242),
            font=label_font,
        )
        draw.text(
            (14, y + 113),
            "Age morph {:.1f}".format(
                float((case.get("age_morph") or {}).get("actual", 0.0))
            ),
            fill=(153, 162, 174),
            font=detail_font,
        )
        pairs = {
            item["pose_id"]: item for item in case["pairs"]
        }
        for column, pose_id in enumerate(pose_ids):
            cell = pair_cell(pairs[pose_id], cell_size)
            x = row_label_width + column * cell_size[0]
            sheet.paste(cell, (x, y))
        y += cell_size[1]
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=True)


def main():
    parser = argparse.ArgumentParser(
        description="Create CC5 dynamic wrinkle age contact sheets."
    )
    parser.add_argument("--summary", default=DEFAULT_SUMMARY)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    summary_path = os.path.realpath(os.path.abspath(args.summary))
    output_dir = os.path.realpath(os.path.abspath(args.output_dir))
    summary = read_json(summary_path)
    by_sex = {"male": [], "female": []}
    for item in summary.get("cases") or []:
        if item.get("structural_pass") is not True:
            continue
        by_sex[item["sex"]].append(item)
    records = []
    for sex in ("male", "female"):
        output_path = os.path.join(
            output_dir,
            "dynamic_wrinkle_age_{}.png".format(sex),
        )
        render_sex(sex, by_sex[sex], output_path)
        records.append(
            {
                "case_count": len(by_sex[sex]),
                "contact_sheet": output_path,
                "sex": sex,
                "visual_review_status": "pending",
            }
        )
    write_json(
        {
            "schema_version": 1,
            "sexes": records,
            "source_summary": summary_path,
        },
        os.path.join(output_dir, "index.json"),
    )
    print(
        "Created {} dynamic wrinkle sheets -> {}".format(
            len(records),
            output_dir,
        )
    )


if __name__ == "__main__":
    main()
