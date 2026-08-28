#!/usr/bin/env python3
"""Stage and render the frozen First Batch matrix with resume support."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat


ROOT = Path(__file__).resolve().parents[3]
ENGINE_ROOT = ROOT / "00_engine"
REMOTE_EXEC = ENGINE_ROOT / "scripts" / "unreal" / "ue_remote_exec.py"
STAGE_SCRIPT = (
    ENGINE_ROOT / "scripts" / "unreal" / "ue_stage_first_batch_render_look.py"
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
DEFAULT_CONFIG = (
    ENGINE_ROOT
    / "scripts"
    / "unreal"
    / "first_batch_local_render_matrix_20260824_v1.json"
)
DEFAULT_OUTPUT = (
    ENGINE_ROOT
    / "outputs"
    / "unreal_render"
    / "first_batch_32look_matrix_20260824_v002"
)
MIN_FREE_BYTES = 40 * 1024**3
MIN_TEMPORAL_MEAN_ABS_DIFF = 2.0
DEFAULT_PROJECT_NAME = os.environ.get("DM_UE_PROJECT_NAME", "datatry_02")
DEFAULT_UE_ENGINE_ROOT = (
    Path(os.environ["DM_UE_ENGINE_ROOT"])
    if os.environ.get("DM_UE_ENGINE_ROOT")
    else None
)
_remote_project_name = DEFAULT_PROJECT_NAME
_remote_engine_root = DEFAULT_UE_ENGINE_ROOT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--project-name", default=None)
    parser.add_argument("--engine-root", type=Path, default=DEFAULT_UE_ENGINE_ROOT)
    parser.add_argument("--start-index", type=int, default=1)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--audit-existing",
        action="store_true",
        help="Validate and backfill rendered media contracts without connecting to UE.",
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Stage and build sequences but do not start MRQ.",
    )
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_command(command: list[str], timeout: int) -> subprocess.CompletedProcess:
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
    return completed


def configure_remote(project_name: str, engine_root: Path | None = None) -> None:
    global _remote_project_name, _remote_engine_root
    _remote_project_name = project_name
    _remote_engine_root = engine_root.resolve() if engine_root is not None else None
    os.environ["DM_UE_PROJECT_NAME"] = project_name
    if _remote_engine_root is not None:
        os.environ["DM_UE_ENGINE_ROOT"] = str(_remote_engine_root)


def remote(command: str, timeout: int = 180) -> dict:
    remote_command = [
        sys.executable,
        str(REMOTE_EXEC),
        "--project",
        _remote_project_name,
        "--discovery-timeout",
        "30",
        "--command",
        command,
    ]
    if _remote_engine_root is not None:
        remote_command.extend(["--engine-root", str(_remote_engine_root)])
    completed = run_command(remote_command, timeout)
    envelope = json.loads(completed.stdout)
    result = envelope.get("command_result", {})
    if not result.get("success"):
        raise RuntimeError(f"Unreal command failed: {result}")
    return result


def tagged(result: dict, prefix: str) -> dict:
    values = [
        json.loads(str(item["output"])[len(prefix) :])
        for item in result.get("output", [])
        if str(item.get("output", "")).startswith(prefix)
    ]
    if len(values) != 1:
        raise RuntimeError(f"Expected one {prefix} record, found {len(values)}")
    return values[0]


def ensure_stage_map(config: dict) -> dict:
    source = config["unreal"]["source_map_package"]
    target = config["unreal"]["staging_map_package"]
    command = (
        "import unreal, json; "
        f"source={source!r}; target={target!r}; "
        "exists=unreal.EditorAssetLibrary.does_asset_exist(target); "
        "asset=None if exists else unreal.EditorAssetLibrary.duplicate_asset(source,target); "
        "created=not exists; ok=exists or asset is not None; "
        "saved=unreal.EditorAssetLibrary.save_asset(target, only_if_is_dirty=False) if ok else False; "
        "asset=None; unreal.SystemLibrary.collect_garbage(); "
        "print('DM_RENDER_STAGE_MAP=' + json.dumps({"
        "'source':source,'target':target,'created':created,'ok':ok,'saved':saved}))"
    )
    report = tagged(remote(command, 300), "DM_RENDER_STAGE_MAP=")
    if not report["ok"] or not report["saved"]:
        raise RuntimeError(f"Unable to ensure staging map: {report}")
    return report


def stage_look(config: dict, row: dict) -> dict:
    script = str(STAGE_SCRIPT.resolve())
    command = (
        f"DM_STAGE_MAP={config['unreal']['staging_map_package']!r}; "
        f"DM_LOOK_ID={row['look_id']!r}; "
        f"DM_BLUEPRINT_CLASS={row['character_blueprint_class']!r}; "
        f"exec(compile(open({script!r}, 'r', encoding='utf-8').read(), "
        f"{script!r}, 'exec'))"
    )
    return tagged(remote(command, 420), "DM_FIRST_BATCH_LOOK_STAGED=")


def build_sequence(config: dict, row: dict, actor_name: str) -> dict:
    command = [
        sys.executable,
        str(SEQUENCE_RUNNER),
        "--project-name",
        _remote_project_name,
        "--action-id",
        row["action_id"],
        "--source-sequence",
        config["unreal"]["source_sequence_package"],
        "--output-sequence",
        config["unreal"]["workspace_sequence_package"],
        "--target-actor",
        actor_name,
        "--expression",
        row["expression_id"],
        "--no-open",
    ]
    if _remote_engine_root is not None:
        command.extend(["--engine-root", str(_remote_engine_root)])
    action_contract = row.get("action_contract")
    if action_contract is not None:
        command.extend(
            [
                "--action-contract-json",
                json.dumps(
                    action_contract,
                    ensure_ascii=True,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            ]
        )
    completed = run_command(
        command,
        420,
    )
    return json.loads(completed.stdout)


def valid_render(folder: Path, row: dict) -> dict | None:
    report_path = folder / "render_report.json"
    if not report_path.is_file():
        return None
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    video = Path(report.get("video", ""))
    automation = report.get("automation_contract", {})
    pose_driver = automation.get("pose_driver_contract", {})
    temporal_motion = automation.get("temporal_motion_contract", {})
    if (
        report.get("status") == "passed"
        and report.get("frame_count") == 150
        and report.get("resolution") == [2560, 1440]
        and report.get("fps") == 30
        and report.get("start_frame_inclusive") == row["start_frame_inclusive"]
        and report.get("end_frame_exclusive") == row["end_frame_exclusive"]
        and video.is_file()
        and video.stat().st_size > 0
        and automation.get("sample_id") == row["sample_id"]
        and automation.get("look_id") == row["look_id"]
        and automation.get("action_id") == row["action_id"]
        and pose_driver.get("passed") is True
        and temporal_motion.get("passed") is True
    ):
        return report
    return None


def select_output_folder(root: Path, row: dict) -> tuple[Path, dict | None]:
    canonical = root / row["output_relative_directory"]
    candidates = [canonical, *sorted(root.glob(canonical.name + "_retry_*"))]
    for folder in reversed(candidates):
        report = valid_render(folder, row)
        if report is not None:
            return folder, report
    if not canonical.exists():
        return canonical, None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return root / f"{canonical.name}_retry_{timestamp}", None


def pose_driver_contract(sequence_report: dict) -> dict:
    sections = sequence_report.get("animation_sections", [])
    checks = {
        "force_custom_mode_required": (
            sequence_report.get("force_custom_mode_required") is True
        ),
        "four_animation_sections": len(sections) == 4,
        "all_sections_force_custom_mode": (
            len(sections) == 4
            and all(section.get("force_custom_mode") is True for section in sections)
        ),
        "native_actor_binding": (
            sequence_report.get("animation_binding_type") == "native_actor_binding"
        ),
        "target_actor_recorded": bool(sequence_report.get("target_actor")),
    }
    return {"checks": checks, "passed": all(checks.values())}


def temporal_motion_contract(folder: Path, expected_frames: int = 150) -> dict:
    frames = sorted(folder.glob("frame_*.png"))
    checks = {
        "expected_frame_count": len(frames) == expected_frames,
        "sample_frames_readable": False,
        "visible_temporal_change": False,
    }
    sample_indices: list[int] = []
    differences: list[float] = []
    if frames:
        sample_indices = sorted(
            {
                0,
                len(frames) // 4,
                len(frames) // 2,
                3 * len(frames) // 4,
                len(frames) - 1,
            }
        )
        try:
            with Image.open(frames[sample_indices[0]]) as source:
                baseline = source.convert("L").resize((320, 180))
            for index in sample_indices[1:]:
                with Image.open(frames[index]) as source:
                    current = source.convert("L").resize((320, 180))
                difference = ImageChops.difference(baseline, current)
                differences.append(float(ImageStat.Stat(difference).mean[0]))
            checks["sample_frames_readable"] = (
                len(differences) == len(sample_indices) - 1
            )
        except (OSError, ValueError):
            differences = []
    maximum = max(differences, default=0.0)
    checks["visible_temporal_change"] = maximum >= MIN_TEMPORAL_MEAN_ABS_DIFF
    return {
        "schema_version": 1,
        "sample_indices": sample_indices,
        "mean_abs_differences_from_first": [
            round(value, 6) for value in differences
        ],
        "maximum_mean_abs_difference": round(maximum, 6),
        "minimum_required": MIN_TEMPORAL_MEAN_ABS_DIFF,
        "checks": checks,
        "passed": all(checks.values()),
    }


def render_case(
    config: dict,
    row: dict,
    folder: Path,
    timeout: int,
    sequence_report: dict,
) -> dict:
    pose_contract = pose_driver_contract(sequence_report)
    if not pose_contract["passed"]:
        raise RuntimeError(
            "Refusing to render a sequence that can fall back to T-pose: "
            f"{pose_contract}"
        )
    command = [
        sys.executable,
        str(RENDER_RUNNER),
        "--project-name",
        _remote_project_name,
        "--output-dir",
        str(folder),
        "--map-path",
        config["unreal"]["staging_map_object"],
        "--sequence-path",
        config["unreal"]["workspace_sequence_object"],
        "--start-frame",
        str(row["start_frame_inclusive"]),
        "--end-frame",
        str(row["end_frame_exclusive"]),
        "--job-name",
        row["sample_id"],
        "--timeout-seconds",
        str(timeout),
        "--skip-profile",
    ]
    if _remote_engine_root is not None:
        command.extend(["--engine-root", str(_remote_engine_root)])
    run_command(
        command,
        timeout + 900,
    )
    report_path = folder / "render_report.json"
    if not report_path.is_file():
        raise RuntimeError(f"Render report is missing: {report_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["automation_contract"] = {
        "schema_version": 1,
        "sample_id": row["sample_id"],
        "look_id": row["look_id"],
        "action_id": row["action_id"],
        "expression_id": row["expression_id"],
        "camera_id": row["camera_id"],
        "sequence": sequence_report.get("output_sequence"),
        "pose_driver_contract": pose_contract,
        "temporal_motion_contract": temporal_motion_contract(folder),
    }
    if not report["automation_contract"]["temporal_motion_contract"]["passed"]:
        report["status"] = "failed_temporal_motion"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report = valid_render(folder, row)
    if report is None:
        raise RuntimeError(f"Render did not pass automation validation: {folder}")
    return report


def audit_existing_matrix(output_root: Path, rows: list[dict]) -> dict:
    records = []
    validated_reports: dict[str, dict] = {}
    for row in rows:
        canonical = output_root / row["output_relative_directory"]
        candidates = [canonical, *sorted(output_root.glob(canonical.name + "_retry_*"))]
        selected_folder = None
        selected_report = None
        for folder in reversed(candidates):
            report_path = folder / "render_report.json"
            if not report_path.is_file():
                continue
            report = json.loads(report_path.read_text(encoding="utf-8"))
            automation = report.setdefault("automation_contract", {})
            automation["temporal_motion_contract"] = temporal_motion_contract(folder)
            report_path.write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            validated = valid_render(folder, row)
            if validated is not None:
                selected_folder = folder
                selected_report = validated
                validated_reports[row["sample_id"]] = validated
                break
        records.append(
            {
                "sample_id": row["sample_id"],
                "status": "passed" if selected_report is not None else "failed",
                "folder": str(selected_folder) if selected_folder else None,
                "temporal_motion_contract": (
                    selected_report["automation_contract"]["temporal_motion_contract"]
                    if selected_report is not None
                    else None
                ),
            }
        )
    result = {
        "schema_version": 1,
        "created_at_utc": utc_now(),
        "status": (
            "passed" if all(row["status"] == "passed" for row in records) else "failed"
        ),
        "output_root": str(output_root),
        "sample_count": len(records),
        "passed_count": sum(row["status"] == "passed" for row in records),
        "failed_count": sum(row["status"] == "failed" for row in records),
        "minimum_temporal_mean_abs_difference": min(
            (
                row["temporal_motion_contract"]["maximum_mean_abs_difference"]
                for row in records
                if row["temporal_motion_contract"] is not None
            ),
            default=0.0,
        ),
        "records": records,
    }
    audit_path = output_root / "matrix_motion_audit.json"
    audit_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    state_path = output_root / "matrix_state.json"
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        for record in state.get("records", []):
            sample_id = record.get("config", {}).get("sample_id")
            if sample_id in validated_reports:
                record["render_report"] = validated_reports[sample_id]
        state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    aggregate_path = output_root / "matrix_report.json"
    if aggregate_path.is_file():
        aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
        aggregate["motion_audit"] = {
            "status": result["status"],
            "path": str(audit_path),
            "passed_count": result["passed_count"],
            "failed_count": result["failed_count"],
            "minimum_temporal_mean_abs_difference": result[
                "minimum_temporal_mean_abs_difference"
            ],
        }
        aggregate_path.write_text(
            json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return result


def write_state(path: Path, config_path: Path, records: list[dict], status: str) -> None:
    payload = {
        "schema_version": 1,
        "updated_at_utc": utc_now(),
        "status": status,
        "config": str(config_path),
        "completed_count": sum(row.get("status") == "passed" for row in records),
        "records": records,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_contact_sheet(records: list[dict], output: Path) -> None:
    passed = [row for row in records if row.get("status") == "passed"]
    if not passed:
        return
    cell_w, image_h, label_h, columns = 480, 270, 74, 4
    rows = (len(passed) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_w, rows * (image_h + label_h)), "#101318")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=16)
    small = ImageFont.load_default(size=13)
    for index, record in enumerate(passed):
        x = index % columns * cell_w
        y = index // columns * (image_h + label_h)
        frames = sorted(Path(record["render_report"]["first_frame"]).parent.rglob("*.png"))
        with Image.open(frames[len(frames) // 2]) as source:
            image = source.convert("RGB")
            image.thumbnail((cell_w, image_h), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (cell_w, image_h), "black")
            canvas.paste(image, ((cell_w - image.width) // 2, (image_h - image.height) // 2))
            sheet.paste(canvas, (x, y))
        row = record["config"]
        draw.text((x + 8, y + image_h + 6), row["look_id"], fill="white", font=font)
        draw.text(
            (x + 8, y + image_h + 31),
            f"{row['action_id']} | {row['camera_id']} | {row['expression_id']}",
            fill="#b9c2cf",
            font=small,
        )
    sheet.save(output)


def build_html(records: list[dict], output: Path) -> None:
    cards = []
    for record in records:
        if record.get("status") != "passed":
            continue
        row = record["config"]
        video = Path(record["render_report"]["video"]).relative_to(output.parent).as_posix()
        cards.append(
            "<article><video controls preload='metadata' src='"
            + html.escape(video)
            + "'></video><h2>"
            + html.escape(row["look_id"])
            + "</h2><p>"
            + html.escape(
                f"{row['action_id']} | {row['camera_id']} | {row['expression_id']}"
            )
            + "</p></article>"
        )
    document = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>First Batch 32-Look Render Matrix</title><style>
body{margin:0;background:#101318;color:#eef2f7;font-family:Arial,sans-serif}
header{padding:22px 28px;border-bottom:1px solid #303744}h1{font-size:24px;margin:0 0 6px}
header p,article p{color:#aeb8c6}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:16px;padding:20px}
article{background:#181d25;border:1px solid #303744;padding:10px;border-radius:6px}video{width:100%;aspect-ratio:16/9;background:#000}
h2{font-size:16px;margin:10px 0 4px}article p{margin:0 0 4px;overflow-wrap:anywhere}</style></head><body>
<header><h1>First Batch 32-Look Render Matrix</h1><p>2560x1440, 30 fps, 5 seconds. Expressions are rendered variation, not an edit axis.</p></header><main>""" + "".join(cards) + "</main></body></html>"
    output.write_text(document, encoding="utf-8")


