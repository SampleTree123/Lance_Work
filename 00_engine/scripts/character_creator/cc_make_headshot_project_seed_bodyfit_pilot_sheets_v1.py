"""Build review sheets for the Headshot project-seed + BodyFit pilot."""

from __future__ import annotations

import argparse
import datetime
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


CASE_IDS = {
    "female": "F_HS_002_H00_BASELINE_F02_Average",
    "male": "M_HS_002_H00_BASELINE_M02_Average",
}
ASSEMBLY_VIEWS = (
    ("bodyfit_reference_full_body", "BodyFit reference", "lit"),
    ("assembled_full_body", "Assembled full body", "lit"),
    ("identity_source_front", "Headshot identity source", "machine"),
    ("assembled_face_front", "Assembled neutral", "machine"),
    ("assembled_face_three_quarter", "Assembled three-quarter", "machine"),
    ("assembled_face_profile", "Assembled profile", "machine"),
)
DYNAMIC_VIEWS = (
    ("post_pose_neutral_front", "Neutral restored"),
    ("blink_bilateral_front", "Blink"),
    ("smile_subtle_front", "Subtle smile"),
    ("smile_medium_front", "Medium smile"),
    ("smile_broad_front", "Broad smile"),
    ("jaw_open_front", "Jaw open"),
)
RELOAD_VIEWS = (
    ("identity_source_front", "Identity source", "machine"),
    ("assembled_face_front", "Before save", "machine"),
    ("reloaded_neutral_front", "After reload", "machine"),
    ("post_pose_neutral_front", "After pose reset", "dynamic"),
)


class ReviewError(RuntimeError):
    pass


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")
    os.replace(temporary, path)


