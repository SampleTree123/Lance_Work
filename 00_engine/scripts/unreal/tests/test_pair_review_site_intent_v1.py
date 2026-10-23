"""Offline regression against the frozen worker's real state/save/check code."""
import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
import pair_review_site_intent_v1 as runtime
from test_scene_site_review_worker_v1 import worker


EXCLUDED = {'action_id': 'walk', 'camera_id': 'front', 'aspect': 'portrait', 'decision': 'excluded'}
ALLOWED = {'action_id': 'idle', 'camera_id': 'front', 'aspect': 'portrait', 'decision': 'allowed'}


@pytest.fixture
def installed(worker, monkeypatch, tmp_path):
    w, d = worker
    monkeypatch.setattr(w, 'RUN', tmp_path)
    d['site'].update(allowed_combinations=[copy.deepcopy(EXCLUDED), copy.deepcopy(ALLOWED)],
                     issue_reviews={'issue': {'status': 'acceptable', 'note': 'old'}})
    d.update(scene='first', appearance='first', method='first')
    monkeypatch.setattr(w, 'scene_signature', lambda: d['scene'])
    monkeypatch.setattr(w, 'input_status', lambda **kwargs: {'valid': True, 'signature': d['appearance']})
    def stamp():
        value = {key: d[key] for key in ('scene', 'appearance', 'method')}
        value['site'] = {key: d['site'][key] for key in ('site_id', 'map', 'position', 'yaw')}
        signature = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
        legacy = d.get('migrated_exclusion_intent')
        if legacy:
            d['site'].update(allowed_combinations=copy.deepcopy(legacy['restrictions']),
                             issue_reviews={}, decisions_stamp=signature)
        return signature
    monkeypatch.setattr(w, 'stamp', stamp)
    d['site']['decisions_stamp'] = stamp()
    d['migrated_exclusion_intent'] = {'restrictions': [copy.deepcopy(EXCLUDED)]}
    def write(path, record):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record), encoding='utf-8')
    monkeypatch.setattr(w, 'write', write)
    # Retain the actual frozen loader's saved-record semantics, without actors.
    def load(request):
        record = w.read(w.RUN / 'sites' / (request['site_id'] + '.json'))
        d.update(site=copy.deepcopy(record['site']), report=record.get('report'))
        # Model the production loader's legacy import union.
        d['site']['allowed_combinations'] = (copy.deepcopy(d['site'].get('allowed_combinations', []))
                                              + copy.deepcopy(d['site'].get('imported_excluded_combinations', [])))
    monkeypatch.setattr(w, 'load_site', load)
    # This is the primary adapter's legacy guard over the real frozen checker.
    base_check = w.start_check
    def check(request, all_shots=False):
        if request.get('excluded_combinations') and request.get('decisions_stamp') != w.stamp():
            raise ValueError('old exclusion stamp')
        return base_check(request, all_shots)
    monkeypatch.setattr(w, 'start_check', check)
    current = {'worker': w}
    runtime.install(current)
    return w, d, current


def request(d, **extra):
    return {'decision_site_id': d['site']['site_id'], 'decision_map': d['site']['map'], **extra}


@pytest.mark.parametrize('change', ['position', 'yaw', 'scene', 'appearance', 'method'])
def test_exclusions_survive_changes_without_promoting_old_pass_or_issues(installed, change):
    w, d, _ = installed
    before = w.state()
    assert before['decisions_fresh']
    if change == 'position':
        d['site']['position']['x'] += 30
    elif change == 'yaw':
        d['site']['yaw'] += 45
    else:
        d[change] = 'changed'
    after = w.state()
    assert after['allowed_combinations'] == [EXCLUDED]
    assert not after['decisions_fresh']
    assert after['issue_reviews'] == {}
    assert after['needs_recheck'] and not after['full_matrix_fresh']
    assert d['site']['issue_reviews']['issue']['note'] == 'old'


def test_stale_exclusion_snapshot_saves_and_empty_snapshot_stays_empty_on_reload(installed):
    w, d, _ = installed
    old = w.stamp()
    d['site']['position']['x'] += 1
    w.save_site(request(d, decisions_stamp=old, allowed_combinations=[EXCLUDED, ALLOWED]))
    saved = w.read(w.RUN / 'sites/test.json')['site']
    assert saved['allowed_combinations'] == [EXCLUDED]
    assert saved[runtime.FIELD]['excluded_combinations'] == [EXCLUDED]
    assert saved['decisions_stamp'] == old
    w.save_site(request(d, decisions_stamp=old, allowed_combinations=[]))
    record = w.read(w.RUN / 'sites/test.json')
    record['site']['imported_excluded_combinations'] = [EXCLUDED]
    w.write(w.RUN / 'sites/test.json', record)
    w.load_site({'site_id': 'test'})
    assert w.state()['allowed_combinations'] == []
    assert d['site'][runtime.FIELD]['excluded_combinations'] == []


