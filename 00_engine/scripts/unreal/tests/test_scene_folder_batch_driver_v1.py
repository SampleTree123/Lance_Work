"""Host-only safety tests. No remote discovery, editor launch or UE connection."""
import json
from pathlib import Path
import sys
import types

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import scene_folder_batch_driver_v1 as d

ROOT = '/Game/TestScene'


def baseline(tmp_path):
    path = d.receipt(ROOT, 'baseline', tmp_path)
    d.atomic(path, {'root': ROOT, 'success': True, 'assets': [{'package': ROOT + '/Map'}]})
    return path


def move(tmp_path, **extra):
    base = baseline(tmp_path)
    data = {'root': ROOT, 'baseline_sha256': d.sha(base), 'rename_returned': True}
    data.update(extra)
    d.atomic(d.receipt(ROOT, 'move', tmp_path), data)
    return base


def proof(tmp_path, success=True):
    base = baseline(tmp_path)
    p = d.receipt(ROOT, 'verified', tmp_path)
    d.atomic(p, {'root': ROOT, 'destination': '/Game/Scenes/TestScene', 'baseline_sha256': d.sha(base), 'success': success})
    return p


@pytest.mark.parametrize('root', ['/Game/StarterContent', '/Game/DataMake', '/Game/Scenes/X', '/Game/X/Y', '/Game/../X', '/Other/X', '/Game/X;quit'])
def test_reject_protected_or_non_root(root):
    with pytest.raises(ValueError):
        d.slug(root)


def test_fresh_needs_baseline(tmp_path):
    assert d.route(ROOT, {}, tmp_path) == ('baseline', None)


def test_whole_brushify_scene_root_allowed():
    assert d.slug('/Game/Brushify') == 'Brushify'
    with pytest.raises(ValueError):
        d.slug('/Game/Brushify/Maps/Dunes')


def test_original_baseline_routes_move(tmp_path):
    baseline(tmp_path)
    assert d.route(ROOT, {}, tmp_path) == ('move', None)


def test_move_success_routes_verify_even_after_failed_verification(tmp_path):
    move(tmp_path)
    proof(tmp_path, False)
    assert d.route(ROOT, {'move_intent': 'durable'}, tmp_path) == ('verify', None)


@pytest.mark.parametrize('returned', [False, None])
def test_uncertain_move_never_retried(tmp_path, returned):
    move(tmp_path, rename_returned=returned)
    with pytest.raises(RuntimeError, match='will not retry'):
        d.route(ROOT, {}, tmp_path)


def test_dispatch_intent_without_receipt_never_retried(tmp_path):
    baseline(tmp_path)
    with pytest.raises(RuntimeError, match='will not retry'):
        d.route(ROOT, {'move_intent': 'durable'}, tmp_path)


def test_verified_resume_uses_sha_bound_proof(tmp_path):
    p = proof(tmp_path)
    assert d.route(ROOT, {'verification_sha256': d.sha(p)}, tmp_path) == ('verified', p)
    with pytest.raises(RuntimeError, match='verification changed'):
        d.route(ROOT, {'verification_sha256': 'changed'}, tmp_path)


def test_baseline_mutation_rejected(tmp_path):
    baseline(tmp_path)
    with pytest.raises(RuntimeError, match='baseline changed'):
        d.route(ROOT, {'baseline_sha256': 'different'}, tmp_path)


def test_later_false_does_not_reuse_earlier_success(tmp_path):
    first = proof(tmp_path)
    later = tmp_path / 'verified_TestScene_v2.json'
    data = d.read(first)
    data['success'] = False
    d.atomic(later, data)
    import os
    os.utime(later, ns=(first.stat().st_atime_ns, first.stat().st_mtime_ns + 1000000))
    assert d.successful_verification(ROOT, d.sha(d.receipt(ROOT, 'baseline', tmp_path)), tmp_path) is None


def test_only_unique_view_setting_changed():
    raw = b'\xef\xbb\xbf[Section]\r\nOther=yes\r\nEditorViews=(old)\r\nOther=unchanged\r\n'
    assert d.reset_view_bytes(raw) == raw.replace(b'EditorViews=(old)', b'EditorViews=()')


@pytest.mark.parametrize('raw', [b'Other=x\n', b'EditorViews=a\nEditorViews=b\n'])
def test_unexpected_ini_layout_refused(raw):
    with pytest.raises(RuntimeError):
        d.reset_view_bytes(raw)


def test_remote_dirty_guard_prevents_any_action(tmp_path, monkeypatch):
    actions = []
    def guard(u):
        raise RuntimeError('Unsaved packages preserved')
    module = types.SimpleNamespace(guard=guard, move=lambda *a: actions.append('move'))
    monkeypatch.setitem(sys.modules, 'unreal', types.SimpleNamespace())
    monkeypatch.setitem(sys.modules, 'ue_scene_folder_organization_v1', module)
    path = tmp_path / 'payload.json'
    import os
    d.atomic(path, {'scripts': str(tmp_path), 'pid': os.getpid(), 'action': 'move', 'root': ROOT})
    with pytest.raises(RuntimeError, match='Unsaved'):
        exec(d.payload_code(path), {})
    assert actions == []


