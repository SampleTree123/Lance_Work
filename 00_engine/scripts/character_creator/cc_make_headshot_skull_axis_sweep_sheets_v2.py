"""Create per-axis review sheets for the Headshot skull sweep v2."""

import argparse
import json
import os

from PIL import Image, ImageDraw, ImageFont, ImageOps


VIEW_ORDER = (
    ("front", "Front"),
    ("three_quarter", "3/4"),
    ("profile", "Profile"),
)
PARAMETER_KEYS = (
    "head_width",
    "head_depth",
    "skull_height",
    "skull_width",
    "skull_depth",
    "skull_back_depth",
    "skull_peak",
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


def write_text(text, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    os.replace(temporary, path)


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


def fitted_image(path, size):
    if not os.path.isfile(path):
        raise RuntimeError("Missing review image: {}".format(path))
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    return ImageOps.fit(
        image,
        size,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )


def validation_results(data):
    validation = (data.get("result") or {}).get("validation")
    if validation is None:
        validation = data.get("validation")
    if validation is None and data.get("diagnostic_mode"):
        validation = data
    if validation is None:
        raise RuntimeError("Result JSON has no validation object")
    return validation.get("results") or []


def signed_token(value):
    if abs(value) <= 1e-9:
        return "Z000"
    prefix = "P" if value > 0 else "N"
    return "{}{:03d}".format(prefix, int(round(abs(value) * 100)))


def flatten_cases(manifest, result_paths):
    presets = {
        preset["preset_id"]: preset
        for preset in manifest.get("presets") or []
    }
    result_cases = []
    for result_path in result_paths:
        result_cases.extend(validation_results(read_json(result_path)))

    flattened = []
    for result_case in result_cases:
        if result_case.get("success") is not True:
            continue
        preset_id = result_case.get("preset_id")
        preset = presets.get(preset_id)
        if preset is None:
            raise RuntimeError("Result preset is missing from manifest: {}".format(preset_id))
        axis = preset.get("axis_sweep") or {}
        morphs = (result_case.get("neck_morph_review") or {}).get("morphs") or []
        if len(morphs) != 1:
            raise RuntimeError("{} must contain one review Morph".format(preset_id))
        candidates = morphs[0].get("candidates") or []
        expected_values = axis.get("values") or []
        if len(candidates) != len(expected_values):
            raise RuntimeError("{} candidate count changed".format(preset_id))
        for candidate in candidates:
            value = float(candidate["value"])
            views = candidate.get("views") or {}
            for view_id, unused_label in VIEW_ORDER:
                if not views.get(view_id) or not os.path.isfile(views[view_id]):
                    raise RuntimeError("{} is missing {}".format(preset_id, view_id))
            is_baseline = axis.get("axis_id") == "HEAD_WIDTH" and len(expected_values) == 1
            case_id = "BASELINE" if is_baseline else "{}_{}".format(
                axis["axis_id"],
                signed_token(value),
            )
            parameters = dict((key, 0.0) for key in PARAMETER_KEYS)
            if not is_baseline:
                parameters[axis["parameter_key"]] = value
            flattened.append(
                {
                    "id": case_id,
                    "label": "Baseline" if is_baseline else "{} {:+.2f}".format(axis["label"], value),
                    "axis_id": "BASELINE" if is_baseline else axis["axis_id"],
                    "axis_label": "Baseline" if is_baseline else axis["label"],
                    "parameter_key": axis["parameter_key"],
                    "parameters": parameters,
                    "preset_id": preset_id,
                    "sex": result_case.get("sex"),
                    "value": value,
                    "views": views,
                }
            )
    return flattened


def by_axis(cases):
    baseline = next(case for case in cases if case["axis_id"] == "BASELINE")
    axes = []
    seen = set()
    for case in cases:
        axis_id = case["axis_id"]
        if axis_id == "BASELINE" or axis_id in seen:
            continue
        seen.add(axis_id)
        axis_cases = sorted(
            [item for item in cases if item["axis_id"] == axis_id],
            key=lambda item: item["value"],
        )
        if len(axis_cases) != 2:
            raise RuntimeError("{} must have negative and positive cases".format(axis_id))
        axes.append((axis_cases[0]["axis_label"], axis_cases[0], baseline, axis_cases[1]))
    return axes


def draw_cell(sheet, draw, case, view_id, origin, image_size, header_height):
    x, y = origin
    label = "{}  ({:+.2f})".format(case["id"], case["value"])
    draw.text((x + 8, y + 6), label, fill=(229, 233, 238), font=font(14, bold=True))
    sheet.paste(
        fitted_image(case["views"][view_id], image_size),
        (x, y + header_height),
    )


def render_overview(sex, axes, output_path):
    image_size = (250, 250)
    header_height = 32
    cell_width = image_size[0]
    cell_height = header_height + image_size[1]
    row_label = 190
    top_header = 76
    width = row_label + 6 * cell_width
    height = top_header + len(axes) * cell_height
    sheet = Image.new("RGB", (width, height), (22, 25, 30))
    draw = ImageDraw.Draw(sheet)
    draw.text((18, 12), "{} Headshot Skull Axis Sweep v2".format(sex.title()), fill=(245, 247, 249), font=font(26, bold=True))
    headings = ("Negative Front", "Baseline Front", "Positive Front", "Negative Profile", "Baseline Profile", "Positive Profile")
    for index, heading in enumerate(headings):
        draw.text((row_label + index * cell_width + 8, 48), heading, fill=(174, 181, 191), font=font(13, bold=True))
    for row, (axis_label, negative, baseline, positive) in enumerate(axes):
        y = top_header + row * cell_height
        draw.text((12, y + 12), axis_label, fill=(232, 235, 239), font=font(17, bold=True))
        draw.text((12, y + 39), "{:+.2f} / 0 / {:+.2f}".format(negative["value"], positive["value"]), fill=(158, 167, 178), font=font(13))
        columns = (
            (negative, "front"),
            (baseline, "front"),
            (positive, "front"),
            (negative, "profile"),
            (baseline, "profile"),
            (positive, "profile"),
        )
        for column, (case, view_id) in enumerate(columns):
            draw_cell(sheet, draw, case, view_id, (row_label + column * cell_width, y), image_size, header_height)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=True)


def render_view_matrix(sex, view_id, view_label, axes, output_path):
    image_size = (420, 420)
    header_height = 34
    row_label = 200
    top_header = 74
    width = row_label + 3 * image_size[0]
    height = top_header + len(axes) * (header_height + image_size[1])
    sheet = Image.new("RGB", (width, height), (22, 25, 30))
    draw = ImageDraw.Draw(sheet)
    draw.text((18, 12), "{} | {} | Skull Axis Sweep v2".format(sex.title(), view_label), fill=(245, 247, 249), font=font(25, bold=True))
    for column, heading in enumerate(("Negative", "Baseline", "Positive")):
        draw.text((row_label + column * image_size[0] + 10, 48), heading, fill=(174, 181, 191), font=font(14, bold=True))
    for row, (axis_label, negative, baseline, positive) in enumerate(axes):
        y = top_header + row * (header_height + image_size[1])
        draw.text((12, y + 10), axis_label, fill=(232, 235, 239), font=font(17, bold=True))
        draw.text((12, y + 38), "{:+.2f} / 0 / {:+.2f}".format(negative["value"], positive["value"]), fill=(158, 167, 178), font=font(13))
        for column, case in enumerate((negative, baseline, positive)):
            draw_cell(sheet, draw, case, view_id, (row_label + column * image_size[0], y), image_size, header_height)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=True)


