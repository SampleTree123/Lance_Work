"""Arrange BodyFit proportion smoke renders for human review."""

import argparse
import json
import os
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


VIEW_FILES = (
    ("full_body", "reconstructed_preview"),
    ("front", "face_front_preview"),
    ("three_quarter", "face_three_quarter_preview"),
    ("profile", "face_profile_preview"),
)
BACKGROUND = (22, 24, 28)
PANEL = (35, 38, 44)
TEXT = (242, 244, 248)
MUTED = (174, 180, 190)
ACCENT = (95, 190, 155)


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(data, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(str(path) + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True, ensure_ascii=True)
        handle.write("\n")
    os.replace(str(temporary), str(path))


def font(size, bold=False):
    names = (
        "arialbd.ttf" if bold else "arial.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    )
    for name in names:
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def fit_image(path, size):
    with Image.open(path) as source:
        image = source.convert("RGB")
    return ImageOps.contain(image, size, Image.Resampling.LANCZOS)


def paste_center(canvas, image, box):
    x0, y0, x1, y1 = box
    x = x0 + (x1 - x0 - image.width) // 2
    y = y0 + (y1 - y0 - image.height) // 2
    canvas.paste(image, (x, y))


def render_bodyfit_sheet(bodyfit_id, cases, destination):
    if len(cases) != 2:
        raise RuntimeError("{} requires exactly two cases".format(bodyfit_id))
    cell = 420
    gutter = 18
    left_label = 145
    header = 158
    footer = 24
    width = left_label + cell * 2 + gutter * 3
    height = header + (cell + gutter) * len(VIEW_FILES) + footer
    canvas = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    title_font = font(28, bold=True)
    heading_font = font(18, bold=True)
    label_font = font(17, bold=True)
    small_font = font(15)
    adjustment = cases[0]["bodyfit_proportion_adjustment"]
    targets = dict(
        (item["role"], float(item["target"]))
        for item in adjustment["applications"]
    )
    draw.text((gutter, 15), bodyfit_id, font=title_font, fill=TEXT)
    draw.text(
        (gutter, 55),
        "Head Scale {:+.0f} | Neck Height {:+.0f}".format(
            targets["head_scale"] * 100.0,
            targets["neck_height"] * 100.0,
        ),
        font=heading_font,
        fill=ACCENT,
    )
    for column, case in enumerate(cases):
        x = left_label + gutter + column * (cell + gutter)
        seed = (
            (case.get("face_context") or {}).get("primary_seed_id")
            or case.get("face_recipe_id")
        )
        draw.text(
            (x, 88),
            seed,
            font=heading_font,
            fill=TEXT,
        )
        draw.text(
            (x, 116),
            case["preset_id"],
            font=small_font,
            fill=MUTED,
        )
    for row, (view_id, artifact_key) in enumerate(VIEW_FILES):
        y = header + row * (cell + gutter)
        draw.text(
            (gutter, y + cell // 2 - 10),
            view_id.replace("_", " ").title(),
            font=label_font,
            fill=MUTED,
        )
        for column, case in enumerate(cases):
            x = left_label + gutter + column * (cell + gutter)
            draw.rounded_rectangle(
                (x, y, x + cell, y + cell),
                radius=6,
                fill=PANEL,
            )
            source = Path(case["artifacts"][artifact_key])
            if not source.is_file():
                raise RuntimeError("Missing review image: {}".format(source))
            image = fit_image(source, (cell - 12, cell - 12))
            paste_center(
                canvas,
                image,
                (x + 6, y + 6, x + cell - 6, y + cell - 6),
            )
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, optimize=True)


def build_review(summary_path, output_dir):
    summary_path = Path(summary_path).resolve()
    output_dir = Path(output_dir).resolve()
    summary = read_json(summary_path)
    if summary.get("success") is not True:
        raise RuntimeError("Smoke validation did not succeed")
    if (summary.get("scene_restoration") or {}).get(
        "restored_exactly"
    ) is not True:
        raise RuntimeError("CC scene was not restored exactly")
    grouped = {}
    for case in summary.get("results") or []:
        if case.get("success") is not True:
            raise RuntimeError("Failed case: {}".format(case.get("preset_id")))
        report = case.get("bodyfit_proportion_adjustment") or {}
        if not all(
            report.get(field) is True
            for field in (
                "canonical_order_verified",
                "eye_structure_preserved",
                "protected_morphs_unchanged",
                "targets_match",
            )
        ):
            raise RuntimeError(
                "Invalid proportion report: {}".format(case["preset_id"])
            )
        grouped.setdefault(report["bodyfit_id"], []).append(case)
    if sorted(len(cases) for cases in grouped.values()) != [2, 2, 2]:
        raise RuntimeError("Expected three BodyFits with two faces each")

    index = {
        "schema_version": 1,
        "source_summary": str(summary_path),
        "scene_restored_exactly": True,
        "bodyfits": [],
    }
    sheet_paths = []
    for bodyfit_id in sorted(grouped):
        cases = sorted(grouped[bodyfit_id], key=lambda item: item["preset_id"])
        bodyfit_dir = output_dir / bodyfit_id
        bodyfit_dir.mkdir(parents=True, exist_ok=True)
        copied = []
        for case_index, case in enumerate(cases, start=1):
            for view_index, (view_id, artifact_key) in enumerate(
                VIEW_FILES,
                start=1,
            ):
                source = Path(case["artifacts"][artifact_key])
                destination = bodyfit_dir / (
                    "{:02d}_face{}_{}_{}.png".format(
                        (case_index - 1) * len(VIEW_FILES) + view_index,
                        case_index,
                        case["preset_id"].split("_")[-1].lower(),
                        view_id,
                    )
                )
                shutil.copy2(source, destination)
                copied.append(destination.name)
        sheet_path = bodyfit_dir / "overview.png"
        render_bodyfit_sheet(bodyfit_id, cases, sheet_path)
        sheet_paths.append(sheet_path)
        applications = cases[0]["bodyfit_proportion_adjustment"][
            "applications"
        ]
        index["bodyfits"].append(
            {
                "bodyfit_id": bodyfit_id,
                "cases": [item["preset_id"] for item in cases],
                "copied_images": copied,
                "head_scale": applications[0]["actual"],
                "neck_height": applications[1]["actual"],
                "overview": sheet_path.relative_to(output_dir).as_posix(),
            }
        )

    master_width = 0
    for path in sheet_paths:
        with Image.open(path) as image:
            master_width = max(master_width, image.width)
    master_images = []
    for path in sheet_paths:
        with Image.open(path) as image:
            copy_image = image.convert("RGB")
        copy_image.thumbnail(
            (master_width, 1040),
            Image.Resampling.LANCZOS,
        )
        master_images.append(copy_image)
    gap = 24
    master = Image.new(
        "RGB",
        (
            master_width,
            sum(image.height for image in master_images)
            + gap * (len(master_images) - 1),
        ),
        BACKGROUND,
    )
    y = 0
    for image in master_images:
        paste_center(master, image, (0, y, master_width, y + image.height))
        y += image.height + gap
    master_path = output_dir / "overview_all_bodyfits.png"
    master.save(master_path, optimize=True)
    index["overview_all_bodyfits"] = master_path.name
    index_path = output_dir / "index.json"
    write_json(index, index_path)
    return index_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    index_path = build_review(args.summary, args.output_dir)
    print("BodyFit proportion review: {}".format(index_path.parent))
    print("Review index: {}".format(index_path))


if __name__ == "__main__":
    main()
