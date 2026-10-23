"""Bounded source/lifecycle/None regression checks; no Unreal import or mutation."""
from pathlib import Path
from types import ModuleType, SimpleNamespace
import copy
import math
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ue_pair_revision_runtime_20261019_v1 as runtime


def actual_case():
    case = runtime._read(runtime.DELIVERY)['cases'][0]
    return case, runtime._read(case['audit'])


def test_actual_completed_pair_has_both_lashes_and_new_source():
    case, audit = actual_case()
    member = runtime._validate_case(case, audit)
    assert len(member['base']) == 6
    assert {r['name'] for r in member['followers']} == {'lash_up_bushy', 'lash_low_bushy'}
    assert all(p.startswith(runtime.UE_ROOT + '/') for p in member['base'].values())


@pytest.mark.parametrize('failure', ['old_source', 'missing_lower', 'different_curve', 'outside_revision'])
def test_rejects_old_source_incomplete_lash_or_unmapped_curves(failure):
    case, audit = copy.deepcopy(actual_case())
    if failure == 'old_source':
        case['source']['sha256'] = '0' * 64
    elif failure == 'missing_lower':
        audit['meshes'] = [r for r in audit['meshes'] if r['name'] != 'lash_low_bushy']
    elif failure == 'different_curve':
        row = next(r for r in audit['meshes'] if r['role'] == 'eyelashes')
        row['morph_source_comparison']['source_to_imported']['CTRL_expressions_eyeBlinkL'] = 'otherCurve'
    else:
        audit['meshes'][0]['path'] = '/Game/OldRevision/wrong.wrong'
    with pytest.raises(ValueError):
        runtime._validate_case(case, audit)


def test_lightweight_guard_detects_removed_or_changed_files(tmp_path):
    path = tmp_path / 'input.json'
    path.write_text('x')
    cfg = {'stamps': {str(path): [path.stat().st_size, path.stat().st_mtime_ns]}}
    assert runtime.unchanged(cfg)
    path.write_text('changed')
    assert not runtime.unchanged(cfg)
    path.unlink()
    assert not runtime.unchanged(cfg)


@pytest.mark.parametrize('clip', [None, 'motion'])
def test_private_none_fix_resets_cached_animation_without_changing_motion(clip):
    module = ModuleType('_pair_test_assembler')
    module.__file__ = str(runtime.SCRIPTS / 'ue_scene_site_appearance_v1.py')
    module.math = math
    module.CACHE_KEY = '_pair_test_cache'
    module.contract = SimpleNamespace(io=SimpleNamespace(digest=lambda _value: 'same'))
    module.fixed = SimpleNamespace(object_path=lambda value: value)
    module.hair_coverage = SimpleNamespace(VERSION=1)
    calls = []
    body = SimpleNamespace(set_animation=lambda value: calls.append(('set', value)),
        override_animation_data=lambda *args: calls.append(('override', args)),
        set_position=lambda *args: calls.append(('position', args)))
    actor = SimpleNamespace(get_actor_label=lambda: 'DM_SiteReview_Test', get_path_name=lambda: 'owner')
    u = SimpleNamespace(_pair_test_cache={'owner': {'actor': actor, 'key': 'same',
                        'body': body, 'motion': clip, 'result': {'success': True}}})
    runtime._patch_none(module)
    result = module.apply_actor(u, actor, {}, .5, clip)
    assert result['time_seconds'] == .5
    assert calls == ([('set', None), ('override', (None, False, False, .5, 1.))]
                     if clip is None else [('position', (.5, False))])


def test_same_owner_cleanup_restores_propagation_and_preserves_peer():
    destroyed, restored = [], []
    a, peer, body = object(), object(), object()
    u = SimpleNamespace(SystemLibrary=SimpleNamespace(is_valid=lambda _a: True), EditorActorSubsystem=object(),
                        get_editor_subsystem=lambda _c: SimpleNamespace(destroy_actor=lambda a: destroyed.append(a) or True))
    state = {'u': u, 'bindings': {'one': {'actors': [a], 'body': body, 'old_propagate': False},
                                'peer': {'actors': [peer]}},
             'fixed': SimpleNamespace(_set_instance_property=lambda *args: restored.append(args))}
    runtime._clear_one(state, 'one')
    assert destroyed == [a]
    assert restored == [(body, 'propagate_curves_to_followers', False)]
    assert state['bindings'] == {'peer': {'actors': [peer]}}


def test_worker_release_precedes_original_scene_restore(monkeypatch):
    events = []
    assembly = SimpleNamespace(_pair_revision_runtime={'prefix': None})
    worker = SimpleNamespace(PREFIX='DM_SiteReview_Pair19_',
        u=SimpleNamespace(SystemLibrary=SimpleNamespace(is_valid=lambda _a: True)),
        owned=lambda: [], trace_ignored=lambda: [], restore=lambda: events.append('restore'))
    monkeypatch.setattr(runtime, 'clear', lambda _a: events.append('clear_lashes'))
    monkeypatch.setattr(runtime, 'owned', lambda _a: ['lash'])
    monkeypatch.setattr(runtime, '_path', lambda a: a)
    runtime.install_worker(worker, assembly)
    assert worker.owned() == ['lash'] and worker.trace_ignored() == ['lash']
    worker.restore()
    assert events == ['clear_lashes', 'restore']
