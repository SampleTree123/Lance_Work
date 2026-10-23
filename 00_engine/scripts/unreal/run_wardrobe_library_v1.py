"""Serial, resumable wardrobe transfer. Never starts, closes or restarts CC.

CC export requires the user-started bridge; UE-only supervision never calls CC.
UE can be restarted normally between saved
operations. Manual fit review is deferred, not waived, by this transfer runner.
"""
from __future__ import annotations

import argparse
import ctypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from audit_wardrobe_progress_v1 import audit, file_hash, read
from run_modular_outfit_pilot_import_v1 import PHASE_TO_MODE, write_json

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "00_engine/scripts"
CC_CLIENT = ROOT / "00_engine/character_creator_bridge/cc_bridge_client.py"


def batch_unit_ids(batch):
    ids = [p["preset_id"] for p in read(batch / "cc_export.json")["presets"]]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError(f"Empty or duplicate batch: {batch}")
    return ids


def remaining_units(library):
    master = [p["preset_id"] for p in read(library / "cc_export.json")["presets"]]
    if len(master) != len(set(master)):
        raise ValueError("Duplicate master IDs")
    allocated = set()
    for batch in sorted(library.glob("batch_*")):
        if not batch.is_dir():
            continue
        ids = batch_unit_ids(batch)
        if set(ids) & allocated or not set(ids) <= set(master):
            raise ValueError(f"Duplicate or unknown allocation: {batch}")
        allocated.update(ids)
    return [uid for uid in master if uid not in allocated]


def stage_complete(path, phase, unit=None):
    if not path.exists():
        return False
    value = read(path)
    if value.get("success") is not True or value.get("mode") != PHASE_TO_MODE[phase]:
        raise ValueError(f"Existing failed or mismatched stage requires diagnosis: {path}")
    if unit is not None and value.get("case_id") != unit:
        raise ValueError(f"Stage case differs: {path}")
    return True


def powershell_json(command):
    result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise RuntimeError(result.stderr[-3000:])
    return json.loads(result.stdout.strip() or "null")


def ue_processes():
    result = powershell_json("@(Get-CimInstance Win32_Process -Filter \"Name='UnrealEditor.exe'\" | "
                             "Select-Object ProcessId,ExecutablePath,CommandLine,CreationDate) | ConvertTo-Json -Compress")
    return [] if result is None else result if isinstance(result, list) else [result]


def free_commit_gib():
    class MemoryStatus(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
            (name, ctypes.c_ulonglong) for name in ("total_phys", "avail_phys", "total_page",
                                                  "avail_page", "total_virtual", "avail_virtual",
                                                  "avail_extended")]
    memory = MemoryStatus()
    memory.length = ctypes.sizeof(memory)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
        raise OSError("GlobalMemoryStatusEx failed")
    return memory.avail_page / 1024**3


