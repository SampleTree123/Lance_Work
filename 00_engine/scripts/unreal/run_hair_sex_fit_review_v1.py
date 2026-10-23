"""Control the bounded male/female hairstyle review level and six-view captures."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from PIL import Image
from build_hair_sex_fit_gallery_v1 import image_name, inspect_png


ROOT = Path(__file__).resolve().parent
ENGINE = ROOT.parents[1]
REVIEW_ROOT = ENGINE / "outputs/unreal_character_import/hair_sex_fit_review_20260929_v1"
PLAN_PATH = REVIEW_ROOT / "review_plan.json"
REMOTE = ROOT / "ue_remote_exec.py"
WORKER = ROOT / "ue_hair_sex_fit_review_v1.py"
VIEWS = ("front", "front_left", "left", "back", "right", "front_right")


def normalize_captures(capture_root: Path | None = None) -> dict:
    """Make UE's zero-alpha RGB pixels visible to ordinary PNG viewers."""
    captures = (capture_root or REVIEW_ROOT / "captures").resolve()
    if not captures.is_relative_to(REVIEW_ROOT.resolve()):
        raise ValueError("Capture output must remain inside the review Run Root")
    backup = captures.with_name(captures.name + "_raw_zero_alpha")
    converted = []
    already_visible = []
    for path in sorted(captures.glob("*.png")):
        with Image.open(path) as image:
            image.load()
            if "A" not in image.getbands() or image.getchannel("A").getextrema() != (0, 0):
                already_visible.append(path.name)
                continue
            rgb = image.convert("RGB")
        before_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        backup.mkdir(exist_ok=True)
        original = backup / path.name
        if original.exists() and hashlib.sha256(original.read_bytes()).hexdigest() != before_sha256:
            original = backup / f"{path.stem}_{before_sha256[:12]}.png"
        if not original.exists():
            shutil.copy2(path, original)
        temporary = path.with_name(path.name + ".tmp")
        try:
            rgb.save(temporary, format="PNG")
            with Image.open(temporary) as check:
                check.load()
                if check.mode != "RGB" or check.size != (900, 900):
                    raise ValueError(f"Unexpected normalized image: {temporary}")
                if check.tobytes() != rgb.tobytes():
                    raise ValueError(f"RGB pixels changed during normalization: {temporary}")
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        converted.append({"file": path.name, "raw_backup": str(original.relative_to(REVIEW_ROOT)),
                          "raw_sha256": before_sha256,
                          "rgb_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                          "rgb_pixels_preserved": True})
    report_path = (REVIEW_ROOT / "capture_visibility_normalization.json" if captures == (REVIEW_ROOT / "captures").resolve()
                   else captures.with_name(captures.name + "_visibility_normalization.json"))
    summary = {"total": len(converted) + len(already_visible), "converted": len(converted),
               "already_visible": len(already_visible), "backup": str(backup), "report": str(report_path)}
    if converted:
        report = {**summary, "updated_at": datetime.now(timezone.utc).isoformat(),
                  "cause": "UE final-color PNG exports contain RGB pixels but all-zero alpha",
                  "correction": "Lossless 8-bit RGB PNG; original RGBA PNGs retained",
                  "files": converted}
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def remote(mode: str, *, index: int, view: str, start: int, count: int, capture_root: Path | None = None,
           progress_root: Path | None = None, hide_scalp: bool = False) -> dict:
    worker = str(WORKER.resolve())
    command = "; ".join([
        f"DM_HSF_MODE={mode!r}", f"DM_HSF_INDEX={index!r}",
        f"DM_HSF_VIEW={view!r}", f"DM_HSF_START={start!r}", f"DM_HSF_COUNT={count!r}",
        f"__file__={worker!r}",
        f"DM_HSF_CAPTURE_ROOT={str((capture_root or REVIEW_ROOT / 'captures').resolve())!r}",
        f"DM_HSF_PROGRESS_ROOT={str((progress_root or REVIEW_ROOT).resolve())!r}",
        f"DM_HSF_HIDE_SCALP={hide_scalp!r}",
        "exec(compile(open(r%r, 'r', encoding='utf-8').read(), r%r, 'exec'), globals())" % (worker, worker),
    ])
    result = subprocess.run(
        [sys.executable, str(REMOTE), "--project", "datatry_02", "--command", command,
         "--discovery-timeout", "60"],
        cwd=str(ENGINE.parent), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=600,
    )
    if result.returncode:
        raise RuntimeError((result.stdout or "") + (result.stderr or ""))
    outer = json.loads(result.stdout)
    command_result = outer.get("command_result") or {}
    if not command_result.get("success"):
        raise RuntimeError(f"UE review command failed: {command_result}")
    marker = "DM_HAIR_SEX_FIT_RESULT="
    for output in reversed(command_result.get("output") or []):
        line = output.get("output", "")
        if marker in line:
            return json.loads(line.split(marker, 1)[1].strip())
    raise RuntimeError(f"Review worker returned no result: {command_result}")


def wait_capture(start: int, count: int, timeout_seconds: int, progress_root: Path | None = None) -> dict:
    path = (progress_root or REVIEW_ROOT) / f"capture_progress_{start:03d}_{start + count - 1:03d}.json"
    deadline = time.monotonic() + timeout_seconds
    last = -1
    last_progress = time.monotonic()
    while time.monotonic() < deadline:
        if path.is_file():
            progress = json.loads(path.read_text(encoding="utf-8"))
            completed = progress["completed_images"]
            if completed != last:
                print(f"Captured {completed}/{progress['total_images']} views", flush=True)
                last = completed
                last_progress = time.monotonic()
            if progress["done"]:
                if not progress["success"]:
                    raise RuntimeError(progress.get("error") or "Hair capture failed")
                return progress
        if time.monotonic() - last_progress > 180:
            raise TimeoutError(f"No hairstyle capture progress for 180 seconds: {path}")
        time.sleep(3)
    raise TimeoutError(f"Hairstyle capture exceeded {timeout_seconds} seconds: {path}")


def validate_captures(plan: dict, start: int, count: int, capture_root: Path) -> dict:
    """Reject transparent, corrupt, or untouched render-target clear-color files."""
    expected = [image_name(case, view)
                for case in plan["cases"][start - 1:start - 1 + count] for view in VIEWS]
    checked = {name: inspect_png(capture_root / name) for name in expected}
    invalid = [name for name, info in checked.items()
               if not info.get("displayable") or (info.get("width"), info.get("height")) != (900, 900)]
    report = {"start": start, "count": count, "expected_images": len(expected),
              "valid_images": len(expected) - len(invalid), "invalid_images": invalid,
              "success": not invalid, "capture_root": str(capture_root), "images": checked,
              "visual_acceptance": "pending_human_review"}
    path = capture_root.with_name(capture_root.name + "_validation.json")
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if invalid:
        raise RuntimeError(f"Invalid rendered images ({len(invalid)}): {path}")
    return {"success": True, "valid_images": len(expected), "report": str(path)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", choices=("inspect", "build", "show", "view", "capture", "status", "normalize"), required=True)
    parser.add_argument("--index", type=int, default=1)
    parser.add_argument("--view", choices=VIEWS, default="front")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--capture-root", type=Path, help="Optional separate image directory within the review Run Root")
    parser.add_argument("--progress-root", type=Path, help="Separate candidate progress and material audit directory")
    parser.add_argument("--hide-scalp", action="store_true", help="Render a temporary hidden-scalp candidate without saving UE assets")
    args = parser.parse_args()
    if args.capture_root and not args.capture_root.resolve().is_relative_to(REVIEW_ROOT.resolve()):
        raise ValueError("Capture output must remain inside the review Run Root")
    if args.progress_root and not args.progress_root.resolve().is_relative_to(REVIEW_ROOT.resolve()):
        raise ValueError("Progress output must remain inside the review Run Root")
    if args.hide_scalp and (args.action != "capture" or not args.capture_root or not args.progress_root):
        raise ValueError("--hide-scalp requires capture with separate --capture-root and --progress-root")
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    if args.action == "inspect":
        print(json.dumps({"counts": plan["counts"], "cases": plan["cases"]}, ensure_ascii=False, indent=2))
        return 0
    if args.action == "status":
        path = (args.progress_root or REVIEW_ROOT) / f"capture_progress_{args.start:03d}_{args.start + args.count - 1:03d}.json"
        print(path.read_text(encoding="utf-8") if path.is_file() else f"No capture progress: {path}")
        return 0
    if args.action == "normalize":
        print(json.dumps(normalize_captures(args.capture_root), ensure_ascii=False), flush=True)
        return 0
    result = remote(args.action, index=args.index, view=args.view, start=args.start, count=args.count,
                    capture_root=args.capture_root, progress_root=args.progress_root, hide_scalp=args.hide_scalp)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    if args.action == "capture":
        wait_capture(args.start, args.count, args.timeout_seconds, args.progress_root)
        print(json.dumps(normalize_captures(args.capture_root), ensure_ascii=False), flush=True)
        print(json.dumps(validate_captures(plan, args.start, args.count,
                                          (args.capture_root or REVIEW_ROOT / "captures").resolve()),
                         ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
