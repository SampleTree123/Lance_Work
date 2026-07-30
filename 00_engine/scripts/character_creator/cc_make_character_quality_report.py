"""Create contact sheets and a concise report for a CC quality batch."""

import argparse
import datetime
import json
import math
import os

from PIL import Image, ImageDraw, ImageFont, ImageOps


class ReportBuildError(RuntimeError):
    pass


IMAGE_KINDS = (
    ("full_body", "reconstructed_preview", "Full Body"),
    ("face_front", "face_front_preview", "Face Front"),
    ("face_three_quarter", "face_three_quarter_preview", "Face Three Quarter"),
    ("face_profile", "face_profile_preview", "Face Profile"),
)
OPTIONAL_IMAGE_KINDS = (
    (
        "face_blink_bilateral",
        "face_blink_bilateral_preview",
        "Face Blink Bilateral",
    ),
    (
        "face_blink_left",
        "face_blink_left_preview",
        "Face Blink Left",
    ),
    (
        "face_blink_right",
        "face_blink_right_preview",
        "Face Blink Right",
    ),
    (
        "face_look_left",
        "face_look_left_preview",
        "Face Look Left",
    ),
    (
        "face_look_right",
        "face_look_right_preview",
        "Face Look Right",
    ),
    (
        "face_look_up",
        "face_look_up_preview",
        "Face Look Up",
    ),
    (
        "face_look_down",
        "face_look_down_preview",
        "Face Look Down",
    ),
    (
        "face_squint",
        "face_squint_preview",
        "Face Squint",
    ),
    (
        "face_widen",
        "face_widen_preview",
        "Face Widen",
    ),
    (
        "face_brow_raise",
        "face_brow_raise_preview",
        "Face Brow Raise",
    ),
    (
        "face_brow_down",
        "face_brow_down_preview",
        "Face Brow Down",
    ),
    (
        "face_brow_raise_left",
        "face_brow_raise_left_preview",
        "Face Brow Raise Left",
    ),
    (
        "face_smile",
        "face_smile_preview",
        "Face Smile",
    ),
    (
        "face_jaw_open",
        "face_jaw_open_preview",
        "Face Jaw Open",
    ),
    (
        "face_jaw_open_three_quarter",
        "face_jaw_open_three_quarter_preview",
        "Face Jaw Open Three Quarter",
    ),
    ("teeth_smile_front", "teeth_smile_preview", "Teeth Smile Front"),
    (
        "teeth_jaw_open_front",
        "teeth_jaw_open_preview",
        "Teeth Jaw Open Front",
    ),
    (
        "teeth_jaw_open_three_quarter",
        "teeth_jaw_open_three_quarter_preview",
        "Teeth Jaw Open Three Quarter",
    ),
    (
        "eye_look_left_front",
        "eye_look_left_preview",
        "Eye Look Left Front",
    ),
    (
        "eye_look_right_front",
        "eye_look_right_preview",
        "Eye Look Right Front",
    ),
    (
        "eye_look_up_front",
        "eye_look_up_preview",
        "Eye Look Up Front",
    ),
    (
        "eye_look_down_front",
        "eye_look_down_preview",
        "Eye Look Down Front",
    ),
)


def now():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


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


def font(size, bold=False):
    candidates = (
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
    )
    for path in candidates:
        if os.path.isfile(path):
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def fit_contained(image, size, background=(244, 245, 247)):
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, background)
    x = (size[0] - image.width) // 2
    y = (size[1] - image.height) // 2
    canvas.paste(image, (x, y))
    return canvas


def build_sheet(results, artifact_key, title, output_path, columns=4):
    rows = int(math.ceil(len(results) / float(columns)))
    image_size = (300, 414)
    tile_width = 324
    tile_height = 488
    margin = 24
    title_height = 76
    sheet = Image.new(
        "RGB",
        (
            margin * 2 + columns * tile_width,
            title_height + margin + rows * tile_height,
        ),
        (229, 232, 236),
    )
    draw = ImageDraw.Draw(sheet)
    title_font = font(30, bold=True)
    label_font = font(18, bold=True)
    detail_font = font(15)
    draw.text((margin, 20), title, fill=(24, 28, 34), font=title_font)

    for index, result in enumerate(results):
        row = index // columns
        column = index % columns
        x = margin + column * tile_width
        y = title_height + row * tile_height
        draw.rounded_rectangle(
            (x, y, x + tile_width - 12, y + tile_height - 12),
            radius=6,
            fill=(255, 255, 255),
            outline=(188, 193, 201),
            width=1,
        )
        image_path = result.get("artifacts", {}).get(artifact_key)
        if not image_path or not os.path.isfile(image_path):
            raise ReportBuildError(
                "Missing {} image for {}: {}".format(
                    artifact_key, result.get("preset_id"), image_path
                )
            )
        with Image.open(image_path) as source:
            preview = fit_contained(source, image_size)
        sheet.paste(preview, (x + 6, y + 6))
        label_y = y + 426
        draw.text(
            (x + 9, label_y),
            result["preset_id"],
            fill=(21, 25, 31),
            font=label_font,
        )
        method = (result.get("face_generation") or {}).get("method") or "unknown"
        method = method.replace("direct_anchor", "direct")
        method = method.replace("dominant_blend", "dominant")
        method = method.replace("regional_sculpt", "regional")
        method = method.replace("controlled_extreme", "extreme")
        appearance_recipe_id = result.get("appearance_recipe_id")
        if appearance_recipe_id:
            detail = "{} | {}".format(
                appearance_recipe_id,
                result.get("face_recipe_id", "unknown"),
            )
        else:
            detail = "{} | {}".format(
                result.get("face_recipe_id", "unknown"),
                method,
            )
        draw.text((x + 9, label_y + 25), detail, fill=(75, 81, 91), font=detail_font)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sheet.save(output_path, "JPEG", quality=94, subsampling=0, optimize=True)


