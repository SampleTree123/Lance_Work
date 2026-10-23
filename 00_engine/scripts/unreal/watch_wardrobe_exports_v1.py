"""Persistent CC-only supervisor. Never starts, stops or restarts desktop apps.

psutil is required. Unknown failures need diagnosis; only resource-gate failures
are retried. The worker retains hash checks, non-overwrite guards and deferrals.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import psutil

from run_wardrobe_library_v1 import ROOT, CC_CLIENT, free_commit_gib
from run_modular_outfit_pilot_import_v1 import write_json

WORKER = Path(__file__).with_name("run_wardrobe_library_v1.py")
TERMINAL = {"export_complete", "export_incomplete", "transfer_complete"}


def read_optional(path):
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}


def retry_reason(state):
    if state.get("status") != "blocked":
        return None
    error = state.get("error", "")
    if error.startswith("Disk free ") and error.endswith("; no automatic deletion"):
        return "disk"
    if error == "Commit headroom insufficient for 30 minutes; CC left running":
        return "memory"
    if error == "CC bridge is unavailable or busy; no CC restart attempted":
        return "bridge"
    return None


def decision(state, workers, children, healthy_idle, resources_ok, ue_open,
             paused, bootstrap, attempts):
    if workers:
        return "observing" if workers == 1 else "needs_attention_multiple_workers"
    if paused:
        return "paused"
    if children:
        return "waiting_child_process"
    if state.get("status") in TERMINAL:
        return "finished_with_deferrals" if state["status"] == "export_incomplete" else "finished"
    if not bootstrap and retry_reason(state) is None:
        return "needs_attention"
    if not bootstrap and attempts >= 3:
        return "needs_attention_retry_limit"
    if ue_open:
        return "waiting_ue_closed"
    if not healthy_idle:
        return "waiting_cc_idle"
    if not resources_ok:
        return "waiting_resources"
    return "start_worker"


def processes():
    workers, children, ue = [], [], []
    for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
        try:
            info = proc.info
            if info["name"].lower() == "unrealeditor.exe":
                ue.append(info)
            command = info["cmdline"] or []
            if any(Path(arg).name == WORKER.name for arg in command):
                workers.append(info)
            if any(Path(arg).name == CC_CLIENT.name for arg in command) and "validate-bodies" in command:
                children.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return workers, children, ue


def inventory(library, run_root):
    finalized = allocated = 0
    for batch in library.glob("batch_*"):
        if not batch.is_dir():
            continue
        units = len(read_optional(batch / "cc_export.json").get("presets", []))
        allocated += units
        if (batch / "ue_import.json").is_file():
            finalized += units
    held = read_optional(run_root / "deferred_cc_batches.json")
    active = {k: v for k, v in held.items() if not (library / k / "ue_import.json").exists()}
    return {"count_basis": "lightweight_manifest_inventory_not_hash_audit",
            "total_units": len(read_optional(library / "cc_export.json").get("presets", [])),
            "finalized_units": finalized, "allocated_units": allocated,
            "deferred_units": sum(len(r["case_ids"]) for r in active.values()),
            "deferred_batches": list(active)}


def start_worker(args, output):
    stamp = str(time.time_ns())
    command = [sys.executable, str(WORKER), "--library-dir", str(args.library_dir),
               "--report-root", str(args.report_root), "--run-root", str(args.run_root),
               "--schedule", "export_only", "--auto-defer-missing-weight-maps",
               "--auto-defer-asset-export-errors", "--execute"]
    stdout, stderr = output / f"worker_{stamp}_stdout.log", output / f"worker_{stamp}_stderr.log"
    with stdout.open("w", encoding="utf-8") as out, stderr.open("w", encoding="utf-8") as err:
        proc = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=out,
                                stderr=err, creationflags=subprocess.CREATE_NO_WINDOW)
    return {"pid": proc.pid, "started_at": time.time(), "command": command,
            "stdout": str(stdout), "stderr": str(stderr)}


class Monitor:
    def __init__(self, args):
        self.args = args
        self.output = args.run_root / "monitor"
        self.output.mkdir(parents=True, exist_ok=True)
        self.ledger = read_optional(self.output / "recovery.json")
        self.last_progress = time.monotonic()
        self.last_signature = None

    def emit(self, **fields):
        data = {"updated_at_utc": datetime.now(timezone.utc).isoformat(),
                "monitor_pid": os.getpid(), "interval_seconds": self.args.interval_seconds, **fields}
        write_json(self.output / "state.json", data)
        with (self.output / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(data, ensure_ascii=True) + "\n")
        print(json.dumps(data, ensure_ascii=True), flush=True)

    def tick(self):
        state = read_optional(self.args.run_root / "state.json")
        workers, children, ue = processes()
        health = subprocess.run([sys.executable, str(CC_CLIENT), "health"], cwd=ROOT,
                                capture_output=True, text=True, encoding="utf-8", timeout=20)
        cc = json.loads(health.stdout) if health.stdout.strip() else {}
        heartbeat = cc.get("heartbeat", {})
        idle = bool(health.returncode == 0 and cc.get("healthy") and not heartbeat.get("busy")
                    and not heartbeat.get("queue_depth"))
        free_disk = shutil.disk_usage(self.args.library_dir).free / 1024**3
        free_commit = free_commit_gib()
        counts = inventory(self.args.library_dir, self.args.run_root)
        signature = (state.get("batch"), state.get("operation"), state.get("updated_at_utc"),
                     counts["finalized_units"], tuple(counts["deferred_batches"]))
        if signature != self.last_signature:
            self.last_signature, self.last_progress = signature, time.monotonic()
        key = json.dumps([state.get("batch"), state.get("operation"), retry_reason(state)])
        attempts = self.ledger.get("attempts", {}).get(key, 0)
        bootstrap = self.args.start_worker and not self.ledger.get("bootstrap_consumed")
        action = decision(state, len(workers), len(children), idle,
                          free_disk >= 20 and free_commit >= 6, bool(ue),
                          (self.output / "PAUSE").exists(), bootstrap, attempts)
        # A restarted supervisor must not reuse its initial start authorization.
        if workers and bootstrap:
            self.ledger["bootstrap_consumed"] = True
            write_json(self.output / "recovery.json", self.ledger)
        if action == "start_worker":
            self.ledger["bootstrap_consumed"] = True
            self.ledger.setdefault("attempts", {})[key] = attempts + 1
            write_json(self.output / "recovery.json", self.ledger)
            self.ledger["last_worker"] = start_worker(self.args, self.output)
            write_json(self.output / "recovery.json", self.ledger)
        cc_process = None
        try:
            proc = psutil.Process(heartbeat["pid"])
            cc_process = {"pid": proc.pid, "create_time": proc.create_time(),
                          "rss_gib": round(proc.memory_info().rss / 1024**3, 2),
                          "cpu_seconds": sum(proc.cpu_times()[:2])}
        except (KeyError, psutil.Error):
            pass
        self.emit(status=action, worker_state=state, workers=workers, cc=cc, cc_process=cc_process,
                  ue_pids=[p["pid"] for p in ue], inventory=counts,
                  free_disk_gib=round(free_disk, 2), free_commit_gib=round(free_commit, 2),
                  recovery_attempts=attempts, last_worker=self.ledger.get("last_worker"),
                  stalled_warning=bool(workers and time.monotonic() - self.last_progress > 1200),
                  safety="No CC lifecycle actions, no UE launch, no overwrite, no false acceptance")
        return action


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("library-dir", "report-root", "run-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--interval-seconds", type=int, default=60)
    parser.add_argument("--start-worker", action="store_true", help="One initial authorized resume; persisted once")
    args = parser.parse_args()
    if os.name != "nt" or args.interval_seconds < 10:
        raise RuntimeError("Windows required; minimum polling interval is 10 seconds")
    import msvcrt
    monitor = Monitor(args)
    with (monitor.output / ".monitor.lock").open("a+b") as lock:
        lock.seek(0)
        if not lock.read(1):
            lock.write(b"0")
            lock.flush()
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        while not (monitor.output / "STOP").exists():
            try:
                action = monitor.tick()
                if action in {"finished", "finished_with_deferrals"}:
                    return
            except Exception as exc:
                monitor.emit(status="monitor_check_failed", error=repr(exc))
            time.sleep(args.interval_seconds)
        monitor.emit(status="monitor_stopped", worker_left_untouched=True)


if __name__ == "__main__":
    main()
