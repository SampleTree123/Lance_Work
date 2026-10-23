"""Launch/reuse the GUI editor and supervise bounded fixed-head hair imports.

Uses existing UnrealEditor.exe and Python remote execution, never UAT/UBT,
dotnet, Live Coding, a commandlet import, or automatic package restoration.
"""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from launch_local_unreal_editor_v1 import ENGINE, PROJECT, runtime_environment

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parents[2]
ROOT = REPO / "00_engine/outputs/unreal_character_import/fixed_head_hair_20261004_v1"
MANIFEST = Path("D:/UE/exports/character_creator/fixed_head_hair_20261004_v1/manifests/batch.json")
REMOTE = SCRIPTS / "ue_remote_exec.py"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def remote(command, run, tag, discovery=30, timeout=1200):
    arguments = [sys.executable, str(REMOTE), "--project", PROJECT.stem,
        "--engine-root", str(ENGINE), "--discovery-timeout", str(discovery), "--command", command]
    started = time.time()
    completed = subprocess.run(arguments, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=timeout)
    output = run / (tag + "_remote.json")
    output.write_text(completed.stdout or completed.stderr, encoding="utf-8")
    if completed.returncode:
        raise RuntimeError("UE remote failed; inspect " + str(output) + "\n" + completed.stderr[-2000:])
    envelope = json.loads(completed.stdout)
    if not envelope.get("command_result", {}).get("success"):
        raise RuntimeError("UE operation failed; inspect " + str(output))
    return envelope


def launch(run, null_rhi=False):
    # Discovery failures must not lead to duplicate editor processes or restart
    # an editor that is still importing. Ask the caller to inspect that state.
    try:
        remote("import unreal; print(unreal.Paths.project_dir())", run, "existing_editor", discovery=5, timeout=20)
        return {"reused_editor": True}
    except (RuntimeError, subprocess.TimeoutExpired):
        if os.name == "nt":
            ps = subprocess.run(["powershell", "-NoProfile", "-Command",
                "Get-CimInstance Win32_Process -Filter \"Name='UnrealEditor.exe'\" | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"],
                capture_output=True, text=True, timeout=15)
            text = ps.stdout.strip()
            if text:
                rows = json.loads(text)
                rows = rows if isinstance(rows, list) else [rows]
                if any(PROJECT.stem.casefold() in str(r.get("CommandLine", "")).casefold() for r in rows):
                    raise RuntimeError("Project editor is alive but remote execution is unavailable; do not launch a duplicate")
    env, folders = runtime_environment(run)
    shader = run / "shader_work"
    shader.mkdir(exist_ok=True)
    recovery = PROJECT.parent / "Saved/Autosaves/PackageRestoreData.json"
    if recovery.is_file():
        shutil.copy2(recovery, run / "package_restore_info_before_launch.json")
    command = [str(ENGINE / "Engine/Binaries/Win64/UnrealEditor.exe"), str(PROJECT),
        "/Engine/Maps/Entry" if null_rhi else "/Game/DataMake/Validation/ScalpHairFit/L_DM_ScalpHairFit_Review_v001",
        "-nosplash", "-nosound", "-nop4", "-NoLiveCoding", "-unattended", "-NoRestorePackages",
        "-DDC-ForceMemoryCache", "-ddc=NoZenLocalFallback", "-ModelContextProtocolPort=28110",
        "-ini:Engine:[/Script/Engine.RendererSettings]:r.PathTracing=0",
        "-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorExperimentalSettings]:bEnableAsyncSkinnedAssetCompilation=False",
        "-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorExperimentalSettings]:bEnableAsyncTextureCompilation=False",
        "-ShaderWorkingDir=" + str(shader), "-abslog=" + str(run / "editor.log")]
    if null_rhi:
        command.append("-nullrhi")
    startup = None
    if os.name == "nt":
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = subprocess.SW_HIDE
    process = subprocess.Popen(command, env=env, cwd=PROJECT.parent, startupinfo=startup)
    report = {"pid": process.pid, "command": command, "environment": folders,
              "log": str(run / "editor.log"), "reused_editor": False}
    write(run / "launch_report.json", report)
    print(json.dumps({"phase": "editor_starting", "pid": process.pid, "log": report["log"]}), flush=True)
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Launched editor exited: " + str(process.returncode))
        try:
            remote("import unreal; print(unreal.Paths.project_dir())", run, "ready", discovery=5, timeout=20)
            return report
        except (RuntimeError, subprocess.TimeoutExpired):
            time.sleep(3)
    raise TimeoutError("Editor remains alive but remote readiness timed out; inspect existing process, do not restart")


def invoke(worker, variables, run, tag):
    command = "import runpy; runpy.run_path(" + repr(str(SCRIPTS / worker)) + ", init_globals=" + repr(variables) + ")"
    return remote(command, run, tag)


