#!/usr/bin/env python3
"""Build and render a resume-safe 10-action first-batch review matrix."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(r"D:\UE\Lance_Work")
ENGINE_ROOT = ROOT / "00_engine"
REGISTRY = (
    ENGINE_ROOT
    / "scripts"
    / "character_creator"
    / "cc_first_batch_action_registry_20260821_v4.json"
)
ACTION_POOL = (
    ENGINE_ROOT
    / "scripts"
    / "character_creator"
    / "cc_first_batch_action_pool_20260824_v1.json"
)
STAGE_RUNNER = (
    ENGINE_ROOT / "scripts" / "unreal" / "run_first_batch_action_matrix_stage.py"
)
SEQUENCE_RUNNER = (
    ENGINE_ROOT / "scripts" / "unreal" / "run_first_batch_20s_sequence.py"
)
PROFILE_RUNNER = (
    ENGINE_ROOT / "scripts" / "unreal" / "run_first_batch_render_profile.py"
)
RENDER_RUNNER = (
    ENGINE_ROOT / "scripts" / "unreal" / "run_first_batch_local_sample_render.py"
)
DEFAULT_OUTPUT = (
    ENGINE_ROOT
    / "outputs"
    / "unreal_render"
    / "first_batch_action_matrix_20260824_v002"
)
SEQUENCE_ROOT = "/Game/DataMake/Sequences/FirstBatch/ActionMatrix"
BASE_MAP = (
    "/Game/DataMake/Scenes/TokyoStylized/"
    "L_DM_TokyoStylized.L_DM_TokyoStylized"
)
MALE_MAP = (
    "/Game/DataMake/Scenes/TokyoStylized/"
    "L_DM_TokyoStylized_MalePilot_v001."
    "L_DM_TokyoStylized_MalePilot_v001"
)
SECTION_PLAN = (0, 1, 2, 3, 1)
EXPRESSION_BY_SECTION = ("happy", "angry", "sad", "happy")
CAMERA_BY_SECTION = ("near", "far", "high", "side")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--render-only", action="store_true")
    return parser.parse_args()


def run_json(command: list[str], timeout: int) -> dict:
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Command failed ({completed.returncode}): {' '.join(command)}\n"
            f"{completed.stdout}\n{completed.stderr}"
        )
    return json.loads(completed.stdout)


def run_render(command: list[str], output_dir: Path, timeout: int) -> dict:
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Render command failed ({completed.returncode}): {' '.join(command)}\n"
            f"{completed.stdout}\n{completed.stderr}"
        )
    report_path = output_dir / "render_report.json"
    if not report_path.is_file():
        raise RuntimeError(
            f"Render completed without a report: {report_path}\n{completed.stdout}"
        )
    return json.loads(report_path.read_text(encoding="utf-8"))


def package_object_path(package_path: str) -> str:
    return f"{package_path}.{package_path.rsplit('/', 1)[-1]}"


def action_slug(action_id: str) -> str:
    return action_id.lower()


def valid_existing_sample(folder: Path) -> dict | None:
    report_path = folder / "render_report.json"
    if not report_path.is_file():
        return None
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if (
        report.get("status") == "passed"
        and report.get("frame_count") == 150
        and report.get("resolution") == [2560, 1440]
        and Path(report.get("video", "")).is_file()
    ):
        return report
    return None


def select_sample_directory(output_root: Path, action_id: str) -> tuple[Path, dict | None]:
    canonical = output_root / action_slug(action_id)
    candidates = [canonical]
    candidates.extend(sorted(output_root.glob(f"{action_slug(action_id)}_retry_*")))
    for candidate in reversed(candidates):
        report = valid_existing_sample(candidate)
        if report is not None:
            return candidate, report
    if not canonical.exists():
        return canonical, None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return output_root / f"{action_slug(action_id)}_retry_{timestamp}", None


def build_contact_sheet(records: list[dict], output: Path) -> None:
    cell_w, image_h, label_h = 640, 360, 82
    columns = 3
    rows = (len(records) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_w, rows * (image_h + label_h)), "#101318")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=20)
    small = ImageFont.load_default(size=16)
    for index, record in enumerate(records):
        column = index % columns
        row = index // columns
        x = column * cell_w
        y = row * (image_h + label_h)
        frame = Path(record["render_report"]["first_frame"])
        frames = sorted(frame.parent.rglob("*.png"))
        middle = frames[len(frames) // 2]
        with Image.open(middle) as source:
            image = source.convert("RGB")
            image.thumbnail((cell_w, image_h), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (cell_w, image_h), "black")
            canvas.paste(image, ((cell_w - image.width) // 2, (image_h - image.height) // 2))
            sheet.paste(canvas, (x, y))
        draw.text((x + 12, y + image_h + 8), record["action_id"], fill="white", font=font)
        draw.text(
            (x + 12, y + image_h + 39),
            f"{record['sex']} | {record['expression']} | camera={record['camera']}",
            fill="#b9c2cf",
            font=small,
        )
    sheet.save(output)


def build_html(records: list[dict], output: Path) -> None:
    cards = []
    for record in records:
        relative_video = Path(record["render_report"]["video"]).relative_to(output.parent).as_posix()
        cards.append(
            "<article><video controls preload='metadata' src='"
            + html.escape(relative_video)
            + "'></video><h2>"
            + html.escape(record["action_id"])
            + "</h2><p>"
            + html.escape(
                f"{record['sex']} | {record['expression']} | camera={record['camera']}"
            )
            + "</p></article>"
        )
    document = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>First Batch 10-Action Matrix</title>
<style>
body{margin:0;background:#101318;color:#eef2f7;font-family:Arial,sans-serif}
header{padding:24px 32px;border-bottom:1px solid #303744}
h1{font-size:24px;margin:0 0 8px}header p,article p{color:#aeb8c6}
main{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:18px;padding:24px}
article{background:#181d25;border:1px solid #303744;padding:12px;border-radius:6px}
video{display:block;width:100%;aspect-ratio:16/9;background:#000}
h2{font-size:16px;margin:12px 0 4px;overflow-wrap:anywhere}article p{margin:0 0 4px}
</style></head><body><header><h1>First Batch 10-Action Matrix</h1>
<p>2560x1440, 30 fps, 5 seconds per sample. Clothing-size clipping is a known deferred first-batch warning.</p>
</header><main>""" + "".join(cards) + "</main></body></html>"
    output.write_text(document, encoding="utf-8")


