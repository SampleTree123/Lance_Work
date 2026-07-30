"""Create paged overview sheets from scalp-hair dynamic case sheets."""

import argparse
import json
import math
import os

from PIL import Image, ImageDraw, ImageFont, ImageOps


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


def preview(path, size):
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    return ImageOps.fit(
        image,
        size,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.43),
    )


def render_page(cases, page_number, page_count, output_path):
    columns = 4
    rows = 5
    cell_width = 400
    cell_height = 250
    header_height = 58
    image_height = 190
    sheet = Image.new(
        "RGB",
        (
            columns * cell_width,
            header_height + rows * cell_height,
        ),
        (22, 25, 30),
    )
    draw = ImageDraw.Draw(sheet)
    title_font = font(22, bold=True)
    label_font = font(14, bold=True)
    detail_font = font(12)
    draw.text(
        (14, 13),
        "CC5 scalp-hair dynamic overview | page {}/{}".format(
            page_number,
            page_count,
        ),
        fill=(240, 242, 245),
        font=title_font,
    )
    for index, case in enumerate(cases):
        column = index % columns
        row = index // columns
        x = column * cell_width
        y = header_height + row * cell_height
        front = preview(
            case["artifact_paths"]["face_front"],
            (cell_width // 2, image_height),
        )
        rear = preview(
            case["artifact_paths"]["hair_rear"],
            (cell_width // 2, image_height),
        )
        sheet.paste(front, (x, y))
        sheet.paste(rear, (x + cell_width // 2, y))
        draw.text(
            (x + 8, y + image_height + 7),
            "{} | {}".format(
                case["preset_id"],
                case["display_name"],
            ),
            fill=(232, 235, 239),
            font=label_font,
        )
        draw.text(
            (x + 8, y + image_height + 29),
            "{} | score {:.2f} | {}".format(
                case["automation_status"],
                case["female_presentation_score"],
                case["silhouette_family"],
            ),
            fill=(160, 169, 180),
            font=detail_font,
        )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=True)


def main():
    parser = argparse.ArgumentParser(
        description="Create paged CC5 scalp-hair overview sheets."
    )
    parser.add_argument("--summary", default=DEFAULT_SUMMARY)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--case-phase",
        choices=("all", "base", "cross_presentation"),
        default="base",
    )
    args = parser.parse_args()
    summary_path = os.path.realpath(os.path.abspath(args.summary))
    output_dir = os.path.realpath(os.path.abspath(args.output_dir))
    summary = read_json(summary_path)
    cases = list(summary.get("cases") or [])
    if args.case_phase != "all":
        cases = [
            item
            for item in cases
            if item.get("case_phase") == args.case_phase
        ]
    cases.sort(key=lambda item: item["preset_id"])
    page_size = 20
    page_count = int(math.ceil(len(cases) / float(page_size)))
    pages = []
    for page_index in range(page_count):
        start = page_index * page_size
        output_path = os.path.join(
            output_dir,
            "overview_{:02d}.png".format(page_index + 1),
        )
        render_page(
            cases[start : start + page_size],
            page_index + 1,
            page_count,
            output_path,
        )
        pages.append(output_path)
    index_path = os.path.join(output_dir, "index.json")
    write_json(
        {
            "case_count": len(cases),
            "case_phase": args.case_phase,
            "page_count": len(pages),
            "pages": pages,
            "schema_version": 1,
            "source_summary": summary_path,
        },
        index_path,
    )
    print(
        "Created {} overview pages for {} cases -> {}".format(
            len(pages),
            len(cases),
            output_dir,
        )
    )


if __name__ == "__main__":
    main()
