import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("wardrobe_continuous", SCRIPTS / "run_wardrobe_library_v1.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def library(tmp_path, ids):
    write(tmp_path / "cc_export.json", {"presets": [{"preset_id": uid} for uid in ids]})


def test_remaining_preserves_master_order_and_excludes_allocated(tmp_path):
    library(tmp_path, ["c", "a", "b"])
    library(tmp_path / "batch_001", ["a"])
    assert runner.remaining_units(tmp_path) == ["c", "b"]


@pytest.mark.parametrize("ids", [["unknown"], ["a", "a"]])
def test_invalid_allocation_rejected(tmp_path, ids):
    library(tmp_path, ["a", "b"])
    library(tmp_path / "batch_001", ids)
    with pytest.raises(ValueError):
        runner.remaining_units(tmp_path)


def test_cross_batch_duplicates_rejected(tmp_path):
    library(tmp_path, ["a"])
    library(tmp_path / "batch_001", ["a"])
    library(tmp_path / "batch_002", ["a"])
    with pytest.raises(ValueError):
        runner.remaining_units(tmp_path)


def test_stage_skip_requires_success_identity_and_mode(tmp_path):
    path = tmp_path / "stage.json"
    assert not runner.stage_complete(path, "split", "a")
    write(path, {"success": True, "mode": "import_split", "case_id": "a"})
    assert runner.stage_complete(path, "split", "a")
    for value in ({"success": False, "mode": "import_split", "case_id": "a"},
                  {"success": True, "mode": "import_split", "case_id": "b"},
                  {"success": True, "mode": "apply_materials", "case_id": "a"}):
        write(path, value)
        with pytest.raises(ValueError):
            runner.stage_complete(path, "split", "a")


def instance(tmp_path):
    return runner.Runner(SimpleNamespace(library_dir=tmp_path / "library", report_root=tmp_path / "reports",
                         run_root=tmp_path / "run", min_free_commit_gib=6, min_free_disk_gib=20,
                         project=tmp_path / "p.uproject", editor=tmp_path / "UnrealEditor.exe"))


@pytest.mark.parametrize("disabled", [None, False, True])
def test_ue_live_coding_startup_option_is_opt_in_and_reused_on_restart(tmp_path, monkeypatch, disabled):
    obj = instance(tmp_path)
    if disabled is not None:
        obj.args.ue_disable_live_coding = disabled
    commands, events, remotes = [], [], []
    monkeypatch.setattr(obj, "current_ue", lambda: [])
    monkeypatch.setattr(runner, "powershell_json", lambda command: commands.append(command))
    monkeypatch.setattr(obj, "emit", lambda status, **fields: events.append(fields))
    monkeypatch.setattr(obj, "remote", lambda command, label, *args: remotes.append((command, label)))
    for _ in range(2):
        obj.heavy_since_restart = 4
        obj.ensure_ue()
        assert obj.heavy_since_restart == 0
    assert len(commands) == 2
    assert [label for _, label in remotes] == ["ue_start_ready", "ue_clean_workspace"] * 2
    for command, event in zip(commands, events):
        assert "-WindowStyle Hidden" in command
        assert str(obj.args.project.resolve()) in command
        assert "/Engine/Maps/Entry" in command
        assert ("-LiveCoding=false" in command) == bool(disabled)
        assert ("-LiveCoding=false" in event["startup_arguments"]) == bool(disabled)
        assert event["operation"] == "ue_start"
        assert "-nosound" not in command
    for command, label in remotes:
        if label == "ue_clean_workspace":
            assert "get_dirty_map_packages" in command
            assert "get_dirty_content_packages" in command


def test_live_coding_flag_does_not_restart_existing_editor(tmp_path, monkeypatch):
    obj = instance(tmp_path)
    obj.args.ue_disable_live_coding = True
    monkeypatch.setattr(obj, "current_ue", lambda: [ue_row(obj)])
    monkeypatch.setattr(runner, "powershell_json", lambda *a: pytest.fail("must not start or stop editor"))
    calls = []
    monkeypatch.setattr(obj, "remote", lambda command, label: calls.append(label))
    obj.ensure_ue()
    assert calls == ["ue_clean_workspace"]


def test_live_coding_cli_flag_is_accepted_without_starting_in_preview(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["run_wardrobe_library_v1.py", "--library-dir", str(tmp_path),
                        "--report-root", str(tmp_path), "--run-root", str(tmp_path),
                        "--ue-disable-live-coding"])
    monkeypatch.setattr(runner, "remaining_units", lambda path: ["a"])
    monkeypatch.setattr(runner.Runner, "execute", lambda *a: pytest.fail("preview must not execute"))
    runner.main()
    assert json.loads(capsys.readouterr().out) == {"unallocated_units": 1, "execute": False}


def test_memory_timeout_does_not_claim_cc_is_running(tmp_path, monkeypatch):
    obj = instance(tmp_path)
    monkeypatch.setattr(obj, "check_disk", lambda: None)
    monkeypatch.setattr(runner, "free_commit_gib", lambda: 1)
    times = iter([0, 1800])
    monkeypatch.setattr(runner.time, "monotonic", lambda: next(times))
    monkeypatch.setattr(obj, "emit", lambda *a, **kw: None)
    with pytest.raises(MemoryError, match="CC left untouched"):
        obj.memory_gate()


def test_memory_gate_restarts_only_ue_between_saved_operations(tmp_path, monkeypatch):
    obj = instance(tmp_path)
    events = []
    obj.heavy_since_restart = 4
    monkeypatch.setattr(obj, "check_disk", lambda: None)
    monkeypatch.setattr(obj, "stop_ue", lambda: events.append("stop_ue"))
    monkeypatch.setattr(obj, "ensure_ue", lambda: events.append("ensure_ue"))
    monkeypatch.setattr(runner, "free_commit_gib", lambda: 20)
    obj.memory_gate(ue=True)
    assert events == ["stop_ue", "ensure_ue"]


@pytest.mark.parametrize("phase,minimum", [("reference", 16), ("split", 16),
                                           ("preflight", 12), ("materials", 12), ("validate", 12)])
def test_phase_specific_memory_floor_preserves_every_stage(tmp_path, monkeypatch, phase, minimum):
    obj = instance(tmp_path)
    obj.args.min_free_commit_gib = 16
    obj.args.min_free_lightweight_commit_gib = 12
    checks = iter([False, True])
    monkeypatch.setattr(runner, "stage_complete", lambda *a: next(checks))
    gates, commands = [], []
    monkeypatch.setattr(obj, "memory_gate", lambda **kw: gates.append(kw))
    monkeypatch.setattr(obj, "python", lambda script, args, label: commands.append(args))
    obj.phase(tmp_path / "batch_001", phase, None if phase == "preflight" else "a")
    assert gates == [{"ue": True, "minimum_gib": minimum}]
    assert len(commands) == 1
    assert commands[0][commands[0].index("--phase") + 1] == phase
    assert ("--auto-dialogs" in commands[0]) == (phase == "reference")
    assert obj.heavy_since_restart == (1 if phase in {"reference", "split"} else 0)


def test_omitted_lightweight_floor_retains_legacy_threshold(tmp_path, monkeypatch):
    obj = instance(tmp_path)
    checks = iter([False, True])
    gates = []
    monkeypatch.setattr(runner, "stage_complete", lambda *a: next(checks))
    monkeypatch.setattr(obj, "memory_gate", lambda **kw: gates.append(kw))
    monkeypatch.setattr(obj, "python", lambda *a: None)
    obj.phase(tmp_path / "batch_001", "validate", "a")
    assert gates == [{"ue": True, "minimum_gib": 6}]


def test_lightweight_floor_does_not_restart_with_adequate_headroom(tmp_path, monkeypatch):
    obj = instance(tmp_path)
    obj.args.min_free_commit_gib = 16
    calls = []
    monkeypatch.setattr(obj, "check_disk", lambda: calls.append("disk"))
    monkeypatch.setattr(runner, "free_commit_gib", lambda: 14)
    monkeypatch.setattr(obj, "stop_ue", lambda: pytest.fail("adequate light-step headroom"))
    obj.memory_gate(ue=True, minimum_gib=12)
    assert calls == ["disk"]


def test_heavy_floor_still_restarts_with_only_lightweight_headroom(tmp_path, monkeypatch):
    obj = instance(tmp_path)
    obj.args.min_free_commit_gib = 16
    readings = iter([14, 20])
    calls = []
    monkeypatch.setattr(obj, "check_disk", lambda: None)
    monkeypatch.setattr(runner, "free_commit_gib", lambda: next(readings))
    monkeypatch.setattr(obj, "stop_ue", lambda: calls.append("stop"))
    monkeypatch.setattr(obj, "ensure_ue", lambda: calls.append("start"))
    obj.memory_gate(ue=True)
    assert calls == ["stop", "start"]


@pytest.mark.parametrize("value", ["0", "-1", "17", "nan", "inf"])
def test_invalid_lightweight_floor_rejected_before_any_work(tmp_path, monkeypatch, value):
    monkeypatch.setattr(sys, "argv", ["run_wardrobe_library_v1.py", "--library-dir", str(tmp_path),
                        "--report-root", str(tmp_path), "--run-root", str(tmp_path),
                        "--min-free-commit-gib", "16", "--min-free-lightweight-commit-gib", value])
    monkeypatch.setattr(runner, "remaining_units", lambda *a: pytest.fail("must not start work"))
    with pytest.raises(SystemExit) as exc:
        runner.main()
    assert exc.value.code == 2


def test_disk_floor_does_not_delete_outputs(tmp_path, monkeypatch):
    obj = instance(tmp_path)
    monkeypatch.setattr(runner.shutil, "disk_usage", lambda _path: SimpleNamespace(free=19 * 1024**3))
    with pytest.raises(OSError, match="no automatic deletion"):
        obj.check_disk()


def test_no_cc_lifecycle_commands_or_force_termination():
    source = (SCRIPTS / "run_wardrobe_library_v1.py").read_text(encoding="utf-8")
    assert "Stop-Process" not in source
    assert "taskkill" not in source
    assert "CharacterCreator.exe" not in source
    assert "-WindowStyle Hidden" in source
    assert "get_dirty_map_packages" in source
    assert "get_dirty_content_packages" in source


def test_background_handoff_targets_only_verified_coordinator():
    source = (SCRIPTS / "start_wardrobe_background_v1.ps1").read_text(encoding="utf-8")
    assert "Stop-Process -Id $CoordinatorId" in source
    assert "CreationDate -ne $created" in source
    assert "$target.CommandLine -ne $initial.CommandLine" in source
    assert "$envelope.command_result.success -eq $true" in source
    assert "ue_normal_exit" in source
    assert "-WindowStyle Hidden" in source
    assert "Stop-Process -Name" not in source
    assert "taskkill" not in source


def ue_row(obj, **changes):
    return {"ProcessId": 42, "CreationDate": "original_start",
            "CommandLine": f'"{obj.args.editor.resolve()}" "{obj.args.project.resolve()}"',
            "ExecutablePath": str(obj.args.editor.resolve()), **changes}


def test_normal_exit_tolerates_disappearing_metadata_only_after_verified_quit(tmp_path, monkeypatch):
    obj = instance(tmp_path)
    original = ue_row(obj)
    snapshots = iter([[original], [ue_row(obj, CommandLine=None, ExecutablePath=None,
                                        CreationDate=None)], []])
    monkeypatch.setattr(runner, "ue_processes", lambda: next(snapshots))
    monkeypatch.setattr(runner.time, "sleep", lambda _: None)
    calls = []
    monkeypatch.setattr(obj, "remote", lambda command, label: calls.append(label))
    monkeypatch.setattr(obj, "emit", lambda *a, **kw: calls.append(kw["exit_observation"]))
    obj.heavy_since_restart = 4
    obj.stop_ue()
    assert calls == ["ue_normal_exit", "verified_pid_metadata_disappearing"]
    assert obj.heavy_since_restart == 0


@pytest.mark.parametrize("changes", [{"CommandLine": None}, {"ExecutablePath": None},
                                    {"CreationDate": None}, {"CommandLine": "other.uproject"}])
def test_unverified_process_cannot_be_closed(tmp_path, monkeypatch, changes):
    obj = instance(tmp_path)
    monkeypatch.setattr(runner, "ue_processes", lambda: [ue_row(obj, **changes)])
    monkeypatch.setattr(obj, "remote", lambda *a: pytest.fail("must not issue quit"))
    with pytest.raises(RuntimeError):
        obj.stop_ue()


@pytest.mark.parametrize("changes", [{"ProcessId": 43}, {"CreationDate": "new_start"},
                                    {"CommandLine": "other.uproject"},
                                    {"ExecutablePath": "different.exe"}])
def test_exit_wait_rejects_replacement_or_wrong_project(tmp_path, monkeypatch, changes):
    obj = instance(tmp_path)
    monkeypatch.setattr(runner, "ue_processes", lambda: [ue_row(obj, **changes)])
    with pytest.raises(RuntimeError):
        obj.wait_for_ue_exit(ue_row(obj))


def test_exit_wait_rejects_multiple_editors(tmp_path, monkeypatch):
    obj = instance(tmp_path)
    monkeypatch.setattr(runner, "ue_processes", lambda: [ue_row(obj), ue_row(obj, ProcessId=43)])
    with pytest.raises(RuntimeError, match="process changed"):
        obj.wait_for_ue_exit(ue_row(obj))


def test_exit_wait_has_timeout_without_force_kill(tmp_path, monkeypatch):
    obj = instance(tmp_path)
    monkeypatch.setattr(runner, "ue_processes", lambda: [ue_row(obj)])
    times = iter([0, 180])
    monkeypatch.setattr(runner.time, "monotonic", lambda: next(times))
    with pytest.raises(TimeoutError, match="no force termination"):
        obj.wait_for_ue_exit(ue_row(obj))


def test_unsaved_quit_failure_never_enters_exit_wait(tmp_path, monkeypatch):
    obj = instance(tmp_path)
    monkeypatch.setattr(runner, "ue_processes", lambda: [ue_row(obj)])
    def fail_quit(*args):
        raise RuntimeError("Unsaved content")
    monkeypatch.setattr(obj, "remote", fail_quit)
    monkeypatch.setattr(obj, "wait_for_ue_exit", lambda *a: pytest.fail("quit did not succeed"))
    with pytest.raises(RuntimeError, match="Unsaved content"):
        obj.stop_ue()


def test_export_only_policy_persists_across_resume(tmp_path):
    obj = instance(tmp_path)
    obj.run_root.mkdir(parents=True)
    obj.args.schedule = "export_only"
    assert obj.select_schedule() == "export_only"
    resumed = instance(tmp_path)
    assert resumed.select_schedule() == "export_only"
    resumed.args.schedule = "interleaved"
    assert resumed.select_schedule() == "interleaved"


@pytest.mark.parametrize("schedule", ["export_only", "interleaved"])
def test_schedule_separates_exports_from_imports(tmp_path, monkeypatch, schedule):
    obj = instance(tmp_path)
    obj.run_root.mkdir(parents=True)
    existing = obj.library / "batch_001"
    existing.mkdir(parents=True)
    new = obj.library / "batch_002"
    calls = []
    monkeypatch.setattr(obj, "new_batches", lambda _: iter([new]))
    monkeypatch.setattr(obj, "stop_ue", lambda: calls.append("stop_ue"))
    monkeypatch.setattr(obj, "export_batch", lambda b: calls.append("cc_" + b.name))
    monkeypatch.setattr(obj, "transfer_batch", lambda b: calls.append("ue_" + b.name))
    monkeypatch.setattr(runner, "audit", lambda *a: {
        "total_units": 2, "cc_exported_units": 2, "ue_transferred_units": 2})
    obj.process_batches({}, schedule)
    if schedule == "export_only":
        assert calls == ["stop_ue", "cc_batch_001", "cc_batch_002"]
        assert obj.state["status"] == "export_complete"
        assert obj.state["next_action"] == "user_export_review_before_ue_import"
        assert not (obj.run_root / "audit_complete.json").exists()
    else:
        assert calls == ["ue_batch_001", "ue_batch_002"]
        assert obj.state["status"] == "transfer_complete"


def test_incomplete_cc_audit_never_starts_imports(tmp_path, monkeypatch):
    obj = instance(tmp_path)
    obj.run_root.mkdir(parents=True)
    monkeypatch.setattr(obj, "new_batches", lambda _: iter([]))
    monkeypatch.setattr(obj, "stop_ue", lambda: None)
    monkeypatch.setattr(obj, "transfer_batch", lambda b: pytest.fail("UE import prohibited"))
    monkeypatch.setattr(runner, "audit", lambda *a: {
        "total_units": 2, "cc_exported_units": 1, "ue_transferred_units": 0})
    with pytest.raises(RuntimeError, match="CC-only audit"):
        obj.process_batches({}, "export_only")
    assert obj.state["status"] != "export_complete"


def test_export_only_handoff_forwards_schedule():
    source = (SCRIPTS / "start_wardrobe_background_v1.ps1").read_text(encoding="utf-8")
    assert "[ValidateSet('interleaved', 'export_only')]" in source
    assert "' --schedule ' + $Schedule" in source
    assert "'NoProcessFoundForGivenId,*'" in source


def test_deferred_batch_is_not_exported_or_reported_as_complete(tmp_path, monkeypatch):
    obj = instance(tmp_path)
    obj.run_root.mkdir(parents=True)
    failed = obj.library / "batch_001"
    failed.mkdir(parents=True)
    obj.deferred_cc = {failed.name: {"case_ids": ["a", "b"]}}
    monkeypatch.setattr(obj, "stop_ue", lambda: None)
    monkeypatch.setattr(obj, "new_batches", lambda _: iter([obj.library / "batch_002"]))
    exports = []
    monkeypatch.setattr(obj, "export_batch", lambda b: exports.append(b.name))
    monkeypatch.setattr(runner, "audit", lambda *a: {
        "total_units": 3, "cc_exported_units": 1, "ue_transferred_units": 0})
    obj.process_batches({}, "export_only")
    assert exports == ["batch_002"]
    assert obj.state["status"] == "export_incomplete"
    assert obj.state["cc_units"] == 1
    assert not list(obj.run_root.glob("audit_cc_complete*"))
    with pytest.raises(RuntimeError, match="Resolve deferred"):
        obj.process_batches({}, "interleaved")


def test_deferral_requires_failed_report_and_locks_evidence(tmp_path, monkeypatch):
    obj = instance(tmp_path)
    obj.run_root.mkdir(parents=True)
    batch = obj.library / "batch_001"
    library(batch, ["a", "b"])
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    report = tmp_path / "00_engine/outputs/character_creator_bridge/artifacts/wardrobe_average/run/batch_001/validation_result.json"
    write(report, {"success": False, "results": [
        {"case_id": "a", "success": True}, {"case_id": "b", "success": False, "error": "missing file"}]})
    obj.args.defer_cc_batch = ["batch_001"]
    obj.load_cc_deferrals()
    assert obj.deferred_cc["batch_001"]["case_ids"] == ["a", "b"]
    resumed = instance(tmp_path)
    resumed.load_cc_deferrals()
    assert resumed.deferred_cc == obj.deferred_cc
    write(report, {"success": True})
    with pytest.raises(ValueError, match="evidence changed"):
        resumed.load_cc_deferrals()


@pytest.mark.parametrize("name", ["batch_404", "../batch_001"])
def test_deferral_rejects_unallocated_batch(tmp_path, name):
    obj = instance(tmp_path)
    obj.args.defer_cc_batch = [name]
    with pytest.raises(ValueError, match="Unknown CC batch"):
        obj.load_cc_deferrals()


def weight_map_failure(tmp_path, monkeypatch):
    obj = instance(tmp_path)
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    batch = obj.library / "batch_001"
    root = tmp_path / "fbx"
    (root / "textures").mkdir(parents=True)
    (root / "test.fbx").write_bytes(b"fbx")
    (root / "color.png").write_bytes(b"texture")
    write(root / "test.json", {"Texture Path": "./color.png", "Weight Map Path": "./textures/weight.png"})
    write(batch / "cc_export.json", {"presets": [{"preset_id": "a", "production_output": {
        "export_root": str(root), "export_basename": "test"}}]})
    report = tmp_path / "00_engine/outputs/character_creator_bridge/artifacts/wardrobe_average/run/batch_001/validation_result.json"
    write(report, {"success": False, "phase": "complete", "failure_count": 1, "results": [{
        "case_id": "a", "success": False, "error": {"type": "ReconstructionError",
        "message": f"Expected outfit export directory is empty: {root / 'textures'}"}}]})
    return obj, batch, root, report


def test_known_missing_weight_map_is_detected(tmp_path, monkeypatch):
    obj, batch, root, report = weight_map_failure(tmp_path, monkeypatch)
    assert obj.is_missing_weight_map_failure(batch)
    (root / "color.png").unlink()
    assert not obj.is_missing_weight_map_failure(batch)


@pytest.mark.parametrize("change", ["other_error", "partial_run", "no_weight_reference", "external_path", "zero_fbx"])
def test_unknown_or_incomplete_failure_is_never_auto_deferred(tmp_path, monkeypatch, change):
    obj, batch, root, report = weight_map_failure(tmp_path, monkeypatch)
    if change == "other_error":
        data = runner.read(report)
        data["results"][0]["error"]["message"] = "Unknown modal dialog"
        write(report, data)
    elif change == "partial_run":
        data = runner.read(report)
        data["phase"] = "running"
        write(report, data)
    elif change == "no_weight_reference":
        write(root / "test.json", {"Texture Path": "color.png"})
    elif change == "external_path":
        write(root / "test.json", {"Texture Path": "color.png", "Weight Map Path": "../outside.png"})
    else:
        (root / "test.fbx").write_bytes(b"")
    assert not obj.is_missing_weight_map_failure(batch)


def test_known_deferral_is_opt_in_and_other_errors_propagate(tmp_path, monkeypatch):
    obj = instance(tmp_path)
    def fail(batch):
        raise RuntimeError("failed CC export")
    monkeypatch.setattr(obj, "export_batch", fail)
    monkeypatch.setattr(obj, "is_missing_weight_map_failure", lambda b: True)
    with pytest.raises(RuntimeError):
        obj.process_export_with_deferral(tmp_path)
    obj.auto_defer_missing_weight_maps = True
    seen = []
    monkeypatch.setattr(obj, "load_cc_deferrals", lambda: seen.append(obj.args.defer_cc_batch))
    monkeypatch.setattr(obj, "emit", lambda *a, **kw: None)
    obj.process_export_with_deferral(tmp_path / "batch_001")
    assert seen == [["batch_001"]]
    monkeypatch.setattr(obj, "is_missing_weight_map_failure", lambda b: False)
    with pytest.raises(RuntimeError):
        obj.process_export_with_deferral(tmp_path)


def isolated_export_failure(tmp_path, monkeypatch):
    obj = instance(tmp_path)
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    batch = obj.library / "batch_001"
    library(batch, ["a", "b"])
    root = tmp_path / "00_engine/outputs/character_creator_bridge/artifacts/wardrobe_average/run/batch_001"
    project = tmp_path / "saved.ccProject"
    project.write_bytes(b"saved project")
    case = root / "cases/a/result.json"
    write(case, {"case_id": "a", "success": False, "production_project": {
        "path": str(project), "sha256": runner.file_hash(project)}})
    report = root / "validation_result.json"
    write(report, {"success": False, "phase": "complete", "blocked": False, "failure_count": 1,
                   "results": [{"case_id": "a", "success": False, "result_path": str(case),
                                "error": {"type": "ReconstructionError", "message":
                                "Export first-batch FullReference character failed: {'returned': True, 'is_error': True, 'status_code': '1'}"}},
                               {"case_id": "b", "success": True}]})
    return obj, batch, report, project


def test_isolated_sdk_error_requires_preserved_project_and_complete_batch(tmp_path, monkeypatch):
    obj, batch, report, project = isolated_export_failure(tmp_path, monkeypatch)
    assert obj.is_isolated_asset_export_failure(batch)
    project.write_bytes(b"changed")
    assert not obj.is_isolated_asset_export_failure(batch)


def test_single_batch_returns_for_review_without_allocating_more(tmp_path, monkeypatch):
    obj = instance(tmp_path)
    obj.run_root.mkdir(parents=True)
    first, second = obj.library / "batch_001", obj.library / "batch_002"
    library(first, ["a"])
    library(second, ["b"])
    calls = []
    monkeypatch.setattr(obj, "export_batch", lambda b: calls.append(b.name))
    monkeypatch.setattr(obj, "new_batches", lambda a: pytest.fail("must not allocate more"))
    obj.process_one_cc_batch({}, "export_only")
    assert calls == ["batch_001"]
    assert obj.state["status"] == "awaiting_batch_review"
    with pytest.raises(ValueError, match="export_only"):
        obj.process_one_cc_batch({}, "interleaved")


def test_single_batch_never_auto_defers_failure(tmp_path, monkeypatch):
    obj = instance(tmp_path)
    obj.run_root.mkdir(parents=True)
    library(obj.library / "batch_001", ["a"])
    obj.auto_defer_missing_weight_maps = True
    def fail(batch):
        raise ValueError("inspect failure")
    monkeypatch.setattr(obj, "export_batch", fail)
    monkeypatch.setattr(obj, "process_export_with_deferral", lambda b: pytest.fail("no automatic deferral"))
    with pytest.raises(ValueError, match="inspect failure"):
        obj.process_one_cc_batch({}, "export_only")


def test_single_batch_allocates_only_first_new_batch(tmp_path, monkeypatch):
    obj = instance(tmp_path)
    obj.run_root.mkdir(parents=True)
    def new_batches(authority):
        batch = obj.library / "batch_001"
        library(batch, ["a"])
        yield batch
        pytest.fail("should not ask for another allocation")
    monkeypatch.setattr(obj, "new_batches", new_batches)
    monkeypatch.setattr(obj, "export_batch", lambda b: None)
    obj.process_one_cc_batch({}, "export_only")
    assert obj.state["batch"] == "batch_001"


def test_single_ue_batch_reuses_completed_and_returns_after_one(tmp_path, monkeypatch):
    obj = instance(tmp_path)
    obj.run_root.mkdir(parents=True)
    library(obj.library, ["a", "b", "c"])
    for number, uid in enumerate(("a", "b", "c"), 1):
        batch = obj.library / f"batch_{number:03d}"
        library(batch, [uid])
        write(batch / "ue_import.json", {"status": "cc_export_passed"})
    write(obj.reports / "batch_001/wardrobe_modules.json", {"success": True})
    calls = []
    monkeypatch.setattr(obj, "transfer_batch", lambda batch: calls.append(batch.name))
    monkeypatch.setattr(obj, "export_batch", lambda b: pytest.fail("must not call CC"))
    monkeypatch.setattr(obj, "new_batches", lambda a: pytest.fail("must not allocate"))
    monkeypatch.setattr(runner, "audit", lambda *args: {
        "cc_exported_units": 3, "ue_transferred_units": 2, "total_units": 3})
    obj.process_one_ue_batch({}, "interleaved")
    assert calls == ["batch_002"]
    assert obj.state["status"] == "awaiting_batch_review"
    assert obj.state["ue_units"] == 2
    assert len(list(obj.run_root.glob("audit_ue_batch_002_*.json"))) == 1


@pytest.mark.parametrize("failure", ["unallocated", "unfinished", "deferred", "export_only", "changed"])
def test_single_ue_batch_rejects_unready_inputs(tmp_path, monkeypatch, failure):
    obj = instance(tmp_path)
    obj.run_root.mkdir(parents=True)
    library(obj.library, ["a"])
    batch = obj.library / "batch_001"
    if failure != "unallocated":
        library(batch, ["a"])
        if failure != "unfinished":
            write(batch / "ue_import.json", {"status": "cc_export_passed"})
    if failure == "deferred":
        obj.deferred_cc = {"batch_001": {}}
    monkeypatch.setattr(obj, "transfer_batch", lambda b: pytest.fail("must not start UE"))
    authority = {"cc_export.json": "different"} if failure == "changed" else {}
    with pytest.raises((ValueError, RuntimeError)):
        obj.process_one_ue_batch(authority, "export_only" if failure == "export_only" else "interleaved")


def test_single_ue_completion_requires_final_audit(tmp_path, monkeypatch):
    obj = instance(tmp_path)
    obj.run_root.mkdir(parents=True)
    library(obj.library, ["a"])
    library(obj.library / "batch_001", ["a"])
    write(obj.library / "batch_001/ue_import.json", {})
    write(obj.reports / "batch_001/wardrobe_modules.json", {})
    monkeypatch.setattr(obj, "transfer_batch", lambda b: pytest.fail("already complete"))
    monkeypatch.setattr(runner, "audit", lambda *args: {
        "cc_exported_units": 1, "ue_transferred_units": 1, "total_units": 1})
    obj.process_one_ue_batch({}, "interleaved")
    assert obj.state["status"] == "transfer_complete"


def test_ue_supervision_transfer_never_calls_export(tmp_path, monkeypatch):
    obj = instance(tmp_path)
    obj.args.one_ue_batch = True
    obj.run_root.mkdir(parents=True)
    batch = obj.library / "batch_001"
    library(batch, ["a"])
    write(batch / "ue_import.json", {})
    calls = []
    monkeypatch.setattr(obj, "export_batch", lambda b: pytest.fail("CC prohibited"))
    monkeypatch.setattr(obj, "ensure_ue", lambda: calls.append("ensure"))
    monkeypatch.setattr(obj, "phase", lambda b, p, u=None: calls.append(p))
    monkeypatch.setattr(obj, "python", lambda *a: calls.append("aggregate"))
    obj.transfer_batch(batch)
    assert calls == ["ensure", "preflight", "reference", "split", "materials", "validate", "aggregate"]


@pytest.mark.parametrize("change", ["blocked", "partial", "all_failed", "unknown", "fatal"])
def test_sdk_deferral_rejects_unclassified_failures(tmp_path, monkeypatch, change):
    obj, batch, report, project = isolated_export_failure(tmp_path, monkeypatch)
    value = runner.read(report)
    if change == "blocked":
        value["blocked"] = True
    elif change == "partial":
        value["phase"] = "running"
    elif change == "all_failed":
        value["results"][1]["success"] = False
        value["failure_count"] = 2
    elif change == "unknown":
        value["results"][0]["error"]["message"] = "different error"
    else:
        write(report.parent / "fatal_dialog.json", {})
    write(report, value)
    assert not obj.is_isolated_asset_export_failure(batch)
