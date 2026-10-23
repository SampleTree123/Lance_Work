"""Prepare/run isolated 5s body windows and accepted-face panel compositions.

Offline --prepare creates 10 body tasks, 40 composition tasks and references to
8 accepted static assets. UE execution is explicit via
DM_NATIVE_FACE_PANEL_FIVE_SECOND_TASK. No original animations are modified.
Short bodies repeat at their original frame rate; only the body clock wraps.
The recorded seams are unblended and are not claimed to be naturally seamless.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import traceback

SCRIPTS = Path(__file__).resolve().parent
BASE = Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import')
RUN = BASE / 'native_face_panel_integration_20261009_v1'
PREVIOUS = BASE / 'native_face_five_second_20261008_v1'
OLD = BASE / 'character_runtime_face_library_20261007_v1'
SELECTION = PREVIOUS / 'accepted_face_selection_v1.json'
ASSET_ROOT = '/Game/DataMake/Validation/NativeFacePanelFiveSecond20261009'
FACE_IDS = ('idle', 'smile', 'displeased', 'sad')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def file_record(path):
    path = Path(path)
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def composer():
    spec = importlib.util.spec_from_file_location('_dm_panel_five_second_composer', SCRIPTS / 'ue_compose_native_face_body_v1.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.RUN, module.ASSET_ROOT = RUN, ASSET_ROOT + '/Composites'
    return module


def output_path(value):
    path = Path(value).resolve()
    if not path.is_relative_to(RUN.resolve()) or path.suffix != '.json':
        raise ValueError('Output must be JSON inside the panel integration run')
    return path


def write_new(path, value, identical_ok=False):
    path = output_path(path)
    if path.exists():
        if identical_ok and read(path) == value:
            return
        raise ValueError('Refusing to overwrite existing evidence: ' + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def accepted_faces(check_assets=True):
    data = read(SELECTION)
    if data.get('selection_accepted') is not True or set(data.get('face_ids', [])) != set(FACE_IDS):
        raise ValueError('Expected accepted four-class selection')
    rows = {}
    for entry in data['entries']:
        key = (entry['sex'], entry['face_id'])
        if key in rows or key[0] not in ('female', 'male') or key[1] not in FACE_IDS or entry.get('selection_accepted') is not True:
            raise ValueError('Invalid or duplicate accepted entry')
        evidence = entry['evidence']['composition_report']
        if file_record(evidence['path'])['sha256'] != evidence['sha256']:
            raise ValueError('Accepted composition report changed')
        report = read(evidence['path'])
        task, verify = report['task'], report['verification']
        if report.get('success') is not True or report.get('sources_unchanged') is not True or task['sex'] != key[0] or task.get('body_mode') != 'static' or task.get('static_use_reference_pose') is not True:
            raise ValueError('Accepted static face is not verified')
        if task.get('face_rate') != 1 or task.get('face_playback') != 'hold' or 'face_envelope' in task or not math.isclose(task['face_end_seconds']-task['face_start_seconds'], 5, abs_tol=1e-8, rel_tol=0):
            raise ValueError('Accepted face timing changed')
        if report['destination'] != entry['package_path'] or not math.isclose(verify['duration_seconds'], 5, abs_tol=1e-6, rel_tol=0) or verify['all_frame_count'] != round(5*verify['fps'])+1 or len(report['face_bones']) != 10:
            raise ValueError('Accepted face verification is incomplete')
        if check_assets and file_record(entry['asset_file_at_selection']['path'])['sha256'] != entry['asset_file_at_selection']['sha256']:
            raise ValueError('Accepted face asset changed')
        rows[key] = (entry, report)
    if set(rows) != {(sex, face) for sex in ('female', 'male') for face in FACE_IDS}:
        raise ValueError('Exactly eight accepted static faces required')
    return rows


def body_sources():
    rows = {}
    for entry in read(OLD / 'compositions/final_v3_manifest.json')['entries']:
        if entry['body_action_id'] == 'static':
            continue
        key = (entry['sex'], entry['body_action_id'])
        report = read(entry['report'])
        if not report.get('success') or report['task']['body_mode'] != 'animation':
            raise ValueError('Old body provenance report failed')
        original = next(row for row in report['sources'] if row['asset'] == report['task']['body_animation'])
        if key in rows:
            if rows[key]['original_body'] != original:
                raise ValueError('Conflicting original-body records')
            continue
        rows[key] = {'source_report': entry['report'], 'original_body': original,
                     'duration_seconds': report['verification']['duration_seconds'], 'fps': report['verification']['fps']}
    if len(rows) != 10 or any(sum(key[0] == sex for key in rows) != 5 for sex in ('female', 'male')):
        raise ValueError('Expected five existing body actions per sex')
    return rows


def body_mapping(numerator, denominator, source_frames, source_duration):
    values = (numerator, denominator, source_frames, source_duration)
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 for v in values):
        raise ValueError('Invalid source body timing')
    fps = numerator / denominator
    total = round(5*fps)
    if source_frames != int(source_frames) or not math.isclose(total, 5*fps, abs_tol=1e-8, rel_tol=0) or not math.isclose(source_frames/fps, source_duration, abs_tol=2e-6, rel_tol=0):
        raise ValueError('Body timing must use an exact native frame grid')
    source_frames = int(source_frames)
    short = source_frames < total
    mapping = [(i % source_frames if short else i)/fps for i in range(total+1)]
    return {'fps': fps, 'frames': total, 'times': [i/fps for i in range(total+1)], 'source_times': mapping,
            'mode': 'repeat_body_original_speed' if short else 'crop_first_five_seconds',
            'source_period_seconds': source_frames/fps, 'seams_seconds': [i/fps for i in range(source_frames, total+1, source_frames)] if short else [],
            'face_clock_wraps': False, 'body_retimed': False, 'seams_blended': False}


def validate_task(task):
    common = {'operation', 'sex', 'report_path'}
    fields = {'body_window': common | {'action_id', 'window_id', 'source_report', 'reference_mesh'},
              'compose': common | {'face_id', 'body_action_id', 'body_window_report', 'composite_id'}}
    if not isinstance(task, dict) or task.get('operation') not in fields or set(task) != fields[task['operation']]:
        raise ValueError('Exact panel task fields required; timing overrides forbidden')
    if task['sex'] not in ('female', 'male'):
        raise ValueError('Invalid sex')
    slug = task['window_id'] if task['operation'] == 'body_window' else task['composite_id']
    if not isinstance(slug, str) or not re.fullmatch('[a-z][a-z0-9_]{0,95}', slug):
        raise ValueError('Invalid unique asset id')
    output_path(task['report_path'])
    if task['operation'] == 'compose':
        if task['face_id'] not in FACE_IDS:
            raise ValueError('Unaccepted face class')
        if output_path(task['body_window_report']) == output_path(task['report_path']):
            raise ValueError('Source and output report paths must differ')
    return task


def preservation(module, u, records, before, destination):
    now = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    result = {'sources_unchanged': all(module.asset_record(row['asset']) == row for row in records),
              'new_dirty_packages_outside_target': sorted(now-before-{destination}),
              'dirty_sources': sorted(now & {row['asset'].split('.')[0] for row in records})}
    if not result['sources_unchanged'] or result['new_dirty_packages_outside_target'] or result['dirty_sources']:
        raise RuntimeError('Original/shared source preservation failed')
    return result


def run_body_window(task):
    source = body_sources().get((task['sex'], task['action_id']))
    if not source or Path(source['source_report']) != Path(task['source_report']):
        raise ValueError('Body task must use selected original action provenance')
    faces = accepted_faces()
    if task['reference_mesh'] != faces[(task['sex'], 'idle')][0]['reference_mesh']:
        raise ValueError('Wrong accepted reference mesh')
    module = composer()
    import unreal as u
    if Path(u.Paths.project_dir()).resolve() != module.PROJECT.resolve():
        raise ValueError('Wrong UE project')
    body, mesh = (u.load_asset(value) for value in (source['original_body']['asset'], task['reference_mesh']))
    if not isinstance(body, u.AnimSequence) or not isinstance(mesh, u.SkeletalMesh) or body.get_editor_property('additive_anim_type') != u.AdditiveAnimationType.AAT_NONE:
        raise ValueError('Require non-additive original body and reference mesh')
    skeleton = body.get_skeleton()
    expected_skeleton = '/Game/DataMake/Validation/CFDNativeBatch4020261006/SharedSkeletons/SKEL_CFDShared_' + task['sex'].title() + '_v1'
    if skeleton != mesh.get_editor_property('skeleton') or skeleton.get_path_name().split('.')[0] != expected_skeleton:
        raise ValueError('Wrong same-sex shared skeleton')
    records = [module.asset_record(asset.get_path_name()) for asset in (body, mesh, skeleton)]
    if records[0] != source['original_body']:
        raise ValueError('Original body changed since old library verification')
    before = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if before & {row['asset'].split('.')[0] for row in records}:
        raise ValueError('Sources must be saved')
    destination = ASSET_ROOT + '/BodyWindows/' + task['sex'] + '/A_' + task['window_id']
    if u.EditorAssetLibrary.does_asset_exist(destination) or output_path(task['report_path']).exists():
        raise ValueError('Refusing to overwrite body window asset/report')
    rate = body.data_model_interface.get_frame_rate()
    count = body.data_model_interface.get_number_of_frames()
    mapping = body_mapping(rate.numerator, rate.denominator, int(getattr(count, 'value', count)), float(body.get_play_length()))
    modifier = u.SkeletonModifier()
    if not modifier.set_skeletal_mesh(mesh):
        raise RuntimeError('Cannot inspect source skeleton')
    bones = sorted(str(n) for n in modifier.get_all_bone_names())
    if len(bones) != 118:
        raise ValueError('Expected audited 118-bone skeleton')
    tracks = {str(n) for n in body.data_model_interface.get_bone_track_names()}
    curves = sorted(module.curve_name_index([str(n) for n in u.AnimationLibrary.get_animation_curve_names(body, u.RawCurveTrackTypes.RCT_FLOAT)]).values())
    options = u.AnimPoseEvaluationOptions()
    options.set_editor_properties({'evaluation_type': u.AnimDataEvalType.SOURCE, 'should_retarget': False,
        'extract_root_motion': False, 'incorporate_root_motion_into_pose': True, 'evaluate_curves': True, 'optional_skeletal_mesh': mesh})

    def sample(asset, time):
        p = u.AnimPoseExtensions.get_anim_pose_at_time(asset, time, options)
        if not u.AnimPoseExtensions.is_valid(p) or not set(bones).issubset({str(n) for n in u.AnimPoseExtensions.get_bone_names(p)}) or not module.curve_names_present(curves, [str(n) for n in u.AnimPoseExtensions.get_curve_names(p)]):
            raise RuntimeError('Evaluator omitted original bones or curves')
        return ({n: u.AnimPoseExtensions.get_bone_pose(p, u.Name(n), u.AnimPoseSpaces.LOCAL) for n in bones},
                {n: float(u.AnimPoseExtensions.get_curve_weight(p, u.Name(n))) for n in curves})

    report = {'success': False, 'task': task, 'destination': destination, 'original_body': source['original_body'],
              'original_body_report': task['source_report'], 'sources': records, 'mapping': mapping,
              'bones': bones, 'curves': curves, 'natural_seam_acceptance': False}
    try:
        samples = [sample(body, time) for time in mapping['source_times']]
        target = u.EditorAssetLibrary.duplicate_asset(body.get_path_name().split('.')[0], destination)
        if not isinstance(target, u.AnimSequence):
            raise RuntimeError('Body duplication failed')
        controller = target.controller
        controller.open_bracket('Original-speed body window with independent face clock', False)
        try:
            controller.set_number_of_frames(u.FrameNumber(value=mapping['frames']), False)
            if mapping['mode'] == 'repeat_body_original_speed':
                for name in bones:
                    if name not in tracks:
                        controller.add_bone_track(u.Name(name), False)
                    values = [row[0][name] for row in samples]
                    if not controller.set_bone_track_keys(u.Name(name), [v.translation for v in values], [v.rotation for v in values], [v.scale3d for v in values], False):
                        raise RuntimeError('Could not write repeated body bone ' + name)
                for name in curves:
                    u.AnimationLibrary.remove_curve(target, u.Name(name), False)
                    u.AnimationLibrary.add_curve(target, u.Name(name), u.RawCurveTrackTypes.RCT_FLOAT, False)
                    u.AnimationLibrary.add_float_curve_keys(target, u.Name(name), mapping['times'], [row[1][name] for row in samples])
        finally:
            controller.close_bracket(False)
        new_rate = target.data_model_interface.get_frame_rate()
        if (new_rate.numerator, new_rate.denominator) != (rate.numerator, rate.denominator) or not math.isclose(float(target.get_play_length()), 5, abs_tol=1e-6, rel_tol=0):
            raise RuntimeError('Body window changed rate or duration')
        if module.curve_name_index([str(n) for n in u.AnimationLibrary.get_animation_curve_names(target, u.RawCurveTrackTypes.RCT_FLOAT)]).keys() != module.curve_name_index(curves).keys():
            raise RuntimeError('Body curve inventory changed')
        if not u.EditorAssetLibrary.save_loaded_asset(target, only_if_is_dirty=False):
            raise RuntimeError('Cannot save body window')
        maxima = {'bones': 0., 'curves': 0.}
        worst = {}
        for index, time in enumerate(mapping['times']):
            actual = sample(target, time)
            for name in bones:
                if not all(math.isfinite(v) for v in module.transform_values(actual[0][name]) + module.transform_values(samples[index][0][name])):
                    raise RuntimeError('Nonfinite body transform')
                error = module.transform_error(actual[0][name], samples[index][0][name])
                if error > maxima['bones']:
                    maxima['bones'], worst['bone'] = error, {'name': name, 'frame': index, 'time': time, 'source_time': mapping['source_times'][index]}
            for name in curves:
                if not all(math.isfinite(v) for v in (actual[1][name], samples[index][1][name])):
                    raise RuntimeError('Nonfinite curve')
                maxima['curves'] = max(maxima['curves'], abs(actual[1][name]-samples[index][1][name]))
        report['verification'] = {'all_frame_count': len(samples), 'bone_count': len(bones), 'fps': mapping['fps'],
            'duration_seconds': float(target.get_play_length()), 'max_absolute_errors': maxima, 'worst': worst, 'tolerance': 1e-4}
        if max(maxima.values()) > 1e-4:
            raise RuntimeError('Body window all-frame original mapping comparison failed')
        report.update(preservation(module, u, records, before, destination))
        report['asset_record'] = module.asset_record(target.get_path_name())
        report['success'] = True
    except Exception:
        report['error'] = traceback.format_exc()
        raise
    finally:
        write_new(task['report_path'], report)
    return report


def run_composition(task):
    entry, face = accepted_faces()[(task['sex'], task['face_id'])]
    body = read(output_path(task['body_window_report']))
    if body.get('success') is not True or body.get('sources_unchanged') is not True or body['task']['sex'] != task['sex'] or body['task']['action_id'] != task['body_action_id'] or body['verification']['bone_count'] != 118 or body['verification']['all_frame_count'] != round(5*body['verification']['fps'])+1 or not math.isclose(body['verification']['duration_seconds'], 5, abs_tol=1e-6, rel_tol=0):
        raise ValueError('Require matching fully verified body window')
    module = composer()
    if module.asset_record(body['asset_record']['asset']) != body['asset_record']:
        raise ValueError('Verified body window changed')
    if module.asset_record(body['original_body']['asset']) != body['original_body']:
        raise ValueError('Original body changed since window preparation')
    ct = {'sex': task['sex'], 'composite_id': task['composite_id'], 'body_animation': body['destination'],
          'face_animation': entry['asset'], 'reference_mesh': entry['reference_mesh'],
          'allowed_face_curve_names': face['task']['allowed_face_curve_names'],
          'face_start_seconds': 0, 'face_end_seconds': 5, 'face_rate': 1, 'face_playback': 'hold',
          'body_mode': 'animation', 'report_path': task['report_path'],
          'panel_integration_task': task, 'accepted_face_selection': file_record(SELECTION),
          'accepted_selection_entry_id': entry['selection_entry_id'],
          'accepted_static_report': entry['evidence']['composition_report'],
          'original_body': body['original_body'], 'body_window_report': file_record(task['body_window_report'])}
    return module.run(ct)


def run(task):
    validate_task(task)
    return run_body_window(task) if task['operation'] == 'body_window' else run_composition(task)


def prepare():
    faces, bodies = accepted_faces(), body_sources()
    windows, compositions, entries = [], [], []
    for (sex, action), source in sorted(bodies.items()):
        slug = action.lower() + '_native5_v1'
        report = RUN / 'body_windows' / (sex+'_'+slug+'.json')
        path = report.with_name(report.stem+'_task.json')
        task = {'operation': 'body_window', 'sex': sex, 'action_id': action, 'window_id': slug,
                'source_report': source['source_report'], 'reference_mesh': faces[(sex, 'idle')][0]['reference_mesh'], 'report_path': str(report)}
        write_new(path, task, True)
        windows.append({'sex': sex, 'body_action_id': action, 'source_duration_seconds': source['duration_seconds'], 'task': str(path), 'report': str(report)})
        for face_id in FACE_IDS:
            comp_id = face_id+'_'+slug
            comp_report = RUN / 'compositions' / (sex+'_'+comp_id+'.json')
            comp_path = comp_report.with_name(comp_report.stem+'_task.json')
            ct = {'operation': 'compose', 'sex': sex, 'face_id': face_id, 'body_action_id': action,
                  'body_window_report': str(report), 'composite_id': comp_id, 'report_path': str(comp_report)}
            write_new(comp_path, ct, True)
            row = {'sex': sex, 'face_id': face_id, 'label': faces[(sex, face_id)][0]['label_zh'], 'body_action_id': action,
                   'body_mode': 'animation', 'task': str(comp_path), 'report': str(comp_report),
                   'asset': ASSET_ROOT+'/Composites/'+sex+'/A_'+comp_id, 'body_window_report': str(report), 'duration_seconds': 5,
                   'original_body_animation': source['original_body']['asset'], 'accepted_selection_entry_id': faces[(sex, face_id)][0]['selection_entry_id']}
            compositions.append(row)
            entries.append(row)
    for (sex, face_id), (entry, report) in sorted(faces.items()):
        entries.append({'sex': sex, 'face_id': face_id, 'label': entry['label_zh'], 'body_action_id': 'static',
            'body_mode': 'static_reference', 'task': None, 'report': entry['evidence']['composition_report']['path'],
            'asset': entry['asset'], 'duration_seconds': 5, 'reuse_accepted_static': True,
            'accepted_selection_entry_id': entry['selection_entry_id']})
    representatives = []
    for action in ('ACT_F06_ELEVATOR_GREETING', 'ACT_F03_AUDIENCE_01'):
        window = next(row for row in windows if row['sex'] == 'female' and row['body_action_id'] == action)
        comp = next(row for row in compositions if row['sex'] == 'female' and row['body_action_id'] == action and row['face_id'] == 'smile')
        representatives.append({'body': window, 'composition': comp})
    manifest = {'schema_version': 1, 'selection': file_record(SELECTION), 'body_tasks': windows,
                'composition_tasks': compositions, 'entries': entries, 'representatives': representatives,
                'prepared_only': True, 'runtime_registry_written': False}
    write_new(RUN/'preparation_manifest_v2.json', manifest, True)
    write_new(RUN/'representative_tasks_v2.json', {'representatives': representatives}, True)
    return manifest


if __name__ == '__main__':
    import sys
    path = globals().get('DM_NATIVE_FACE_PANEL_FIVE_SECOND_TASK')
    if isinstance(path, str):
        result = run(read(path))
        print(json.dumps({'success': result['success'], 'destination': result['destination']}))
    elif sys.argv[1:] == ['--prepare']:
        result = prepare()
        print(json.dumps({'body_tasks': len(result['body_tasks']), 'dynamic': len(result['composition_tasks']), 'entries': len(result['entries']), 'representatives': result['representatives']}, indent=2))
    else:
        raise ValueError('Use --prepare offline or set DM_NATIVE_FACE_PANEL_FIVE_SECOND_TASK in UE')
