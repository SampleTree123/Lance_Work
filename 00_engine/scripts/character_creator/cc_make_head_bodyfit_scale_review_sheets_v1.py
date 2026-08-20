"""Build human-review sheets for a completed CC5 head scale matrix."""

import argparse
import html
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


BACKGROUND = (22, 25, 30)
PANEL = (31, 35, 41)
TEXT = (240, 242, 245)
MUTED = (177, 184, 194)
GRID = (65, 71, 80)
REFERENCE = (218, 174, 72)


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(data, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True, ensure_ascii=True)
        handle.write("\n")
    os.replace(str(temporary), str(path))


def font(size, bold=False):
    candidates = (
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
    )
    for path in candidates:
        if os.path.isfile(path):
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def load_rgb(path):
    with Image.open(path) as source:
        return ImageOps.exif_transpose(source).convert("RGB")


def contain(image, size):
    canvas = Image.new("RGB", size, PANEL)
    fitted = ImageOps.contain(image, size, method=Image.Resampling.LANCZOS)
    x = (size[0] - fitted.width) // 2
    y = (size[1] - fitted.height) // 2
    canvas.paste(fitted, (x, y))
    return canvas


def fill(image, size, centering=(0.5, 0.5)):
    return ImageOps.fit(
        image,
        size,
        method=Image.Resampling.LANCZOS,
        centering=centering,
    )


def head_shoulders_crop(image):
    width, height = image.size
    box = (
        int(round(width * 0.22)),
        int(round(height * 0.01)),
        int(round(width * 0.78)),
        int(round(height * 0.57)),
    )
    return image.crop(box)


def slider_label(value):
    slider_value = int(round(float(value) * 100.0))
    return "{:+d}".format(slider_value) if slider_value else "0"


def bodyfit_name(result):
    source_project = result.get("application", {}).get("source_project")
    if source_project:
        return Path(source_project).stem
    preset_id = result.get("preset_id", "UNKNOWN")
    return preset_id.replace("HBS_BODY_", "").replace("HBS_FACE_", "")


def case_title(case):
    role = case["face_shape_role"].replace("_", " ")
    return "{} | {} | {}".format(
        case["bodyfit_id"], case["face_recipe_id"], role
    )


def is_previous_reference(case, value):
    return (
        case["preset_id"] == "HBS_FACE_M04_AVERAGE"
        and abs(float(value) - 0.35) < 1e-6
    )


def collect_cases(summary_path):
    summary = read_json(summary_path)
    if summary.get("success") is not True:
        raise RuntimeError("Matrix summary is not successful: {}".format(summary_path))

    cases = []
    for result in summary.get("results", []):
        if result.get("success") is not True:
            raise RuntimeError("Failed matrix case: {}".format(result.get("preset_id")))
        review = result.get("head_scale_review") or {}
        candidates = []
        for candidate in review.get("candidates", []):
            image_path = os.path.realpath(os.path.abspath(candidate["image"]))
            if not os.path.isfile(image_path):
                raise RuntimeError("Missing review image: {}".format(image_path))
            candidates.append(
                {
                    "actual": candidate.get("application", {}).get("actual"),
                    "image": image_path,
                    "value": float(candidate["value"]),
                }
            )
        candidates.sort(key=lambda item: item["value"])
        if len(candidates) != 10:
            raise RuntimeError(
                "Expected 10 candidates for {}, got {}.".format(
                    result.get("preset_id"), len(candidates)
                )
            )
        cases.append(
            {
                "bodyfit_id": bodyfit_name(result),
                "candidates": candidates,
                "face_recipe_id": result.get("face_recipe_id", "UNKNOWN"),
                "face_shape_role": review.get("face_shape_role", "unknown"),
                "preset_id": result.get("preset_id", "UNKNOWN"),
                "restored_exactly": review.get("restored_exactly") is True,
                "review_groups": list(review.get("review_groups", [])),
                "sex": result.get("sex", "unknown"),
            }
        )
    return summary, cases


