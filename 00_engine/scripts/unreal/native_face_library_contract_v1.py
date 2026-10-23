"""Read-only registry for verified native face/body derived animations.

This module never scans import folders or creates assets. Successful import
alone is insufficient: every selectable entry binds a composition report and a
root visual record. ``validated_review`` does not mean user acceptance.
"""
from __future__ import annotations

import copy
from collections import OrderedDict
import hashlib
import json
from pathlib import Path
import re
import math

SCHEMA = 'native_face_library_v1'
RUN = Path(__file__).resolve().parents[2] / 'outputs/unreal_character_import/character_runtime_face_library_20261007_v1'
REGISTRY = RUN / 'native_face_library_registry_v1.json'
PROJECT_CONTENT = Path('D:/UE/projects/datatry_02/Content')
ASSET_ROOT = '/Game/DataMake/Validation/NativeFaceLibrary20261007'
SKELETONS = {sex: f'/Game/DataMake/Validation/CFDNativeBatch4020261006/SharedSkeletons/SKEL_CFDShared_{sex.title()}_v1.SKEL_CFDShared_{sex.title()}_v1'
             for sex in ('female', 'male')}
CHECKS = ('non_face_body_unchanged', 'active_curves_mapped', 'face_support_bones_verified',
          'component_curve_sync_verified', 'source_assets_unchanged', 'saved_asset_readback_verified')