def test_save_without_new_decisions_preserves_exclusions_after_move(installed):
    w, d, _ = installed
    w.state()
    d['site']['yaw'] += 1
    w.save_site(request(d))
    assert w.read(w.RUN / 'sites/test.json')['site']['allowed_combinations'] == [EXCLUDED]
    assert w.state()['allowed_combinations'] == [EXCLUDED]


def test_save_without_new_decisions_preserves_still_fresh_allowed_and_issues(installed):
    w, d, _ = installed
    w.save_site(request(d))
    state = w.state()
    assert state['decisions_fresh']
    assert state['allowed_combinations'] == [ALLOWED, EXCLUDED]
    assert state['issue_reviews']['issue']['note'] == 'old'


def test_old_file_explicit_empty_overrides_imported_restrictions(installed):
    w, d, _ = installed
    site = copy.deepcopy(d['site'])
    site.update(allowed_combinations=[], imported_excluded_combinations=[EXCLUDED])
    site.pop(runtime.FIELD, None)
    w.write(w.RUN / 'sites/test.json', {'site': site})
    w.load_site({'site_id': 'test'})
    assert w.state()['allowed_combinations'] == []


def test_stale_issue_reviews_still_reject_without_saving_exclusions(installed):
    w, d, _ = installed
    old = w.stamp()
    d['site']['yaw'] += 1
    with pytest.raises(ValueError, match='问题审查'):
        w.save_site(request(d, decisions_stamp=old, allowed_combinations=[],
                            issue_reviews={'issue': {'status': 'acceptable'}}))
    assert w.state()['allowed_combinations'] == [EXCLUDED]
    assert not (w.RUN / 'sites/test.json').exists()


@pytest.mark.parametrize('field', ['decision_site_id', 'decision_map'])
def test_delayed_request_cannot_edit_or_check_another_site(installed, field):
    w, d, _ = installed
    payload = request(d, allowed_combinations=[], excluded_combinations=[EXCLUDED])
    payload[field] = 'other'
    with pytest.raises(ValueError, match='其他拍摄点'):
        w.save_site(payload)
    with pytest.raises(ValueError, match='其他拍摄点'):
        w.start_check(payload, True)
    assert d['job'] is None


def test_check_uses_same_site_stale_exclusions_but_keeps_current_job_stamp(installed, monkeypatch):
    w, d, _ = installed
    old = w.stamp()
    d['site']['position']['x'] += 4
    shots = [{'shot_id': row['action_id'], 'motion_id': row['action_id'],
              'camera_id': row['camera_id'], 'orientation': row['aspect'], 'samples': []}
             for row in (EXCLUDED, ALLOWED)]
    actions = [{'motion_id': row['action_id'], 'samples': []} for row in (EXCLUDED, ALLOWED)]
    monkeypatch.setattr(w, 'placed', lambda _: {'shots': shots, 'actions': actions})
    monkeypatch.setattr(w, 'owned', lambda: [])
    monkeypatch.setattr(w.u, 'register_slate_post_tick_callback', lambda callback: 'offline', raising=False)
    w.start_check(request(d, decisions_stamp=old, excluded_combinations=[EXCLUDED]), True)
    assert d['job']['shots'] == [shots[1]]
    assert d['job']['scope']['kind'] == 'remaining'
    assert d['job']['stamp'] == w.stamp() != old
    assert w.state()['needs_recheck']


def test_install_is_idempotent_and_does_not_rewrite_report_freshness(installed):
    w, d, current = installed
    stamp = w.stamp
    runtime.install(current)
    assert w.stamp is stamp
    d['report'] = {'stamp': w.stamp(), 'status': 'complete',
                   'scope': {'kind': 'all', 'combinations': 2},
                   'summary': {'checked_items': 2, 'total_items': 2},
                   'coverage': {'full_matrix_checked': True}}
    assert w.state()['full_matrix_fresh']
    d['site']['yaw'] += 1
    assert not w.state()['full_matrix_fresh']