def relative_link(target, report_dir):
    return os.path.relpath(target, report_dir).replace(os.sep, "/")


def build_report(root):
    root = os.path.realpath(os.path.abspath(root))
    result_path = os.path.join(root, "validation_result.json")
    if not os.path.isfile(result_path):
        raise ReportBuildError("Missing validation result: {}".format(result_path))
    validation = read_json(result_path)
    results = validation.get("results") or []
    if not results:
        raise ReportBuildError("Validation result contains no characters")

    review_dir = os.path.join(root, "review")
    os.makedirs(review_dir, exist_ok=True)
    sheets = {}
    image_kinds = list(IMAGE_KINDS)
    for candidate in OPTIONAL_IMAGE_KINDS:
        unused_kind, artifact_key, unused_title = candidate
        if all(
            os.path.isfile(item.get("artifacts", {}).get(artifact_key, ""))
            for item in results
        ):
            image_kinds.append(candidate)
    for kind, artifact_key, title in image_kinds:
        path = os.path.join(review_dir, "contact_sheet_{}.jpg".format(kind))
        build_sheet(results, artifact_key, "CC Quality Batch - {}".format(title), path)
        sheets[kind] = path
        if kind.startswith("face_"):
            for sex in ("male", "female"):
                sex_results = [item for item in results if item.get("sex") == sex]
                if not sex_results:
                    continue
                sex_path = os.path.join(
                    review_dir,
                    "contact_sheet_{}_{}.jpg".format(kind, sex),
                )
                build_sheet(
                    sex_results,
                    artifact_key,
                    "CC Face - {} - {}".format(sex.title(), title),
                    sex_path,
                )
                sheets["{}_{}".format(kind, sex)] = sex_path
        if kind.startswith("teeth_") or kind.startswith("eye_"):
            recipe_ids = sorted(
                {
                    item.get("appearance_recipe_id")
                    for item in results
                    if item.get("appearance_recipe_id")
                }
            )
            for recipe_id in recipe_ids:
                for sex in ("male", "female"):
                    group_results = [
                        item
                        for item in results
                        if item.get("appearance_recipe_id") == recipe_id
                        and item.get("sex") == sex
                    ]
                    if not group_results:
                        continue
                    group_name = "{}_{}_{}".format(
                        kind,
                        sex,
                        recipe_id.lower(),
                    )
                    group_path = os.path.join(
                        review_dir,
                        "contact_sheet_{}.jpg".format(group_name),
                    )
                    build_sheet(
                        group_results,
                        artifact_key,
                        "{} - {} - {}".format(
                            title,
                            sex.title(),
                            recipe_id,
                        ),
                        group_path,
                    )
                    sheets[group_name] = group_path

    errors = [float(item.get("face_max_abs_error") or 0.0) for item in results]
    failed = [item["preset_id"] for item in results if not item.get("success")]
    report = {
        "schema_version": 1,
        "generated_at": now(),
        "source_validation_result": result_path,
        "run_id": validation.get("run_id"),
        "library_id": validation.get("library_id"),
        "success": bool(validation.get("success")) and not failed,
        "requested_count": validation.get("requested_count"),
        "success_count": validation.get("success_count"),
        "failure_count": validation.get("failure_count"),
        "maximum_face_abs_error": max(errors),
        "failed_character_ids": failed,
        "contact_sheets": sheets,
        "characters": [
            {
                "character_id": item.get("preset_id"),
                "sex": item.get("sex"),
                "face_recipe_id": item.get("face_recipe_id"),
                "face_generation": item.get("face_generation"),
                "appearance_recipe_id": item.get("appearance_recipe_id"),
                "appearance_asset_ids": item.get("appearance_asset_ids"),
                "appearance_matches_recipe": item.get(
                    "appearance_matches_recipe"
                ),
                "morphs_unchanged_after_appearance": item.get(
                    "morphs_unchanged_after_appearance"
                ),
                "appearance_morphs_within_policy": item.get(
                    "appearance_morphs_within_policy"
                ),
                "success": item.get("success"),
                "body_reconstruction_exact": item.get(
                    "reconstruction_matches_library"
                ),
                "face_matches_recipe": item.get("face_matches_recipe"),
                "body_unchanged_after_face": item.get(
                    "body_unchanged_after_face"
                ),
                "junction_unchanged_after_face": item.get(
                    "junction_unchanged_after_face"
                ),
                "face_max_abs_error": item.get("face_max_abs_error"),
                "images": {
                    "full_body": item.get("artifacts", {}).get(
                        "reconstructed_preview"
                    ),
                    "face_front": item.get("artifacts", {}).get(
                        "face_front_preview"
                    ),
                    "face_three_quarter": item.get("artifacts", {}).get(
                        "face_three_quarter_preview"
                    ),
                    "face_profile": item.get("artifacts", {}).get(
                        "face_profile_preview"
                    ),
                    "teeth_smile_front": item.get("artifacts", {}).get(
                        "teeth_smile_preview"
                    ),
                    "teeth_jaw_open_front": item.get("artifacts", {}).get(
                        "teeth_jaw_open_preview"
                    ),
                    "teeth_jaw_open_three_quarter": item.get(
                        "artifacts", {}
                    ).get("teeth_jaw_open_three_quarter_preview"),
                    "eye_look_left_front": item.get(
                        "artifacts", {}
                    ).get("eye_look_left_preview"),
                    "eye_look_right_front": item.get(
                        "artifacts", {}
                    ).get("eye_look_right_preview"),
                    "eye_look_up_front": item.get(
                        "artifacts", {}
                    ).get("eye_look_up_preview"),
                    "eye_look_down_front": item.get(
                        "artifacts", {}
                    ).get("eye_look_down_preview"),
                },
            }
            for item in results
        ],
    }
    report_json = os.path.join(review_dir, "quality_report.json")
    write_json(report, report_json)

    report_md = os.path.join(review_dir, "quality_report.md")
    lines = [
        "# CC Character Quality Batch",
        "",
        "- Run: `{}`".format(validation.get("run_id")),
        "- Result: `{}/{}` passed".format(
            validation.get("success_count"), validation.get("requested_count")
        ),
        "- Maximum face absolute error: `{:.3e}`".format(max(errors)),
        "- Saved projects: `no` (preview-only geometry validation)",
        "",
        "## Contact Sheets",
        "",
    ]
    for kind, unused_key, title in image_kinds:
        lines.append(
            "- [{}]({})".format(
                title, relative_link(sheets[kind], review_dir)
            )
        )
    lines.extend(
        [
            "",
            "## Characters",
            "",
            "| Character | Sex | Face | Appearance | Body exact | Face exact | Appearance exact | Morphs isolated | Max error |",
            "|---|---|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for item in results:
        appearance = item.get("appearance_matches_recipe")
        appearance_isolated = item.get("appearance_morphs_within_policy")
        if appearance_isolated is None:
            appearance_isolated = item.get(
                "morphs_unchanged_after_appearance"
            )
        lines.append(
            "| {preset_id} | {sex} | {face_recipe_id} | {appearance_recipe_id} | {body} | {face} | {appearance} | {isolated} | {error:.3e} |".format(
                preset_id=item.get("preset_id"),
                sex=item.get("sex"),
                face_recipe_id=item.get("face_recipe_id"),
                appearance_recipe_id=item.get("appearance_recipe_id") or "n/a",
                body="yes" if item.get("reconstruction_matches_library") else "no",
                face="yes" if item.get("face_matches_recipe") else "no",
                appearance="n/a"
                if appearance is None
                else ("yes" if appearance else "no"),
                isolated=(
                    "n/a"
                    if appearance_isolated is None
                    else ("yes" if appearance_isolated else "no")
                ),
                error=float(item.get("face_max_abs_error") or 0.0),
            )
        )
    with open(report_md, "w", encoding="ascii", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")

    return {
        "success": report["success"],
        "review_dir": review_dir,
        "quality_report_json": report_json,
        "quality_report_md": report_md,
        "contact_sheets": sheets,
        "character_count": len(results),
        "maximum_face_abs_error": max(errors),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="Completed batch artifact root")
    args = parser.parse_args()
    print(json.dumps(build_report(args.root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
