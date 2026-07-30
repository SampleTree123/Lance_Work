"""Build paged six-view contact sheets for the scalp-hair matrix."""

import argparse
import datetime
import json
import math
import os

from PIL import Image, ImageDraw, ImageFont, ImageOps


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BATCH = os.path.join(
    SCRIPT_DIR, "cc_scalp_hair_compatibility_batch_v1.json"
)
VIEW_SPECS = (
    ("Full", "reconstructed_preview"),
    ("Front", "face_front_preview"),
    ("3/4", "face_three_quarter_preview"),
    ("Profile", "face_profile_preview"),
    ("Rear 3/4", "hair_rear_three_quarter_preview"),
    ("Rear", "hair_rear_preview"),
)


class ContactSheetError(RuntimeError):
    pass


def now():
    return datetime.datetime.now().astimezone().replace(
        microsecond=0
    ).isoformat()


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


def indexed(items, key, label):
    result = {}
    for item in items:
        value = item.get(key)
        if not isinstance(value, str) or not value or value in result:
            raise ContactSheetError(
                "{} IDs are invalid or duplicated".format(label)
            )
        result[value] = item
    return result


def font(size, bold=False):
    candidates = (
        (
            r"C:\Windows\Fonts\arialbd.ttf"
            if bold
            else r"C:\Windows\Fonts\arial.ttf"
        ),
        (
            r"C:\Windows\Fonts\segoeuib.ttf"
            if bold
            else r"C:\Windows\Fonts\segoeui.ttf"
        ),
    )
    for path in candidates:
        if os.path.isfile(path):
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def fit_contained(path, size):
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        image.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, (28, 31, 36))
    x = (size[0] - image.width) // 2
    y = (size[1] - image.height) // 2
    canvas.paste(image, (x, y))
    return canvas


def chunked(items, size):
    for index in range(0, len(items), size):
        yield items[index : index + size]


def draw_tile(sheet, origin, record, fonts):
    x, y = origin
    tile_width = 984
    tile_height = 790
    sheet_draw = ImageDraw.Draw(sheet)
    sheet_draw.rounded_rectangle(
        (x, y, x + tile_width - 12, y + tile_height - 12),
        radius=8,
        fill=(244, 245, 247),
        outline=(190, 195, 203),
        width=2,
    )
    pack = record["preset"]["hair_builder_pack"]
    prior = record["preset"]["presentation_prior"]
    asset = record["preset"]["appearance_recipe"]["assets"][0]
    title = "{0}-{1:02d}  {2}".format(
        pack["pack_code"],
        int(pack["asset_index"]),
        asset["display_name"],
    )
    sheet_draw.text(
        (x + 18, y + 14),
        title,
        fill=(20, 24, 30),
        font=fonts["title"],
    )
    prior_text = "prior: {0} / female score {1:.2f}".format(
        prior["label"],
        float(prior["female_presentation_score"]),
    )
    sheet_draw.text(
        (x + 20, y + 48),
        prior_text,
        fill=(70, 77, 87),
        font=fonts["detail"],
    )
    steps = (
        (record["result"].get("appearance_application") or {}).get("steps")
        or []
    )
    added_objects = (
        steps[0].get("added_objects") or []
        if steps
        else []
    )
    hair_parts = sum(
        item.get("collection") == "GetHairs" for item in added_objects
    )
    accessories = sum(
        item.get("collection") == "GetAccessories"
        for item in added_objects
    )
    structure_text = "scene additions: {} hair part(s), {} accessory(s)".format(
        hair_parts,
        accessories,
    )
    sheet_draw.text(
        (x + 20, y + 70),
        structure_text,
        fill=(70, 77, 87),
        font=fonts["detail"],
    )

    image_width = 294
    image_height = 286
    image_gap_x = 22
    image_gap_y = 52
    image_start_y = y + 104
    artifacts = record["result"].get("artifacts") or {}
    for index, (label, artifact_key) in enumerate(VIEW_SPECS):
        row = index // 3
        column = index % 3
        image_x = x + 20 + column * (image_width + image_gap_x)
        image_y = image_start_y + row * (image_height + image_gap_y)
        path = artifacts.get(artifact_key)
        if not isinstance(path, str) or not os.path.isfile(path):
            raise ContactSheetError(
                "Missing {} for {}".format(
                    artifact_key,
                    record["preset"]["preset_id"],
                )
            )
        preview = fit_contained(path, (image_width, image_height))
        sheet.paste(preview, (image_x, image_y))
        sheet_draw.rectangle(
            (
                image_x,
                image_y,
                image_x + image_width,
                image_y + image_height,
            ),
            outline=(130, 136, 145),
            width=1,
        )
        sheet_draw.text(
            (image_x + 4, image_y + image_height + 6),
            label,
            fill=(48, 54, 63),
            font=fonts["view"],
        )