def create_review_sheets(manifest_path, result_paths, output_dir):
    manifest = read_json(manifest_path)
    cases = flatten_cases(manifest, result_paths)
    records = []
    indexed_profiles = []
    for sex in ("female", "male"):
        sex_cases = [case for case in cases if case["sex"] == sex]
        if not sex_cases:
            continue
        axes = by_axis(sex_cases)
        overview_path = os.path.join(output_dir, sex, "overview.png")
        render_overview(sex, axes, overview_path)
        comparisons = {}
        for view_id, view_label in VIEW_ORDER:
            path = os.path.join(output_dir, sex, "{}_comparison.png".format(view_id))
            render_view_matrix(sex, view_id, view_label, axes, path)
            comparisons[view_id] = path
        records.append(
            {
                "sex": sex,
                "case_count": len(sex_cases),
                "overview": overview_path,
                "view_comparisons": comparisons,
                "presets": sorted(set(case["preset_id"] for case in sex_cases)),
            }
        )
        indexed_profiles.extend(
            {
                "case_id": case["id"],
                "preset_id": case["preset_id"],
                "sex": sex,
                "profile": {
                    "id": case["id"],
                    "label": case["label"],
                    "axis_id": case["axis_id"],
                    "axis_label": case["axis_label"],
                    "value": case["value"],
                    "parameters": case["parameters"],
                },
                "views": case["views"],
            }
            for case in sex_cases
        )

    index = {
        "schema_version": 2,
        "manifest": manifest_path,
        "result_paths": result_paths,
        "case_count": len(cases),
        "image_count": len(cases) * len(VIEW_ORDER),
        "groups": records,
        "profiles": indexed_profiles,
    }
    write_json(index, os.path.join(output_dir, "index.json"))
    lines = [
        "# Headshot Skull Axis Sweep v2",
        "",
        "Range-discovery artifacts only. Canonical projects were loaded read-only and were not overwritten.",
        "",
        "## Review Order",
        "",
        "1. Review each sex `overview.png` by axis.",
        "2. Compare negative, baseline, and positive in each `*_comparison.png`.",
        "3. Use the visual portal for arbitrary A/B inspection.",
        "4. Reject distorted extremes; select a smaller production interval per axis.",
        "",
        "## Matrix",
        "",
        "- Cases: {}".format(len(cases)),
        "- Source images: {}".format(len(cases) * len(VIEW_ORDER)),
        "- Axes per sex: 7",
        "- Canonical project writes: none",
        "",
    ]
    write_text("\n".join(lines), os.path.join(output_dir, "README.md"))
    return index


def main():
    parser = argparse.ArgumentParser(description="Create Headshot skull axis sweep v2 review sheets")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--result", action="append", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    index = create_review_sheets(
        os.path.realpath(os.path.abspath(args.manifest)),
        [os.path.realpath(os.path.abspath(path)) for path in args.result],
        os.path.realpath(os.path.abspath(args.output_dir)),
    )
    print("Created {} cases / {} images -> {}".format(index["case_count"], index["image_count"], os.path.realpath(os.path.abspath(args.output_dir))))


if __name__ == "__main__":
    main()
