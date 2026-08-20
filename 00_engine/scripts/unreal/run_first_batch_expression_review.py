#!/usr/bin/env python3
"""Orchestrate the first-batch expression PIE review and contact sheet."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import time

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(r"D:\UE\Lance_Work\00_engine")
REMOTE_EXEC = ROOT / "scripts" / "unreal" / "ue_remote_exec.py"
STAGE_SCRIPT = ROOT / "scripts" / "unreal" / "ue_stage_first_batch_expression_review.py"
PIE_SCRIPT = ROOT / "scripts" / "unreal" / "ue_run_first_batch_expression_review.py"
CLEANUP_SCRIPT = ROOT / "scripts" / "unreal" / "ue_cleanup_first_batch_expression_review.py"
OUTPUT_DIR = (
    ROOT
    / "outputs"
    / "unreal_character_import"
    / "first_batch_expressions_20260820_v1"
    / "runtime_review"
)
REPORT_PATH = OUTPUT_DIR / "pie_expression_review.json"
SHEET_PATH = OUTPUT_DIR / "first_batch_expression_contact_sheet.png"
PROJECT_NAME = "datatry_02"


def execute_file_arguments(path: Path) -> list[str]:
    script_path = str(path.resolve())
    command = (
        f"exec(compile(open({script_path!r}, 'r', encoding='utf-8').read(), "
        f"{script_path!r}, 'exec'))"
    )
    return ["--command", command]


def run_remote(arguments: list[str], timeout: float = 120.0) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(REMOTE_EXEC),
            "--project",
            PROJECT_NAME,
            "--discovery-timeout",
            "30",
            *arguments,
        ],
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "Unreal remote command failed:\n"
            + completed.stdout[-5000:]
            + completed.stderr[-5000:]
        )
    envelope = json.loads(completed.stdout)
    for line in envelope.get("command_result", {}).get("output", []):
        output = str(line.get("output", "")).strip()
        if output.startswith("DM_FIRST_BATCH_EXPRESSION_"):
            print(output)


def wait_for_report(timeout_seconds: float = 240.0) -> dict:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if REPORT_PATH.is_file():
            try:
                report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                report = None
            if report is not None:
                if report.get("sample_count") == report.get("expected_sample_count"):
                    return report
                if report.get("success") is False and report.get("errors"):
                    return report
        time.sleep(0.5)
    raise TimeoutError(f"Expression review did not complete: {REPORT_PATH}")


def load_font(size: int, bold: bool = False):
    candidates = (
        Path(r"C:\Windows\Fonts\arialbd.ttf")
        if bold
        else Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\msyhbd.ttc")
        if bold
        else Path(r"C:\Windows\Fonts\msyh.ttc"),
    )
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def build_contact_sheet(report: dict) -> None:
    rows = [
        (actor_id, expression_id)
        for actor_id in ("F02", "M02")
        for expression_id in ("happy", "angry", "sad")
    ]
    samples = ("early", "middle", "late")
    by_key = {
        (item["actor_id"], item["expression_id"], item["sample_id"]): item
        for item in report["records"]
    }
    tile_w, tile_h = 360, 300
    gap = 12
    label_w = 170
    header_h = 86
    row_h = tile_h + 22
    width = label_w + len(samples) * (tile_w + gap) + gap
    height = header_h + len(rows) * row_h + gap
    canvas = Image.new("RGB", (width, height), "#10151d")
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(27, bold=True)
    label_font = load_font(18, bold=True)
    detail_font = load_font(14)
    draw.text((18, 12), "First Batch Expressions", fill="#f4f6f8", font=title_font)
    draw.text(
        (18, 49),
        "Body animation + runtime-selectable Happy / Angry / Sad face layer",
        fill="#9da9b8",
        font=detail_font,
    )
    for column, sample_id in enumerate(samples):
        x = label_w + column * (tile_w + gap)
        draw.text((x + 4, 55), sample_id, fill="#dce3eb", font=label_font)
    for row_index, (actor_id, expression_id) in enumerate(rows):
        y = header_h + row_index * row_h
        draw.text((18, y + 112), actor_id, fill="#f4f6f8", font=label_font)
        draw.text((18, y + 140), expression_id, fill="#80c7ff", font=detail_font)
        for column, sample_id in enumerate(samples):
            record = by_key[(actor_id, expression_id, sample_id)]
            with Image.open(record["image"]["path"]) as source:
                fitted = ImageOps.fit(
                    source.convert("RGB"),
                    (tile_w, tile_h),
                    method=Image.Resampling.LANCZOS,
                    centering=(0.5, 0.5),
                )
            x = label_w + column * (tile_w + gap)
            canvas.paste(fitted, (x, y))
            draw.rectangle(
                (x, y, x + tile_w - 1, y + tile_h - 1),
                outline="#384553",
                width=1,
            )
    canvas.save(SHEET_PATH, quality=95)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if REPORT_PATH.exists():
        REPORT_PATH.unlink()
    if SHEET_PATH.exists():
        SHEET_PATH.unlink()
    run_remote(execute_file_arguments(STAGE_SCRIPT))
    report = None
    try:
        run_remote(
            [
                "--command",
                "import unreal; s=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); "
                "s.editor_play_simulate() if not s.is_in_play_in_editor() else None",
            ]
        )
        time.sleep(4.0)
        run_remote(execute_file_arguments(PIE_SCRIPT))
        report = wait_for_report()
    finally:
        try:
            run_remote(
                [
                    "--command",
                    "import unreal; s=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); "
                    "s.editor_request_end_play() if s.is_in_play_in_editor() else None",
                ]
            )
            time.sleep(1.0)
        finally:
            run_remote(execute_file_arguments(CLEANUP_SCRIPT))
    if report is None:
        raise RuntimeError("Expression review produced no report")
    if not report.get("automatic_success"):
        raise RuntimeError(
            "Expression review failed:\n"
            + "\n".join(str(item) for item in report.get("errors", []))
        )
    build_contact_sheet(report)
    print(
        "DM_FIRST_BATCH_EXPRESSION_PIE_REVIEW="
        + json.dumps(
            {
                "contact_sheet": str(SHEET_PATH),
                "report": str(REPORT_PATH),
                "sample_count": report["sample_count"],
                "success": True,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
