#!/usr/bin/env python3
"""Orchestrate the F02/M02 P0 runtime PIE review and contact sheet."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import time

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(r"D:\UE\Lance_Work\00_engine")
REMOTE_EXEC = ROOT / "scripts" / "unreal" / "ue_remote_exec.py"
STAGE_SCRIPT = ROOT / "scripts" / "unreal" / "ue_stage_p0_runtime_validation.py"
PIE_SCRIPT = ROOT / "scripts" / "unreal" / "ue_run_p0_runtime_validation.py"
CLEANUP_SCRIPT = ROOT / "scripts" / "unreal" / "ue_cleanup_p0_runtime_validation.py"
OUTPUT_DIR = (
    ROOT
    / "outputs"
    / "unreal_character_import"
    / "p0_runtime_pilot_20260819_v1"
    / "runtime_review"
)
REPORT_PATH = OUTPUT_DIR / "pie_runtime_review.json"
SHEET_PATH = OUTPUT_DIR / "p0_runtime_pilot_contact_sheet.png"
PROJECT_NAME = "datatry_02"
MAX_REMOTE_ATTEMPTS = 3


def execute_file_arguments(path: Path) -> list[str]:
    script_path = str(path.resolve())
    command = (
        f"exec(compile(open({script_path!r}, 'r', encoding='utf-8').read(), "
        f"{script_path!r}, 'exec'))"
    )
    return ["--command", command]


def run_remote(arguments: list[str], timeout: float = 120.0) -> None:
    last_error = ""
    for attempt in range(1, MAX_REMOTE_ATTEMPTS + 1):
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
        if completed.returncode == 0:
            try:
                envelope = json.loads(completed.stdout)
            except json.JSONDecodeError:
                envelope = {}
            for line in envelope.get("command_result", {}).get("output", []):
                output = str(line.get("output", "")).strip()
                if output.startswith("DM_P0_RUNTIME_"):
                    print(output)
            return
        last_error = completed.stdout[-5000:] + completed.stderr[-5000:]
        if attempt < MAX_REMOTE_ATTEMPTS:
            time.sleep(1.5)
    raise RuntimeError(f"Unreal remote command failed:\n{last_error}")


def wait_for_report(timeout_seconds: float = 240.0) -> dict:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if REPORT_PATH.is_file():
            try:
                report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                report = None
            if report is not None:
                if report.get("case_count") == report.get("expected_case_count"):
                    return report
                if report.get("success") is False and report.get("errors"):
                    return report
        time.sleep(0.5)
    raise TimeoutError(f"P0 PIE review did not complete: {REPORT_PATH}")


def load_font(size: int, bold: bool = False):
    candidates = (
        Path(r"C:\Windows\Fonts\arialbd.ttf") if bold else Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\msyhbd.ttc") if bold else Path(r"C:\Windows\Fonts\msyh.ttc"),
    )
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def build_contact_sheet(report: dict) -> None:
    order = (
        ("neutral", "full_front", "Neutral full front"),
        ("neutral", "full_side", "Neutral full side"),
        ("neutral", "head_front", "Neutral head"),
        ("natural_blink", "head_front", "Blink"),
        ("asymmetric_blink", "head_front", "Asymmetric blink"),
        ("subtle_smile", "head_front", "Subtle smile"),
    )
    rows = (
        ("F02", "walk"),
        ("F02", "idle"),
        ("M02", "walk"),
        ("M02", "understood"),
    )
    by_case = {
        (item["actor_id"], item["body_id"], item["face_id"]): item
        for item in report["records"]
    }

    tile_w, tile_h = 292, 164
    gap = 12
    label_w = 178
    header_h = 92
    row_h = tile_h + 48
    width = label_w + len(order) * (tile_w + gap) + gap
    height = header_h + len(rows) * row_h + gap
    canvas = Image.new("RGB", (width, height), "#10151d")
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(28, bold=True)
    header_font = load_font(15, bold=True)
    body_font = load_font(17, bold=True)
    detail_font = load_font(13)

    draw.text((20, 14), "UE 5.8 P0 Runtime Pilot", fill="#f4f6f8", font=title_font)
    draw.text(
        (20, 51),
        "F02 / M02 | body selection + FullReference direct-Morph face layer",
        fill="#9da9b8",
        font=detail_font,
    )
    for column, (_, _, label) in enumerate(order):
        x = label_w + column * (tile_w + gap)
        draw.text((x + 4, 66), label, fill="#dce3eb", font=header_font)

    for row_index, (actor_id, body_id) in enumerate(rows):
        y = header_h + row_index * row_h
        draw.text((20, y + 52), actor_id, fill="#f4f6f8", font=body_font)
        draw.text((20, y + 78), body_id, fill="#80c7ff", font=detail_font)
        for column, (face_id, view, _) in enumerate(order):
            record = by_case[(actor_id, body_id, face_id)]
            image_path = Path(record["captures"][view]["image"]["path"])
            with Image.open(image_path) as source:
                source = source.convert("RGB")
                fitted = ImageOps.fit(
                    source,
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
            draw.text(
                (x + 4, y + tile_h + 8),
                face_id,
                fill="#9da9b8",
                font=detail_font,
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
        raise RuntimeError("P0 PIE review produced no report")
    if not report.get("automatic_success"):
        raise RuntimeError(
            "P0 PIE review failed:\n"
            + "\n".join(str(item) for item in report.get("errors", []))
        )
    build_contact_sheet(report)
    print(
        "DM_P0_RUNTIME_PIE_REVIEW="
        + json.dumps(
            {
                "case_count": report["case_count"],
                "contact_sheet": str(SHEET_PATH),
                "image_count": report["image_count"],
                "report": str(REPORT_PATH),
                "success": True,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
