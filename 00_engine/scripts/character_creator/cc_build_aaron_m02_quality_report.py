import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


CAPTURES = (
    ("neutral_front", "Neutral front", "static"),
    ("neutral_three_quarter", "Three-quarter", "static"),
    ("neutral_profile", "Profile", "static"),
    ("full_body_front", "Full body", "static"),
    ("blink_bilateral_front", "Blink", "dynamic"),
    ("smile_front", "Smile", "dynamic"),
    ("jaw_open_front", "Jaw open", "dynamic"),
)


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(value, path):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path):
    with Image.open(path) as image:
        size = list(image.size)
        mode = image.mode
    return {
        "path": str(path),
        "bytes": os.path.getsize(path),
        "sha256": sha256_file(path),
        "pixel_size": size,
        "mode": mode,
    }


def font(size, bold=False):
    candidates = (
        Path("C:/Windows/Fonts/arialbd.ttf") if bold else None,
        Path("C:/Windows/Fonts/arial.ttf"),
    )
    for candidate in candidates:
        if candidate and candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def capture_path(report, capture_id, capture_kind):
    key = "static_captures" if capture_kind == "static" else "dynamic_captures"
    record = report[key][capture_id]
    path = record["path"]
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    return path


def build_contact_sheet(subjects, captures, output_path, cell_size=440):
    row_label_width = 190
    column_header_height = 72
    row_height = cell_size + 42
    width = row_label_width + (len(captures) * cell_size)
    height = column_header_height + (len(subjects) * row_height)
    background = (18, 21, 27)
    panel = (29, 34, 42)
    border = (67, 74, 85)
    text_color = (238, 241, 245)
    secondary = (171, 179, 190)
    sheet = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(sheet)
    header_font = font(24, bold=True)
    row_font = font(25, bold=True)
    sub_font = font(18)

    for column, unused_capture_id, label, unused_kind in (
        (index, capture_id, label, kind)
        for index, (capture_id, label, kind) in enumerate(captures)
    ):
        x0 = row_label_width + (column * cell_size)
        draw.rectangle(
            (x0, 0, x0 + cell_size - 1, column_header_height - 1),
            fill=panel,
            outline=border,
        )
        bbox = draw.textbbox((0, 0), label, font=header_font)
        text_width = bbox[2] - bbox[0]
        draw.text(
            (x0 + ((cell_size - text_width) / 2), 22),
            label,
            font=header_font,
            fill=text_color,
        )

    for row, subject in enumerate(subjects):
        y0 = column_header_height + (row * row_height)
        draw.rectangle(
            (0, y0, row_label_width - 1, y0 + row_height - 1),
            fill=panel,
            outline=border,
        )
        draw.text(
            (22, y0 + 28),
            subject["label"],
            font=row_font,
            fill=text_color,
        )
        draw.text(
            (22, y0 + 68),
            subject["subtitle"],
            font=sub_font,
            fill=secondary,
        )
        for column, (capture_id, unused_label, capture_kind) in enumerate(captures):
            x0 = row_label_width + (column * cell_size)
            image_path = capture_path(
                subject["report"], capture_id, capture_kind
            )
            with Image.open(image_path) as source:
                source = source.convert("RGB")
                fitted = ImageOps.contain(
                    source, (cell_size - 12, cell_size - 12), Image.Resampling.LANCZOS
                )
            tile = Image.new("RGB", (cell_size, cell_size), background)
            tile.paste(
                fitted,
                ((cell_size - fitted.width) // 2, (cell_size - fitted.height) // 2),
            )
            sheet.paste(tile, (x0, y0))
            draw.rectangle(
                (x0, y0, x0 + cell_size - 1, y0 + cell_size - 1),
                outline=border,
                width=1,
            )
            draw.text(
                (x0 + 10, y0 + cell_size + 10),
                capture_id,
                font=sub_font,
                fill=secondary,
            )
    sheet.save(output_path, format="PNG", optimize=True)


def selected_pose_records(report):
    validation_path = report["facial_pose_validation"]["path"]
    validation = read_json(validation_path)
    by_id = dict((item["pose_id"], item) for item in validation["poses"])
    return {
        pose_id: {
            "frame": by_id[pose_id].get("frame"),
            "target_weights": by_id[pose_id]["target_weights"],
            "evaluated_expression_weights": by_id[pose_id][
                "evaluated_expression_weights"
            ],
            "rmse_from_post_pose_neutral": next(
                item["rmse"]
                for item in validation["evidence_liveness"]["poses"]
                if item["pose_id"] == pose_id
            ),
        }
        for pose_id in (
            "blink_bilateral_front",
            "smile_front",
            "jaw_open_front",
        )
    }


def subject_record(label, report_path, report):
    captures = {}
    for capture_id, unused_label, capture_kind in CAPTURES:
        path = capture_path(report, capture_id, capture_kind)
        captures[capture_id] = file_record(path)
    subject = report["subject"]
    return {
        "label": label,
        "report_path": str(report_path),
        "subject_id": report["subject_id"],
        "benchmark_strategy": report["benchmark_strategy"],
        "height_cm": subject["height_cm"],
        "asset_count": subject["asset_inventory"]["object_count"],
        "avatar_part_count": subject["avatar_part_inventory"]["part_count"],
        "mesh_count": subject["material_fingerprint"]["mesh_count"],
        "material_count": subject["material_fingerprint"]["material_count"],
        "expression_count": subject["facial_profile"]["expression_count"],
        "restoration": report["restoration"],
        "pose_records": selected_pose_records(report),
        "captures": captures,
    }


def matched_conditions(aaron, m02):
    keys = (
        "preview_capture_mode",
        "preview_resolution",
        "face_camera",
        "preview_lightroom",
        "face_position",
        "full_body_position",
        "pose_ids",
    )
    comparisons = {}
    for key in keys:
        comparisons[key] = {
            "aaron": aaron["conditions"].get(key),
            "m02": m02["conditions"].get(key),
            "matches": (
                aaron["conditions"].get(key)
                == m02["conditions"].get(key)
            ),
        }
    return {
        "all_matched": all(item["matches"] for item in comparisons.values()),
        "comparisons": comparisons,
        "expression_state_check": (
            "Target and evaluated weights are recorded per subject; "
            "temporary clip implementation may differ."
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--aaron-report", required=True)
    parser.add_argument("--m02-report", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--assessment-file")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    if output_dir.exists() and not args.overwrite:
        raise FileExistsError(
            "Output directory already exists; pass --overwrite to rebuild known outputs: "
            + str(output_dir)
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    aaron_report_path = Path(args.aaron_report)
    m02_report_path = Path(args.m02_report)
    aaron = read_json(aaron_report_path)
    m02 = read_json(m02_report_path)
    assessment = (
        read_json(Path(args.assessment_file))
        if args.assessment_file
        else {"status": "pending_manual_visual_review"}
    )
    subjects = (
        {
            "label": "Aaron",
            "subtitle": "Official baseline",
            "report": aaron,
        },
        {
            "label": "M02",
            "subtitle": "Current factory output",
            "report": m02,
        },
    )
    sheet_specs = (
        ("aaron_m02_contact_sheet.png", CAPTURES, 420),
        ("aaron_m02_geometry_sheet.png", CAPTURES[:4], 520),
        (
            "aaron_m02_expression_sheet.png",
            (CAPTURES[0], CAPTURES[4], CAPTURES[5], CAPTURES[6]),
            520,
        ),
    )
    sheet_records = {}
    for filename, captures, cell_size in sheet_specs:
        path = output_dir / filename
        build_contact_sheet(subjects, captures, path, cell_size=cell_size)
        sheet_records[filename] = file_record(path)

    report = {
        "schema_version": 1,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "comparison_id": output_dir.name,
        "matched_conditions": matched_conditions(aaron, m02),
        "subjects": {
            "aaron": subject_record(
                "Aaron official", aaron_report_path, aaron
            ),
            "m02": subject_record("M02 current", m02_report_path, m02),
        },
        "contact_sheets": sheet_records,
        "qualitative_assessment": assessment,
    }
    report_path = output_dir / "aaron_m02_quality_benchmark.json"
    write_json(report, report_path)
    print(str(report_path))


if __name__ == "__main__":
    main()
