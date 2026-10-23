"""Launch local UE with writable workspace logs for its AutomationTool children."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import shutil

WORKSPACE = Path(r"D:\UE")
ENGINE = WORKSPACE / "UE_5.8"
PROJECT = WORKSPACE / "projects/datatry_02/datatry_02.uproject"
RUN_ROOT = Path(__file__).resolve().parents[2] / "outputs/unreal_character_import/hair_sex_fit_review_20260929_v1/rendering_repair_v2"


def runtime_environment(run):
    run = run.resolve()
    if not run.is_relative_to(WORKSPACE.resolve()):
        raise ValueError("UE runtime logs must stay within the configured workspace")
    folders = {"uebp_LogFolder": run / "uat_logs", "uebp_FinalLogFolder": run / "uat_logs",
               "uebp_EngineSavedFolder": run / "uat_saved"}
    env = os.environ.copy()
    for name, folder in folders.items():
        folder.mkdir(parents=True, exist_ok=True)
        env[name] = str(folder)
    return env, {key: str(value) for key, value in folders.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("editor", "sdk-check"), default="editor")
    parser.add_argument("--hair-review", action="store_true", help="Open the static SceneCapture review map without loading path-tracer PSOs")
    args = parser.parse_args()
    run = RUN_ROOT / (args.mode + "_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    run.mkdir(parents=True)
    env, paths = runtime_environment(run)
    if os.name == "nt":
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = subprocess.SW_HIDE
    else:
        startup = None
    if args.mode == "sdk-check":
        log_path = run / "sdk_check.log"
        command = [str(ENGINE / "Engine/Build/BatchFiles/RunUAT.bat"), "-nocompileuat",
                   f"-ScriptsForProject={PROJECT}", "Turnkey", "-utf8output", "-command=VerifySdk", "-platform=Win64",
                   f"-ReportFilename={run / 'TurnkeyReport.log'}", f"-log={run / 'TurnkeyLog.log'}"]
        with log_path.open("w", encoding="utf-8") as log:
            completed = subprocess.run(command, env=env, cwd=ENGINE / "Engine", stdout=log,
                                       stderr=subprocess.STDOUT, startupinfo=startup, timeout=180)
        text = log_path.read_text(encoding="utf-8", errors="replace")
        result = {"mode": args.mode, "exit_code": completed.returncode, "log": str(log_path),
                  "no_unhandled_dotnet_exception": "Unhandled exception" not in text and "UnauthorizedAccessException" not in text,
                  "environment": paths}
        result["success"] = completed.returncode == 0 and result["no_unhandled_dotnet_exception"]
    else:
        shader_dir = WORKSPACE / "Lance_Work/00_engine/temp/hair_rendering_shader_work"
        shader_dir.mkdir(parents=True, exist_ok=True)
        command = [str(ENGINE / "Engine/Binaries/Win64/UnrealEditor.exe"), str(PROJECT), "-nosplash", "-nosound", "-nop4",
                   "-NoLiveCoding", "-DDC-ForceMemoryCache", "-ddc=NoZenLocalFallback",
                   f"-ShaderWorkingDir={shader_dir}", f"-abslog={run / 'editor.log'}"]
        if args.hair_review:
            recovery = PROJECT.parent / "Saved/Autosaves/PackageRestoreData.json"
            if recovery.is_file():
                shutil.copy2(recovery, run / "package_restore_info_before_launch.json")
            command.extend(["/Game/DataMake/Validation/ScalpHairFit/L_DM_ScalpHairFit_Review_v001",
                            "-unattended", "-ini:Engine:[/Script/Engine.RendererSettings]:r.PathTracing=0"])
        process = subprocess.Popen(command, env=env, cwd=PROJECT.parent, startupinfo=startup)
        result = {"mode": args.mode, "pid": process.pid, "environment": paths, "log": str(run / "editor.log"),
                  "status": "launched_not_yet_verified", "command": command}
    (run / "launch_report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False), flush=True)
    if args.mode == "sdk-check" and not result["success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
