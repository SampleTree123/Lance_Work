"""Consolidate CC5 skin-age validation runs and build visual evidence."""

import argparse
import datetime
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat


AGE_LABELS = ("young", "middle", "older")
AGE_WEIGHTS = {"young": 0.0, "middle": 0.5, "older": 1.0}
ARTIFACT_KEYS = (
    "face_front_preview",
    "face_three_quarter_preview",
    "face_profile_preview",
)
MEAN_ABS_THRESHOLD = 0.05
CHANGED_FRACTION_THRESHOLD = 0.002


class ValidationError(RuntimeError):
    pass


def read_json(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, payload):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(
            payload,
            handle,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        handle.write("\n")


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def image_record(path):
    target = Path(path)
    if not target.is_file():
        raise ValidationError("Missing render: {}".format(target))
    with Image.open(target) as source:
        image = source.convert("RGB")
        pixel_digest = hashlib.sha256(image.tobytes()).hexdigest()
        return {
            "bytes": target.stat().st_size,
            "file_sha256": file_sha256(target),
            "height": image.height,
            "path": str(target),
            "pixel_sha256": pixel_digest,
            "width": image.width,
        }


def image_difference(first_path, second_path):
    with Image.open(first_path) as first_source:
        first = first_source.convert("RGB")
    with Image.open(second_path) as second_source:
        second = second_source.convert("RGB")
    first_size = first.size
    second_size = second.size
    resampled = False
    if first.size != second.size:
        first_ratio = first.width / float(first.height)
        second_ratio = second.width / float(second.height)
        if abs(first_ratio - second_ratio) > 1e-4:
            raise ValidationError(
                "Render aspect ratios differ: {} != {}".format(
                    first.size, second.size
                )
            )
        comparison_size = (
            min(first.width, second.width),
            min(first.height, second.height),
        )
        first = first.resize(
            comparison_size, Image.Resampling.LANCZOS
        )
        second = second.resize(
            comparison_size, Image.Resampling.LANCZOS
        )
        resampled = True
    difference = ImageChops.difference(first, second)
    statistics = ImageStat.Stat(difference)
    channels = difference.split()
    maximum = ImageChops.lighter(
        ImageChops.lighter(channels[0], channels[1]),
        channels[2],
    )
    histogram = maximum.histogram()
    changed_pixels = sum(histogram[5:])
    pixel_count = first.width * first.height
    mean_abs_rgb = sum(statistics.mean[:3]) / 3.0
    rms_rgb = math.sqrt(
        sum(value * value for value in statistics.rms[:3]) / 3.0
    )
    changed_fraction = changed_pixels / float(pixel_count)
    meaningful = (
        mean_abs_rgb >= MEAN_ABS_THRESHOLD
        or changed_fraction >= CHANGED_FRACTION_THRESHOLD
    )
    return {
        "changed_fraction_gt4": round(changed_fraction, 8),
        "comparison_size": list(first.size),
        "first_size": list(first_size),
        "mean_abs_rgb": round(mean_abs_rgb, 6),
        "meaningful": meaningful,
        "resampled": resampled,
        "rms_rgb": round(rms_rgb, 6),
        "second_size": list(second_size),
    }


def discover_cases(source_roots, expected_ids):
    candidates = {preset_id: [] for preset_id in expected_ids}
    for priority, root_value in enumerate(source_roots):
        root = Path(root_value)
        if not root.is_dir():
            raise ValidationError(
                "Validation source root does not exist: {}".format(root)
            )
        for result_path in sorted(root.rglob("result.json")):
            try:
                payload = read_json(result_path)
            except (OSError, ValueError):
                continue
            case_id = payload.get("case_id")
            if (
                case_id in candidates
                and isinstance(payload.get("age_levels"), list)
                and payload.get("asset")
            ):
                candidates[case_id].append(
                    {
                        "payload": payload,
                        "priority": priority,
                        "result_path": str(result_path),
                    }
                )
    selected = {}
    duplicates = {}
    for case_id, records in candidates.items():
        successful = [
            record
            for record in records
            if record["payload"].get("success") is True
        ]
        if not successful:
            raise ValidationError(
                "No successful validation result for {}".format(case_id)
            )
        successful.sort(
            key=lambda item: (
                item["priority"],
                item["result_path"].lower(),
            )
        )
        selected[case_id] = successful[0]
        duplicates[case_id] = [
            item["result_path"] for item in successful[1:]
        ]
    return selected, duplicates


def material_status(case):
    verification = case.get("material_verification")
    if verification:
        return verification.get("status")
    if (
        case.get("material_changed") is True
        and "CC_Base_Body"
        in (case.get("material_changed_meshes") or [])
    ):
        return "verified_by_material_api_legacy"
    return "unknown"


def validate_case(preset, record):
    case = record["payload"]
    errors = []
    if case.get("success") is not True:
        errors.append("case_not_successful")
    if case.get("asset", {}).get("sha256") != preset["skin_asset"]["sha256"]:
        errors.append("asset_sha256_mismatch")
    for key in (
        "morphs_preserved_after_skin",
        "eye_geometry_preserved",
        "eyeball_move_preserved",
        "age_cycle_restored",
    ):
        if case.get(key) is not True:
            errors.append("{}_failed".format(key))

    dialog = case.get("dialog_policy") or {}
    skin_dialog = dialog.get("skin_material") or {}
    if dialog.get("fatal_unknown_dialog") is not None:
        errors.append("unknown_dialog_observed")
    if skin_dialog.get("matched_count") != 1:
        errors.append("skin_dialog_match_count")
    if skin_dialog.get("clicked_count") != 1:
        errors.append("skin_dialog_click_count")

    status = material_status(case)
    if status in ("failed", "unknown", None):
        errors.append("material_verification_{}".format(status))

    age_by_label = {
        item.get("label"): item for item in (case.get("age_levels") or [])
    }
    if set(age_by_label) != set(AGE_LABELS):
        errors.append("age_level_set_mismatch")

    images = {}
    for age_label in AGE_LABELS:
        age = age_by_label.get(age_label)
        if age is None:
            continue
        actual = float((age.get("application") or {}).get("actual", -1.0))
        if abs(actual - AGE_WEIGHTS[age_label]) > 1e-7:
            errors.append("{}_weight_mismatch".format(age_label))
        artifacts = age.get("artifacts") or {}
        images[age_label] = {}
        for key in ARTIFACT_KEYS:
            try:
                images[age_label][key] = image_record(artifacts.get(key))
            except (OSError, ValidationError, TypeError) as exc:
                errors.append("{}_{}:{}".format(age_label, key, exc))

    age_differences = {}
    for key in ARTIFACT_KEYS:
        if not all(key in images.get(label, {}) for label in AGE_LABELS):
            continue
        young_path = images["young"][key]["path"]
        middle_path = images["middle"][key]["path"]
        older_path = images["older"][key]["path"]
        age_differences[key] = {
            "young_to_middle": image_difference(
                young_path, middle_path
            ),
            "middle_to_older": image_difference(
                middle_path, older_path
            ),
            "young_to_older": image_difference(
                young_path, older_path
            ),
        }
        if not age_differences[key]["young_to_middle"]["meaningful"]:
            errors.append("{}_young_middle_not_distinct".format(key))
        if not age_differences[key]["middle_to_older"]["meaningful"]:
            errors.append("{}_middle_older_not_distinct".format(key))

    return {
        "age_differences": age_differences,
        "age_from_filename": preset["age_from_filename"],
        "errors": errors,
        "group": preset["group"],
        "identity_label": preset["identity_label"],
        "images": images,
        "material_status": status,
        "preset_id": preset["preset_id"],
        "region_label": preset["region_label"],
        "result_path": record["result_path"],
        "sex": preset["sex"],
        "success": not errors,
    }


def add_skin_distinctness(case_records):
    for sex in ("female", "male"):
        sex_cases = [
            item for item in case_records if item["sex"] == sex
        ]
        for item in sex_cases:
            current_path = item["images"]["young"][
                "face_front_preview"
            ]["path"]
            comparisons = []
            for other in sex_cases:
                if other["preset_id"] == item["preset_id"]:
                    continue
                other_path = other["images"]["young"][
                    "face_front_preview"
                ]["path"]
                comparison = image_difference(current_path, other_path)
                comparison["preset_id"] = other["preset_id"]
                comparisons.append(comparison)
            nearest = min(
                comparisons,
                key=lambda value: (
                    value["mean_abs_rgb"],
                    value["changed_fraction_gt4"],
                ),
            )
            item["nearest_young_skin"] = nearest
            item["young_skin_visually_distinct"] = nearest["meaningful"]
            if not nearest["meaningful"]:
                item["errors"].append("young_skin_not_visually_distinct")
                item["success"] = False


def font(size):
    candidates = (
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\segoeui.ttf"),
    )
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def fitted_thumbnail(path, size):
    with Image.open(path) as source:
        image = source.convert("RGB")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, (25, 28, 32))
    left = (size[0] - image.width) // 2
    top = (size[1] - image.height) // 2
    canvas.paste(image, (left, top))
    return canvas


