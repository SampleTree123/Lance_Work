"""Camera fallback behavior against fake UE queries; never opens the editor."""
import copy
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

S = Path(__file__).parents[1]
sys.path.insert(0, str(S))
import ue_camera_collision_proxy_review_v1 as proxy


def vector(*xyz):
    return SimpleNamespace(**dict(zip(('x', 'y', 'z'), xyz)))


def raw_hit(*, point=(4., 0., 40.), normal=(0., 1., 0.), penetrating=False, component='/Test/Fence.Mesh'):
    values = [True, penetrating, .2, 4., vector(*point), vector(*point),
              vector(*normal), vector(*normal), None,
              SimpleNamespace(get_actor_label=lambda: 'Fence'),
              SimpleNamespace(get_path_name=lambda: component)]
    return SimpleNamespace(to_tuple=lambda: values)


@pytest.fixture
def setup(monkeypatch):
    calls, responses, writes = [], {}, []

    def line(*args):
        calls.append(('ray', args[4]))
        return responses.get(('ray', args[4]))

    def sphere(*args):
        calls.append(('sphere', args[5]))
        return responses.get(('sphere', args[5]))

    u = SimpleNamespace(SystemLibrary=SimpleNamespace(
        line_trace_single=line, sphere_trace_single=sphere),
        TraceTypeQuery=SimpleNamespace(ECC_VISIBILITY='visibility'),
        DrawDebugTrace=SimpleNamespace(NONE='none'))
    monkeypatch.setitem(sys.modules, 'unreal', u)
    spec = importlib.util.spec_from_file_location('camera_proxy_base_worker_test', S / 'ue_scene_site_review_v1.py')
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    row = {'t': 0., 'frame_index': 0, 'position': [0., 0., 40.]}
    shot = {'shot_id': 'walk_front', 'motion_id': 'walk', 'camera_id': 'front',
            'orientation': 'landscape', 'samples': [row]}
    candidate = {'bone': 'head', 'position': [10., 0., 60.]}
    state = {'local': {'shots': [shot], 'input_fingerprint': 'same'}}
    job = {'id': 'check_test', 'shots': [shot], 'status': 'running', 'completed': 1, 'total': 1,
           'scope': {'kind': 'all'}, 'stamp': 'same', 'site': {}, 'site_z': 0.,
           'issues': [], 'seen': set(),
           'action_samples': {'walk': {0: {'bones': {'head': candidate['position']}}}}}
    worker.live = lambda: state
    worker.world = lambda: 'world'
    worker.vec = lambda xyz: vector(*xyz)
    worker.trace_ignored = lambda: ['owned_character']
    worker.visible_targets = lambda *args: [candidate]
    worker.write = lambda path, report: writes.append((path, report))
    proxy.install(worker)
    return SimpleNamespace(w=worker, job=job, shot=shot, row=row, candidate=candidate,
                           state=state, responses=responses, calls=calls, writes=writes)


def run(s):
    s.w.check_shot_sample(s.job, s.shot, s.row, 0)


def kinds(s):
    return [issue['kind'] for issue in s.job['issues']]


def test_original_complex_visibility_hit_is_retained_without_simple_ray(setup):
    s = setup
    s.responses[('ray', True)] = raw_hit()
    s.responses[('ray', False)] = raw_hit()
    run(s)
    assert kinds(s) == ['occlusion']
    assert ('ray', False) not in s.calls
    assert 'collision_method' not in s.job['issues'][0]['hit']


def test_simple_ray_reports_conservative_proxy_after_complex_miss(setup):
    s = setup
    s.responses[('ray', False)] = raw_hit(penetrating=True)
    run(s)
    assert kinds(s) == ['occlusion_proxy']
    issue = s.job['issues'][0]
    assert '可能包含栏杆空隙' in issue['message']
    assert issue['hit']['collision_method'] == 'simple_visibility'
    assert issue['hit']['start_penetrating'] is True
    assert issue['hit']['component'] == '/Test/Fence.Mesh'
    assert s.calls.index(('ray', True)) < s.calls.index(('ray', False))


def test_original_complex_camera_hit_is_retained_without_simple_sweep(setup):
    s = setup
    s.responses[('sphere', True)] = raw_hit()
    run(s)
    assert kinds(s) == ['camera_collision']
    assert ('sphere', False) not in s.calls


def test_simple_sweep_records_camera_proxy_and_radius(setup):
    s = setup
    s.responses[('sphere', False)] = raw_hit()
    run(s)
    assert kinds(s) == ['camera_collision_proxy']
    hit = s.job['issues'][0]['hit']
    assert hit['sweep_radius_cm'] == 8.
    assert hit['trace_start'] == s.row['position']
    assert hit['trace_end'] == [.01, 0., 40.]


def test_no_hit_stays_clear_and_both_query_modes_are_used(setup):
    s = setup
    run(s)
    assert kinds(s) == []
    assert sorted(s.calls) == sorted([('ray', True), ('ray', False), ('sphere', True), ('sphere', False)])


