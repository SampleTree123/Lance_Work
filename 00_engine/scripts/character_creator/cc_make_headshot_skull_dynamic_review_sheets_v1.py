"""Create dynamic-pose review sheets for selected Headshot skull profiles."""

import argparse
import importlib.util
import os


SCRIPT_ROOT = os.path.dirname(os.path.realpath(__file__))
BASE_SHEET_PATH = os.path.join(
    SCRIPT_ROOT,
    "cc_make_headshot_skull_profile_review_sheets_v1.py",
)
spec = importlib.util.spec_from_file_location("headshot_static_sheets", BASE_SHEET_PATH)
STATIC = importlib.util.module_from_spec(spec)
spec.loader.exec_module(STATIC)

from PIL import Image, ImageDraw


POSE_ORDER = (
    ("post_pose_neutral_front", "Neutral restored"),
    ("blink_bilateral_front", "Blink"),
    ("smile_subtle_front", "Subtle smile"),
    ("smile_medium_front", "Medium smile"),
    ("smile_broad_front", "Broad smile"),
    ("jaw_open_front", "Jaw open"),
)


def dynamic_images(case):
    review = case.get("neck_morph_review") or {}
    morphs = review.get("morphs") or []
    if len(morphs) != 1:
        raise RuntimeError("{} must contain one Morph review".format(case["preset_id"]))
    candidates = morphs[0].get("candidates") or []
    if len(candidates) != 1:
        raise RuntimeError("{} must contain one candidate".format(case["preset_id"]))
    dynamic = candidates[0].get("dynamic_pose_review") or {}
    report_path = dynamic.get("report_path")
    if not report_path or not os.path.isfile(report_path):
        raise RuntimeError("{} has no dynamic report".format(case["preset_id"]))
    report = STATIC.read_json(report_path)
    images = {
        "post_pose_neutral_front": report["post_pose_neutral_capture"]["path"]
    }
    for pose in report.get("poses") or []:
        images[pose["pose_id"]] = pose["image"]
    for pose_id, unused_label in POSE_ORDER:
        path = images.get(pose_id)
        if not path or not os.path.isfile(path):
            raise RuntimeError("{} is missing {}".format(case["preset_id"], pose_id))
    return images


def render_overview(sex, cases, profiles, case_images, output_path):
    cell = (300, 300)
    column_header = 72
    row_label = 105
    top_header = 58
    width = row_label + len(cases) * cell[0]
    height = top_header + column_header + len(POSE_ORDER) * cell[1]
    sheet = Image.new("RGB", (width, height), (22, 25, 30))
    draw = ImageDraw.Draw(sheet)
    draw.text(
        (18, 13),
        "{} Canonical Skull Dynamic Gate".format(sex.title()),
        fill=(242, 244, 247),
        font=STATIC.font(25, bold=True),
    )
    for column, case in enumerate(cases):
        profile = profiles[case["preset_id"]]
        x = row_label + column * cell[0]
        draw.text(
            (x + 10, top_header + 8),
            profile["id"],
            fill=(240, 242, 245),
            font=STATIC.font(18, bold=True),
        )
        draw.text(
            (x + 10, top_header + 37),
            profile["label"],
            fill=(174, 181, 191),
            font=STATIC.font(14),
        )
        for row, (pose_id, pose_label) in enumerate(POSE_ORDER):
            y = top_header + column_header + row * cell[1]
            sheet.paste(
                STATIC.fitted_image(case_images[case["preset_id"]][pose_id], cell),
                (x, y),
            )
            if column == 0:
                draw.text(
                    (10, y + cell[1] // 2 - 10),
                    pose_label,
                    fill=(207, 211, 218),
                    font=STATIC.font(15, bold=True),
                )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=True)