def normalize_capture(path):
    from PIL import Image, ImageStat
    with Image.open(path) as image:
        image.load()
        rgb = image.convert("RGB")
        if image.size != (900, 900) or max(ImageStat.Stat(rgb).stddev) < 1.:
            raise RuntimeError("Blank or malformed representative capture: " + str(path))
        transparent = "A" in image.getbands() and image.getchannel("A").getextrema() == (0, 0)
    if transparent:
        backup = path.parent / "raw_zero_alpha"
        backup.mkdir(exist_ok=True)
        original = backup / path.name
        if not original.exists():
            shutil.copy2(path, original)
        rgb.save(path, format="PNG")
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "zero_alpha_normalized": transparent, "readable": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", choices=("launch", "import", "review", "audit", "status"), default="import")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--pilot", action="store_true")
    selection.add_argument("--all", action="store_true")
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--hair-id", default="HAIR_HB3_17")
    parser.add_argument("--launch", action="store_true", help="Launch only when no project editor is alive")
    parser.add_argument("--nullrhi", action="store_true", help="GPU-free GUI editor for import/audit; never use for review")
    args = parser.parse_args()
    if args.action == "status":
        path = ROOT / "import_report.json"
        print(path.read_text(encoding="utf-8") if path.exists() else "No import report")
        return
    run = ROOT / "runner" / (args.action + "_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    run.mkdir(parents=True)
    if args.nullrhi and args.action == "review":
        parser.error("Representative captures require a rendering editor")
    if args.launch or args.action == "launch":
        launch(run, args.nullrhi)
    if args.action == "launch":
        return
    if args.action == "audit":
        invoke("ue_audit_fixed_head_hair_v1.py", {}, run, "final_audit")
        audit = read(ROOT / "final_runtime_audit.json")
        if not audit.get("success"):
            raise RuntimeError(audit.get("error", "Final index load audit failed"))
        print(json.dumps({"phase": "final_audit_passed", "cases_loaded": audit["cases_loaded"],
                          "shared_skeletons": len(audit["shared_skeletons"])}), flush=True)
        return
    if args.action == "import":
        if not args.pilot and not args.all:
            parser.error("import requires --pilot or --all")
        manifest = read(args.manifest)
        selected = [r for r in manifest["cases"] if not args.pilot or r["hair_id"] == args.hair_id]
        if args.pilot and {r["sex"] for r in selected} != {"female", "male"}:
            raise RuntimeError("Pilot requires both sex branches")
        if args.all and len(selected) != 80:
            raise RuntimeError("Full batch must contain exactly 80 cases")
        # The all-import phase must wait for the complete export phase. This
        # check happens before dispatching any Unreal asset mutation.
        for case in selected:
            if case.get("status") != "exported":
                raise RuntimeError("Export is not committed yet: " + case["case_id"])
            for kind in ("fbx", "json"):
                path = Path(case[kind])
                if not path.is_file() or path.stat().st_size != case[kind + "_record"]["bytes"]:
                    raise RuntimeError("Incomplete export input: " + str(path))
        for index, case in enumerate(selected, 1):
            config = run / (case["case_id"] + "_config.json")
            write(config, {"case_ids": [case["case_id"]], "max_cases": 1})
            print(json.dumps({"phase": "importing", "index": index, "total": len(selected),
                              "case_id": case["case_id"]}), flush=True)
            invoke("ue_import_fixed_head_hair_v1.py", {"DM_FIXED_HAIR_MANIFEST": str(args.manifest),
                "DM_FIXED_HAIR_CONFIG": str(config)}, run, case["case_id"])
            report = read(ROOT / "import_report.json")
            actual = [r for r in report["records"] if r["case_id"] == case["case_id"]]
            if len(actual) != 1 or not actual[0].get("success"):
                raise RuntimeError("Case did not commit a successful result")
            print(json.dumps({"phase": "completed", "index": index, "total": len(selected),
                              "case_id": case["case_id"], "completed_cases": report["completed_cases"]}), flush=True)
        return
    started = time.time()
    invoke("ue_review_fixed_head_hair_pilot_v1.py", {"DM_FIXED_HAIR_PILOT_ID": args.hair_id}, run, "review")
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        path = ROOT / "pilot_review.json"
        if path.exists() and path.stat().st_mtime >= started:
            review = read(path)
            if review.get("error"):
                raise RuntimeError(review["error"])
            if review.get("capture_complete"):
                if len(review["captures"]) != 6:
                    raise RuntimeError("Representative capture count differs from six")
                normalized = [normalize_capture(Path(r["path"])) for r in review["captures"]]
                write(ROOT / "pilot_capture_readability.json", {"success": True, "images": normalized})
                print(json.dumps({"phase": "review_ready", "level": review["level"],
                                  "capture_count": 6, "visual_review_complete": False}), flush=True)
                return
        time.sleep(2)
    raise TimeoutError("Capture observation timed out; check the existing pilot callback before retrying")


if __name__ == "__main__":
    main()
