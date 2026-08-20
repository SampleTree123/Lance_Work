"""Create labeled detail contact sheets from a CC face material matrix."""

import argparse
import json
import os
import textwrap

from PIL import Image, ImageDraw, ImageFont, ImageOps


CROP_MODES = {
    "eye": {
        "box": (0.20, 0.22, 0.80, 0.53),
        "tile": (440, 250),
        "title": "Eye, tearline, and eyelid detail",
    },
    "skin": {
        "box": (0.22, 0.18, 0.78, 0.80),
        "tile": (360, 400),
        "title": "Forehead, cheek, nose, and mouth skin response",
    },
    "full": {
        "box": (0.0, 0.0, 1.0, 1.0),
        "tile": (320, 320),
        "title": "Full face",
    },
}


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


def fitted_font(draw, text, max_width, start_size, minimum_size, bold=False):
    for size in range(start_size, minimum_size - 1, -1):
        candidate = font(size, bold=bold)
        bounds = draw.textbbox((0, 0), text, font=candidate)
        if bounds[2] - bounds[0] <= max_width:
            return candidate
    return font(minimum_size, bold=bold)


def crop_image(path, crop_box, tile_size):
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    left, top, right, bottom = crop_box
    crop = image.crop(
        (
            int(image.width * left),
            int(image.height * top),
            int(image.width * right),
            int(image.height * bottom),
        )
    )
    return ImageOps.fit(
        crop,
        tile_size,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )


def draw_wrapped(draw, text, xy, width, line_height, fill, text_font):
    lines = textwrap.wrap(str(text), width=width) or [str(text)]
    x, y = xy
    for line in lines[:2]:
        draw.text((x, y), line, fill=fill, font=text_font)
        y += line_height


def render(report_path, output_path, crop_mode):
    report = read_json(report_path)
    profiles = report.get("profiles") or []
    lights = report.get("lights") or []
    if not profiles or not lights:
        raise RuntimeError("Material matrix report has no profiles or lights")
    mode = CROP_MODES[crop_mode]
    tile_width, tile_height = mode["tile"]
    row_label_width = 155
    header_height = 98
    column_label_height = 82
    footer_height = 48
    width = row_label_width + len(profiles) * tile_width
    height = (
        header_height
        + column_label_height
        + len(lights) * tile_height
        + footer_height
    )
    sheet = Image.new("RGB", (width, height), (22, 25, 30))
    draw = ImageDraw.Draw(sheet)
    title = "CC face material matrix | {}".format(mode["title"])
    draw.text(
        (18, 14),
        title,
        fill=(241, 243, 246),
        font=fitted_font(
            draw,
            title,
            max_width=width - 36,
            start_size=26,
            minimum_size=16,
            bold=True,
        ),
    )
    draw.text(
        (18, 54),
        "Same subject geometry, camera, pose, textures, and render resolution.",
        fill=(181, 188, 198),
        font=font(16),
    )
    profile_x = row_label_width
    for index, profile in enumerate(profiles):
        x = profile_x + index * tile_width
        draw.text(
            (x + 10, header_height + 8),
            profile["id"],
            fill=(236, 239, 243),
            font=font(16, bold=True),
        )
        draw_wrapped(
            draw,
            profile.get("label") or profile["id"],
            (x + 10, header_height + 34),
            width=46 if crop_mode == "eye" else 37,
            line_height=18,
            fill=(177, 184, 194),
            text_font=font(13),
        )
        if index:
            draw.line(
                (x, header_height, x, height - footer_height),
                fill=(62, 68, 77),
                width=1,
            )
    light_lookup = {item["id"]: item for item in lights}
    row_y = header_height + column_label_height
    for row_index, light in enumerate(lights):
        y = row_y + row_index * tile_height
        draw.text(
            (14, y + 16),
            light["id"],
            fill=(220, 224, 230),
            font=font(15, bold=True),
        )
        draw.text(
            (14, y + 42),
            "light control",
            fill=(151, 160, 171),
            font=font(12),
        )
        for column_index, profile in enumerate(profiles):
            captures = {
                item["light_id"]: item
                for item in (profile.get("captures") or [])
            }
            capture = captures.get(light["id"])
            if capture is None:
                raise RuntimeError(
                    "Missing capture for {} / {}".format(
                        profile["id"], light["id"]
                    )
                )
            image = crop_image(capture["path"], mode["box"], mode["tile"])
            x = profile_x + column_index * tile_width
            sheet.paste(image, (x, y))
        if row_index:
            draw.line(
                (0, y, width, y),
                fill=(62, 68, 77),
                width=1,
            )
    restored = report.get("restoration", {}).get("materials_restored") is True
    eye_restored = (
        report.get("restoration", {})
        .get("eye_integrity", {})
        .get("matches")
        is True
    )
    draw.text(
        (18, height - footer_height + 14),
        "Material restore: {} | Eye integrity restore: {} | Profiles: {} | Lights: {}".format(
            "pass" if restored else "fail",
            "pass" if eye_restored else "fail",
            len(profiles),
            len(light_lookup),
        ),
        fill=(205, 211, 219),
        font=font(15, bold=True),
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=True)


def main():
    parser = argparse.ArgumentParser(
        description="Create a CC face material matrix contact sheet."
    )
    parser.add_argument("--report", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--crop-mode",
        choices=sorted(CROP_MODES),
        required=True,
    )
    args = parser.parse_args()
    render(
        os.path.realpath(os.path.abspath(args.report)),
        os.path.realpath(os.path.abspath(args.output)),
        args.crop_mode,
    )
    print("Created face material contact sheet -> {}".format(args.output))


if __name__ == "__main__":
    main()