def write_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def font(size: int, bold: bool = False):
    candidates = (
        Path(os.environ.get("WINDIR", r"C:\Windows"))
        / "Fonts"
        / ("arialbd.ttf" if bold else "arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
        if bold
        else Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    )
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def existing_image(path_value: str | None, label: str) -> Path:
    if not isinstance(path_value, str) or not path_value:
        raise ReviewError("Missing {} path".format(label))
    path = Path(path_value).resolve()
    if not path.is_file() or path.stat().st_size <= 0:
        raise ReviewError("Missing {}: {}".format(label, path))
    return path


def fitted_image(path: Path, size: tuple[int, int]) -> Image.Image:
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
    contained = ImageOps.contain(image, size, method=Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, (18, 21, 26))
    canvas.paste(
        contained,
        ((size[0] - contained.width) // 2, (size[1] - contained.height) // 2),
    )
    return canvas


def render_grid(
    title: str,
    records: list[tuple[str, Path]],
    output_path: Path,
    columns: int,
    cell_size: tuple[int, int] = (540, 540),
) -> None:
    rows = (len(records) + columns - 1) // columns
    title_height = 72
    label_height = 54
    width = columns * cell_size[0]
    height = title_height + rows * (cell_size[1] + label_height)
    sheet = Image.new("RGB", (width, height), (18, 21, 26))
    draw = ImageDraw.Draw(sheet)
    draw.text((20, 17), title, fill=(242, 244, 247), font=font(27, True))
    for index, (label, image_path) in enumerate(records):
        row, column = divmod(index, columns)
        x = column * cell_size[0]
        y = title_height + row * (cell_size[1] + label_height)
        sheet.paste(fitted_image(image_path, cell_size), (x, y))
        draw.rectangle(
            (x, y + cell_size[1], x + cell_size[0], y + cell_size[1] + label_height),
            fill=(29, 33, 40),
        )
        draw.text(
            (x + 15, y + cell_size[1] + 14),
            label,
            fill=(220, 224, 230),
            font=font(19, True),
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=True)


def indexed_results(validation: dict) -> dict[str, dict]:
    results = validation.get("results") or []
    indexed = {}
    for record in results:
        preset_id = record.get("preset_id")
        if not isinstance(preset_id, str) or not preset_id or preset_id in indexed:
            raise ReviewError("Machine validation has invalid or duplicate preset IDs")
        indexed[preset_id] = record
    return indexed


def validate_machine_result(record: dict, expected_sex: str) -> None:
    if record.get("success") is not True or record.get("sex") != expected_sex:
        raise ReviewError("Machine result failed for {}".format(expected_sex))
    gate = record.get("dynamic_pose_gate") or {}
    if (
        gate.get("expression_set_uid") != "CC5 MetaHuman"
        or gate.get("expression_count") != 379
        or gate.get("pose_count") != 5
        or (gate.get("neutral_eye_integrity") or {}).get("matches") is not True
    ):
        raise ReviewError("Dynamic gate is incomplete for {}".format(expected_sex))
    if (record.get("reload") or {}).get("passed") is not True:
        raise ReviewError("Saved-project reload failed for {}".format(expected_sex))


def validate_lit_result(record: dict, expected_id: str, expected_sex: str) -> None:
    if (
        record.get("success") is not True
        or record.get("preset_id") != expected_id
        or record.get("sex") != expected_sex
    ):
        raise ReviewError("Lit capture result failed for {}".format(expected_sex))
    lighting = (record.get("rendering") or {}).get(
        "assembled_full_body_lighting"
    ) or {}
    if (
        lighting.get("policy")
        != "translate_movable_lights_with_full_body_subject"
        or int(lighting.get("movable_light_count", 0)) <= 0
    ):
        raise ReviewError("Lit capture policy is missing for {}".format(expected_sex))


def artifact_paths(record: dict, keys: tuple[str, ...], label: str) -> dict[str, Path]:
    artifacts = record.get("artifacts") or {}
    return {
        key: existing_image(artifacts.get(key), "{} {}".format(label, key))
        for key in keys
    }


def dynamic_paths(record: dict, label: str) -> dict[str, Path]:
    directory_value = (record.get("artifacts") or {}).get("dynamic_directory")
    if not directory_value:
        raise ReviewError("Missing dynamic directory for {}".format(label))
    directory = Path(directory_value).resolve()
    return {
        pose_id: existing_image(
            str(directory / (pose_id + ".png")),
            "{} {}".format(label, pose_id),
        )
        for pose_id, unused_label in DYNAMIC_VIEWS
    }


def create_review(
    machine_validation_path: Path,
    female_lit_result_path: Path,
    male_lit_result_path: Path,
    output_dir: Path,
) -> dict:
    machine_validation_path = machine_validation_path.resolve()
    female_lit_result_path = female_lit_result_path.resolve()
    male_lit_result_path = male_lit_result_path.resolve()
    output_dir = output_dir.resolve()
    validation = read_json(machine_validation_path)
    if (
        validation.get("success") is not True
        or validation.get("success_count") != 2
        or validation.get("failure_count") != 0
    ):
        raise ReviewError("Complete two-case machine validation did not pass")
    machine_results = indexed_results(validation)
    lit_results = {
        "female": read_json(female_lit_result_path),
        "male": read_json(male_lit_result_path),
    }
    groups = []
    for sex in ("female", "male"):
        preset_id = CASE_IDS[sex]
        if preset_id not in machine_results:
            raise ReviewError("Missing machine case {}".format(preset_id))
        machine = machine_results[preset_id]
        lit = lit_results[sex]
        validate_machine_result(machine, sex)
        validate_lit_result(lit, preset_id, sex)
        machine_images = artifact_paths(
            machine,
            (
                "identity_source_front",
                "assembled_face_front",
                "assembled_face_three_quarter",
                "assembled_face_profile",
                "reloaded_neutral_front",
            ),
            preset_id,
        )
        lit_images = artifact_paths(
            lit,
            ("bodyfit_reference_full_body", "assembled_full_body"),
            preset_id,
        )
        dynamic_images = dynamic_paths(machine, preset_id)
        assembly_sheet = output_dir / sex / "assembly_overview.png"
        dynamic_sheet = output_dir / sex / "dynamic_overview.png"
        reload_sheet = output_dir / sex / "reload_overview.png"
        render_grid(
            "{} Headshot seed + BodyFit assembly".format(sex.title()),
            [
                (
                    label,
                    lit_images[key] if source == "lit" else machine_images[key],
                )
                for key, label, source in ASSEMBLY_VIEWS
            ],
            assembly_sheet,
            columns=3,
        )
        render_grid(
            "{} dynamic facial gate".format(sex.title()),
            [(label, dynamic_images[key]) for key, label in DYNAMIC_VIEWS],
            dynamic_sheet,
            columns=3,
        )
        reload_sources = {
            **machine_images,
            **dynamic_images,
        }
        render_grid(
            "{} identity, reload, and neutral restoration".format(sex.title()),
            [(label, reload_sources[key]) for key, label, unused in RELOAD_VIEWS],
            reload_sheet,
            columns=4,
            cell_size=(440, 440),
        )
        groups.append(
            {
                "sex": sex,
                "preset_id": preset_id,
                "sheets": {
                    "assembly": str(assembly_sheet),
                    "dynamic": str(dynamic_sheet),
                    "reload": str(reload_sheet),
                },
                "views": {
                    **{key: str(value) for key, value in machine_images.items()},
                    **{key: str(value) for key, value in dynamic_images.items()},
                    **{key: str(value) for key, value in lit_images.items()},
                },
                "machine_gate": {
                    "expression_count": 379,
                    "expression_set_uid": "CC5 MetaHuman",
                    "neutral_eye_integrity": True,
                    "pose_count": 5,
                    "reload_success": True,
                },
                "lit_capture": {
                    "lighting_policy": (
                        (lit.get("rendering") or {})
                        .get("assembled_full_body_lighting", {})
                        .get("policy")
                    ),
                    "result": str(
                        female_lit_result_path if sex == "female" else male_lit_result_path
                    ),
                },
            }
        )
    index = {
        "schema_version": 1,
        "review_id": "headshot_project_seed_bodyfit_pilot_review_20260810_v1",
        "generated_at": datetime.datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
        "status": "pending_review",
        "production_approved": False,
        "case_count": 2,
        "machine_validation": str(machine_validation_path),
        "machine_validation_run": "run_20260810_v4",
        "visual_source_policy": (
            "Face, dynamic-pose, and reload evidence comes from the complete "
            "2/2 machine run. Full-body evidence comes from the later light-"
            "translated single-case captures."
        ),
        "groups": groups,
        "known_evidence_note": (
            "The female lit case completed successfully, but its parent bridge "
            "request failed after case completion while writing the top-level "
            "summary. The summary scope defect was fixed and regression-tested; "
            "the male explicit-subset request then completed successfully."
        ),
    }
    write_json(index, output_dir / "index.json")
    write_text(
        "\n".join(
            [
                "# Headshot Project-Seed + BodyFit Pilot Review",
                "",
                "Machine gate: passed 2/2 cases. Production approval remains pending human visual review.",
                "",
                "Review order:",
                "",
                "1. Compare the gray BodyFit reference with the assembled full body.",
                "2. Check identity continuity across front, three-quarter, and profile views.",
                "3. Inspect blink closure, smiles, jaw opening, teeth/lip clearance, and eye placement.",
                "4. Compare before-save, after-reload, and post-pose neutral images.",
                "",
                "The complete machine authority is `run_20260810_v4`; corrected full-body lighting is a visual derivative only.",
                "",
            ]
        ),
        output_dir / "README.md",
    )
    return index


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create Headshot project-seed + BodyFit pilot review sheets"
    )
    parser.add_argument("--machine-validation", type=Path, required=True)
    parser.add_argument("--female-lit-result", type=Path, required=True)
    parser.add_argument("--male-lit-result", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    index = create_review(
        args.machine_validation,
        args.female_lit_result,
        args.male_lit_result,
        args.output_dir,
    )
    print("Created {} review cases -> {}".format(index["case_count"], args.output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