class Runner:
    def __init__(self, args):
        self.args = args
        self.library = args.library_dir.resolve()
        self.reports = args.report_root.resolve()
        self.run_root = args.run_root.resolve()
        self.operation = 0
        self.heavy_since_restart = 0
        self.deferred_cc = {}
        self.auto_defer_missing_weight_maps = False
        self.auto_defer_asset_export_errors = False
        self.state = {"schema_version": 1, "status": "starting", "pid": os.getpid(),
                      "library": str(self.library), "manual_fit_review": "deferred_until_all_imported",
                      "cc_lifecycle": "user_offline_session_only", "completed_batches": []}

    def emit(self, status, **fields):
        self.state.update(fields, status=status, updated_at_utc=datetime.now(timezone.utc).isoformat())
        write_json(self.run_root / "state.json", self.state)
        event = {"at": self.state["updated_at_utc"], "status": status, **fields}
        with (self.run_root / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=True) + "\n")
        print(json.dumps(event), flush=True)

    def run(self, command, label):
        self.operation += 1
        path = self.run_root / "commands" / f"{time.time_ns()}_{label}.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        self.emit("running", operation=label, log=str(path))
        with path.open("w", encoding="utf-8") as stream:
            stream.write(json.dumps(command) + "\n")
            stream.flush()
            result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        if result.returncode:
            raise RuntimeError(f"{label} returned {result.returncode}; inspect {path}")
        return path

    def python(self, script, arguments, label):
        return self.run([sys.executable, str(script), *map(str, arguments)], label)

    def remote(self, payload, label, discovery=12):
        return self.python(SCRIPTS / "unreal/ue_remote_exec.py",
                           ["--project", self.args.project.stem, "--discovery-timeout", discovery,
                            "--command", payload], label)

    def check_disk(self):
        free = shutil.disk_usage(self.library).free / 1024**3
        if free < self.args.min_free_disk_gib:
            raise OSError(f"Disk free {free:.2f} GiB < {self.args.min_free_disk_gib} GiB; no automatic deletion")

    def current_ue(self):
        rows = ue_processes()
        if len(rows) > 1:
            raise RuntimeError("Multiple UE processes; refusing automatic lifecycle changes")
        if rows:
            self.validate_ue_identity(rows[0])
        return rows

    def validate_ue_identity(self, row, exiting=False):
        command, executable = row.get("CommandLine"), row.get("ExecutablePath")
        if not exiting and (not command or not executable or not row.get("CreationDate")):
            raise RuntimeError(f"UE identity metadata unavailable: {row}")
        if ((command and str(self.args.project.resolve()).lower() not in command.lower())
                or (executable and Path(executable).resolve() != self.args.editor.resolve())):
            raise RuntimeError(f"UE process does not match the configured project/editor: {row}")

    def wait_for_ue_exit(self, original):
        deadline = time.monotonic() + 180
        logged_missing_metadata = False
        while True:
            rows = ue_processes()
            if not rows:
                return
            # Only observe the already verified process after quit; never act on a replacement.
            if len(rows) != 1 or rows[0].get("ProcessId") != original["ProcessId"]:
                raise RuntimeError(f"UE process changed while awaiting normal exit: {rows}")
            row = rows[0]
            if row.get("CreationDate") and row["CreationDate"] != original["CreationDate"]:
                raise RuntimeError(f"UE PID was reused while awaiting normal exit: {row}")
            self.validate_ue_identity(row, exiting=True)
            if not logged_missing_metadata and any(not row.get(key) for key in
                                                   ("CommandLine", "ExecutablePath", "CreationDate")):
                self.emit("running", exit_observation="verified_pid_metadata_disappearing", exit_process=row)
                logged_missing_metadata = True
            if time.monotonic() >= deadline:
                raise TimeoutError("UE did not exit normally; no force termination attempted")
            time.sleep(3)

    def stop_ue(self):
        rows = self.current_ue()
        if not rows:
            return
        self.remote("import unreal; "
                    "assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'Unsaved map'; "
                    "assert not unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages(), 'Unsaved content'; "
                    "unreal.SystemLibrary.quit_editor()", "ue_normal_exit")
        self.wait_for_ue_exit(rows[0])
        self.heavy_since_restart = 0

    def ensure_ue(self):
        if not self.current_ue():
            # Start-Process must be hidden; do not change the project's startup map.
            def quote(value):
                return "'" + str(value).replace("'", "''") + "'"
            arguments = chr(34) + str(self.args.project.resolve()) + chr(34) + ' /Engine/Maps/Entry'
            if getattr(self.args, "ue_disable_live_coding", False):
                arguments += ' -LiveCoding=false'
            command = (f"Start-Process -FilePath {quote(self.args.editor.resolve())} "
                       f"-ArgumentList {quote(arguments)} "
                       "-WindowStyle Hidden -PassThru | Select-Object Id | ConvertTo-Json -Compress")
            self.emit("running", operation="ue_start", startup_arguments=arguments)
            powershell_json(command)
            self.heavy_since_restart = 0
            self.remote("import unreal; print('WARDROBE_AUTOMATION_READY')", "ue_start_ready", 180)
        self.remote("import unreal; "
                    "assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'Unsaved map'; "
                    "assert not unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages(), 'Unsaved content'; "
                    "assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Engine/Maps/Entry'); "
                    "unreal.SystemLibrary.collect_garbage()", "ue_clean_workspace")

    def memory_gate(self, ue=False, minimum_gib=None):
        minimum = self.args.min_free_commit_gib if minimum_gib is None else minimum_gib
        self.check_disk()
        if ue and (self.heavy_since_restart >= 4 or free_commit_gib() < minimum):
            self.stop_ue()
            self.ensure_ue()
        deadline = time.monotonic() + 1800
        while free_commit_gib() < minimum:
            self.emit("waiting_memory", free_commit_gib=round(free_commit_gib(), 2),
                      required_free_commit_gib=minimum)
            if time.monotonic() >= deadline:
                raise MemoryError("Commit headroom insufficient for 30 minutes; CC left untouched")
            time.sleep(60)

    def export_batch(self, batch):
        if (batch / "ue_import.json").exists():
            return
        self.stop_ue()
        self.memory_gate()
        output = ROOT / "00_engine/outputs/character_creator_bridge/artifacts/wardrobe_average" / self.run_root.name / batch.name
        result_path = output / "validation_result.json"
        if not result_path.exists():
            health = subprocess.run([sys.executable, str(CC_CLIENT), "health"], cwd=ROOT,
                                    capture_output=True, text=True, encoding="utf-8")
            data = json.loads(health.stdout)
            if health.returncode or not data.get("healthy") or data.get("heartbeat", {}).get("busy"):
                raise RuntimeError("CC bridge is unavailable or busy; no CC restart attempted")
            preset_outputs = [p["production_output"] for p in read(batch / "cc_export.json")["presets"]]
            if any(Path(o["project_path"]).exists() or Path(o["export_root"]).exists() for o in preset_outputs):
                raise FileExistsError("Incomplete CC batch has output assets; inspect before retrying, no overwrite")
            staging = SCRIPTS / "character_creator/runtime_staging" / self.run_root.name / batch.name
            staging.mkdir(parents=True, exist_ok=True)
            target = staging / "cc_export.json"
            if not target.exists():
                shutil.copyfile(batch / "cc_export.json", target)
            if file_hash(target) != file_hash(batch / "cc_export.json"):
                raise ValueError("Staged CC manifest differs")
            self.python(CC_CLIENT, ["validate-bodies", "--library-file", target, "--output-dir", output,
                                    "--confirm-scene-replace", "--auto-dismiss-undo-warning", "--timeout", "21600",
                                    "--job-id", f"{self.run_root.name}-{batch.name}"], f"cc_{batch.name}")
        if read(result_path).get("success") is not True:
            raise ValueError(f"CC export did not pass: {result_path}")
        self.python(SCRIPTS / "character_creator/cc_prepare_wardrobe_batch_v1.py",
                    ["--library-dir", self.library, "--batch-dir", batch, "--finalize-result", result_path],
                    f"finalize_{batch.name}")

    def phase(self, batch, phase, unit=None):
        report = self.reports / batch.name
        path = report / (f"{unit}_{PHASE_TO_MODE[phase]}.json" if unit else "preflight.json")
        if stage_complete(path, phase, unit):
            return
        minimum = self.args.min_free_commit_gib
        if phase in {"preflight", "materials", "validate"}:
            lightweight = getattr(self.args, "min_free_lightweight_commit_gib", None)
            if lightweight is not None:
                minimum = lightweight
        self.memory_gate(ue=True, minimum_gib=minimum)
        args = ["--project", self.args.project.stem, "--manifest", batch / "ue_import.json",
                "--report-root", report, "--phase", phase]
        if unit:
            args += ["--case-id", unit]
        if phase == "reference":
            args.append("--auto-dialogs")
        self.python(SCRIPTS / "unreal/run_modular_outfit_pilot_import_v1.py", args,
                    f"{batch.name}_{unit or 'all'}_{phase}")
        if not stage_complete(path, phase, unit):
            raise RuntimeError(f"Missing successful stage report: {path}")
        if phase in {"reference", "split"}:
            self.heavy_since_restart += 1

    def transfer_batch(self, batch):
        mapping = self.reports / batch.name / "wardrobe_modules.json"
        if mapping.exists():
            return  # Initial audit already verified published mappings and sources.
        if getattr(self.args, "one_ue_batch", False):
            if not (batch / "ue_import.json").exists():
                raise RuntimeError("UE-only supervision requires a finalized CC batch")
        else:
            self.export_batch(batch)
        self.ensure_ue()
        self.emit("running", batch=batch.name, units=batch_unit_ids(batch))
        self.phase(batch, "preflight")
        for unit in batch_unit_ids(batch):
            for phase in ("reference", "split", "materials", "validate"):
                self.phase(batch, phase, unit)
        self.python(SCRIPTS / "unreal/validate_wardrobe_import_batch_v1.py",
                    ["--manifest", batch / "ue_import.json", "--report-root", self.reports / batch.name],
                    f"aggregate_{batch.name}")
        self.state["completed_batches"].append(batch.name)
        self.emit("batch_completed", batch=batch.name)

    def select_schedule(self):
        path = self.run_root / "execution_policy.json"
        policy = read(path) if path.exists() else {"schedule": "interleaved"}
        saved = policy["schedule"]
        schedule = getattr(self.args, "schedule", None) or saved
        if schedule not in {"interleaved", "export_only"}:
            raise ValueError(f"Unknown wardrobe schedule: {schedule}")
        requested = getattr(self.args, "auto_defer_missing_weight_maps", None)
        self.auto_defer_missing_weight_maps = (policy.get("auto_defer_missing_weight_maps", False)
                                              if requested is None else requested)
        requested_assets = getattr(self.args, "auto_defer_asset_export_errors", None)
        self.auto_defer_asset_export_errors = (policy.get("auto_defer_asset_export_errors", False)
                                               if requested_assets is None else requested_assets)
        write_json(path, {"schema_version": 1, "schedule": schedule,
                          "auto_defer_missing_weight_maps": self.auto_defer_missing_weight_maps,
                          "auto_defer_asset_export_errors": self.auto_defer_asset_export_errors})
        self.emit("running", schedule=schedule, previous_schedule=saved)
        return schedule

    def new_batches(self, authority):
        remaining = remaining_units(self.library)
        number = max((int(p.name.split('_')[1]) for p in self.library.glob("batch_*") if p.is_dir()), default=0)
        for index in range(0, len(remaining), self.args.batch_size):
            self.check_disk()
            if {name: file_hash(self.library / name) for name in authority} != authority:
                raise ValueError("Master library changed while the run was active")
            number += 1
            batch = self.library / f"batch_{number:03d}"
            args = ["--library-dir", self.library, "--batch-dir", batch]
            for unit in remaining[index:index + self.args.batch_size]:
                args += ["--unit-id", unit]
            self.python(SCRIPTS / "character_creator/cc_prepare_wardrobe_batch_v1.py", args, f"prepare_{batch.name}")
            yield batch

    def load_cc_deferrals(self):
        path = self.run_root / "deferred_cc_batches.json"
        records = read(path) if path.exists() else {}
        known = {b.name: b for b in self.library.glob("batch_*") if b.is_dir()}
        for name in getattr(self.args, "defer_cc_batch", []) or []:
            if name not in known:
                raise ValueError(f"Unknown CC batch for explicit deferral: {name}")
            if name in records:
                continue
            batch = known[name]
            report = ROOT / "00_engine/outputs/character_creator_bridge/artifacts/wardrobe_average" / self.run_root.name / name / "validation_result.json"
            result = read(report)
            ids = batch_unit_ids(batch)
            failed = [item for item in result.get("results", []) if item.get("success") is False]
            if (result.get("success") is not False or not failed
                    or {item.get("case_id") for item in result.get("results", [])} != set(ids)
                    or (batch / "ue_import.json").exists()):
                raise ValueError(f"Deferral requires a failed, unfinalized CC batch: {name}")
            records[name] = {"case_ids": ids, "manifest_sha256": file_hash(batch / "cc_export.json"),
                             "failed_cases": failed, "report": str(report), "report_sha256": file_hash(report)}
        active = {}
        for name, record in records.items():
            if (name not in known or batch_unit_ids(known[name]) != record["case_ids"]
                    or file_hash(known[name] / "cc_export.json") != record["manifest_sha256"]
                    or file_hash(Path(record["report"])) != record["report_sha256"]):
                raise ValueError(f"Deferred CC evidence changed: {name}")
            if not (known[name] / "ue_import.json").exists():
                active[name] = record
        if records:
            write_json(path, records)
        self.deferred_cc = active
        self.emit("running", deferred_cc_batches=list(active),
                  deferred_cc_units=sum(len(r["case_ids"]) for r in active.values()))

    def is_missing_weight_map_failure(self, batch):
        report = ROOT / "00_engine/outputs/character_creator_bridge/artifacts/wardrobe_average" / self.run_root.name / batch.name / "validation_result.json"
        try:
            summary = read(report)
            presets = {p["preset_id"]: p for p in read(batch / "cc_export.json")["presets"]}
            results = summary.get("results", [])
            if (summary.get("success") is not False or summary.get("phase") != "complete"
                    or len(results) != len(presets) or {r["case_id"] for r in results} != set(presets)):
                return False
            failures = [r for r in results if r.get("success") is False]
            if not failures or summary.get("failure_count") != len(failures):
                return False
            for row in failures:
                output = presets[row["case_id"]]["production_output"]
                root, base = Path(output["export_root"]), output["export_basename"]
                expected = f"Expected outfit export directory is empty: {root / 'textures'}"
                if (row.get("error", {}).get("type") != "ReconstructionError"
                        or row["error"].get("message") != expected
                        or not (root / "textures").is_dir()
                        or any(p.is_file() for p in (root / "textures").rglob("*"))
                        or not (root / (base + ".fbx")).is_file()
                        or (root / (base + ".fbx")).stat().st_size == 0):
                    return False
                value = json.loads((root / (base + ".json")).read_text(encoding="utf-8-sig"))
                refs = []
                def walk(item):
                    if isinstance(item, dict):
                        for key, child in item.items():
                            if key in {"Texture Path", "Weight Map Path"} and child:
                                refs.append((key, child))
                            walk(child)
                    elif isinstance(item, list):
                        for child in item:
                            walk(child)
                walk(value)
                missing = []
                material_count = 0
                for key, relative in refs:
                    if not isinstance(relative, str):
                        return False
                    target = (root / relative.replace("\\", "/")).resolve()
                    if root.resolve() not in target.parents:
                        return False
                    if key == "Texture Path":
                        material_count += 1
                    if not target.is_file() or target.stat().st_size == 0:
                        missing.append(key)
                if not material_count or not missing or set(missing) != {"Weight Map Path"}:
                    return False
            return True
        except (OSError, ValueError, KeyError, TypeError):
            return False

    def is_isolated_asset_export_failure(self, batch):
        report = ROOT / "00_engine/outputs/character_creator_bridge/artifacts/wardrobe_average" / self.run_root.name / batch.name / "validation_result.json"
        try:
            summary = read(report)
            rows = summary.get("results", [])
            ids = batch_unit_ids(batch)
            failed = [r for r in rows if r.get("success") is False]
            if (summary.get("success") is not False or summary.get("phase") != "complete"
                    or summary.get("blocked") is not False or not failed
                    or len(rows) != len(ids) or {r["case_id"] for r in rows} != set(ids)
                    or summary.get("failure_count") != len(failed)
                    or not any(r.get("success") is True for r in rows)
                    or (report.parent / "fatal_dialog.json").exists()):
                return False
            expected = "Export first-batch FullReference character failed: {'returned': True, 'is_error': True, 'status_code': '1'}"
            for row in failed:
                if row.get("error", {}).get("type") != "ReconstructionError" or row["error"].get("message") != expected:
                    return False
                case = read(Path(row["result_path"]))
                if case.get("case_id") != row["case_id"] or case.get("success") is not False:
                    return False
                project = case.get("production_project", {})
                if not project.get("sha256") or file_hash(Path(project["path"])) != project["sha256"]:
                    return False
            return True
        except (OSError, ValueError, KeyError, TypeError):
            return False

    def process_export_with_deferral(self, batch):
        try:
            self.export_batch(batch)
        except (RuntimeError, ValueError):
            reason = None
            if self.auto_defer_missing_weight_maps and self.is_missing_weight_map_failure(batch):
                reason = "deferred_missing_physics_weight_map"
            elif self.auto_defer_asset_export_errors and self.is_isolated_asset_export_failure(batch):
                reason = "deferred_isolated_cc_export_error"
            if reason is None:
                raise
            self.args.defer_cc_batch = [batch.name]
            self.load_cc_deferrals()
            self.emit("running", operation=reason, batch=batch.name)

    def process_batches(self, authority, schedule):
        export_only = schedule == "export_only"
        if self.deferred_cc and not export_only:
            raise RuntimeError("Resolve deferred CC batches before resuming UE imports")
        if export_only:
            self.stop_ue()
        self.emit("running", workflow_stage="cc_export" if export_only else "interleaved_transfer")
        process = self.process_export_with_deferral if export_only else self.transfer_batch
        for batch in sorted(self.library.glob("batch_*")):
            if batch.is_dir():
                if batch.name in self.deferred_cc:
                    self.emit("running", batch=batch.name, operation="deferred_failed_cc_batch")
                    continue
                self.emit("running", batch=batch.name)
                process(batch)
        for batch in self.new_batches(authority):
            self.emit("running", batch=batch.name)
            process(batch)
        final = audit(self.library, self.reports)
        if export_only:
            deferred_units = sum(len(r["case_ids"]) for r in self.deferred_cc.values())
            prefix = "audit_cc_incomplete" if deferred_units else "audit_cc_complete"
            path = self.run_root / f"{prefix}_{time.time_ns()}.json"
            write_json(path, final)
            if final["cc_exported_units"] + deferred_units != final["total_units"]:
                raise RuntimeError("CC-only audit did not cover every unit; UE import remains disabled")
            self.emit("export_incomplete" if deferred_units else "export_complete", cc_units=final["cc_exported_units"],
                      ue_units=final["ue_transferred_units"], audit=str(path),
                      next_action="resolve_deferred_cc_batches" if deferred_units else "user_export_review_before_ue_import")
            return
        write_json(self.run_root / "audit_complete.json", final)
        if final["ue_transferred_units"] != final["total_units"]:
            raise RuntimeError("Full-library audit did not cover every unit")
        self.emit("transfer_complete", cc_units=final["cc_exported_units"], ue_units=final["ue_transferred_units"],
                  next_action="full_library_manual_fit_review")

    def process_one_cc_batch(self, authority, schedule):
        if schedule != "export_only":
            raise ValueError("Single-batch supervision requires export_only")
        pending = [b for b in sorted(self.library.glob("batch_*")) if b.is_dir()
                   and b.name not in self.deferred_cc and not (b / "ue_import.json").exists()]
        batch = pending[0] if pending else next(self.new_batches(authority), None)
        if batch is None:
            self.process_batches(authority, schedule)
            return
        self.emit("running", workflow_stage="cc_export", batch=batch.name)
        # One explicit operation per invocation; failures must be inspected by the caller.
        self.export_batch(batch)
        self.emit("awaiting_batch_review", operation="single_batch_finalized", batch=batch.name,
                  units=batch_unit_ids(batch), next_action="assistant_review_before_next_batch")

    def process_one_ue_batch(self, authority, schedule):
        if schedule != "interleaved" or self.deferred_cc:
            raise ValueError("UE-only supervision requires import-enabled policy and no CC deferrals")
        batches = [b for b in sorted(self.library.glob("batch_*")) if b.is_dir()]
        if remaining_units(self.library) or any(not (b / "ue_import.json").exists() for b in batches):
            raise RuntimeError("Finish all CC exports before UE-only supervision; no CC call attempted")
        if {name: file_hash(self.library / name) for name in authority} != authority:
            raise ValueError("Master library changed before UE-only batch")
        batch = next((b for b in batches if not (self.reports / b.name / "wardrobe_modules.json").exists()), None)
        if batch is not None:
            self.emit("running", workflow_stage="ue_transfer_only", batch=batch.name)
            self.transfer_batch(batch)
        final = audit(self.library, self.reports)
        path = self.run_root / f"audit_ue_{batch.name if batch else 'complete'}_{time.time_ns()}.json"
        write_json(path, final)
        complete = final["ue_transferred_units"] == final["total_units"]
        self.emit("transfer_complete" if complete else "awaiting_batch_review",
                  operation="single_ue_batch_checked", cc_units=final["cc_exported_units"],
                  ue_units=final["ue_transferred_units"], audit=str(path),
                  next_action="full_library_manual_fit_review" if complete else "assistant_review_before_next_batch")

    def execute(self):
        if getattr(self.args, "one_cc_batch", False) and getattr(self.args, "one_ue_batch", False):
            raise ValueError("Select only one single-batch mode")
        authority = {name: file_hash(self.library / name)
                     for name in ("cc_export.json", "ue_import.json", "wardrobe_registry.json")}
        lock_path = self.run_root / "input_lock.json"
        if lock_path.exists() and read(lock_path) != authority:
            raise ValueError("Master library changed since this continuous run started")
        if not lock_path.exists():
            write_json(lock_path, authority)
        self.emit("running", operation="initial_audit")
        initial = audit(self.library, self.reports)
        write_json(self.run_root / f"audit_start_{time.time_ns()}.json", initial)
        self.emit("running", initial_cc_units=initial["cc_exported_units"],
                  initial_ue_units=initial["ue_transferred_units"], total_units=initial["total_units"])
        schedule = self.select_schedule()
        self.load_cc_deferrals()
        if getattr(self.args, "one_cc_batch", False):
            self.process_one_cc_batch(authority, schedule)
        elif getattr(self.args, "one_ue_batch", False):
            self.process_one_ue_batch(authority, schedule)
        else:
            self.process_batches(authority, schedule)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library-dir", type=Path, required=True)
    parser.add_argument("--report-root", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--project", type=Path, default=Path(r"D:\UE\projects\datatry_02\datatry_02.uproject"))
    parser.add_argument("--editor", type=Path, default=Path(r"D:\UE\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"))
    parser.add_argument("--batch-size", type=int, choices=range(1, 7), default=3)
    parser.add_argument("--one-cc-batch", action="store_true",
                        help="Export/finalize at most one batch, then return for direct caller review; no auto-deferral")
    parser.add_argument("--one-ue-batch", action="store_true",
                        help="Import at most one already exported batch, audit and return for direct review; never calls CC")
    parser.add_argument("--ue-disable-live-coding", action="store_true",
                        help="Pass -LiveCoding=false only when starting UE; do not change preferences or restart an existing editor")
    parser.add_argument("--min-free-commit-gib", type=float, default=6)
    parser.add_argument("--min-free-lightweight-commit-gib", type=float,
                        help="Optional lower UE preflight/materials/validation headroom; imports and CC keep the main threshold")
    parser.add_argument("--min-free-disk-gib", type=float, default=20)
    parser.add_argument("--schedule", choices=("interleaved", "export_only"),
                        help="Persist scheduling policy; omitted resumes the previous policy")
    parser.add_argument("--defer-cc-batch", action="append", default=[],
                        help="Explicitly defer an inspected failed batch without marking its units complete")
    parser.add_argument("--auto-defer-missing-weight-maps", action=argparse.BooleanOptionalAction, default=None,
                        help="Persist narrowly checked physics-weight-map deferral; all other failures still block")
    parser.add_argument("--auto-defer-asset-export-errors", action=argparse.BooleanOptionalAction, default=None,
                        help="Defer exact CC export errors only in finished mixed-success batches, preserving failure evidence")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if (args.min_free_lightweight_commit_gib is not None
            and not 0 < args.min_free_lightweight_commit_gib <= args.min_free_commit_gib):
        parser.error("Lightweight commit headroom must be positive and no greater than --min-free-commit-gib")
    if not args.execute:
        print(json.dumps({"unallocated_units": len(remaining_units(args.library_dir)), "execute": False}))
        return
    if os.name != "nt":
        raise RuntimeError("Desktop runner requires Windows")
    import msvcrt
    args.report_root.mkdir(parents=True, exist_ok=True)
    args.run_root.mkdir(parents=True, exist_ok=True)
    with (args.report_root / ".wardrobe_runner.lock").open("a+b") as lock:
        lock.seek(0)
        if lock.read(1) == b"":
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        runner = Runner(args)
        try:
            runner.execute()
        except BaseException as exc:
            runner.emit("blocked", error=str(exc), operation=runner.state.get("operation"))
            raise


if __name__ == "__main__":
    main()
