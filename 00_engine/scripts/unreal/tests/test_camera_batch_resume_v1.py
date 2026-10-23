"""No-UE recovery tests for the root-owned frozen batch runner."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import Mock

import pytest


@pytest.fixture
def runner(tmp_path, monkeypatch):
    path = Path(__file__).parents[3] / 'outputs/camera_motion_scene_alignment_20261012_v1/run_camera_batches.py'
    spec = importlib.util.spec_from_file_location('batch_resume_test_runner', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'RUN', tmp_path)
    return module


def evidence(runner, attempt, ids):
    path = runner.RUN / ('media_validation_' + attempt + '.json')
    path.write_text(json.dumps({'attempt': attempt, 'videos': [{'shot_id': sid} for sid in ids]}))
    return path


def test_previous_version_reuses_original_attempt_and_no_ue(runner, monkeypatch):
    shot = {'shot_id': 's1', 'orientation': 'landscape', 'width': 1280, 'height': 720}
    plan = runner.RUN / 'legacy_cross_sex_camera_plan_v1.json'
    plan.write_text(json.dumps({'shots': [shot]}))
    (runner.RUN / 'batch_schedule_cross_v1.json').write_text(json.dumps({
        'plan_sha256': runner.sha(plan), 'groups': [['s1']]}))
    evidence(runner, 'cross_000_landscape_v1', ['s1'])
    monkeypatch.setattr(runner, 'verified_ids', Mock(return_value=['s1']))
    remote = Mock(side_effect=AssertionError('No UE calls permitted'))
    publish = Mock()
    monkeypatch.setattr(runner, 'remote', remote)
    monkeypatch.setattr(runner, 'publish_and_retire', publish)
    runner.run('cross', 12, 'v2')
    remote.assert_not_called()
    publish.assert_called_once_with('cross_000_landscape_v1', 'cross')


@pytest.mark.parametrize('ids', [['s1'], ['s1', 'other'], ['s1', 's1']])
def test_partial_conflicting_duplicate_group_rejected(runner, monkeypatch, ids):
    evidence(runner, 'cross_000_landscape_v1', ids)
    monkeypatch.setattr(runner, 'verified_ids', Mock(return_value=['s1', 's2']))
    with pytest.raises(RuntimeError, match='Resume group differs'):
        runner.completed_group_attempt('cross_000_landscape', 'cross_000_landscape_v2',
                                       [{'shot_id': 's1'}, {'shot_id': 's2'}])


def test_changed_media_proof_rejected(runner, monkeypatch):
    evidence(runner, 'cross_000_landscape_v1', ['s1'])
    monkeypatch.setattr(runner, 'verified_ids', Mock(side_effect=ValueError('Changed retained media')))
    with pytest.raises(ValueError, match='Changed retained media'):
        runner.completed_group_attempt('cross_000_landscape', 'cross_000_landscape_v2', [{'shot_id': 's1'}])


def test_dead_editor_records_separate_evidence(runner, monkeypatch):
    shot = {'shot_id': 's1', 'orientation': 'landscape', 'width': 1280, 'height': 720}
    (runner.RUN / 'legacy_cross_sex_camera_plan_v1.json').write_text(json.dumps({'shots': [shot]}))
    receipt_dir = runner.RUN / 'render_receipts'
    receipt_dir.mkdir()
    receipt = receipt_dir / 'cross_000_landscape_v2.json'
    receipt.write_text(json.dumps({'status': 'rendering', 'success': False}))
    original = receipt.read_bytes()
    process = Mock()
    process.name.return_value = 'UnrealEditor.exe'
    process.is_running.return_value = False
    monkeypatch.setattr(runner.psutil, 'Process', Mock(return_value=process))
    monkeypatch.setattr(runner, 'remote', Mock(side_effect=AssertionError('No UE calls permitted')))
    with pytest.raises(RuntimeError, match='UE exited'):
        runner.run('cross', 12, 'v2', 12345)
    assert receipt.read_bytes() == original
    failure = json.loads((receipt_dir / 'cross_000_landscape_v2_editor_exit.json').read_text())
    assert failure['original_receipt_sha256'] == runner.sha(receipt)
    assert failure['editor_pid'] == 12345
