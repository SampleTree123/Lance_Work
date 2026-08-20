"""Create review sheets for the Headshot skull-profile visual matrix."""

import argparse
import json
import os

from PIL import Image, ImageDraw, ImageFont, ImageOps


VIEW_ORDER = (
    ("front", "Front"),
    ("three_quarter", "3/4"),
    ("profile", "Profile"),
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


def case_views(case):
    review = case.get("neck_morph_review") or {}
    morphs = review.get("morphs") or []
    if len(morphs) != 1:
        raise RuntimeError(
            "{} must contain one review Morph".format(case.get("preset_id"))
        )
    candidates = morphs[0].get("candidates") or []
    if len(candidates) != 1:
        raise RuntimeError(
            "{} must contain one review candidate".format(
                case.get("preset_id")
            )
        )
    views = candidates[0].get("views") or {}
    for view_id, unused_label in VIEW_ORDER:
        path = views.get(view_id)
        if not path or not os.path.isfile(path):
            raise RuntimeError(
                "{} is missing {}".format(case.get("preset_id"), view_id)
            )
    return views


def profile_map(manifest):
    profiles = {}
    for preset in manifest.get("presets") or []:
        preset_id = preset.get("preset_id")
        profile = preset.get("head_shape_profile")
        if preset_id and isinstance(profile, dict):
            profiles[preset_id] = profile
    return profiles


def short_parameters(profile):
    return (
        "HW {head_width:+.2f}  HD {head_depth:+.2f}  "
        "SH {skull_height:+.2f}  SW {skull_width:+.2f}  "
        "SD {skull_depth:+.2f}  BD {skull_back_depth:+.2f}  "
        "SP {skull_peak:+.2f}"
    ).format(**profile)


def render_overview(sex, cases, profiles, output_path):
    cell = (300, 300)
    column_header = 72
    row_label = 78
    top_header = 58
    width = row_label + len(cases) * cell[0]
    height = top_header + column_header + len(VIEW_ORDER) * cell[1]
    sheet = Image.new("RGB", (width, height), (22, 25, 30))
    draw = ImageDraw.Draw(sheet)
    draw.text(
        (18, 13),
        "{} Headshot Skull Profile Review".format(sex.title()),
        fill=(242, 244, 247),
        font=font(25, bold=True),
    )
    for column, case in enumerate(cases):
        preset_id = case["preset_id"]
        profile = profiles[preset_id]
        x = row_label + column * cell[0]
        draw.text(
            (x + 10, top_header + 8),
            profile["id"],
            fill=(240, 242, 245),
            font=font(18, bold=True),
        )
        draw.text(
            (x + 10, top_header + 37),
            profile["label"],
            fill=(174, 181, 191),
            font=font(14),
        )
        views = case_views(case)
        for row, (view_id, view_label) in enumerate(VIEW_ORDER):
            y = top_header + column_header + row * cell[1]
            sheet.paste(fitted_image(views[view_id], cell), (x, y))
            if column == 0:
                draw.text(
                    (10, y + cell[1] // 2 - 10),
                    view_label,
                    fill=(207, 211, 218),
                    font=font(16, bold=True),
                )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=True)


def render_view_strip(sex, view_id, view_label, cases, profiles, output_path):
    cell = (512, 512)
    header = 105
    width = len(cases) * cell[0]
    height = header + cell[1]
    sheet = Image.new("RGB", (width, height), (22, 25, 30))
    draw = ImageDraw.Draw(sheet)
    for column, case in enumerate(cases):
        preset_id = case["preset_id"]
        profile = profiles[preset_id]
        x = column * cell[0]
        draw.text(
            (x + 12, 9),
            "{} | {}".format(profile["id"], profile["label"]),
            fill=(240, 242, 245),
            font=font(18, bold=True),
        )
        draw.text(
            (x + 12, 39),
            "{} | {}".format(sex.title(), view_label),
            fill=(174, 181, 191),
            font=font(14),
        )
        draw.text(
            (x + 12, 65),
            short_parameters(profile),
            fill=(174, 181, 191),
            font=font(12),
        )
        sheet.paste(fitted_image(case_views(case)[view_id], cell), (x, header))
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=True)


