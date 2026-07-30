"""Build full-face and eye-crop contact sheets for a direct eyelash matrix."""

import argparse
import json
import os

from PIL import Image, ImageDraw, ImageFont, ImageOps


POSES = (
    ("face_front_preview", "Neutral"),
    ("eyelash_blink_preview", "Blink"),
    ("eyelash_asymmetric_preview", "Left Blink"),
    ("eyelash_wide_preview", "Wide"),
)


class ContactSheetError(RuntimeError):
    pass


def read_json(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def font(size, bold=False):
    candidates = (
        r"C:\Windows\Fonts\segoeuib.ttf"
        if bold
        else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf"
        if bold
        else r"C:\Windows\Fonts\arial.ttf",
    )
    for path in candidates:
        if os.path.isfile(path):
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def fitted(image, size):
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, (27, 31, 37))
    x = (size[0] - image.width) // 2
    y = (size[1] - image.height) // 2
    canvas.paste(image, (x, y))
    return canvas


def eye_crop(image):
    image = ImageOps.exif_transpose(image).convert("RGB")
    width, height = image.size
    return image.crop(
        (
            0,
            int(height * 0.38),
            int(width * 0.64),
            int(height * 0.72),
        )
    )


def load_cases(root):
    summary_path = os.path.join(root, "validation_result.json")
    if not os.path.isfile(summary_path):
        raise ContactSheetError(
            "Validation summary is missing: {}".format(summary_path)
        )
    summary = read_json(summary_path)
    if summary.get("success") is not True:
        raise ContactSheetError("Eyelash validation did not succeed")
    sex_results = summary.get("sex_results") or []
    if len(sex_results) != 1:
        raise ContactSheetError(
            "Expected one sex result, found {}".format(len(sex_results))
        )
    sex_result = sex_results[0]
    cases = sex_result.get("cases") or []
    if not cases:
        raise ContactSheetError("Validation contains no eyelash cases")
    for case in cases:
        if (
            case.get("eye_geometry_preserved") is not True
            or case.get("eyeball_move_preserved") is not True
        ):
            raise ContactSheetError(
                "Eye invariants failed for {}".format(case.get("case_id"))
            )
        artifacts = (case.get("render") or {}).get("artifacts") or {}
        for artifact_key, unused_label in POSES:
            path = artifacts.get(artifact_key)
            if not path or not os.path.isfile(path):
                raise ContactSheetError(
                    "Missing {} for {}".format(
                        artifact_key, case.get("case_id")
                    )
                )
    return sex_result.get("sex"), cases


def build_sheet(sex, cases, output_path, crop_eyes):
    columns = len(POSES)
    image_size = (340, 210) if crop_eyes else (225, 300)
    tile_width = image_size[0] + 18
    tile_height = image_size[1] + 12
    row_label_height = 42
    title_height = 82
    margin = 24
    width = margin * 2 + columns * tile_width
    height = (
        title_height
        + margin
        + len(cases) * (row_label_height + tile_height)
    )
    sheet = Image.new("RGB", (width, height), (224, 228, 233))
    draw = ImageDraw.Draw(sheet)
    title_font = font(30, bold=True)
    heading_font = font(18, bold=True)
    label_font = font(18, bold=True)
    detail_font = font(14)
    view_name = "Eye Crops" if crop_eyes else "Full Face"
    draw.text(
        (margin, 16),
        "CC5 Eyelash Matrix - {} - {}".format(sex.title(), view_name),
        fill=(20, 24, 30),
        font=title_font,
    )
    for column, unused_pose in enumerate(POSES):
        draw.text(
            (margin + column * tile_width + 8, 56),
            unused_pose[1],
            fill=(50, 57, 67),
            font=heading_font,
        )

    y = title_height + margin
    for case in cases:
        asset = case.get("asset") or {}
        draw.text(
            (margin, y),
            asset.get("display_name") or case.get("case_id"),
            fill=(20, 24, 30),
            font=label_font,
        )
        draw.text(
            (margin + 260, y + 3),
            asset.get("asset_id") or "",
            fill=(83, 90, 101),
            font=detail_font,
        )
        y += row_label_height
        artifacts = (case.get("render") or {}).get("artifacts") or {}
        for column, (artifact_key, unused_label) in enumerate(POSES):
            path = artifacts[artifact_key]
            with Image.open(path) as source:
                image = eye_crop(source) if crop_eyes else source.copy()
                preview = fitted(image, image_size)
            x = margin + column * tile_width
            sheet.paste(preview, (x, y))
            draw.rectangle(
                (x, y, x + image_size[0] - 1, y + image_size[1] - 1),
                outline=(134, 141, 151),
                width=1,
            )
        y += tile_height

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sheet.save(output_path, "JPEG", quality=95, subsampling=0)


def build(root):
    root = os.path.realpath(os.path.abspath(root))
    sex, cases = load_cases(root)
    review_dir = os.path.join(root, "review")
    full_path = os.path.join(
        review_dir, "eyelash_contact_sheet_{}_full.jpg".format(sex)
    )
    crop_path = os.path.join(
        review_dir, "eyelash_contact_sheet_{}_eyes.jpg".format(sex)
    )
    build_sheet(sex, cases, full_path, crop_eyes=False)
    build_sheet(sex, cases, crop_path, crop_eyes=True)
    return {
        "success": True,
        "sex": sex,
        "case_count": len(cases),
        "full_sheet": full_path,
        "eye_sheet": crop_path,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            build(args.root),
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
