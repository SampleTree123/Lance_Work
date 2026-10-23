"""Private camera-only simple-collision supplement; import never touches Unreal.

Complex hits retain the existing worker's behavior. Simple collision is a
conservative proxy and can close real openings, so its findings require preview.
The caller owns installation scope and input/stamp invalidation.
"""
from __future__ import annotations

import copy

REVISION = 1
METHOD = 'complex_visibility_with_simple_camera_proxy_v1'
LIMITATIONS = (
    '相机另用简化碰撞补查；简化碰撞可能封住栏杆等真实空隙，代理命中必须预览确认。',
    '补查沿用原采样时刻和最多五个可见骨点；仍不能证明无碰撞物体、网格、服装或发型无遮挡。',
)


def supporting_floor_contact(hit, candidate, site_z):
    """Match the frozen worker's foot/ball baseline-floor exception exactly."""
    return bool(hit and candidate['bone'] in ('foot_l', 'foot_r', 'ball_l', 'ball_r')
                and hit['normal'][2] > .7
                and abs(hit['point'][2] - site_z) <= 5.
                and abs(candidate['position'][2] - site_z) <= 5.)


def simple_hit(worker, start, end, radius=None):
    """Query without changing channel, ignored actors, or scene collision state."""
    u = worker.u
    args = (worker.world(), worker.vec(start), worker.vec(end))
    if radius is None:
        raw = u.SystemLibrary.line_trace_single(
            *args, u.TraceTypeQuery.ECC_VISIBILITY, False,
            worker.trace_ignored(), u.DrawDebugTrace.NONE)
    else:
        raw = u.SystemLibrary.sphere_trace_single(
            *args, radius, u.TraceTypeQuery.ECC_VISIBILITY, False,
            worker.trace_ignored(), u.DrawDebugTrace.NONE)
    hit = worker.hit_data(raw)
    if not hit:
        return None
    # Never modify the existing decoder's object or the caller's point lists.
    result = copy.deepcopy(hit)
    result.update(collision_method='simple_visibility', trace_complex=False,
                  trace_start=list(start), trace_end=list(end))
    if radius is not None:
        result['sweep_radius_cm'] = float(radius)
    try:
        values = raw.to_tuple()
        result['start_penetrating'] = bool(values[1])
        component = values[10]
        result['component'] = component.get_path_name() if component else None
    except (AttributeError, IndexError, TypeError, RuntimeError):
        # Metadata availability must not erase an otherwise valid hit.
        result.update(start_penetrating=None, component=None)
    return result


def proxy_issue(job, kind, message, t, shot, hit):
    """Keep the first time per blocker, including later blockers in this shot."""
    blocker = hit.get('component') or hit.get('actor') or 'unknown'
    key = (shot['motion_id'], shot['shot_id'], kind, blocker)
    seen = job.setdefault('_camera_proxy_seen', set())
    if key in seen:
        return
    seen.add(key)
    job['issues'].append({'id': str(len(job['issues']) + 1), 'severity': 'review',
        'kind': kind, 'message': message, 'action_id': shot['motion_id'],
        'camera_id': shot['camera_id'], 'aspect': shot['orientation'],
        'time_seconds': t, 'hit': hit})


def check_proxy_sample(worker, job, shot, row, index):
    """Supplement one existing sample without replacing complex hit evidence."""
    job.setdefault('scope', {})['camera_check_method'] = METHOD
    p, t = row['position'], row['t']
    if not worker._seen(job, 'camera_collision', shot=shot):
        previous = shot['samples'][index - 1]['position'] if index else p
        hit = simple_hit(worker, previous, [p[0] + .01, p[1], p[2]], 8.)
        if hit:
            proxy_issue(job, 'camera_collision_proxy',
                         '简化碰撞范围疑似碰到相机：' + str(hit.get('actor')) + '，需预览确认（可能包含栏杆空隙）',
                         t, shot=shot, hit=hit)
    if worker._seen(job, 'occlusion', shot=shot):
        return
    bones = job['action_samples'][shot['motion_id']][row['frame_index']]['bones']
    for candidate in worker.visible_targets(row, shot, bones):
        hit = simple_hit(worker, p, candidate['position'])
        if hit and not supporting_floor_contact(hit, candidate, job['site_z']):
            proxy_issue(job, 'occlusion_proxy',
                         '简化碰撞范围疑似遮挡：' + str(hit.get('actor')) + '，需预览确认（可能包含栏杆空隙）',
                         t, shot=shot, hit=hit)


def enrich_report(report):
    """Return a detached report so retained callers' dictionaries stay intact."""
    report = copy.deepcopy(report)
    report['camera_check_method'] = METHOD
    report['camera_collision_proxy_revision'] = REVISION
    ground_support = report.get('scope', {}).get('ground_support')
    if isinstance(ground_support, dict):
        ground_support['camera_occlusion_policy'] = METHOD
    report['limitations'] = list(report.get('limitations', []))
    for limitation in LIMITATIONS:
        if limitation not in report['limitations']:
            report['limitations'].append(limitation)
    suffix = '；相机简化碰撞补查（代理命中需预览确认）'
    if not report.get('sampling', '').endswith(suffix):
        report['sampling'] = report.get('sampling', '') + suffix
    return report


def install(worker):
    """Wrap only this worker; repeated installation never stacks wrappers."""
    if getattr(worker, '_camera_collision_proxy_revision', None) == REVISION:
        return worker
    originals = getattr(worker, '_camera_collision_proxy_originals', None)
    if originals is None:
        originals = {name: getattr(worker, name) for name in ('check_shot_sample', 'finish', 'write')}

    def check_shot_sample(job, shot, row, index):
        originals['check_shot_sample'](job, shot, row, index)
        check_proxy_sample(worker, job, shot, row, index)

    def finish(job, status='complete', error=None):
        job.setdefault('scope', {})['camera_check_method'] = METHOD
        result = originals['finish'](job, status, error)
        state = worker.live()
        report = state.get('report')
        if report is not None:
            state['report'] = enrich_report(report)
        return result

    def write(path, value):
        if isinstance(value, dict) and value.get('schema') == 'scene_site_review_report_v1':
            value = enrich_report(value)
        return originals['write'](path, value)

    worker.check_shot_sample, worker.finish = check_shot_sample, finish
    worker.write = write
    worker._camera_collision_proxy_revision = REVISION
    worker._camera_collision_proxy_originals = originals
    return worker
