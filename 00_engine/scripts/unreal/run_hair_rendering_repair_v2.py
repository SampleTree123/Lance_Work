"""Supervise source-driven hair repairs one style at a time and verify saved assets."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

from launch_local_unreal_editor_v1 import ENGINE, PROJECT, runtime_environment

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parents[1] / "outputs/unreal_character_import/hair_sex_fit_review_20260929_v1/rendering_repair_v2"


def hidden_startup():
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    return startup


def run_one(hair_id):
    command = ("import runpy; runpy.run_path(" + repr(str(SCRIPTS / "ue_repair_hair_rendering_v2.py"))
               + ", init_globals={'DM_HAIR_RENDER_ID': " + repr(hair_id) + "})")
    result = subprocess.run([sys.executable, str(SCRIPTS / "ue_remote_exec.py"), "--project", "datatry_02",
                             "--command", command, "--discovery-timeout", "30"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
    if result.returncode:
        raise RuntimeError((result.stdout + result.stderr)[-4000:])
    outer = json.loads(result.stdout)
    if not outer.get("command_result", {}).get("success"):
        raise RuntimeError("Remote repair did not succeed: " + hair_id)
    report = json.loads((ROOT / "reports" / (hair_id + ".json")).read_text(encoding="utf-8"))
    if not report.get("success"):
        raise RuntimeError("Repair report failed: " + hair_id)
    return report


def verify():
    run = ROOT / ("fresh_verify_" + time.strftime("%Y%m%d_%H%M%S"))
    run.mkdir()
    env, folders = runtime_environment(run)
    bootstrap = run / "verify_saved_hair.py"
    bootstrap.write_text("import runpy\nrunpy.run_path(" + repr(str(SCRIPTS / "ue_audit_hair_rendering_v2.py"))
                         + ", init_globals={'DM_HAIR_AUDIT_V2': True, 'DM_HAIR_AUDIT_FRESH': True})\n", encoding="utf-8")
    log_path = run / "editor_cmd.log"
    command = [str(ENGINE / "Engine/Binaries/Win64/UnrealEditor-Cmd.exe"), str(PROJECT),
               "-run=pythonscript", f"-script={bootstrap}", "-unattended", "-nop4", "-nullrhi", "-nosound",
               "-nosplash", "-DDC-ForceMemoryCache", "-ddc=NoZenLocalFallback", "-ModelContextProtocolPort=28110",
               r"-ShaderWorkingDir=D:\UE\Lance_Work\00_engine\temp\hair_rendering_shader_work"]
    started = time.time()
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.run(command, env=env, cwd=PROJECT.parent, stdout=log, stderr=subprocess.STDOUT,
                                 startupinfo=hidden_startup(), timeout=600)
    audit_path = ROOT / "fresh_load_material_audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() and audit_path.stat().st_mtime >= started else None
    result = {"success": process.returncode == 0 and bool(audit and audit.get("success")),
              "exit_code": process.returncode, "audit": str(audit_path), "log": str(log_path), "environment": folders}
    (run / "verification_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result), flush=True)
    if not result["success"]:
        raise RuntimeError("Fresh-process hair verification failed")


def repair_cmd(selected):
    run = ROOT / ("cmd_repair_" + time.strftime("%Y%m%d_%H%M%S"))
    run.mkdir()
    env, _ = runtime_environment(run)
    bootstrap = run / "repair_saved_hair.py"
    bootstrap.write_text(
        "import runpy\n"
        "worker=runpy.run_path(" + repr(str(SCRIPTS / "ue_repair_hair_rendering_v2.py")) + ")\n"
        "for hair_id in " + repr(selected) + ":\n    worker['repair'](hair_id)\n", encoding="utf-8")
    log_path = run / "editor_cmd.log"
    command = [str(ENGINE / "Engine/Binaries/Win64/UnrealEditor-Cmd.exe"), str(PROJECT),
               "-run=pythonscript", f"-script={bootstrap}", "-unattended", "-nop4", "-nullrhi", "-nosound",
               "-nosplash", "-DDC-ForceMemoryCache", "-ddc=NoZenLocalFallback", "-ModelContextProtocolPort=28110",
               "-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorExperimentalSettings]:bEnableAsyncSkinnedAssetCompilation=False",
               "-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorExperimentalSettings]:bEnableAsyncTextureCompilation=False",
               r"-ShaderWorkingDir=D:\UE\Lance_Work\00_engine\temp\hair_rendering_shader_work"]
    print(json.dumps({"started": True, "styles": len(selected), "log": str(log_path)}), flush=True)
    with log_path.open("w", encoding="utf-8") as log:
        result = subprocess.run(command, env=env, cwd=PROJECT.parent, stdout=log, stderr=subprocess.STDOUT,
                                startupinfo=hidden_startup(), timeout=600)
    if result.returncode:
        raise RuntimeError("Commandlet repair failed: " + str(log_path))
    print(json.dumps({"success": True, "styles": len(selected), "exit_code": result.returncode}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--hair-id")
    selection.add_argument("--remaining", action="store_true")
    selection.add_argument("--verify", action="store_true")
    parser.add_argument("--transport", choices=("remote", "cmd"), default="remote")
    args = parser.parse_args()
    if args.verify:
        verify()
        return
    plan = json.loads((ROOT / "repair_plan.json").read_text(encoding="utf-8"))
    ids = sorted({row["hair_id"] for row in plan["rows"]})
    if args.hair_id and args.hair_id not in ids:
        raise ValueError("Unknown retained hair ID " + args.hair_id)
    selected = [args.hair_id] if args.hair_id else []
    if args.remaining:
        for hair_id in ids:
            path = ROOT / "reports" / (hair_id + ".json")
            rows = [row for row in plan["rows"] if row["hair_id"] == hair_id]
            report = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
            expected = {(row["mesh"], row["slot_index"], row["v2_material"]) for row in rows}
            actual = {(row["mesh"], row["slot"], row["new_material"].split(".", 1)[0]) for row in report.get("materials", [])}
            if not report.get("success") or report.get("slots") != len(rows) or actual != expected:
                selected.append(hair_id)
    if args.transport == "cmd":
        repair_cmd(selected)
        return
    for index, hair_id in enumerate(selected, 1):
        report = run_one(hair_id)
        print(json.dumps({"completed": index, "total": len(selected), "hair_id": hair_id, "slots": report["slots"]}), flush=True)


if __name__ == "__main__":
    main()