def test_wrong_remote_pid_prevents_even_guard(tmp_path, monkeypatch):
    actions = []
    monkeypatch.setitem(sys.modules, 'unreal', types.SimpleNamespace())
    monkeypatch.setitem(sys.modules, 'ue_scene_folder_organization_v1', types.SimpleNamespace(guard=lambda u: actions.append('guard')))
    path = tmp_path / 'payload.json'
    d.atomic(path, {'scripts': str(tmp_path), 'pid': -1, 'action': 'quit'})
    with pytest.raises(RuntimeError, match='PID mismatch'):
        exec(d.payload_code(path), {})
    assert actions == []


def test_versioned_verify_passes_unique_receipt(tmp_path, monkeypatch):
    actions = []
    def verify(u, root, receipt_filename=None):
        actions.append((root, receipt_filename))
    module = types.SimpleNamespace(guard=lambda u: None, verify=verify)
    monkeypatch.setitem(sys.modules, 'unreal', types.SimpleNamespace())
    monkeypatch.setitem(sys.modules, 'ue_scene_folder_organization_v1', module)
    path = tmp_path / 'payload.json'
    import os
    d.atomic(path, {'scripts': str(tmp_path), 'pid': os.getpid(), 'action': 'verify', 'root': ROOT, 'receipt_filename': 'unique.json'})
    exec(d.payload_code(path), {})
    assert actions == [(ROOT, 'unique.json')]


def test_old_verify_cannot_overwrite_receipt(tmp_path, monkeypatch):
    actions = []
    module = types.SimpleNamespace(RUN=tmp_path, guard=lambda u: None, verify=lambda u, root: actions.append(root))
    monkeypatch.setitem(sys.modules, 'unreal', types.SimpleNamespace())
    monkeypatch.setitem(sys.modules, 'ue_scene_folder_organization_v1', module)
    d.receipt(ROOT, 'verified', tmp_path).write_text('{}')
    path = tmp_path / 'payload.json'
    import os
    d.atomic(path, {'scripts': str(tmp_path), 'pid': os.getpid(), 'action': 'verify', 'root': ROOT})
    with pytest.raises(RuntimeError, match='Versioned verify API'):
        exec(d.payload_code(path), {})
    assert actions == []


def test_quit_wait_failure_cannot_reset_or_launch(tmp_path, monkeypatch):
    calls = []
    driver = d.Driver.__new__(d.Driver)
    driver.process = types.SimpleNamespace(wait=lambda **kw: (_ for _ in ()).throw(TimeoutError()))
    driver.dispatch = lambda action: calls.append(action)
    monkeypatch.setattr(d, 'RUN', tmp_path)
    monkeypatch.setattr(d, 'assert_identity', lambda p: {'pid': 99})
    monkeypatch.setattr(d, 'reset_view_bytes', lambda raw: pytest.fail('Reset forbidden before PID exit'))
    monkeypatch.setattr(d.subprocess, 'Popen', lambda *a, **kw: pytest.fail('Launch forbidden before PID exit'))
    with pytest.raises(RuntimeError, match='no forced kill'):
        driver.restart()
    assert calls == ['guard', 'quit']


def test_publish_verified_subset_only(tmp_path, monkeypatch):
    p = proof(tmp_path)
    registry = tmp_path / 'overlay.json'
    d.atomic(registry, {'schema': 'scene_folder_relocation_v1', 'status': 'in_progress', 'mappings': []})
    driver = d.Driver.__new__(d.Driver)
    driver.roots = [ROOT, '/Game/PendingScene']
    driver.state = {'roots': {ROOT: {}}}
    driver.save = lambda: None
    driver.progress = lambda message: None
    monkeypatch.setattr(d, 'RUN', tmp_path)
    monkeypatch.setattr(d, 'REGISTRY', registry)
    original_route = d.route
    monkeypatch.setattr(d, 'route', lambda root, entry: original_route(root, entry, tmp_path))
    driver.publish([ROOT])
    result = d.read(registry)
    assert result['status'] == 'in_progress'
    assert [r['old_prefix'] for r in result['mappings']] == [ROOT]
    assert result['mappings'][0]['verification_receipt']['sha256'] == d.sha(p)
    with pytest.raises(ValueError):
        driver.publish(['/Game/NotRequested'])


def test_failed_batch_cannot_publish_partial(tmp_path, monkeypatch):
    proof(tmp_path, False)
    registry = tmp_path / 'overlay.json'
    d.atomic(registry, {'schema': 'scene_folder_relocation_v1', 'status': 'in_progress', 'mappings': []})
    pin = d.sha(registry)
    driver = d.Driver.__new__(d.Driver)
    driver.roots, driver.state = [ROOT], {'roots': {ROOT: {}}}
    monkeypatch.setattr(d, 'REGISTRY', registry)
    original_route = d.route
    monkeypatch.setattr(d, 'route', lambda root, entry: original_route(root, entry, tmp_path))
    with pytest.raises(RuntimeError, match='must verify'):
        driver.publish([ROOT])
    assert d.sha(registry) == pin