def make_age_progression_sheet(case_records, sex, output_path):
    rows = [item for item in case_records if item["sex"] == sex]
    thumb_size = (210, 280)
    label_width = 250
    header_height = 42
    row_height = thumb_size[1] + 34
    width = label_width + len(AGE_LABELS) * thumb_size[0]
    height = header_height + len(rows) * row_height
    sheet = Image.new("RGB", (width, height), (18, 21, 25))
    draw = ImageDraw.Draw(sheet)
    header_font = font(18)
    label_font = font(14)
    draw.text((12, 10), "{} skin age matrix".format(sex), fill="white", font=header_font)
    for column, age_label in enumerate(AGE_LABELS):
        draw.text(
            (
                label_width + column * thumb_size[0] + 10,
                10,
            ),
            "{} ({})".format(
                age_label, int(AGE_WEIGHTS[age_label] * 100)
            ),
            fill=(220, 225, 230),
            font=header_font,
        )
    for row_index, item in enumerate(rows):
        top = header_height + row_index * row_height
        draw.rectangle(
            (0, top, width, top + row_height - 1),
            fill=(25, 29, 34) if row_index % 2 == 0 else (31, 35, 40),
        )
        label = "{}\n{}\n{}".format(
            item["preset_id"],
            item["identity_label"],
            item["group"],
        )
        draw.multiline_text(
            (12, top + 12),
            label,
            fill=(235, 238, 240),
            font=label_font,
            spacing=6,
        )
        for column, age_label in enumerate(AGE_LABELS):
            image_path = item["images"][age_label][
                "face_front_preview"
            ]["path"]
            thumb = fitted_thumbnail(image_path, thumb_size)
            sheet.paste(
                thumb,
                (label_width + column * thumb_size[0], top),
            )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, "PNG")
    return str(output)