def test_simple_supporting_floor_contact_retains_existing_exception(setup):
    s = setup
    s.candidate.update(bone='ball_r', position=[10., 0., -.36])
    s.responses[('ray', False)] = raw_hit(point=(7., 0., 0.), normal=(0., 0., 1.))
    run(s)
    assert kinds(s) == []
    s.responses[('ray', False)] = raw_hit(point=(7., 0., 8.), normal=(0., 0., 1.))
    run(s)
    assert kinds(s) == ['occlusion_proxy']


def test_install_idempotent_and_query_metadata_never_aliases_inputs(setup):
    s = setup
    wrapped = s.w.check_shot_sample
    assert proxy.install(s.w) is s.w
    assert s.w.check_shot_sample is wrapped
    before = copy.deepcopy((s.row, s.candidate))
    s.responses[('ray', False)] = raw_hit()
    run(s)
    s.job['issues'][0]['hit']['trace_start'][0] = 999.
    s.job['issues'][0]['hit']['trace_end'][0] = 999.
    assert (s.row, s.candidate) == before
    run(s)
    assert kinds(s) == ['occlusion_proxy']


def test_finish_delivers_method_and_limitations_without_mutating_first_report(setup):
    s = setup
    s.job['scope']['ground_support'] = {'camera_occlusion_policy': 'unchanged', 'body_collision_policy': 'unchanged'}
    run(s)
    s.w.finish(s.job)
    assert len(s.writes) == 1
    final = s.writes[0][1]
    assert final == s.state['report']
    assert final['camera_check_method'] == proxy.METHOD
    assert final['scope']['camera_check_method'] == proxy.METHOD
    assert final['scope']['ground_support']['camera_occlusion_policy'] == proxy.METHOD
    assert final['scope']['ground_support']['body_collision_policy'] == 'unchanged'
    assert all(text in final['limitations'] for text in proxy.LIMITATIONS)
    assert final['summary']['issues'] == 0
    assert final['coverage']['full_matrix_checked'] is True


def test_first_floor_proxy_does_not_hide_later_fence_or_camera_blocker(setup):
    s = setup
    s.candidate.update(bone='ball_r', position=[10., 0., 2.])
    s.responses[('ray', False)] = raw_hit(point=(7., 0., 17.5), normal=(0., 0., 1.),
                                         component='/Test/InnerFloor.Mesh')
    run(s)
    s.row['t'] = 3.
    s.responses[('ray', False)] = raw_hit(component='/Test/AltarFence.Mesh')
    s.responses[('sphere', False)] = raw_hit(component='/Test/AltarFence.Mesh')
    run(s)
    s.row['t'] = 3.5
    run(s)
    assert kinds(s) == ['occlusion_proxy', 'camera_collision_proxy', 'occlusion_proxy']
    assert [i['time_seconds'] for i in s.job['issues']] == [0., 3., 3.]
    assert [i['hit']['component'] for i in s.job['issues']] == [
        '/Test/InnerFloor.Mesh', '/Test/AltarFence.Mesh', '/Test/AltarFence.Mesh']


def test_different_targets_can_report_different_blockers_in_one_sample(setup):
    s = setup
    s.w.visible_targets = lambda *args: [s.candidate, {'bone': 'hand_l', 'position': [10., 1., 50.]}]
    hits = iter([raw_hit(component='/Test/Fence.Mesh'), raw_hit(component='/Test/Pillar.Mesh')])
    original_line = s.w.u.SystemLibrary.line_trace_single
    s.w.u.SystemLibrary.line_trace_single = lambda *args: original_line(*args) if args[4] else next(hits)
    run(s)
    assert kinds(s) == ['occlusion_proxy', 'occlusion_proxy']
    assert len(s.job['_camera_proxy_seen']) == 2


def test_report_enrichment_and_unrelated_writes_do_not_mutate_arguments(setup):
    s = setup
    report = {'schema': 'scene_site_review_report_v1', 'limitations': [], 'sampling': 'original'}
    before = copy.deepcopy(report)
    s.w.write('report.json', report)
    assert report == before
    assert s.writes[-1][1]['camera_check_method'] == proxy.METHOD
    other = {'schema': 'reply', 'state': {}}
    s.w.write('reply.json', other)
    assert s.writes[-1][1] is other


def test_optional_hit_metadata_failure_does_not_drop_hit(setup):
    s = setup
    decoded = {'point': [1., 2., 3.], 'normal': [0., 0., 1.], 'actor': 'Fence'}
    s.responses[('ray', False)] = object()
    s.w.hit_data = lambda raw: decoded
    result = proxy.simple_hit(s.w, [0., 0., 40.], [10., 0., 60.])
    assert result['start_penetrating'] is None
    assert result['component'] is None
    assert 'collision_method' not in decoded
