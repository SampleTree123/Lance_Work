from pathlib import Path
from types import SimpleNamespace
import copy
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pair_scene_review_20261019_v1 as pair
import ue_camera_collision_proxy_review_v1 as proxy


def current(monkeypatch, report):
    monkeypatch.setattr(proxy, 'install', lambda w: w)
    events = []
    cache = {'map': 'old'}
    def state():
        return {'current_result_fresh':True, 'full_matrix_fresh':True,
                'needs_recheck':False, 'check':{'report':copy.deepcopy(report)},
                'allowed_combinations':[{'decision':'excluded'}]}
    def stale(job, force=False):
        events.append((force, dict(cache)))
        return 'changed' if force and not cache else None
    w = SimpleNamespace(stamp=lambda:'original', state=state, job_stale_reason=stale)
    c = {'worker':w, 'fast_caches':{'scene':cache}}
    return c, events


def test_old_report_expires_without_erasing_decisions(monkeypatch):
    c, _ = current(monkeypatch, {'status':'complete'})
    pair.install_camera_checks(c)
    s = c['worker'].state()
    assert not s['current_result_fresh'] and s['needs_recheck']
    assert s['allowed_combinations'] == [{'decision':'excluded'}]
    assert c['worker'].stamp() != 'original'


def test_new_report_survives_idempotent_cached_install(monkeypatch):
    c, _ = current(monkeypatch, {'camera_check_method':proxy.METHOD})
    pair.install_camera_checks(c)
    original = c['worker'].stamp
    pair.install_camera_checks(c)
    assert c['worker'].stamp is original
    assert c['worker'].state()['current_result_fresh']
    assert c['worker'].state()['scene_freshness_policy'] == 'explicit_check_snapshot_not_continuous'


def test_final_check_refreshes_scene_but_browsing_does_not(monkeypatch):
    c, events = current(monkeypatch, {})
    pair.install_camera_checks(c)
    c['worker'].state()
    assert c['fast_caches']['scene'] == {'map':'old'}
    assert c['worker'].job_stale_reason({}, force=False) is None
    assert c['worker'].job_stale_reason({}, force=True) == 'changed'
    assert events == [(False, {'map':'old'}), (True, {})]
