"""Frozen per-site representative scene clips and a Chinese review gallery.

Does not import/connect to UE. Inputs are the existing primary-level catalog and
root-selected points. Site revisions remain independent for bounded resumption.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import scene_site_review_geometry_v1 as geo

S = Path(__file__).resolve().parent
RUN = S.parents[1] / 'outputs/all_primary_scene_sites_20261015_v1'
INDEX = 'scene_samples_index_v1.json'
ASSETS = '/Game/DataMake/Validation/AllPrimarySceneSites20261015'
CONTENT = Path('D:/UE/projects/datatry_02/Content')
PREFERENCES = (('landscape', 'orbit_360', '横屏环绕 · 场景空间'),
               ('portrait', 'front_full', '竖屏全身 · 人物构图'))


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def object_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def render_definition(site, *, include_policy=True):
    position = site.get('position')
    if isinstance(position, dict):
        position = [float(position[k]) for k in ('x', 'y', 'z')]
    elif position is not None:
        position = list(map(float, position))
    definition = {'site_id': site['site_id'], 'revision': site.get('revision', 'v1'),
            'map': site['map'].split('.')[0], 'position': position,
            'yaw': float(site.get('yaw', 0.)),
            'exposure_compensation': float(site.get('exposure_compensation', 0.))}
    if include_policy:
        definition['exclusions'] = sorted(object_sha(v) for v in site.get('exclusions', []))
        if 'compatibility_policy_revision' in site:
            definition['compatibility_policy_revision'] = copy.deepcopy(site['compatibility_policy_revision'])
    if 'sample_preferences' in site:
        definition['sample_preferences'] = copy.deepcopy(site['sample_preferences'])
    return definition


def sample_render_binding(shot):
    keys = ('shot_id', 'source_shot_id', 'motion_id', 'camera_id', 'orientation',
            'source_shot_plan_sha256', 'source_trajectory_sha256', 'trajectory_sha256',
            'exposure_compensation', 'width', 'height', 'aspect_ratio', *geo.CLOCK_FIELDS)
    return {**{key: shot[key] for key in keys},
            'actual_placed_frames_sha256': object_sha(shot['frames'] + [shot['endpoint_validation_frame']])}


def frozen_sample_excluded(shot, exclusions):
    return excluded(shot, exclusions) or excluded(
        dict(shot, shot_id=shot.get('source_shot_id', shot['shot_id'])), exclusions)


def policy_metadata(site, frozen_site):
    snapshot = lambda value: {'compatibility_policy_revision': copy.deepcopy(value.get('compatibility_policy_revision')),
                              'exclusions': copy.deepcopy(value.get('exclusions', []))}
    current, frozen = snapshot(site), snapshot(frozen_site)
    return {'current_policy': current, 'frozen_render_metadata': frozen,
            'policy_differs_from_frozen_snapshot': current != frozen,
            'authority_zh': '当前排除以本次目录配置为准；冻结样片计划内的排除是生成时历史快照，旧计划与媒体回执未改写。'}


def write(path, value, *, frozen=False):
    path = Path(path)
    if path.exists() and frozen:
        if read(path) != value:
            raise ValueError('Frozen site plan changed; use a fresh site revision: ' + str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.partial')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,47}', value):
        raise ValueError('Site/revision identifiers must be short filename-safe strings')
    return value


def initialize_catalog(inventory_path, *, run=RUN):
    """Keep the exact26 existing primary entries; only initialize empty points."""
    import scene_site_catalog_v1 as directory
    run, inventory_path = Path(run).resolve(), Path(inventory_path).resolve()
    inventory = read(inventory_path)
    scenes = inventory['scenes']
    if len(scenes) != 26 or len({s['map_path'] for s in scenes}) != 26:
        raise ValueError('Require the frozen existing26-primary inventory')
    target = run / 'scene_samples_sites_v1.json'
    if target.is_file():
        current = read(target)
        if {s['map'] for s in current['sites']} != {s['map_path'] for s in scenes}:
            raise ValueError('Existing sample catalog primary map scope differs')
        return {'catalog': str(target), 'scenes': len(current['sites']), 'existing_preserved': True}
    sites = []
    for scene in scenes:
        package = scene['package']
        path = scene['map_path']
        stem = re.sub(r'[^A-Za-z0-9_]', '_', package.lower())[:20]
        sites.append({'site_id': 'primary_' + stem + '_' + object_sha(path)[:8],
            'catalog_scene_id': scene['id'], 'scene_label': directory.PACKAGE_NAMES.get(package, package) + ' / ' + path.rsplit('/', 1)[-1],
            'map': path, 'position': None, 'yaw': 0., 'exposure_compensation': 0.,
            'exclusions': [], 'revision': 'v1', 'location_label': '拍摄点待选择'})
    write(target, {'schema': 'primary_scene_sample_sites_v1', 'source_inventory': {
        'path': str(inventory_path), 'sha256': sha(inventory_path)}, 'sites': sites,
        'primary_scene_count': 26, 'scene_purpose_rescreened': False})
    return {'catalog': str(target), 'scenes': len(sites), 'existing_preserved': False}


def validate_site(site):
    identifier(site['site_id'])
    identifier(site.get('revision', 'v1'))
    package = site['map'].split('.')[0]
    if not package.startswith('/Game/Scenes/') or not re.fullmatch(r'/Game/[A-Za-z0-9_/]+', package):
        raise ValueError('Require an existing catalog primary map in Content/Scenes')
    position = site.get('position')
    if position is None:
        return False
    values = [position[k] for k in ('x', 'y', 'z')] if isinstance(position, dict) else position
    if len(values) != 3 or not all(math.isfinite(float(v)) for v in [*values, site.get('yaw', 0.), site.get('exposure_compensation', 0.)]):
        raise ValueError('Site position, yaw and exposure must be finite')
    if not -10 <= float(site.get('exposure_compensation', 0.)) <= 10:
        raise ValueError('Camera exposure compensation outside bounded review range')
    return True


def excluded(shot, exclusions):
    for item in exclusions:
        if isinstance(item, str):
            if item == shot['shot_id']:
                return True
        elif isinstance(item, dict):
            if item.get('shot_id') and item['shot_id'] == shot['shot_id']:
                return True
            fields = ((item.get('motion_id', item.get('action_id')), 'motion_id'),
                      (item.get('camera_id'), 'camera_id'),
                      (item.get('orientation', item.get('aspect')), 'orientation'))
            constrained = [(v, key) for v, key in fields if v is not None]
            if constrained and all(shot[key] == value for value, key in constrained):
                return True
        else:
            raise ValueError('Exclusions must use shot IDs or explicit combination objects')
    return False


def select_samples(shots, site):
    """Prefer two walking samples; retain sites through compatible alternatives."""
    if 'sample_preferences' in site:
        preferences = site['sample_preferences']
        fields = ('motion_id', 'camera_id', 'orientation')
        if (not isinstance(preferences, list) or len(preferences) != 2
                or any(not isinstance(p, dict) for p in preferences)
                or any(p.get('orientation') not in ('landscape', 'portrait') for p in preferences)
                or {p.get('orientation') for p in preferences} != {'landscape', 'portrait'}):
            raise ValueError('sample_preferences requires exactly one landscape and one portrait entry')
        selected = []
        for orientation, _, _ in PREFERENCES:
            preference = next(p for p in preferences if p['orientation'] == orientation)
            if (any(not isinstance(preference.get(k), str) or not preference[k].strip() for k in fields)
                    or not isinstance(preference.get('reason_zh'), str) or not preference['reason_zh'].strip()):
                raise ValueError('sample_preferences requires explicit motion/camera/orientation and reason_zh')
            matching = [s for s in shots if all(s[k] == preference[k] for k in fields)]
            if len(matching) != 1 or preference['camera_id'] == 'front_head':
                raise ValueError('sample_preferences must uniquely match the current nonface library')
            shot = matching[0]
            if excluded(shot, site.get('exclusions', [])):
                raise ValueError('sample_preferences cannot select an excluded combination')
            selected.append((shot, {'label_zh': '指定代表样片 · ' + shot['camera_label'],
                'preferred': {k: preference[k] for k in fields}, 'fallback_used': False,
                'explicit_preference': True, 'reason_zh': preference['reason_zh'].strip(),
                'reason': 'explicit representative selection; no exclusion implied'}))
        return selected
    candidates = [s for s in shots if s['camera_id'] != 'front_head'
                  and not excluded(s, site.get('exclusions', []))]
    selected = []
    for orientation, camera, label in PREFERENCES:
        available = [s for s in candidates if s['orientation'] == orientation]
        if not available:
            continue
        available.sort(key=lambda s: (
            0 if (s['motion_id'], s['camera_id']) == ('MOTION_CAND_008', camera) else
            1 if s['motion_id'] == 'MOTION_CAND_008' and s['camera_id'] == 'front_full' else
            2 if s['camera_id'] in (camera, 'front_full') else 3,
            s['motion_id'], s['camera_id'], s['shot_id']))
        shot = available[0]
        selected.append((shot, {'label_zh': label if shot['camera_id'] == camera else '兼容替代 · ' + shot['camera_label'],
                               'preferred': {'motion_id': 'MOTION_CAND_008', 'camera_id': camera, 'orientation': orientation},
                               'fallback_used': (shot['motion_id'], shot['camera_id']) != ('MOTION_CAND_008', camera),
                               'reason': 'prefer walking; select an unexcluded full/orbit alternative when needed'}))
    return selected


def place_shot(original, site, selection):
    shot = copy.deepcopy(original)
    sid = identifier(site['site_id'])
    revision = identifier(site.get('revision', 'v1'))
    position = site['position']
    location = [float(position[k]) for k in ('x', 'y', 'z')] if isinstance(position, dict) else list(map(float, position))
    yaw = float(site.get('yaw', 0.))
    rows = shot['frames'] + [shot['endpoint_validation_frame']]
    source_diagnostics = {key: shot.pop(key) for key in ('path_metrics', 'geometry_pass_scope',
        'framing_diagnostics', 'quality', 'camera_standard_v2', 'camera_standard_v3') if key in shot}
    for row in rows:
        row['position'] = geo.transform_point(row['position'], location, yaw)
        row['look_at'] = geo.transform_point(row['look_at'], location, yaw)
        row['rotation_pitch_yaw_roll'][1] += yaw
    # Keep camera IDs short even for long catalog scene IDs; full identity is metadata.
    identity = object_sha({'site': sid, 'revision': revision, 'source': original['shot_id']})[:10]
    shot_id = f'ps_{sid[:30]}_{revision[:12]}_{original["orientation"][0]}_{identity}'
    shot.update(shot_id=shot_id, group='primary_scene_samples', scene_id=sid,
        scene_label=site.get('scene_label', sid), scene_source_map=site['map'].split('.')[0],
        scene_anchor_cm=location, actor_offset_cm=location, scene_yaw_degrees=yaw,
        source_shot_id=original['shot_id'], source_shot_plan_sha256=object_sha(original),
        source_trajectory_sha256=original['trajectory_sha256'], trajectory_sha256=object_sha(rows),
        site_revision=revision, exposure_compensation=float(site.get('exposure_compensation', 0.)),
        exposure_policy='zero preserves scene exposure; nonzero overrides only sample-camera exposure bias',
        sample_selection=selection, source_camera_diagnostics=source_diagnostics,
        site_placement={'source_coordinate_system': 'frozen actor identity origin; no initial-root recentering',
                        'location_xyz_cm': location, 'yaw_degrees': yaw,
                        'scope': 'rigid placement only; environment compatibility checked separately'},
        geometry_pass_scope='source trajectory rigidly placed; source diagnostics historical; no environment/visibility certification',
        human_acceptance='pending')
    if {f: shot[f] for f in geo.CLOCK_FIELDS} != {f: original[f] for f in geo.CLOCK_FIELDS}:
        raise ValueError('Scene placement changed the accepted body clock')
    return shot


def build_plans(catalog_path, *, run=RUN, library=None, site_ids=None, require_scene_count=26):
    run, catalog_path = Path(run).resolve(), Path(catalog_path).resolve()
    catalog = read(catalog_path)
    sites = catalog['sites']
    if len(sites) != require_scene_count or len({s['site_id'] for s in sites}) != len(sites):
        raise ValueError('Require exactly the existing primary catalog entries with unique site IDs')
    wanted = set(site_ids) if site_ids else {s['site_id'] for s in sites}
    if not wanted.issubset({s['site_id'] for s in sites}):
        raise ValueError('Unknown selected primary site')
    library = geo.load_library() if library is None else library
    source_pins = copy.deepcopy(library['sources'])
    cards, total = [], 0
    for site in sites:
        ready = validate_site(site)
        card = copy.deepcopy(site)
        card.update(status='point_pending' if not ready else 'not_selected', sample_plan=None, sample_count=0)
        card.update(copy.deepcopy(catalog.get('survey_metadata', {}).get(site['site_id'], {})))
        card['exclusions'] = copy.deepcopy(site.get('exclusions', []))
        card['compatibility_policy_revision'] = copy.deepcopy(site.get('compatibility_policy_revision'))
        relative = Path('plans') / (identifier(site['site_id']) + '_' + identifier(site.get('revision', 'v1')) + '.json')
        if ready and (site['site_id'] in wanted or (run / relative).is_file()):
            existing = read(run / relative) if (run / relative).is_file() else None
            if existing and any(frozen_sample_excluded(s, site.get('exclusions', [])) for s in existing['shots']):
                raise ValueError('Frozen sample is excluded; use a fresh site revision: ' + str(run / relative))
            shots = [place_shot(s, site, selection) for s, selection in select_samples(library['shots'], site)]
            plan = {'schema': 'primary_scene_sample_trial_v1', 'scene_id': site['site_id'],
                'revision': site.get('revision', 'v1'), 'site': copy.deepcopy(site), 'shots': shots,
                'source_pins': source_pins, 'source_samples_sha256': next(
                    (p['sha256'] for p in source_pins if Path(p['path']) == geo.SAMPLES), ''),
                'coordinate_policy': 'same exact rigid placement as numeric scene-site geometry',
                'clock_policy': 'same selected source windows and playback rates; no trimming or speed change',
                'source_scene_policy': 'load original read-only; sample maps/sequences only in owned namespace',
                'selection_scope': 'up to two compatible representative clips; excludes do not remove the scene card',
                'human_acceptance': 'pending'}
            if shots:
                if existing:
                    if (render_definition(existing['site'], include_policy=False) != render_definition(site, include_policy=False)
                            or existing.get('source_pins') != source_pins
                            or [sample_render_binding(s) for s in existing['shots']] != [sample_render_binding(s) for s in shots]):
                        raise ValueError('Frozen site plan changed; use a fresh site revision: ' + str(run / relative))
                    # Labels/observational metadata are displayed from the index;
                    # existing exact shot objects and their media receipts stay bound.
                    shots = existing['shots']
                else:
                    write(run / relative, plan, frozen=True)
                card.update(status='planned', sample_plan={'path': relative.as_posix(), 'sha256': sha(run / relative)},
                            sample_count=len(shots), selected_source_shot_ids=[s['source_shot_id'] for s in shots])
                card['current_policy_vs_frozen_render_metadata'] = policy_metadata(site, existing['site'] if existing else site)
                total += len(shots)
            else:
                card.update(status='no_compatible_nonface_sample', note_zh='本点位暂无未排除的非面部样片组合，场景仍保留。')
        cards.append(card)
    index = {'schema': 'primary_scene_samples_index_v1', 'source_catalog': {'path': str(catalog_path), 'sha256': sha(catalog_path)},
             'scene_count': len(cards), 'sample_count': total, 'sites': cards,
             'survey_metadata': copy.deepcopy(catalog.get('survey_metadata', {})),
             'existing_primary_catalog_only': True, 'scene_purpose_rescreened': False,
             'default_samples_per_site': 2, 'human_acceptance': 'pending'}
    write(run / INDEX, index)
    return {'index': str(run / INDEX), 'scenes': len(cards), 'planned_samples': total,
            'points_pending': sum(c['status'] == 'point_pending' for c in cards)}


def compatibility_review_data(run):
    """Small optional display records only; never load numeric reports here."""
    path = Path(run)/'compatibility_review_recommendations_v1.json'
    if not path.is_file():
        return {}, None, {'actions': {}, 'cameras': {}}
    try:
        document = read(path)
    except (OSError, ValueError):
        return {}, None, {'actions': {}, 'cameras': {}}
    if document.get('schema') != 'primary_scene_compatibility_review_recommendations_v1':
        return {}, None, {'actions': {}, 'cameras': {}}
    rows = {r['site_id']: r for r in document.get('scenes', []) if isinstance(r, dict) and r.get('site_id')}
    labels = {'actions': {}, 'cameras': {}}
    catalog_path = geo.RUN/'site_review_catalog_v1.json'
    if catalog_path.is_file():
        try:
            catalog = read(catalog_path)
        except (OSError, ValueError):
            catalog = {}
        labels['actions'] = {a.get('motion_id', a.get('id')): a.get('motion_label') or a.get('label')
                             for a in catalog.get('actions', [])}
        labels['cameras'] = {c.get('camera_id', c.get('id')): c.get('camera_label') or c.get('label')
                             for c in catalog.get('cameras', [])}
    return rows, {'path': path.name, 'sha256': sha(path)}, labels


def compatibility_review_card(site, review, labels, run):
    """Use only the exact site/point/report binding; labels do not alter decisions."""
    if not review or review.get('site_id') != site['site_id'] or site.get('survey_status') == 'stale_requires_recheck':
        return None
    if review.get('map') and review['map'].split('.')[0] != site['map'].split('.')[0]:
        return None
    if review.get('selected_point'):
        from merge_primary_scene_surveys_v1 import _same_point
        if not _same_point(site, review['selected_point']):
            return None
    if review.get('source_report'):
        pin = site.get('survey_report')
        expected = review['source_report']
        if not pin or (Path(run)/pin['path']).resolve() != Path(expected['path']).resolve() or pin['sha256'] != expected['sha256']:
            return None
    groups = []
    for field, title in [('priority_exact_camera_combinations', '相机实体疑点：优先核看这些组合'),
                         ('action_route_review_combinations', '路线与接地待查：先看动作'),
                         ('visual_only_combinations', '遮挡与小细节：先看画面')]:
        rows = []
        for row in review.get(field, []):
            action = row['action_id']
            rows.append({'action_id': action, 'action_label': labels['actions'].get(action) or action,
                'orientation': row['aspect'],
                'cameras': [{'camera_id': camera, 'label': labels['cameras'].get(camera) or camera}
                            for camera in row['camera_ids']]})
        if rows:
            groups.append({'title_zh': title, 'combinations': rows})
    focus = review.get('review_focus_zh', '')
    for action, label in labels['actions'].items():
        if action and label and action != label:
            focus = re.sub(r'(?<![A-Za-z0-9_])'+re.escape(action)+r'(?![A-Za-z0-9_])',
                           lambda match, label=label: label, focus)
    summary = review.get('summary', {})
    return {'review_focus_zh': focus,
        'camera_entity_count': summary.get('priority_exact_camera_combination_count', 0),
        'route_review_count': summary.get('action_route_review_combination_count', 0),
        'visual_only_count': summary.get('visual_only_combination_count', 0), 'groups': groups,
        'notice_zh': '仅供审看建议，尚未按这些建议排除组合；类别可能重合，不能相加当作排除数量。',
        'recommendations_applied': False}


def visual_review_data(run):
    """Read only the small review ledgers; media validation is not visual approval."""
    records, pins = {}, []
    for name in ('scene_visual_retries_v1.json', 'agent_scene_visual_notes_v1.json',
                 'agent_dynamic_exposure_notes_v2.json', 'agent_new_point_visual_notes_v3.json',
                 'root_execution_progress_v1.json'):
        path = run / name
        if path.is_file():
            records[name] = read(path)
            pins.append({'path': name, 'sha256': sha(path)})
    return records, pins


def visual_review_card(site, records, run):
    result = {'status': 'unviewed', 'label_zh': '未查看',
              'note_zh': '本页暂无当前样片的初审记录。',
              'human_acceptance': 'pending', 'human_label_zh': '待用户审查'}
    clips = site.get('clips', [])
    current_plan = site.get('sample_plan') or {}

    def same_contact(left, right):
        def normalized(value):
            path = Path(value)
            return str((path if path.is_absolute() else run / path).resolve()).casefold()
        return bool(left and right) and normalized(left) == normalized(right)

    # These newer ledgers pin both the viewed contact and its source video.
    # Compare with verified_rows' media hashes, never with an unpinned path alone.
    current_reviews = []
    for clip in clips:
        if not clip.get('playable'):
            continue
        found = None
        for name in ('agent_new_point_visual_notes_v3.json', 'agent_dynamic_exposure_notes_v2.json'):
            for row in records.get(name, {}).get('items', []):
                plan_pin, contact_pin, video_pin = (row.get(k) or {} for k in ('plan', 'contact', 'video'))
                if (row.get('viewed') is True and row.get('site_id') == site['site_id']
                        and row.get('shot_id') == clip['shot_id']
                        and plan_pin.get('sha256') and plan_pin['sha256'] == current_plan.get('sha256')
                        and same_contact(plan_pin.get('path'), current_plan.get('path'))
                        and contact_pin.get('sha256')
                        and contact_pin['sha256'] == clip.get('timeline_contact_sha256')
                        and same_contact(contact_pin.get('path'), clip.get('timeline_contact'))
                        and video_pin.get('sha256') and video_pin['sha256'] == clip.get('video_sha256')
                        and same_contact(video_pin.get('path'), clip.get('video'))):
                    found = row
                    break
            if found is not None:
                break
        if found is not None:
            current_reviews.append((clip, found))
    if current_reviews:
        observations = []
        for clip, row in current_reviews:
            aspect = '横屏' if clip['orientation'] == 'landscape' else '竖屏'
            if row.get('recommendation_zh'):
                observations.append(aspect + '：' + row['recommendation_zh'])
            for issue in row.get('remaining_issues_zh') or []:
                observations.append(aspect + '提醒：' + issue)
        result.update(observations_zh=observations,
                      note_zh='仅抽帧初审，未连续观看动态视频；结论只覆盖当前所见样片，仍待用户审查。')
        if any(row.get('needs_improvement') is True for _, row in current_reviews):
            return dict(result, status='needs_improvement', label_zh='待改进')
        if len(current_reviews) < len(clips):
            return dict(result, status='initial_review_recorded', label_zh='已有部分初审记录',
                        note_zh='部分当前样片尚未初审；已记录内容仅限抽帧，仍待连续播放与用户审查。')
        if any(row.get('remaining_issues_zh') or row.get('needs_improvement') is not False
               for _, row in current_reviews):
            return dict(result, status='initial_review_recorded', label_zh='已有初审记录（有提醒）')
        return dict(result, status='sampled_no_obvious_issue', label_zh='初审未见明显问题')

    retries = records.get('scene_visual_retries_v1.json', {}).get('items', [])
    retry = next((r for r in retries if r.get('site_id') == site['site_id']
                  and r.get('status', '').startswith(('queued', 'pending'))), None)
    if retry and retry.get('current_revision') == site.get('revision', 'v1'):
        return dict(result, status='needs_improvement', label_zh='待改进',
                    note_zh='已记录画面问题，需要改善点位、遮挡或亮度后再审看。')
    if retry:
        result['note_zh'] = '上一版有画面问题，当前版本需要重新初审。'
    if not clips or not all(c.get('playable') and c.get('timeline_contact') for c in clips):
        return result

    notes = records.get('agent_scene_visual_notes_v1.json', {}).get('scenes', [])
    note = next((n for n in notes if n.get('site_id') == site['site_id']), {})
    note_plan = note.get('plan') or {}
    matching_plan = (current_plan.get('sha256') and current_plan.get('sha256') == note_plan.get('sha256')
                     and same_contact(current_plan.get('path'), note_plan.get('path')))
    viewed = []
    if matching_plan:
        for clip in clips:
            contact = next((c for c in note.get('contacts', []) if c.get('viewed')
                            and c.get('shot_id') == clip['shot_id']
                            and same_contact(c.get('contact'), clip['timeline_contact'])), None)
            if contact:
                viewed.append(contact)
        if any(c.get('visible_issues') or c.get('retry_recommended') for c in viewed):
            return dict(result, status='needs_improvement', label_zh='待改进',
                        note_zh='当前样片初审记录了画面疑点，需要进一步处理和审看。')
        if len(viewed) == len(clips):
            return dict(result, status='sampled_no_obvious_issue', label_zh='初审未见明显问题',
                        note_zh='仅抽帧初审，仍需观看动态样片并由用户审查。')
    roots = records.get('root_execution_progress_v1.json', {}).get('sites', [])
    root_note = next((r for r in roots if r.get('site_id') == site['site_id']), {})
    if all(any(same_contact(clip['timeline_contact'], c)
               for c in root_note.get('reviewed_contacts', [])) for clip in clips):
        if root_note.get('visual_status') == 'sampled_no_obvious_issue':
            return dict(result, status='sampled_no_obvious_issue', label_zh='初审未见明显问题',
                        note_zh='仅抽帧初审，仍需观看动态样片并由用户审查。')
        return dict(result, status='initial_review_recorded', label_zh='已有初审记录',
                    note_zh='当前样片已有抽帧初审记录，仍待用户审查。')
    if viewed:
        result['note_zh'] = '当前样片仅部分完成抽帧初审，仍需继续查看。'
    return result


def build_gallery(run=RUN, *, numeric_report=None):
    from run_all_motion_camera_review_v1 import verified_rows
    run = Path(run).resolve()
    index = read(run / INDEX)
    review_rows, review_pin, review_labels = compatibility_review_data(run)
    visual_records, visual_pins = visual_review_data(run)
    cards, all_media = [], 0
    survey_pin_cache = {}
    for site in index['sites']:
        card = copy.deepcopy(site)
        card['clips'] = []
        card['preview_image_ready'] = False
        if site.get('survey_summary', {}).get('applies_to_current_site') and site['survey_summary'].get('full_matrix_sampled'):
            card['display_location_label'] = (site.get('location_label') or site.get('name') or site['site_id']).replace('待完整复查', '完整数字采样已完成').replace('待完整检查', '完整数字采样已完成')
        if site.get('survey_report'):
            try:
                from merge_primary_scene_surveys_v1 import _verify_pins, _same_point, _validate_dual, _uses_dual
                report_path = (run / site['survey_report']['path']).resolve()
                report_path.relative_to(run)
                if sha(report_path) != site['survey_report']['sha256']:
                    raise ValueError('Survey report changed')
                report = read(report_path)
                _verify_pins(report['source_pins'], survey_pin_cache)
                if site.get('survey_dual_evidence'):
                    dual_pin = site['survey_dual_evidence']
                    dual_path = (run / dual_pin['path']).resolve()
                    dual_path.relative_to(run)
                    if sha(dual_path) != dual_pin['sha256']:
                        raise ValueError('Dual evidence changed')
                    base, selected, dual = _validate_dual(dual_path, run, survey_pin_cache)
                    if base != report or selected != site['survey_full_attempt_index']:
                        raise ValueError('Dual evidence differs from displayed full attempt')
                elif _uses_dual(report):
                    raise ValueError('Private proxy report lacks its dual evidence')
                if site.get('survey_report_applies_to_site'):
                    candidate = report['full_attempts'][site['survey_full_attempt_index']]['candidate']
                    if not _same_point(site, candidate):
                        raise ValueError('Survey point differs from displayed location')
            except (OSError, ValueError, KeyError, TypeError, IndexError):
                card.pop('display_location_label', None)
                card['survey_status'] = 'stale_requires_recheck'
                card['survey_summary'] = dict(card.get('survey_summary', {}), applies_to_current_site=False)
                card['survey_summary']['collision_proxy_qualified'] = False
                card['survey_qualification_status'] = 'stale_requires_recheck'
                card['survey_warning_zh'] = '数字报告或其来源已改变，当前点位需要重新核对；视频仍按各自冻结计划展示。'
        review = compatibility_review_card(card, review_rows.get(site['site_id']), review_labels, run)
        if review:
            card.update(review_focus_zh=review['review_focus_zh'], compatibility_review=review)
        if site.get('preview_image'):
            preview = (run / site['preview_image']).resolve()
            preview.relative_to(run)
            if preview.is_file():
                card.update(preview_image=preview.relative_to(run).as_posix(),
                            preview_image_sha256=sha(preview), preview_image_ready=True)
        if site['sample_plan']:
            plan_path = run / site['sample_plan']['path']
            if sha(plan_path) != site['sample_plan']['sha256']:
                raise ValueError('Scene sample plan differs from index')
            frozen_plan = read(plan_path)
            shots = {s['shot_id']: s for s in frozen_plan['shots']}
            if any(frozen_sample_excluded(s, site.get('exclusions', [])) for s in shots.values()):
                raise ValueError('Current compatibility policy excludes a frozen representative sample')
            card['current_policy_vs_frozen_render_metadata'] = policy_metadata(site, frozen_plan['site'])
            media = verified_rows(shots, run)
            for shot in shots.values():
                row = {key: shot[key] for key in ('shot_id', 'motion_id', 'motion_label', 'camera_id',
                    'camera_label', 'orientation', 'duration_seconds', 'frame_count', 'width', 'height', 'sample_selection')}
                row.update(playable=shot['shot_id'] in media)
                if row['playable']:
                    row.update({key: media[shot['shot_id']][key] for key in ('video', 'poster', 'video_sha256',
                        'verification_receipt', 'verification_receipt_sha256', 'timeline_contact',
                        'timeline_contact_sha256')})
                    all_media += 1
                card['clips'].append(row)
        card['visual_review'] = visual_review_card(card, visual_records, run)
        cards.append(card)
    data = {'schema': 'primary_scene_samples_delivery_v1', 'scenes': cards,
            'scene_count': len(cards), 'playable': all_media, 'planned_samples': index['sample_count'],
            'selected_site_count': sum(s.get('position') is not None for s in cards),
            'index_pin': {'path': str(run / INDEX), 'sha256': sha(run / INDEX)},
            'human_acceptance': 'pending', 'numeric_report': str(numeric_report) if numeric_report else None,
            'compatibility_review_source': review_pin,
            'visual_review_sources': visual_pins,
            'scope_zh': '每个现有主关卡保留一张卡片。视频仅检查代表性构图、光照和空间；全部动作镜头的数字检查另行记录。'}
    encoded = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    target = run / 'gallery/index.html'
    target.parent.mkdir(exist_ok=True)
    target.write_text(HTML.replace('__DATA__', encoded), encoding='utf-8')
    (target.parent / '打开主场景样片.cmd').write_text('@echo off\n"' + sys.executable + '" "'
        + str(S / 'open_common_camera_gallery_v1.py') + '" --run-root "' + str(run)
        + '" --port 8900 %*\nif errorlevel 1 pause\n', encoding='utf-8')
    write(run / 'scene_samples_delivery_v1.json', data)
    return {'index': str(target), 'scenes': len(cards), 'playable': all_media, 'samples': index['sample_count']}


HTML = r'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>主场景拍摄点审查</title>
<style>*{box-sizing:border-box}body{margin:0;background:#111923;color:#e8eff7;font:16px/1.7 system-ui,"Microsoft YaHei",sans-serif}main{max-width:1500px;margin:auto;padding:28px}h1{margin-bottom:8px}p,small{color:#b5c5d7}.notice{padding:14px 18px;background:#1c3041;border-left:4px solid #71bdcf;border-radius:8px}.tools{display:flex;gap:12px;flex-wrap:wrap;margin:22px 0}input,select,button{font:inherit;padding:8px 13px;border:1px solid #53677d;border-radius:7px;background:#1b3044;color:white}input{min-width:260px}.scene{border:1px solid #30465d;border-radius:12px;background:#182432;padding:20px;margin:22px 0}.scene h2{margin:0}.facts{display:flex;gap:16px;flex-wrap:wrap;color:#bed0e0;font-size:14px}.clips{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:16px}.clip{background:#0b1119;border-radius:8px;overflow:hidden}.clip p{padding:0 13px}video{width:100%;max-height:620px;display:block;background:black}.scene-image{width:100%;max-height:520px;object-fit:contain;background:#0b1119;margin-top:14px}.pending{padding:45px;text-align:center;background:#101a26;border-radius:8px;color:#b7c6d6}details{font-size:13px;word-break:break-all;color:#adc1d5}summary{cursor:pointer}.good{color:#91d6b5}.review{margin:18px 0;padding:14px 18px;border:1px solid #51636d;border-radius:8px;background:#1b2936}.review p{margin:4px 0 10px}.review details{font-size:15px}.review li{margin-bottom:12px}.review small{display:block;font-size:12px;line-height:1.5;color:#9caebd}.review h4{margin-bottom:8px}.visual-status{padding:10px 14px;border-left:4px solid #d4b66b;background:#28303a}.visual-status.needs_improvement{border-color:#ed9b83}.visual-status.sampled_no_obvious_issue{border-color:#91d6b5}.visual-status small{display:block}@media(max-width:800px){main{padding:16px}.clips{grid-template-columns:1fr}}</style>
<main><h1>主场景拍摄点审查</h1><p>按现有主关卡目录逐场景选择一个拍摄点，查看人物大小、亮度及活动空间。同组保持既定动作片段、时长和播放速度。</p><div class="notice">当前横屏非面部镜头沿用已接受的50%移近标准，竖屏和面部参数保持现用配置。可排除不适合的动作或镜头组合，并保留场景供其余组合使用。视频可播放仅代表文件已核验，不代表场景适用或画面已通过。逐场景初审提示只依据已有审看记录，所有场景仍待用户审查。</div>
<div class="tools"><input id="search" placeholder="按场景、点位或关卡名称查找" aria-label="查找场景"><select id="filter"><option value="all">全部场景</option><option value="ready">已有样片</option><option value="pending">待准备</option></select><button id="pause">暂停全部</button><span id="progress"></span></div><div id="cards"></div><p id="scope"></p></main>
<script>const DATA=__DATA__;const root=document.querySelector('#cards');const el=(t,text,cls)=>{let x=document.createElement(t);if(text!==undefined)x.textContent=text;if(cls)x.className=cls;return x};function appendReview(card,s){const r=s.compatibility_review;if(!r)return;const box=el('div',undefined,'review');if(s.review_focus_zh)box.append(el('p','审看重点：'+s.review_focus_zh));box.append(el('p',`相机实体疑点 ${r.camera_entity_count} 组合　· 路线待查 ${r.route_review_count} 组合　· 遮挡与小细节待看 ${r.visual_only_count} 组合`));box.append(el('small',r.notice_zh));if(r.groups.length){const details=el('details');details.append(el('summary','展开具体动作、镜头与画幅'));for(const g of r.groups){details.append(el('h4',g.title_zh));const list=el('ul');for(const row of g.combinations){const item=el('li');item.append(el('div',`${row.orientation==='portrait'?'竖屏':'横屏'} · ${row.action_label} · ${row.cameras.map(c=>c.label).join('、')}`));item.append(el('small',`${row.action_id} / ${row.cameras.map(c=>c.camera_id).join(', ')}`));list.append(item)}details.append(list)}box.append(details)}card.append(box)}function render(){root.querySelectorAll('video').forEach(v=>v.pause());root.replaceChildren();let query=document.querySelector('#search').value.toLowerCase(),filter=document.querySelector('#filter').value;for(const s of DATA.scenes){let ready=s.clips.some(c=>c.playable);if(filter==='ready'&&!ready||filter==='pending'&&ready)continue;if(query&&!JSON.stringify([s.scene_label,s.site_id,s.map]).toLowerCase().includes(query))continue;let card=el('section',undefined,'scene');card.append(el('h2',s.scene_label||s.site_id));const vr=s.visual_review||{label_zh:'未查看',human_label_zh:'待用户审查',note_zh:'本页暂无当前样片的初审记录。',status:'unviewed'};const vb=el('div',undefined,'visual-status '+vr.status);vb.append(el('strong',vr.label_zh+' · '+vr.human_label_zh),el('small',vr.note_zh));for(const observation of vr.observations_zh||[])vb.append(el('p',observation));card.append(vb);let pos=s.position?Array.isArray(s.position)?s.position:[s.position.x,s.position.y,s.position.z]:null;card.append(el('p',s.display_location_label||s.location_label||s.name||s.site_id));card.append(el('div',`点位：${pos?pos.map(v=>Number(v).toFixed(1)).join(' / ')+' cm':'待选择'}　· 朝向 ${s.yaw||0}°　· 相机曝光补偿 ${s.exposure_compensation||0} EV`,'facts'));let numeric=s.survey_summary||{};card.append(el('p',numeric.applies_to_current_site?`数字采样：${numeric.no_proxy_conflict_combinations}/1260 组合未发现代理冲突；疑似问题 ${numeric.suspected_conflict_combinations||0} 组合。`:'数字采样：当前点位完整检查待完成。'));if(s.survey_warning_zh)card.append(el('p',s.survey_warning_zh,'notice'));if(s.survey_report){let link=document.createElement('a');link.href='../'+s.survey_report.path;link.textContent=s.survey_status==='stale_requires_recheck'?'查看历史数字报告（来源需重新核对）':s.survey_report_applies_to_site&&numeric.applies_to_current_site?'查看当前点位数字报告':'查看其他候选点报告（不能套用本点）';link.target='_blank';link.rel='noopener';link.style.color='#8bd1ff';card.append(link)}if(s.survey_dual_evidence){let raw=document.createElement('a');raw.href='../'+s.survey_dual_evidence.path;raw.textContent='查看原始场景变化与草层证据';raw.target='_blank';raw.rel='noopener';raw.style.cssText='display:block;color:#8bd1ff;margin-top:8px';card.append(raw)}if(s.survey_ground_evidence){let ground=document.createElement('a');ground.href='../'+s.survey_ground_evidence.path;ground.textContent='查看地面对象查询记录（身体与相机仍用原检查）';ground.target='_blank';ground.rel='noopener';ground.style.cssText='display:block;color:#8bd1ff;margin-top:8px';card.append(ground)}if(s.survey_ground_diagnostic){let diag=document.createElement('a');diag.href='../'+s.survey_ground_diagnostic.path;diag.textContent='查看同位置复杂未命中／简单命中诊断';diag.target='_blank';diag.rel='noopener';diag.style.cssText='display:block;color:#8bd1ff;margin-top:8px';card.append(diag)}appendReview(card,s);let exc=s.exclusions||[];const policyMeta=s.current_policy_vs_frozen_render_metadata;card.append(el('p',`当前配置排除 ${exc.length} 个组合；疑似问题不会自动排除，其余组合仍保留。`));if(policyMeta&&policyMeta.policy_differs_from_frozen_snapshot)card.append(el('p',policyMeta.authority_zh,'notice'));if(s.note_zh)card.append(el('p',s.note_zh,'notice'));let details=el('details'),summary=el('summary','查看关卡与当前排除配置');details.append(summary,el('div',s.map),el('div','当前兼容性策略版本：'+(s.compatibility_policy_revision||'未标注')),el('pre',JSON.stringify(exc,null,2)));if(policyMeta&&policyMeta.policy_differs_from_frozen_snapshot)details.append(el('div','冻结样片计划历史策略快照（不作为当前排除配置）'),el('pre',JSON.stringify(policyMeta.frozen_render_metadata,null,2)));card.append(details);if(s.preview_image_ready){let preview=document.createElement('img');preview.src='../'+s.preview_image;preview.alt=(s.scene_label||s.site_id)+' 人物与曝光预览';preview.className='scene-image';preview.loading='lazy';card.append(preview,el('small','静态预览用于选择人物亮度和构图；动态舒适度需看样片。'))}let clips=el('div',undefined,'clips');if(!s.clips.length)clips.append(el('div',s.status==='point_pending'?'正在选择拍摄点':'样片尚未准备','pending'));for(const c of s.clips){let box=el('article',undefined,'clip');if(c.playable){let v=document.createElement('video');v.controls=true;v.preload='metadata';v.muted=true;v.playsInline=true;v.src='../'+c.video;v.poster='../'+c.poster;box.append(v)}else box.append(el('div','样片正在准备，尚未核验','pending'));box.append(el('p',`${c.orientation==='landscape'?'横屏':'竖屏'} · ${c.motion_label} · ${c.camera_label} · ${c.duration_seconds.toFixed(2)}秒`));if(c.sample_selection.explicit_preference)box.append(el('p','代表样片选择：'+c.sample_selection.reason_zh));else if(c.sample_selection.fallback_used)box.append(el('p','本片使用另一组未排除的兼容组合。'));clips.append(box)}card.append(clips);root.append(card)}document.querySelector('#progress').textContent=`${DATA.scene_count}个主场景 · 已选点 ${DATA.selected_site_count}/${DATA.scene_count} · 文件已核验 ${DATA.playable}/${DATA.planned_samples} 条样片`;document.querySelector('#scope').textContent=DATA.scope_zh}document.querySelector('#search').oninput=render;document.querySelector('#filter').onchange=render;document.querySelector('#pause').onclick=()=>document.querySelectorAll('video').forEach(v=>v.pause());render();</script></html>'''


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['init', 'plan', 'gallery'])
    parser.add_argument('--run-root', type=Path, default=RUN)
    parser.add_argument('--catalog', type=Path)
    parser.add_argument('--inventory', type=Path)
    parser.add_argument('--site-ids', nargs='*')
    parser.add_argument('--numeric-report', type=Path)
    args = parser.parse_args()
    if args.mode == 'init':
        result = initialize_catalog(args.inventory or args.run_root / 'survey_inventory_v1.json', run=args.run_root)
    elif args.mode == 'plan':
        if not args.catalog:
            parser.error('plan requires --catalog with all26 existing primary entries')
        result = build_plans(args.catalog, run=args.run_root, site_ids=args.site_ids)
    else:
        result = build_gallery(args.run_root, numeric_report=args.numeric_report)
    print(json.dumps(result, ensure_ascii=False))