def main() -> int:
    args = parse_args()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    configure_remote(
        args.project_name or config.get("unreal", {}).get("project_name", DEFAULT_PROJECT_NAME),
        args.engine_root,
    )
    if config.get("status") != "frozen_for_local_render":
        raise RuntimeError(f"Render matrix is not frozen: {config.get('status')}")
    if not all(config["coverage"]["checks"].values()):
        raise RuntimeError("Render matrix coverage checks are not all true")
    sample_count = len(config.get("samples", []))
    if sample_count < 1:
        raise RuntimeError("Render matrix contains no samples")
    if args.start_index < 1 or args.start_index > sample_count:
        raise ValueError(f"--start-index must be in 1..{sample_count}")
    selected = config["samples"][args.start_index - 1 :]
    if args.limit is not None:
        if args.limit < 1:
            raise ValueError("--limit must be positive")
        selected = selected[: args.limit]

    output_root = args.output_dir.resolve()
    if args.audit_existing:
        result = audit_existing_matrix(output_root, selected)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "passed" else 1
    if args.dry_run:
        print(
            json.dumps(
                {
                    "status": "dry_run_passed",
                    "config": str(config_path),
                    "output": str(output_root),
                    "selected_samples": len(selected),
                    "first_sample": selected[0]["sample_id"],
                    "last_sample": selected[-1]["sample_id"],
                    "coverage": config["coverage"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    output_root.mkdir(parents=True, exist_ok=True)
    free_bytes = shutil.disk_usage(output_root).free
    if free_bytes < MIN_FREE_BYTES:
        raise RuntimeError(
            f"At least {MIN_FREE_BYTES / 1024**3:.0f} GiB free is required; "
            f"found {free_bytes / 1024**3:.1f} GiB"
        )

    stage_map_report = ensure_stage_map(config)
    run_command([sys.executable, str(PROFILE_RUNNER)], 300)
    state_path = output_root / "matrix_state.json"
    records = []
    for ordinal, row in enumerate(selected, start=args.start_index):
        folder, existing = select_output_folder(output_root, row)
        if existing is not None and not args.prepare_only:
            record = {
                "ordinal": ordinal,
                "status": "passed",
                "resume": "reused_valid_output",
                "config": row,
                "render_report": existing,
            }
            records.append(record)
            write_state(state_path, config_path, records, "running")
            print(f"[{ordinal}/{sample_count}] reused {row['sample_id']}", flush=True)
            continue

        print(
            f"[{ordinal}/{sample_count}] staging {row['look_id']} | {row['action_id']} | "
            f"{row['camera_id']} | {row['expression_id']}",
            flush=True,
        )
        stage_report = stage_look(config, row)
        sequence_report = build_sequence(config, row, stage_report["actor_name"])
        if not sequence_report.get("success"):
            raise RuntimeError(f"Sequence build failed: {sequence_report}")
        if not pose_driver_contract(sequence_report)["passed"]:
            raise RuntimeError(
                "Sequence does not satisfy the anti-T-pose contract: "
                f"{pose_driver_contract(sequence_report)}"
            )
        if args.prepare_only:
            records.append(
                {
                    "ordinal": ordinal,
                    "status": "prepared",
                    "config": row,
                    "stage_report": stage_report,
                    "sequence_report": sequence_report,
                }
            )
            write_state(state_path, config_path, records, "prepared")
            continue

        render_report = render_case(
            config,
            row,
            folder,
            args.timeout_seconds,
            sequence_report,
        )
        records.append(
            {
                "ordinal": ordinal,
                "status": "passed",
                "resume": "rendered",
                "config": row,
                "stage_report": stage_report,
                "sequence_report": sequence_report,
                "render_report": render_report,
            }
        )
        write_state(state_path, config_path, records, "running")
        remote(
            "import unreal; unreal.SystemLibrary.collect_garbage(); "
            "print('DM_MATRIX_GC=done')",
            180,
        )

    complete = (
        not args.prepare_only
        and args.start_index == 1
        and len(selected) == sample_count
        and all(row.get("status") == "passed" for row in records)
    )
    status = "passed" if complete else ("prepared" if args.prepare_only else "partial_passed")
    write_state(state_path, config_path, records, status)
    if not args.prepare_only:
        build_contact_sheet(records, output_root / "matrix_contact_sheet.png")
        build_html(records, output_root / "index.html")
    aggregate = {
        "schema_version": 1,
        "created_at_utc": utc_now(),
        "status": status,
        "config": str(config_path),
        "output_root": str(output_root),
        "stage_map": stage_map_report,
        "expected_sample_count": sample_count,
        "selected_count": len(selected),
        "passed_count": sum(row.get("status") == "passed" for row in records),
        "prepared_count": sum(row.get("status") == "prepared" for row in records),
        "rendered_look_count": len(
            {row["config"]["look_id"] for row in records if row.get("status") == "passed"}
        ),
        "rendered_action_counts": dict(
            Counter(
                row["config"]["action_id"]
                for row in records
                if row.get("status") == "passed"
            )
        ),
        "rendered_camera_counts": dict(
            Counter(
                row["config"]["camera_id"]
                for row in records
                if row.get("status") == "passed"
            )
        ),
        "rendered_expression_counts": dict(
            Counter(
                row["config"]["expression_id"]
                for row in records
                if row.get("status") == "passed"
            )
        ),
        "temporal_motion_passed_count": sum(
            row.get("render_report", {})
            .get("automation_contract", {})
            .get("temporal_motion_contract", {})
            .get("passed")
            is True
            for row in records
            if row.get("status") == "passed"
        ),
        "state": str(state_path),
        "contact_sheet": str(output_root / "matrix_contact_sheet.png"),
        "review_html": str(output_root / "index.html"),
    }
    report_path = output_root / "matrix_report.json"
    report_path.write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(aggregate, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