def build_sheet(records, title, output_path):
    columns = 2
    rows = int(math.ceil(len(records) / float(columns)))
    margin = 28
    title_height = 82
    tile_width = 984
    tile_height = 790
    sheet = Image.new(
        "RGB",
        (
            margin * 2 + columns * tile_width,
            title_height + margin + rows * tile_height,
        ),
        (220, 224, 230),
    )
    draw = ImageDraw.Draw(sheet)
    fonts = {
        "page": font(32, bold=True),
        "title": font(23, bold=True),
        "detail": font(17),
        "view": font(16, bold=True),
    }
    draw.text(
        (margin, 20),
        title,
        fill=(18, 22, 28),
        font=fonts["page"],
    )
    for index, record in enumerate(records):
        row = index // columns
        column = index % columns
        draw_tile(
            sheet,
            (
                margin + column * tile_width,
                title_height + row * tile_height,
            ),
            record,
            fonts,
        )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sheet.save(output_path, "JPEG", quality=94, subsampling=0, optimize=True)


def build(root, batch_path, page_size):
    root = os.path.realpath(os.path.abspath(root))
    batch_path = os.path.realpath(os.path.abspath(batch_path))
    result_path = os.path.join(root, "validation_result.json")
    for path in (batch_path, result_path):
        if not os.path.isfile(path):
            raise ContactSheetError("Input is missing: {}".format(path))
    if page_size < 1:
        raise ContactSheetError("Page size must be positive")

    batch = read_json(batch_path)
    validation = read_json(result_path)
    presets = indexed(batch.get("presets") or [], "preset_id", "Batch preset")
    results = indexed(
        validation.get("results") or [],
        "preset_id",
        "Validation result",
    )
    if len(results) != 120:
        raise ContactSheetError(
            "Expected the complete 120-preset matrix; found {}".format(
                len(results)
            )
        )

    records = []
    for preset_id, result in results.items():
        preset = presets.get(preset_id)
        if preset is None:
            raise ContactSheetError(
                "Validation preset is absent from batch: {}".format(preset_id)
            )
        if result.get("success") is not True:
            raise ContactSheetError(
                "Validation failed: {}".format(preset_id)
            )
        records.append({"preset": preset, "result": result})

    review_dir = os.path.join(root, "review", "scalp_hair")
    sheets = []
    pack_ids = sorted(
        {
            item["preset"]["hair_builder_pack"]["pack_id"]
            for item in records
        }
    )
    for pack_id in pack_ids:
        for sex in ("male", "female"):
            subset = [
                item
                for item in records
                if item["preset"]["hair_builder_pack"]["pack_id"] == pack_id
                and item["preset"]["sex"] == sex
            ]
            subset.sort(
                key=lambda item: int(
                    item["preset"]["hair_builder_pack"]["asset_index"]
                )
            )
            if len(subset) != 20:
                raise ContactSheetError(
                    "{} / {} expected 20 results; found {}".format(
                        pack_id,
                        sex,
                        len(subset),
                    )
                )
            pack_code = subset[0]["preset"]["hair_builder_pack"]["pack_code"]
            for page_index, page in enumerate(
                chunked(subset, page_size),
                start=1,
            ):
                filename = "{}_{}_page_{:02d}.jpg".format(
                    pack_code.lower(),
                    sex,
                    page_index,
                )
                output_path = os.path.join(review_dir, filename)
                title = "{} / {} / page {}".format(
                    pack_code,
                    sex.title(),
                    page_index,
                )
                build_sheet(page, title, output_path)
                sheets.append(
                    {
                        "pack_id": pack_id,
                        "pack_code": pack_code,
                        "sex": sex,
                        "page": page_index,
                        "asset_count": len(page),
                        "path": output_path,
                    }
                )

    manifest = {
        "schema_version": 1,
        "generated_at": now(),
        "source_batch": batch_path,
        "source_validation": result_path,
        "matrix_count": len(results),
        "view_ids": [item[1] for item in VIEW_SPECS],
        "page_size": page_size,
        "sheets": sheets,
    }
    manifest_path = os.path.join(
        review_dir,
        "scalp_hair_contact_sheets.json",
    )
    write_json(manifest, manifest_path)
    return {
        "success": True,
        "review_directory": review_dir,
        "manifest": manifest_path,
        "sheet_count": len(sheets),
        "matrix_count": len(results),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        required=True,
        help="Merged scalp-hair validation artifact root",
    )
    parser.add_argument("--batch", default=DEFAULT_BATCH)
    parser.add_argument("--page-size", type=int, default=10)
    args = parser.parse_args()
    print(
        json.dumps(
            build(args.root, args.batch, args.page_size),
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