def render_detail_sheet(case, output_path):
    columns = 5
    rows = 2
    tile_width = 352
    tile_height = 526
    header_height = 86
    width = columns * tile_width
    height = header_height + rows * tile_height
    sheet = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    draw.text((18, 12), case_title(case), fill=TEXT, font=font(25, bold=True))
    draw.text(
        (18, 49),
        "Fixed camera and fixed crop. Gold border marks the previous provisional M04 choice.",
        fill=MUTED,
        font=font(15),
    )

    for index, candidate in enumerate(case["candidates"]):
        column = index % columns
        row = index // columns
        x = column * tile_width
        y = header_height + row * tile_height
        image = load_rgb(candidate["image"])
        full = contain(image, (320, 320))
        close = fill(head_shoulders_crop(image), (320, 150), centering=(0.5, 0.25))
        sheet.paste(full, (x + 16, y + 42))
        sheet.paste(close, (x + 16, y + 370))

        highlighted = is_previous_reference(case, candidate["value"])
        color = REFERENCE if highlighted else TEXT
        label = "Head Scale {}".format(slider_label(candidate["value"]))
        draw.text((x + 16, y + 10), label, fill=color, font=font(18, bold=True))
        border = REFERENCE if highlighted else GRID
        draw.rectangle(
            (x + 7, y + 3, x + tile_width - 8, y + tile_height - 7),
            outline=border,
            width=3 if highlighted else 1,
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=True)


def matrix_sort_key(case, group):
    if group == "face_variation":
        role_order = {"average": 0, "narrow_long": 1, "broad_round": 2}
        return (role_order.get(case["face_shape_role"], 99), case["preset_id"])
    bodyfit = case["bodyfit_id"].upper()
    order = {
        "F01_LEAN": 0,
        "F02_AVERAGE": 1,
        "F03_ATHLETIC": 2,
        "F04_HEAVY": 3,
        "M01_LEAN": 4,
        "M02_AVERAGE": 5,
        "M03_ATHLETIC": 6,
        "M04_HEAVY": 7,
    }
    return (order.get(bodyfit, 99), case["preset_id"])


def render_overview(cases, group, view, output_path):
    cases = sorted(cases, key=lambda item: matrix_sort_key(item, group))
    values = [candidate["value"] for candidate in cases[0]["candidates"]]
    for case in cases[1:]:
        if [candidate["value"] for candidate in case["candidates"]] != values:
            raise RuntimeError("Candidate value columns differ between matrix cases.")

    label_width = 310
    cell = 184
    header_height = 92
    row_height = 214
    width = label_width + cell * len(values)
    height = header_height + row_height * len(cases)
    sheet = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    title = "{} | {}".format(group.replace("_", " ").title(), view.replace("_", " ").title())
    draw.text((16, 14), title, fill=TEXT, font=font(25, bold=True))
    for index, value in enumerate(values):
        x = label_width + index * cell
        color = REFERENCE if abs(value - 0.35) < 1e-6 else TEXT
        draw.text(
            (x + 14, 58),
            slider_label(value),
            fill=color,
            font=font(17, bold=True),
        )

    for row, case in enumerate(cases):
        y = header_height + row * row_height
        draw.text((16, y + 22), case["bodyfit_id"], fill=TEXT, font=font(18, bold=True))
        draw.text((16, y + 52), case["face_recipe_id"], fill=MUTED, font=font(14))
        draw.text(
            (16, y + 77),
            case["face_shape_role"].replace("_", " "),
            fill=MUTED,
            font=font(14),
        )
        for column, candidate in enumerate(case["candidates"]):
            x = label_width + column * cell
            image = load_rgb(candidate["image"])
            if view == "head_shoulders":
                image = head_shoulders_crop(image)
            panel = contain(image, (176, 176))
            sheet.paste(panel, (x + 4, y + 4))
            highlighted = is_previous_reference(case, candidate["value"])
            draw.rectangle(
                (x + 2, y + 2, x + cell - 3, y + 181),
                outline=REFERENCE if highlighted else GRID,
                width=3 if highlighted else 1,
            )
        draw.line((0, y + row_height - 1, width, y + row_height - 1), fill=GRID, width=1)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=True)


