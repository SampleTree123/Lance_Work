import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import watch_wardrobe_exports_v1 as monitor


def choose(state=None, **changes):
    args = dict(state=state or {}, workers=0, children=0, healthy_idle=True,
                resources_ok=True, ue_open=False, paused=False, bootstrap=False, attempts=0)
    args.update(changes)
    return monitor.decision(**args)


def test_unknown_or_orphaned_run_never_blindly_restarted():
    assert choose({"status": "running"}) == "needs_attention"
    assert choose({"status": "blocked", "error": "Partial output"}) == "needs_attention"


@pytest.mark.parametrize("error", [
    "Disk free 5.00 GiB < 20 GiB; no automatic deletion",
    "Commit headroom insufficient for 30 minutes; CC left running",
    "CC bridge is unavailable or busy; no CC restart attempted",
])
def test_resource_recovery_bounded_and_gated(error):
    state = {"status": "blocked", "error": error}
    assert choose(state) == "start_worker"
    assert choose(state, attempts=3) == "needs_attention_retry_limit"
    assert choose(state, healthy_idle=False) == "waiting_cc_idle"
    assert choose(state, resources_ok=False) == "waiting_resources"
    assert choose(state, ue_open=True) == "waiting_ue_closed"
    assert choose(state, paused=True) == "paused"


def test_initial_resume_never_duplicates_or_starts_import():
    assert choose(bootstrap=True) == "start_worker"
    assert choose(bootstrap=True, workers=1) == "observing"
    assert choose(bootstrap=True, workers=2) == "needs_attention_multiple_workers"
    assert choose(bootstrap=True, children=1) == "waiting_child_process"
    assert choose({"status": "export_complete"}, bootstrap=True) == "finished"
    assert choose({"status": "export_incomplete"}, bootstrap=True) == "finished_with_deferrals"


def test_inventory_does_not_count_deferred_cases_as_finalized(tmp_path):
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
    lib, run = tmp_path / "lib", tmp_path / "run"
    write(lib / "cc_export.json", {"presets": [1, 2, 3, 4]})
    write(lib / "batch_001/cc_export.json", {"presets": [1]})
    write(lib / "batch_001/ue_import.json", {})
    write(lib / "batch_002/cc_export.json", {"presets": [2, 3]})
    write(run / "deferred_cc_batches.json", {"batch_002": {"case_ids": [2, 3]}})
    result = monitor.inventory(lib, run)
    assert (result["finalized_units"], result["allocated_units"], result["deferred_units"]) == (1, 3, 2)
    assert result["count_basis"] == "lightweight_manifest_inventory_not_hash_audit"


def test_worker_command_is_cc_only_and_hidden(tmp_path, monkeypatch):
    from types import SimpleNamespace
    captured = {}
    def launch(command, **kwargs):
        captured.update(command=command, kwargs=kwargs)
        return SimpleNamespace(pid=123)
    monkeypatch.setattr(monitor.subprocess, "Popen", launch)
    monkeypatch.setattr(monitor.subprocess, "CREATE_NO_WINDOW", 0x8000000, raising=False)
    args = SimpleNamespace(library_dir=tmp_path, report_root=tmp_path, run_root=tmp_path)
    assert monitor.start_worker(args, tmp_path)["pid"] == 123
    command = captured["command"]
    assert command[command.index("--schedule") + 1] == "export_only"
    assert captured["kwargs"]["creationflags"] == 0x8000000
    assert "--auto-defer-asset-export-errors" in command
