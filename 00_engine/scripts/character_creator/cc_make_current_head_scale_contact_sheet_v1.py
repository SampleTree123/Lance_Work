"""Create a labeled contact sheet for a current-scene Head Scale sweep."""

import argparse
import json
import os

from PIL import Image, ImageDraw, ImageFont, ImageOps


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


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


def load_image(path, size):
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    return ImageOps.fit(
        image,
        size,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )


def upper_body(image, size):
    crop = (
        int(image.width * 0.20),
        int(image.height * 0.08),
        int(image.width * 0.80),
        int(image.height * 0.68),
    )
    return ImageOps.fit(
        image.crop(crop),
        size,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.42),
    )


def render(report_path, output_path):
    report = read_json(report_path)
    candidates = report.get("candidates") or []
    if not candidates:
        raise RuntimeError("Head Scale report has no candidates")
    tile_size = (420, 420)
    columns = len(candidates)
    header_height = 112
    label_height = 42
    row_label_height = 32
    footer_height = 52
    width = columns * tile_size[0]
    height = (
        header_height
        + label_height
        + tile_size[1]
        + row_label_height
        + tile_size[1]
        + footer_height
    )
    sheet = Image.new("RGB", (width, height), (22, 25, 30))
    draw = ImageDraw.Draw(sheet)
    draw.text(
        (18, 14),
        "Current character | Head Scale +30 to +60",
        fill=(241, 243, 246),
        font=font(27, bold=True),
    )
    draw.text(
        (18, 52),
        "Same character, clothing, pose, camera, and all other Morph values.",
        fill=(181, 188, 198),
        font=font(16),
    )
    draw.text(
        (18, 78),
        "Initial and restored Head Scale: {:+.0f}".format(
            float(report["initial_weight"]) * 100.0
        ),
        fill=(181, 188, 198),
        font=font(16),
    )
    top_y = header_height + label_height
    lower_label_y = top_y + tile_size[1]
    lower_y = lower_label_y + row_label_height
    for index, candidate in enumerate(candidates):
        x = index * tile_size[0]
        image = load_image(candidate["image"], tile_size)
        sheet.paste(image, (x, top_y))
        sheet.paste(upper_body(image, tile_size), (x, lower_y))
        label = "Head Scale {:+.0f}".format(float(candidate["value"]) * 100.0)
        draw.text(
            (x + 14, header_height + 10),
            label,
            fill=(236, 239, 243),
            font=font(18, bold=True),
        )
        draw.text(
            (x + 14, lower_label_y + 7),
            "Head and shoulders",
            fill=(180, 187, 197),
            font=font(14, bold=True),
        )
        if index:
            draw.line(
                (x, header_height, x, height - footer_height),
                fill=(65, 71, 80),
                width=1,
            )
    restored = "yes" if report.get("restored_exactly") else "no"
    draw.text(
        (18, height - footer_height + 15),
        "Current project restored exactly: {} | Decision status: pending".format(
            restored
        ),
        fill=(207, 212, 219),
        font=font(16, bold=True),
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=True)


def main():
    parser = argparse.ArgumentParser(
        description="Create a current-scene Head Scale contact sheet."
    )
    parser.add_argument("--report", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report_path = os.path.realpath(os.path.abspath(args.report))
    output_path = os.path.realpath(os.path.abspath(args.output))
    render(report_path, output_path)
    print("Created current Head Scale contact sheet -> {}".format(output_path))


if __name__ == "__main__":
    main()