def render_pose_strip(
    sex,
    pose_id,
    pose_label,
    cases,
    profiles,
    case_images,
    output_path,
):
    cell = (512, 512)
    header = 78
    sheet = Image.new(
        "RGB",
        (len(cases) * cell[0], header + cell[1]),
        (22, 25, 30),
    )
    draw = ImageDraw.Draw(sheet)
    for column, case in enumerate(cases):
        profile = profiles[case["preset_id"]]
        x = column * cell[0]
        draw.text(
            (x + 12, 9),
            "{} | {}".format(profile["id"], profile["label"]),
            fill=(240, 242, 245),
            font=STATIC.font(18, bold=True),
        )
        draw.text(
            (x + 12, 39),
            "{} | {}".format(sex.title(), pose_label),
            fill=(174, 181, 191),
            font=STATIC.font(14),
        )
        sheet.paste(
            STATIC.fitted_image(case_images[case["preset_id"]][pose_id], cell),
            (x, header),
        )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=True)


def create_dynamic_review_sheets(manifest_path, result_paths, output_dir):
    manifest = STATIC.read_json(manifest_path)
    profiles = STATIC.profile_map(manifest)
    cases = []
    for result_path in result_paths:
        cases.extend(STATIC.validation_results(STATIC.read_json(result_path)))
    cases = sorted(
        [case for case in cases if case.get("success") is True],
        key=lambda item: item["preset_id"],
    )
    if len(cases) != 8:
        raise RuntimeError("Dynamic Headshot gate requires eight successful cases")
    case_images = dict((case["preset_id"], dynamic_images(case)) for case in cases)
    groups = []
    profile_records = []
    for sex in ("female", "male"):
        sex_cases = [case for case in cases if case.get("sex") == sex]
        if len(sex_cases) != 4:
            raise RuntimeError("Dynamic Headshot gate requires four {} cases".format(sex))
        overview = os.path.join(output_dir, sex, "overview.png")
        render_overview(sex, sex_cases, profiles, case_images, overview)
        comparisons = {}
        for pose_id, pose_label in POSE_ORDER:
            output_path = os.path.join(output_dir, sex, "{}_comparison.png".format(pose_id))
            render_pose_strip(
                sex,
                pose_id,
                pose_label,
                sex_cases,
                profiles,
                case_images,
                output_path,
            )
            comparisons[pose_id] = output_path
        groups.append(
            {
                "sex": sex,
                "case_count": len(sex_cases),
                "overview": overview,
                "view_comparisons": comparisons,
                "presets": [case["preset_id"] for case in sex_cases],
            }
        )
        profile_records.extend(
            {
                "preset_id": case["preset_id"],
                "sex": sex,
                "profile": profiles[case["preset_id"]],
                "views": case_images[case["preset_id"]],
            }
            for case in sex_cases
        )
    index = {
        "schema_version": 1,
        "manifest": manifest_path,
        "result_paths": result_paths,
        "case_count": len(cases),
        "pose_count_per_case": len(POSE_ORDER),
        "source_image_count": len(cases) * (len(POSE_ORDER) + 3),
        "groups": groups,
        "profiles": profile_records,
    }
    STATIC.write_json(index, os.path.join(output_dir, "index.json"))
    lines = [
        "# Headshot Canonical Skull Dynamic Gate",
        "",
        "Machine gate: 8/8 cases passed. Human visual review remains required.",
        "",
        "1. Inspect female and male `overview.png`.",
        "2. Check blink closure, lip/teeth intersections, jaw opening, and neutral restoration.",
        "3. Compare the same H-profile across both sexes before production approval.",
        "",
        "- Canonical profiles: H00 Baseline, H01 Long Deep, H02 Low Flat, H03 Narrow Shallow.",
        "- Dynamic poses per case: 5 plus restored neutral.",
        "- Raw images: 72, including three static views per case.",
        "- Controlled Morphs were unchanged during poses and restored after every case.",
        "",
    ]
    STATIC.write_text("\n".join(lines), os.path.join(output_dir, "README.md"))
    return index


def main():
    parser = argparse.ArgumentParser(
        description="Create selected Headshot skull dynamic review sheets"
    )
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--result", action="append", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    index = create_dynamic_review_sheets(
        os.path.realpath(os.path.abspath(args.manifest)),
        [os.path.realpath(os.path.abspath(path)) for path in args.result],
        os.path.realpath(os.path.abspath(args.output_dir)),
    )
    print(
        "Created {} canonical dynamic cases -> {}".format(
            index["case_count"],
            os.path.realpath(os.path.abspath(args.output_dir)),
        )
    )


if __name__ == "__main__":
    main()
