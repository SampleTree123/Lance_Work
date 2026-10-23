"""All fixtures are temporary files; no real INI or UE process is modified."""
from pathlib import Path
import sys
import types
import json
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import restore_scene_editor_views_v1 as m


def overlay():
    return {'schema': 'scene_folder_relocation_v1', 'status': 'in_progress', 'mappings': [
        {'old_prefix': '/Game/Foo', 'new_prefix': '/Game/Scenes/Foo', 'status': 'verified'}]}


def test_boundary_suffix_and_other_current_bytes():
    source = b'Old=x\nEditorViews=(("/Game/Foo/Map.Map",(X=5)),("/Game/Foobar/M.M",(X=6)))\nOld=y\n'
    current = b'\xef\xbb\xbf[Current]\r\nNew=keep\r\nEditorViews=()\r\nLast=keep\r\n'
    actual, changes = m.restore_bytes(source, current, overlay())
    expected = current.replace(b'EditorViews=()', b'EditorViews=(("/Game/Scenes/Foo/Map.Map",(X=5)),("/Game/Foobar/M.M",(X=6)))')
    assert actual == expected
    assert len(changes) == 1
    assert m.restore_bytes(actual, current, overlay())[0] == actual


def test_bom_on_setting_line_preserved():
    current = b'\xef\xbb\xbfEditorViews=()\r\nX=keep\r\n'
    output, _ = m.restore_bytes(b'EditorViews=(("/Game/Foo/M.M",()))\n', current, overlay())
    assert output.startswith(b'\xef\xbb\xbfEditorViews=')
    assert output.endswith(b'\r\nX=keep\r\n')


def test_casefold_fname_collision_rejected():
    source = b'EditorViews=(("/Game/Foo/M.M",()),("/Game/scenes/foo/m.m",()))\n'
    with pytest.raises(ValueError, match='collision'):
        m.restore_bytes(source, b'EditorViews=()\n', overlay())


@pytest.mark.parametrize('raw', [b'X=1\n', b'EditorViews=()\nEditorViews=()\n'])
def test_unknown_layout_refused(raw):
    with pytest.raises(ValueError, match='exactly one'):
        m.restore_bytes(raw, b'EditorViews=()\n', overlay())


def test_unverified_mapping_refused():
    data = overlay()
    data['mappings'][0]['status'] = 'moving'
    with pytest.raises(ValueError, match='not verified'):
        m.restore_bytes(b'EditorViews=(("/Game/Foo/M.M",()))\n', b'EditorViews=()\n', data)


def test_live_project_editor_refused(tmp_path):
    process = types.SimpleNamespace(pid=99, name=lambda: 'UnrealEditor.exe', cmdline=lambda: ['UE.exe', str(m.PROJECT)])
    with pytest.raises(RuntimeError, match='still running'):
        m.assert_no_editor([process], tmp_path / 'missing.lock')


def test_other_project_and_no_editor_safe(tmp_path):
    process = types.SimpleNamespace(pid=99, name=lambda: 'UnrealEditor.exe', cmdline=lambda: ['UE.exe', 'D:/Other/Other.uproject'])
    m.assert_no_editor([process], tmp_path / 'missing.lock')


def test_driver_lock_refused(tmp_path):
    p = tmp_path / 'driver.lock'
    p.write_text('active')
    with pytest.raises(RuntimeError, match='lock exists'):
        m.assert_no_editor([], p)


def test_changed_pin_refused(tmp_path):
    p = tmp_path / 'input'
    p.write_bytes(b'new')
    with pytest.raises(RuntimeError, match='Input changed'):
        m.check_pins({str(p): m.sha_bytes(b'old')})


@pytest.mark.parametrize('success,correct_hash', [(False, True), (True, False)])
def test_failed_or_tampered_proof_refused(tmp_path, success, correct_hash):
    p = tmp_path / 'proof.json'
    p.write_text(json.dumps({'success': success}))
    registry = tmp_path / 'registry.json'
    data = overlay()
    data['mappings'][0]['verification_receipt'] = {'path': str(p), 'sha256': m.sha_bytes(p.read_bytes()) if correct_hash else 'wrong'}
    registry.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        m.read_overlay(registry)


def test_complete_roots_required():
    with pytest.raises(ValueError, match='24-scene'):
        m.require_complete(overlay(), {'success': True, 'roots': [{'root': '/Game/Foo'}]})
    inventory = {'success': True, 'roots': [{'root': '/Game/Scene' + str(i)} for i in range(24)]}
    with pytest.raises(ValueError, match='not verified'):
        m.require_complete(overlay(), inventory)


def test_versioned_receipt_never_overwrites(tmp_path):
    p = tmp_path / 'receipt.json'
    m.exclusive_json(p, {'original': True})
    original = p.read_bytes()
    with pytest.raises(FileExistsError):
        m.exclusive_json(p, {'changed': True})
    assert p.read_bytes() == original


def test_full_apply_only_temporary_ini_and_preserves_sources(tmp_path, monkeypatch):
    registry, inventory, original, current = [tmp_path / name for name in ('registry.json', 'inventory.json', 'original.ini', 'current.ini')]
    mappings = []
    roots = ['/Game/Scene' + str(i) for i in range(24)]
    for i, root in enumerate(roots):
        proof = tmp_path / f'proof{i}.json'
        dest = '/Game/Scenes/' + root[6:]
        proof.write_text(json.dumps({'root': root, 'destination': dest, 'success': True}))
        mappings.append({'old_prefix': root, 'new_prefix': dest, 'status': 'verified',
                         'verification_receipt': {'path': str(proof), 'sha256': m.sha_bytes(proof.read_bytes())}})
    registry.write_text(json.dumps({'schema': 'scene_folder_relocation_v1', 'status': 'complete', 'mappings': mappings}))
    inventory.write_text(json.dumps({'success': True, 'roots': [{'root': r} for r in roots + ['/Game/StarterContent']]}))
    original.write_bytes(b'EditorViews=(("/Game/Scene0/M.M",(X=1)))\nOld=yes\n')
    before = b'\xef\xbb\xbf[Editor]\r\nEditorViews=()\r\nCurrent=keep\r\n'
    current.write_bytes(before)
    frozen = {p: p.read_bytes() for p in (registry, inventory, original)}
    for key, value in {'REGISTRY': registry, 'INVENTORY': inventory, 'ORIGINAL': original, 'INI': current, 'RUN': tmp_path}.items():
        monkeypatch.setattr(m, key, value)
    checks = []
    monkeypatch.setattr(m, 'assert_no_editor', lambda: checks.append('no-editor'))
    monkeypatch.setattr(sys, 'argv', ['restore_scene_editor_views_v1.py', '--apply'])
    m.main()
    assert current.read_bytes() == before.replace(b'EditorViews=()', b'EditorViews=(("/Game/Scenes/Scene0/M.M",(X=1)))')
    assert all(p.read_bytes() == raw for p, raw in frozen.items())
    assert checks == ['no-editor', 'no-editor']
    assert next(tmp_path.glob('editor_views_current_before_restore_*.ini')).read_bytes() == before
    receipt = json.loads(next(tmp_path.glob('editor_views_restored_*.json')).read_text())
    assert receipt['success'] is True and len(receipt['mappings']) == 1