def main() -> int:
    args = parse_args()
    output_root = args.output_dir.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    pool = json.loads(ACTION_POOL.read_text(encoding="utf-8"))
    by_id = {record["action_id"]: record for record in registry["actions"]}
    active_ids = [
        action_id
        for sex in ("female", "male")
        for action_id in pool["active_actions"][sex]
    ]
    missing = sorted(set(active_ids) - set(by_id))
    if missing:
        raise RuntimeError(f"Active actions missing from registry: {missing}")
    actions = [by_id[action_id] for action_id in active_ids]
    female = [record for record in actions if record["sex"] == "female"]
    male = [record for record in actions if record["sex"] == "male"]
    if len(female) != 5 or len(male) != 5:
        raise RuntimeError(f"Expected 5 female and 5 male actions, found {len(female)} and {len(male)}")

    stage_records = {}
    sequence_records = {}
    if not args.render_only:
        base_stage = run_json([sys.executable, str(STAGE_RUNNER), "base"], 180)
        stage_records["female"] = base_stage
        for action in female:
            package = f"{SEQUENCE_ROOT}/LS_DM_{action['action_id']}_20s_v001"
            sequence_records[action["action_id"]] = run_json(
                [
                    sys.executable,
                    str(SEQUENCE_RUNNER),
                    "--action-id",
                    action["action_id"],
                    "--output-sequence",
                    package,
                    "--target-actor",
                    base_stage["target_actor"],
                    "--no-open",
                ],
                300,
            )
        male_stage = run_json([sys.executable, str(STAGE_RUNNER), "male"], 300)
        stage_records["male"] = male_stage
        for action in male:
            package = f"{SEQUENCE_ROOT}/LS_DM_{action['action_id']}_20s_v001"
            sequence_records[action["action_id"]] = run_json(
                [
                    sys.executable,
                    str(SEQUENCE_RUNNER),
                    "--action-id",
                    action["action_id"],
                    "--output-sequence",
                    package,
                    "--target-actor",
                    male_stage["target_actor"],
                    "--no-open",
                ],
                300,
            )
        run_json([sys.executable, str(STAGE_RUNNER), "base"], 180)

    profile = subprocess.run(
        [sys.executable, str(PROFILE_RUNNER)],
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    if profile.returncode != 0:
        raise RuntimeError(profile.stdout + "\n" + profile.stderr)

    review_records = []
    for sex, sex_actions in (("female", female), ("male", male)):
        map_path = BASE_MAP if sex == "female" else MALE_MAP
        for index, action in enumerate(sex_actions):
            section = SECTION_PLAN[index]
            start = section * 150
            end = start + 150
            package = f"{SEQUENCE_ROOT}/LS_DM_{action['action_id']}_20s_v001"
            sequence_path = package_object_path(package)
            sample_dir, render_report = select_sample_directory(
                output_root, action["action_id"]
            )
            if render_report is None:
                render_report = run_render(
                    [
                        sys.executable,
                        str(RENDER_RUNNER),
                        "--output-dir",
                        str(sample_dir),
                        "--map-path",
                        map_path,
                        "--sequence-path",
                        sequence_path,
                        "--start-frame",
                        str(start),
                        "--end-frame",
                        str(end),
                        "--job-name",
                        f"DM_{action['action_id']}_5s_v001",
                        "--timeout-seconds",
                        str(args.timeout_seconds),
                        "--skip-profile",
                    ],
                    sample_dir,
                    args.timeout_seconds + 600,
                )
            review_records.append(
                {
                    "action_id": action["action_id"],
                    "sex": sex,
                    "section_index": section,
                    "camera": CAMERA_BY_SECTION[section],
                    "expression": EXPRESSION_BY_SECTION[section],
                    "map": map_path,
                    "sequence": sequence_path,
                    "render_report": render_report,
                }
            )

    contact_sheet = output_root / "action_matrix_contact_sheet.png"
    review_html = output_root / "index.html"
    build_contact_sheet(review_records, contact_sheet)
    build_html(review_records, review_html)
    aggregate = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "technical_render_passed_pending_human_visual_review",
        "registry": str(REGISTRY),
        "sample_count": len(review_records),
        "resolution": [2560, 1440],
        "fps": 30,
        "duration_seconds_per_sample": 5.0,
        "known_first_batch_warning": (
            "Some Look/action pairs may show clothing-body or hair-clothing "
            "intersections. Clothing sizing and compatibility correction is deferred."
        ),
        "stage_records": stage_records,
        "sequence_records": sequence_records,
        "samples": review_records,
        "contact_sheet": str(contact_sheet),
        "review_html": str(review_html),
    }
    report_path = output_root / "action_matrix_report.json"
    report_path.write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": aggregate["status"],
        "sample_count": aggregate["sample_count"],
        "report": str(report_path),
        "contact_sheet": str(contact_sheet),
        "review_html": str(review_html),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