def create_review_sheets(manifest_path, result_paths, output_dir):
    manifest = read_json(manifest_path)
    profiles = profile_map(manifest)
    cases = []
    for result_path in result_paths:
        cases.extend(validation_results(read_json(result_path)))
    cases = [case for case in cases if case.get("success") is True]
    cases.sort(key=lambda item: item["preset_id"])
    if any(case["preset_id"] not in profiles for case in cases):
        raise RuntimeError("A result case has no manifest profile")

    records = []
    for sex in ("female", "male"):
        sex_cases = [case for case in cases if case.get("sex") == sex]
        if not sex_cases:
            continue
        overview_path = os.path.join(output_dir, sex, "overview.png")
        render_overview(sex, sex_cases, profiles, overview_path)
        view_paths = {}
        for view_id, view_label in VIEW_ORDER:
            output_path = os.path.join(
                output_dir,
                sex,
                "{}_comparison.png".format(view_id),
            )
            render_view_strip(
                sex,
                view_id,
                view_label,
                sex_cases,
                profiles,
                output_path,
            )
            view_paths[view_id] = output_path
        records.append(
            {
                "sex": sex,
                "case_count": len(sex_cases),
                "overview": overview_path,
                "view_comparisons": view_paths,
                "presets": [case["preset_id"] for case in sex_cases],
            }
        )

    index = {
        "schema_version": 1,
        "manifest": manifest_path,
        "result_paths": result_paths,
        "case_count": len(cases),
        "groups": records,
        "profiles": [
            {
                "preset_id": case["preset_id"],
                "sex": case.get("sex"),
                "profile": profiles[case["preset_id"]],
                "views": case_views(case),
            }
            for case in cases
        ],
    }
    write_json(index, os.path.join(output_dir, "index.json"))
    unique_profiles = {}
    for case in cases:
        profile = profiles[case["preset_id"]]
        unique_profiles.setdefault(profile["id"], profile)
    lines = [
        "# Headshot Skull Profile Review",
        "",
        "Visual-review artifacts only. No canonical face prototype was saved or overwritten.",
        "The profiles are not production-approved until user review is complete.",
        "",
        "## Review Order",
        "",
        "1. Open `female/overview.png` and `male/overview.png`.",
        "2. Use the three `*_comparison.png` files in each sex folder for closer inspection.",
        "3. Compare front width first, then crown and occipital shape in profile view.",
        "",
        "## Parameter Legend",
        "",
        "`HW` Head Width; `HD` Head Depth; `SH` Skull Height; `SW` Skull Width; "
        "`SD` Skull Depth; `BD` Skull Back Depth; `SP` Skull Peak.",
        "",
        "| Profile | Label | HW | HD | SH | SW | SD | BD | SP |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for profile_id in sorted(unique_profiles):
        profile = unique_profiles[profile_id]
        lines.append(
            "| {id} | {label} | {head_width:+.2f} | {head_depth:+.2f} | "
            "{skull_height:+.2f} | {skull_width:+.2f} | "
            "{skull_depth:+.2f} | {skull_back_depth:+.2f} | "
            "{skull_peak:+.2f} |".format(**profile)
        )
    lines.extend(
        [
            "",
            "## Machine Result",
            "",
            "- Cases: {}".format(len(cases)),
            "- Views per case: {}".format(len(VIEW_ORDER)),
            "- Controlled Morph restoration: see each source `validation_result.json`.",
            "- Full machine-readable paths and values: `index.json`.",
            "",
        ]
    )
    write_text("\n".join(lines), os.path.join(output_dir, "README.md"))
    return index


def main():
    parser = argparse.ArgumentParser(
        description="Create Headshot skull-profile review sheets"
    )
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--result", action="append", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    index = create_review_sheets(
        os.path.realpath(os.path.abspath(args.manifest)),
        [os.path.realpath(os.path.abspath(path)) for path in args.result],
        os.path.realpath(os.path.abspath(args.output_dir)),
    )
    print(
        "Created {} Headshot skull-profile cases -> {}".format(
            index["case_count"],
            os.path.realpath(os.path.abspath(args.output_dir)),
        )
    )


if __name__ == "__main__":
    main()
