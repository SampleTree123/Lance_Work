"""Build a compact contact sheet from the M02 Elder Morph PIE review."""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


CASES = (
    ("age_000_neutral", "Age 0 | neutral"),
    ("age_050_neutral", "Age 0.5 | neutral"),
    ("age_100_neutral", "Age 1 | neutral"),
    ("age_100_blink", "Age 1 | blink"),
    ("age_100_smile", "Age 1 | subtle smile"),
    ("age_100_jaw_open", "Age 1 | jaw curve 0.65"),
)


def font(size, bold=False):
    candidates = (
        Path(r"C:\Windows\Fonts\arialbd.ttf") if bold else Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\segoeuib.ttf") if bold else Path(r"C:\Windows\Fonts\segoeui.ttf"),
    )
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def crop_head_shoulders(source):
    width, height = source.size
    return source.crop(
        (
            int(width * 0.29),
            int(height * 0.035),
            int(width * 0.71),
            int(height * 0.88),
        )
    )


def build(review_dir, output_path):
    review_dir = Path(review_dir).resolve()
    report_path = review_dir / "pie_review.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("success") is not True or report.get("case_count") != len(CASES):
        raise RuntimeError("PIE review is incomplete or unsuccessful")

    cases_by_id = {item["id"]: item for item in report["cases"]}
    tile_width = 500
    tile_height = 610
    label_height = 54
    header_height = 92
    sheet = Image.new("RGB", (tile_width * 3, header_height + tile_height * 2), "#171a1f")
    draw = ImageDraw.Draw(sheet)
    draw.text((22, 14), "M02 Elder Morph | live PIE review", fill="#f2f4f7", font=font(28, bold=True))
    draw.text(
        (22, 53),
        "Full_Face_Elder broadcast to 11 affected modules | 20 runtime components",
        fill="#aeb7c4",
        font=font(18),
    )

    for index, (case_id, label) in enumerate(CASES):
        record = cases_by_id.get(case_id)
        if record is None:
            raise RuntimeError("Missing review case: " + case_id)
        source_path = Path(record["capture"]["path"])
        if not source_path.is_file():
            raise RuntimeError("Missing capture: " + str(source_path))
        with Image.open(source_path) as image:
            cropped = crop_head_shoulders(image.convert("RGB"))
            panel = ImageOps.contain(cropped, (tile_width - 24, tile_height - label_height - 20))

        column = index % 3
        row = index // 3
        x = column * tile_width
        y = header_height + row * tile_height
        panel_x = x + (tile_width - panel.width) // 2
        panel_y = y + label_height
        sheet.paste(panel, (panel_x, panel_y))
        draw.text((x + 16, y + 13), label, fill="#f2f4f7", font=font(21, bold=True))
        draw.rectangle((x + 5, y + 5, x + tile_width - 6, y + tile_height - 6), outline="#4a5260", width=1)

    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=True)
    return output_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output_path = build(args.review_dir, args.output)
    print(json.dumps({"output": str(output_path), "success": True}, indent=2))


if __name__ == "__main__":
    main()