def make_young_pool_sheet(case_records, sex, output_path):
    rows = [item for item in case_records if item["sex"] == sex]
    columns = 4 if sex == "female" else 3
    thumb_size = (230, 307)
    label_height = 48
    cell_width = thumb_size[0]
    cell_height = thumb_size[1] + label_height
    row_count = int(math.ceil(len(rows) / float(columns)))
    sheet = Image.new(
        "RGB",
        (columns * cell_width, row_count * cell_height),
        (18, 21, 25),
    )
    draw = ImageDraw.Draw(sheet)
    label_font = font(13)
    for index, item in enumerate(rows):
        column = index % columns
        row = index // columns
        left = column * cell_width
        top = row * cell_height
        image_path = item["images"]["young"][
            "face_front_preview"
        ]["path"]
        sheet.paste(
            fitted_thumbnail(image_path, thumb_size),
            (left, top),
        )
        draw.text(
            (left + 7, top + thumb_size[1] + 5),
            "{}\n{}".format(
                item["preset_id"], item["identity_label"]
            ),
            fill=(235, 238, 240),
            font=label_font,
            spacing=3,
        )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, "PNG")
    return str(output)


def write_markdown(path, report):
    summary = report["summary"]
    lines = [
        "# CC5 Skin Age Validation",
        "",
        "Generated: `{}`".format(report["generated_at"]),
        "",
        "## Summary",
        "",
        "- Result: **{}**".format(
            "PASS" if summary["success"] else "FAIL"
        ),
        "- Skin assets: `{}/{}`".format(
            summary["successful_case_count"],
            summary["expected_case_count"],
        ),
        "- Age states: `{}`".format(summary["age_state_count"]),
        "- Rendered images: `{}`".format(summary["image_count"]),
        "- Female / male: `{}` / `{}`".format(
            summary["female_count"], summary["male_count"]
        ),
        "- Material API render confirmations: `{}`".format(
            summary["render_confirmation_required_count"]
        ),
        "",
        "## Evidence",
        "",
        "- [Female age progression](female_age_progression_front.png)",
        "- [Male age progression](male_age_progression_front.png)",
        "- [Female young skin pool](female_young_skin_pool.png)",
        "- [Male young skin pool](male_young_skin_pool.png)",
        "- [Machine-readable report](validation_summary.json)",
        "",
        "## Cases",
        "",
        "| Preset | Sex | Skin | Material check | Nearest young skin | Mean pixel delta | Result |",
        "|---|---|---|---|---|---:|---|",
    ]
    for item in report["cases"]:
        nearest = item["nearest_young_skin"]
        lines.append(
            "| `{}` | {} | {} | `{}` | `{}` | {:.3f} | {} |".format(
                item["preset_id"],
                item["sex"],
                item["identity_label"],
                item["material_status"],
                nearest["preset_id"],
                nearest["mean_abs_rgb"],
                "PASS" if item["success"] else "FAIL",
            )
        )
    lines.extend(
        [
            "",
            "Supplier region labels are inventory labels, not ethnicity ground truth.",
            "",
        ]
    )
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix-file", required=True)
    parser.add_argument(
        "--source-root", action="append", required=True
    )
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    matrix_path = Path(args.matrix_file).resolve()
    output_dir = Path(args.output_dir).resolve()
    if output_dir.exists():
        raise ValidationError(
            "Output directory already exists: {}".format(output_dir)
        )
    output_dir.mkdir(parents=True)

    matrix = read_json(matrix_path)
    presets = matrix.get("presets") or []
    expected_ids = [item["preset_id"] for item in presets]
    if len(expected_ids) != 21 or len(set(expected_ids)) != 21:
        raise ValidationError("Expected exactly 21 unique skin presets")

    selected, duplicates = discover_cases(
        args.source_root, expected_ids
    )
    cases = [
        validate_case(preset, selected[preset["preset_id"]])
        for preset in presets
    ]
    add_skin_distinctness(cases)

    evidence = {
        "female_age_progression_front": make_age_progression_sheet(
            cases,
            "female",
            output_dir / "female_age_progression_front.png",
        ),
        "female_young_skin_pool": make_young_pool_sheet(
            cases,
            "female",
            output_dir / "female_young_skin_pool.png",
        ),
        "male_age_progression_front": make_age_progression_sheet(
            cases,
            "male",
            output_dir / "male_age_progression_front.png",
        ),
        "male_young_skin_pool": make_young_pool_sheet(
            cases,
            "male",
            output_dir / "male_young_skin_pool.png",
        ),
    }
    successful_count = sum(item["success"] for item in cases)
    image_count = sum(
        len(item["images"].get(age, {}))
        for item in cases
        for age in AGE_LABELS
    )
    summary = {
        "age_state_count": len(cases) * len(AGE_LABELS),
        "expected_case_count": len(presets),
        "female_count": sum(item["sex"] == "female" for item in cases),
        "image_count": image_count,
        "male_count": sum(item["sex"] == "male" for item in cases),
        "render_confirmation_required_count": sum(
            item["material_status"] == "render_confirmation_required"
            for item in cases
        ),
        "success": successful_count == len(presets),
        "successful_case_count": successful_count,
    }
    report = {
        "cases": cases,
        "duplicate_successful_results": duplicates,
        "evidence": evidence,
        "generated_at": datetime.datetime.now().astimezone().isoformat(),
        "matrix_file": str(matrix_path),
        "schema_version": 1,
        "source_roots": [
            str(Path(value).resolve()) for value in args.source_root
        ],
        "summary": summary,
    }
    write_json(output_dir / "validation_summary.json", report)
    write_markdown(output_dir / "README.md", report)
    print(
        json.dumps(
            {
                "output_dir": str(output_dir),
                "summary": summary,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not summary["success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