# Only parsed, reduced import reports are retained across validations. Hashes
# are never cached: every catalog call reads and hashes each evidence file.
NATIVE_IMPORT_CACHE_LIMIT = 8
_NATIVE_IMPORT_CACHE = OrderedDict()
PANEL_RUN = RUN.parent / 'native_face_panel_integration_20261009_v1'
PANEL_REGISTRY = PANEL_RUN / 'native_face_library_registry_v2.json'
ACTIVE_POINTER = PANEL_RUN / 'active_face_library_v1.json'
ACCEPTED_SELECTION = RUN.parent / 'native_face_five_second_20261008_v1/accepted_face_selection_v1.json'
PANEL_ASSET_ROOT = '/Game/DataMake/Validation/NativeFacePanelFiveSecond20261009'
SCHEMA_V2 = 'native_face_library_v2'
FACE_IDS = ('idle', 'smile', 'displeased', 'sad')
LEGACY_FACE_MAP = {'gentle_smile': 'smile', 'dramatic_sad': 'sad', 'gentle_displeased': 'displeased'}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def source(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def _asset_path(value, *, owned=False):
    if not isinstance(value, str) or not re.fullmatch(r'/Game/[A-Za-z0-9_/]+\.[A-Za-z0-9_]+', value):
        raise ValueError('Expected a complete /Game asset object path')
    if value.rsplit('/', 1)[1].split('.')[0] != value.rsplit('.', 1)[1]:
        raise ValueError('Asset object and package names differ')
    if owned and not value.startswith(ASSET_ROOT + '/'):
        raise ValueError('Face derived assets must stay in the isolated native face root')
    return value


def _native_import_summary(document):
    if not isinstance(document, dict):
        raise ValueError('Expected a JSON native import evidence object')
    fields = ('success', 'source_unchanged', 'skeleton_file_unchanged',
              'new_dirty_packages_outside_destination', 'source', 'skeleton_after')
    summary = {key: copy.deepcopy(document[key]) for key in fields if key in document}
    if 'task' in document:
        summary['task'] = {'sex': document['task'].get('sex')}
    if 'animations' in document:
        summary['animations'] = [{key: copy.deepcopy(row[key])
            for key in ('path', 'skeleton', 'active_curve_names') if key in row} for row in document['animations']]
    return summary


def _native_import_json(path, actual_sha, raw):
    key = (str(path.resolve()), actual_sha)
    if key not in _NATIVE_IMPORT_CACHE:
        # Parse the exact bytes whose full SHA was just checked, not a second
        # file read that could have changed between hashing and parsing.
        _NATIVE_IMPORT_CACHE[key] = _native_import_summary(json.loads(raw.decode('utf-8-sig')))
    _NATIVE_IMPORT_CACHE.move_to_end(key)
    while len(_NATIVE_IMPORT_CACHE) > NATIVE_IMPORT_CACHE_LIMIT:
        _NATIVE_IMPORT_CACHE.popitem(last=False)
    return copy.deepcopy(_NATIVE_IMPORT_CACHE[key])


def _evidence(record, cache, *, json_file=False, native_import=False):
    if (not isinstance(record, dict) or not isinstance(record.get('path'), str)
            or not re.fullmatch(r'[0-9a-f]{64}', record.get('sha256', ''))):
        raise ValueError('Every source needs an absolute path and SHA256')
    path = Path(record['path'])
    if not path.is_absolute() or not path.is_file():
        raise ValueError('Evidence source does not exist: ' + str(path))
    key = (str(path.resolve()), record['sha256'], native_import)
    if key not in cache:
        raw = path.read_bytes()
        actual_sha = hashlib.sha256(raw).hexdigest()
        if actual_sha != record['sha256']:
            raise ValueError('Evidence source SHA changed: ' + str(path))
        if path.suffix.lower() == '.json':
            cache[key] = (_native_import_json(path, actual_sha, raw) if native_import
                          else json.loads(raw.decode('utf-8-sig')))
        else:
            cache[key] = None
    if json_file and (path.suffix.lower() != '.json' or not isinstance(cache[key], dict)):
        raise ValueError('Expected a JSON evidence object')
    return cache[key]


def _package(asset_path, record, cache):
    expected = (PROJECT_CONTENT / (asset_path.split('.', 1)[0].removeprefix('/Game/') + '.uasset')).resolve()
    if Path(record.get('path', '')).resolve() != expected:
        raise ValueError('Saved package evidence does not belong to the selected animation')
    _evidence(record, cache)


def _coverage(value):
    if not isinstance(value, dict) or value.get('coverage') not in ('all_frames', 'sampled_frames'):
        raise ValueError('Composition must state the real non-face comparison coverage')
    checked, total = value.get('checked_frame_count'), value.get('frame_count')
    if type(checked) is not int or type(total) is not int or not 0 < checked <= total:
        raise ValueError('Invalid non-face comparison frame counts')
    if value['coverage'] == 'all_frames' and checked != total:
        raise ValueError('An all-frame claim needs all frames checked')
    return copy.deepcopy(value)


def validate_registry(document):
    if isinstance(document, dict) and document.get('schema') == SCHEMA_V2:
        return validate_registry_v2(document)
    if not isinstance(document, dict) or document.get('schema') != SCHEMA:
        raise ValueError('Unsupported native face registry schema')
    if document.get('status') not in ('validated_review', 'published'):
        raise ValueError('Candidate/unverified assets cannot enter the selectable face library')
    if not isinstance(document.get('sources'), dict) or not document['sources']:
        raise ValueError('Face registry requires bound source evidence')
    cache = {}
    for record in document['sources'].values():
        _evidence(record, cache)
    entries = document.get('entries')
    if not isinstance(entries, list) or not entries:
        raise ValueError('Face registry has no verified derived entries')
    seen, paths, names = set(), set(), {}
    normalized = []
    for raw in entries:
        if not isinstance(raw, dict):
            raise ValueError('Face entries must be objects')
        row = copy.deepcopy(raw)
        sex, face_id, body = row.get('sex'), row.get('face_id'), row.get('body_action_id')
        if sex not in SKELETONS or not isinstance(face_id, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,63}', face_id) or face_id == 'none':
            raise ValueError('Invalid face identity; none is an intrinsic body-only operation')
        if not isinstance(body, str) or not (body == 'static' or re.fullmatch(r'ACT_[A-Z0-9_]+', body) or body.startswith('/Game/')):
            raise ValueError('Use a stable body action ID, object path, or static')
        if body.startswith('/Game/'):
            _asset_path(body)
        key = (sex, face_id, body)
        if key in seen:
            raise ValueError('Duplicate sex/face/body selection')
        seen.add(key)
        if not isinstance(row.get('label'), str) or not row['label'].strip():
            raise ValueError('Face entry requires a readable label')
        name_key = (sex, face_id)
        if name_key in names and names[name_key] != row['label']:
            raise ValueError('One face ID must keep one label across body actions')
        names[name_key] = row['label']
        animation = _asset_path(row.get('animation_path'), owned=True)
        native = _asset_path(row.get('native_animation_path'), owned=True)
        if animation in paths or animation == native or row.get('skeleton_path') != SKELETONS[sex]:
            raise ValueError('Derived animation path or shared Skeleton is invalid')
        paths.add(animation)
        _package(animation, row['package'], cache)
        reports = row.get('evidence', {})
        imported = _evidence(reports.get('native_import'), cache, json_file=True, native_import=True)
        if (imported.get('success') is not True or imported.get('task', {}).get('sex') != sex
                or imported.get('source_unchanged') is not True or imported.get('skeleton_file_unchanged') is not True
                or imported.get('new_dirty_packages_outside_destination') != []):
            raise ValueError('Native import did not preserve the source/shared Skeleton')
        source_animation = next((a for a in imported.get('animations', []) if a.get('path') == native), None)
        if source_animation is None or source_animation.get('skeleton') != SKELETONS[sex] or not source_animation.get('active_curve_names'):
            raise ValueError('Native source animation is missing, curve-empty, or uses another Skeleton')
        _evidence(imported['source'], cache)
        _evidence(imported['skeleton_after'], cache)
        composed = _evidence(reports.get('composition'), cache, json_file=True)
        if (composed.get('success') is not True or composed.get('animation_path') != animation
                or composed.get('native_animation_path') != native or composed.get('sex') != sex
                or composed.get('body_action_id') != body or composed.get('skeleton_path') != SKELETONS[sex]
                or any(composed.get('checks', {}).get(check) is not True for check in CHECKS)):
            raise ValueError('Derived face/body composition has not passed the required bounded checks')
        if composed.get('package') != row['package']:
            raise ValueError('Composition report is not bound to the current saved derived package')
        row['non_face_validation'] = _coverage(composed.get('non_face_validation'))
        playback = row.get('playback', {})
        if playback.get('mode') == 'loop':
            if playback.get('end_behavior') != 'repeat' or composed.get('loop_boundary_verified') is not True:
                raise ValueError('Loop playback requires a separately verified boundary')
        elif playback.get('mode') == 'oneshot':
            if playback.get('end_behavior') not in ('return_body', 'hold_last'):
                raise ValueError('One-shot playback needs an explicit end behavior')
        else:
            raise ValueError('Playback mode must be loop or oneshot')
        visual = _evidence(reports.get('root_visual'), cache, json_file=True)
        if (visual.get('reviewer') != 'root_agent' or visual.get('status') != 'reviewed_for_panel'
                or animation not in visual.get('animation_paths', []) or not isinstance(visual.get('observations'), str)
                or not visual['observations'].strip()):
            raise ValueError('A root visual record is required before adding a face to the review panel')
        row['user_acceptance'] = visual.get('user_acceptance', 'pending')
        normalized.append(row)
    return {'schema': SCHEMA, 'status': document['status'], 'sources': copy.deepcopy(document['sources']), 'entries': normalized}


def catalog(path=REGISTRY, *, published_only=False):
    before = source(path)
    result = validate_registry(read(path))
    if before != source(path):
        raise ValueError('Face registry changed while reading')
    if published_only and result['status'] != 'published':
        raise ValueError('This is a validated review library, not a published final library')
    result['registry_source'] = before
    return result


def active_registry_path():
    """An explicit published pointer; never fall back from an invalid pointer."""
    if not ACTIVE_POINTER.exists():
        return REGISTRY
    pointer = read(ACTIVE_POINTER)
    if pointer.get('schema') != 'native_face_active_pointer_v1' or Path(pointer.get('registry', {}).get('path', '')).resolve() != PANEL_REGISTRY.resolve():
        raise ValueError('Invalid explicit face library activation')
    _evidence(pointer['registry'], {}, json_file=True)
    return PANEL_REGISTRY


def panel_playback(playback):
    return isinstance(playback, dict) and (playback.get('mode'), playback.get('end_behavior')) in {('loop', 'repeat'), ('oneshot', 'hold_last')}


def migrate_legacy_appearance(appearance, old_sha, library):
    """Only the immutable legacy registry may authorize a known ID migration."""
    result, changes = copy.deepcopy(appearance), []
    if library.get('schema') != SCHEMA_V2 or old_sha == library.get('registry_source', {}).get('sha256'):
        return result, changes
    legacy = library['sources']['legacy_registry']
    if old_sha != legacy['sha256']:
        raise ValueError('旧表情配置来源不匹配，不能自动迁移。')
    _evidence(legacy, {}, json_file=True)
    for sex, row in result.items():
        face = row['face_id']
        if face == 'none':
            continue
        if face not in LEGACY_FACE_MAP:
            raise ValueError('旧表情没有对应的新类别，请明确重新选择：' + str(face))
        row['face_id'] = LEGACY_FACE_MAP[face]
        changes.append({'sex': sex, 'old_face_id': face, 'new_face_id': row['face_id']})
    return result, changes


def _same_record(a, b):
    return isinstance(a, dict) and isinstance(b, dict) and Path(a.get('path', '')).resolve() == Path(b.get('path', '')).resolve() and a.get('sha256') == b.get('sha256')


def _five_second_composition(report, sex, animation, face_animation, start, end, cache):
    task, verify = report.get('task', {}), report.get('verification', {})
    if (report.get('success') is not True or report.get('sources_unchanged') is not True
            or report.get('new_dirty_packages_outside_target') != [] or task.get('sex') != sex
            or report.get('destination') != animation.split('.')[0]
            or task.get('face_animation', '').split('.')[0] != face_animation.split('.')[0]
            or task.get('face_start_seconds') != start or task.get('face_end_seconds') != end
            or task.get('face_rate') != 1 or task.get('face_playback') != 'hold' or 'face_envelope' in task
            or not math.isclose(verify.get('duration_seconds', -1), 5, abs_tol=1e-6)
            or verify.get('all_frame_count') != round(5 * verify.get('fps', 0)) + 1
            or verify.get('all_frame_count', 0) < 151 or len(report.get('face_bones', [])) != 10
            or verify.get('unrelated_curve_keys_identical') is not True):
        raise ValueError('Native five-second composition/timing evidence is incomplete')
    maxima = verify.get('max_absolute_errors', {})
    if any(not math.isfinite(maxima.get(k, math.inf)) or maxima[k] > 1e-4 for k in ('protected_bones', 'face_curves')):
        raise ValueError('Five-second body/curve comparison failed')
    for k, limit in {'translation_cm': .001, 'rotation_degrees': .2, 'scale_abs': .0001}.items():
        actual = verify.get('face_bone_metric_maxima', {}).get(k, math.inf)
        if not math.isfinite(actual) or actual > limit:
            raise ValueError('Five-second face support bone comparison failed')
    if not report.get('sources'):
        raise ValueError('Composition source assets are not bound')
    for record in report['sources']:
        _evidence(record, cache)
    return {'coverage': 'all_frames', 'checked_frame_count': verify['all_frame_count'], 'frame_count': verify['all_frame_count']}


def validate_registry_v2(document):
    if document.get('status') not in ('validated_review', 'published'):
        raise ValueError('Unverified five-second registry')
    sources, cache = document.get('sources', {}), {}
    for key in ('contract', 'accepted_selection', 'legacy_registry', 'preparation_manifest', 'root_visual'):
        _evidence(sources.get(key), cache, json_file=key != 'contract')
    for record in sources.values():
        _evidence(record, cache)
    if (not _same_record(sources['contract'], source(__file__))
            or Path(sources['accepted_selection']['path']).resolve() != ACCEPTED_SELECTION.resolve()):
        raise ValueError('Registry must bind this contract and the exact accepted selection')
    accepted = _evidence(sources['accepted_selection'], cache, json_file=True)
    if accepted.get('selection_accepted') is not True or not _same_record(sources['legacy_registry'], accepted.get('runtime_registry_unchanged')):
        raise ValueError('Accepted selection or historical registry binding changed')
    choices = {(r['sex'], r['face_id']): r for r in accepted.get('entries', [])}
    if len(accepted.get('entries', [])) != 8 or set(choices) != {(s, f) for s in SKELETONS for f in FACE_IDS}:
        raise ValueError('Exactly eight accepted sex/face selections required')
    manifest = _evidence(sources['preparation_manifest'], cache, json_file=True)
    if not _same_record(manifest.get('selection'), sources['accepted_selection']):
        raise ValueError('Preparation did not bind the accepted selection')
    visual = _evidence(sources['root_visual'], cache, json_file=True)
    if (visual.get('reviewer') != 'root_agent' or visual.get('status') != 'reviewed_for_panel'
            or not str(visual.get('observations', '')).strip() or not visual.get('animation_paths')
            or visual.get('scope') != 'representative_combinations_only'):
        raise ValueError('Explicit representative root visual evidence is required')
    for record in visual.get('evidence', []):
        _evidence(record, cache)
    if not visual.get('evidence'):
        raise ValueError('Root visual record must reference actual visual evidence')
    expected = {(r['sex'], r['face_id'], r['body_action_id']): r for r in manifest.get('entries', [])}
    entries = document.get('entries', [])
    if len(expected) != 48 or len(entries) != 48:
        raise ValueError('Require 40 dynamic and eight accepted static combinations')
    seen, paths, rows = set(), set(), []
    for raw in entries:
        row = copy.deepcopy(raw)
        key = (row.get('sex'), row.get('face_id'), row.get('body_action_id'))
        if key in seen or key not in expected or key[:2] not in choices:
            raise ValueError('Unexpected or duplicate face/body entry')
        seen.add(key)
        sex, face, body = key
        choice, planned = choices[key[:2]], expected[key]
        if choice.get('selection_accepted') is not True:
            raise ValueError('Individual face selection is not accepted')
        animation = _asset_path(row.get('animation_path'))
        if animation in paths or row.get('skeleton_path') != SKELETONS[sex] or row.get('label') != choice['label_zh']:
            raise ValueError('Invalid animation, skeleton or accepted label')
        paths.add(animation)
        if animation.split('.')[0] != planned['asset'].split('.')[0] or row.get('playback') != {'mode': 'oneshot', 'end_behavior': 'hold_last', 'rate': 1, 'duration_seconds': 5}:
            raise ValueError('Planned source and original-speed oneshot playback required')
        _package(animation, row['package'], cache)
        _package(choice['source_animation'], choice['source_asset'], cache)
        _package(choice['asset'], choice['asset_file_at_selection'], cache)
        evidence = row.get('evidence', {})
        if row.get('native_animation_path') != choice['source_animation'] or not _same_record(evidence.get('native_import'), choice['evidence']['source_report']):
            raise ValueError('Wrong accepted native source')
        imported = _evidence(evidence['native_import'], cache, json_file=True, native_import=True)
        source_anim = next((a for a in imported.get('animations', []) if a.get('path') == choice['source_animation']), {})
        if (imported.get('success') is not True or imported.get('task', {}).get('sex') != sex
                or imported.get('source_unchanged') is not True or imported.get('skeleton_file_unchanged') is not True
                or imported.get('new_dirty_packages_outside_destination') != []
                or source_anim.get('skeleton') != SKELETONS[sex] or not source_anim.get('active_curve_names')):
            raise ValueError('Accepted native import preservation failed')
        _evidence(imported['source'], cache)
        _evidence(imported['skeleton_after'], cache)
        static_report = _evidence(choice['evidence']['composition_report'], cache, json_file=True)
        window = choice['source_window']
        coverage = _five_second_composition(static_report, sex, choice['asset'], choice['source_animation'], window['start_seconds'], window['end_seconds'], cache)
        if static_report['task'].get('body_mode') != 'static' or static_report['task'].get('static_use_reference_pose') is not True:
            raise ValueError('Accepted static baseline is not reference pose')
        comp = _evidence(evidence.get('composition'), cache, json_file=True)
        if Path(evidence['composition']['path']).resolve() != Path(planned['report']).resolve():
            raise ValueError('Composition differs from preparation')
        if body == 'static':
            if animation != choice['asset'] or not _same_record(evidence['composition'], choice['evidence']['composition_report']):
                raise ValueError('Only the eight exact accepted static assets may be reused')
        else:
            if not animation.startswith(PANEL_ASSET_ROOT + '/Composites/' + sex + '/'):
                raise ValueError('Dynamic asset escaped new integration root')
            coverage = _five_second_composition(comp, sex, animation, choice['asset'], 0, 5, cache)
            task = comp['task']
            if (task.get('body_mode') != 'animation' or not _same_record(task.get('accepted_face_selection'), sources['accepted_selection'])
                    or not _same_record(task.get('accepted_static_report'), choice['evidence']['composition_report'])
                    or task.get('panel_integration_task', {}).get('body_action_id') != body
                    or task.get('panel_integration_task', {}).get('face_id') != face
                    or task.get('allowed_face_curve_names') != static_report['task'].get('allowed_face_curve_names')):
                raise ValueError('Dynamic source selection binding failed')
            body_report = _evidence(task.get('body_window_report'), cache, json_file=True)
            verify = body_report.get('verification', {})
            mapping = body_report.get('mapping', {})
            if (body_report.get('success') is not True or body_report.get('sources_unchanged') is not True
                    or body_report.get('new_dirty_packages_outside_target') != [] or body_report.get('dirty_sources') != []
                    or body_report.get('task', {}).get('sex') != sex or body_report.get('task', {}).get('action_id') != body
                    or body_report.get('original_body', {}).get('asset') != planned.get('original_body_animation')
                    or body_report.get('original_body') != task.get('original_body')
                    or not body_report.get('destination', '').startswith(PANEL_ASSET_ROOT + '/BodyWindows/' + sex + '/')
                    or mapping.get('mode') not in ('repeat_body_original_speed', 'crop_first_five_seconds')
                    or mapping.get('face_clock_wraps') is not False or mapping.get('body_retimed') is not False
                    or mapping.get('seams_blended') is not False or mapping.get('fps') != verify.get('fps')
                    or task.get('body_animation') != body_report.get('destination')
                    or verify.get('bone_count') != 118 or verify.get('duration_seconds') != 5
                    or verify.get('all_frame_count') != round(5 * verify.get('fps', 0)) + 1
                    or any(not math.isfinite(v) or v > 1e-4 for v in verify.get('max_absolute_errors', {}).values())
                    or set(verify.get('max_absolute_errors', {})) != {'bones', 'curves'}):
                raise ValueError('Original-speed body window verification failed')
            _package(body_report['asset_record']['asset'], body_report['asset_record'], cache)
            for record in body_report['sources']:
                _evidence(record, cache)
        row['non_face_validation'] = coverage
        row['user_acceptance'] = 'accepted_four_representative_classes_not_all_combinations'
        rows.append(row)
    if seen != set(expected) or not set(visual['animation_paths']).issubset(paths):
        raise ValueError('Registry/representative visual coverage mismatch')
    for sex in SKELETONS:
        bodies = {r['body_action_id'] for r in rows if r['sex'] == sex}
        if len(bodies) != 6 or 'static' not in bodies or any((sex, f, b) not in seen for f in FACE_IDS for b in bodies):
            raise ValueError('Each sex needs the exact four faces across six body choices')
    return {'schema': SCHEMA_V2, 'status': document['status'], 'sources': copy.deepcopy(sources), 'entries': rows}


def available_faces(library, sex, body_action_id):
    if sex not in SKELETONS:
        raise ValueError('Invalid sex')
    return [{'face_id': 'none', 'label': '无表情（恢复身体动作）'}] + [
        {'face_id': row['face_id'], 'label': row['label'], 'playback': copy.deepcopy(row['playback']),
         'validation_scope': copy.deepcopy(row['non_face_validation']), 'user_acceptance': row['user_acceptance']}
        for row in library['entries'] if row['sex'] == sex and row['body_action_id'] == body_action_id]


def resolve(library, sex, face_id, body_action_id, *, body_animation_path=None):
    if sex not in SKELETONS:
        raise ValueError('Invalid sex')
    if face_id == 'none':
        if body_action_id == 'static' and body_animation_path is not None:
            raise ValueError('Static body-only restoration must not retain a clip')
        if body_action_id != 'static':
            _asset_path(body_animation_path)
        return {'face_id': 'none', 'animation_path': body_animation_path, 'restore_body_only': True,
                'clear_face_curves': True, 'playback': 'body_settings_unchanged'}
    rows = [row for row in library['entries'] if (row['sex'], row['face_id'], row['body_action_id']) == (sex, face_id, body_action_id)]
    if len(rows) != 1:
        raise ValueError('No verified face/body combination exists; no automatic fallback is allowed')
    return {**copy.deepcopy(rows[0]), 'restore_body_only': False, 'registry_source': library.get('registry_source')}