def write_html(index, output_path):
    lines = [
        "<!doctype html>",
        '<html lang="en"><head><meta charset="utf-8">',
        "<title>CC5 Head Scale Review</title>",
        "<style>",
        "body{background:#16191e;color:#f0f2f5;font-family:Segoe UI,Arial,sans-serif;margin:24px}",
        "h1,h2{margin:0 0 14px}section{margin:0 0 36px}",
        "img{max-width:100%;height:auto;border:1px solid #414750;display:block;margin:10px 0 22px}",
        "a{color:#e2b85c}code{color:#cfd5dd}",
        "</style></head><body>",
        "<h1>CC5 Head Scale Review</h1>",
        "<p>Slider range: -40 to +40. Gold border: previous provisional M04 choice (+35).</p>",
    ]
    for group in ("face_variation", "bodyfit_matrix"):
        record = index["groups"][group]
        lines.append("<section><h2>{}</h2>".format(html.escape(group.replace("_", " ").title())))
        for key in ("full_body_overview", "head_shoulders_overview"):
            relative = record[key]
            lines.append('<a href="{0}"><img src="{0}" alt="{1}"></a>'.format(html.escape(relative), html.escape(key)))
        for detail in record["details"]:
            lines.append('<p><a href="{}">{}</a></p>'.format(html.escape(detail["sheet"]), html.escape(detail["title"])))
        lines.append("</section>")
    lines.append("</body></html>")
    output_path = Path(output_path)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_review(summary_path, output_dir):
    summary_path = os.path.realpath(os.path.abspath(summary_path))
    output_dir = Path(os.path.realpath(os.path.abspath(output_dir)))
    summary, cases = collect_cases(summary_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    index = {
        "case_count": len(cases),
        "groups": {},
        "matrix_restored_exactly": summary.get("scene_restoration", {}).get("restored_exactly") is True,
        "schema_version": 1,
        "source_summary": summary_path,
    }

    group_directories = {
        "face_variation": "01_face_variation",
        "bodyfit_matrix": "02_bodyfit_matrix",
    }
    for group, directory_name in group_directories.items():
        group_cases = [case for case in cases if group in case["review_groups"]]
        if not group_cases:
            raise RuntimeError("No cases found for review group {}.".format(group))
        group_dir = output_dir / directory_name
        full_path = group_dir / "overview_full_body.png"
        close_path = group_dir / "overview_head_shoulders.png"
        render_overview(group_cases, group, "full_body", full_path)
        render_overview(group_cases, group, "head_shoulders", close_path)
        details = []
        for case in sorted(group_cases, key=lambda item: matrix_sort_key(item, group)):
            detail_path = group_dir / (case["preset_id"] + "_detail.png")
            render_detail_sheet(case, detail_path)
            details.append(
                {
                    "bodyfit_id": case["bodyfit_id"],
                    "face_recipe_id": case["face_recipe_id"],
                    "face_shape_role": case["face_shape_role"],
                    "preset_id": case["preset_id"],
                    "restored_exactly": case["restored_exactly"],
                    "sheet": detail_path.relative_to(output_dir).as_posix(),
                    "title": case_title(case),
                }
            )
        index["groups"][group] = {
            "case_count": len(group_cases),
            "details": details,
            "full_body_overview": full_path.relative_to(output_dir).as_posix(),
            "head_shoulders_overview": close_path.relative_to(output_dir).as_posix(),
        }

    index_path = output_dir / "index.json"
    write_json(index, index_path)
    write_html(index, output_dir / "index.html")
    return index_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    index_path = build_review(args.summary, args.output_dir)
    print("Review sheets created: {}".format(index_path.parent))
    print("Review index: {}".format(index_path))


if __name__ == "__main__":
    main()
