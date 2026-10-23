"""M3-only preparation/UE wrapper around the unchanged N3 five-second generator.

Offline: --prepare-report <successful M3 import JSON> --action-id ACT_...
UE: runpy.run_path(__file__, init_globals={'DM_MOTION_FACE_PILOT_TASK': task_path}, run_name='__main__')
No registry publication, old source edits, short-clip looping or time scaling.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import math
from pathlib import Path
import re

SCRIPTS = Path(__file__).resolve().parent
RUN = Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/motion_library_expansion_20261009_v1')
ROOT = '/Game/DataMake/Validation/MotionLibraryExpansion20261009'
CONTENT = Path('D:/UE/projects/datatry_02/Content')
SCHEMA = 'motion_library_face_pilot_v1'


def load(filename):
    spec = importlib.util.spec_from_file_location('_motion_face_pilot_' + filename[:-3], SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def panel():
    module = load('ue_native_face_panel_five_second_v1.py')
    module.RUN, module.ASSET_ROOT = RUN, ROOT
    return module


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def checked_record(record):
    if not isinstance(record, dict) or not re.fullmatch('[0-9a-f]{64}', record.get('sha256', '')):
        raise ValueError('Expected source SHA256 record')
    path = Path(record.get('path', '')).resolve(strict=True)
    if not Path(record.get('path', '')).is_absolute() or panel().file_record(path)['sha256'] != record['sha256']:
        raise ValueError('Bound source changed: ' + str(path))
    return path


def package_record(record, expected):
    if not isinstance(record, dict) or record.get('asset', '').split('.')[0] != expected:
        raise ValueError('Package does not match imported animation')
    if checked_record(record) != (CONTENT / (expected.removeprefix('/Game/') + '.uasset')).resolve():
        raise ValueError('Package evidence path does not match asset')
    # N3 composer records deliberately have no bytes field; retain its exact schema.
    return {key: record[key] for key in ('asset', 'path', 'sha256')}


def import_source(record, sex=None):
    path = checked_record(record)
    if not path.is_relative_to((RUN / 'imports').resolve()) or path.suffix != '.json':
        raise ValueError('Import evidence must be inside M3/imports')
    data = read(path)
    task, verify = data.get('task', {}), data.get('verification', {})
    actual_sex, name = task.get('sex'), task.get('name')
    if actual_sex not in ('female', 'male') or (sex is not None and actual_sex != sex) or not re.fullmatch('[a-z][a-z0-9_]{0,63}', name or ''):
        raise ValueError('Import sex/name mismatch')
    destination = ROOT + '/' + actual_sex + '/' + name
    if (data.get('success') is not True or data.get('eligible_for_native_five_seconds') is not True
            or data.get('destination') != destination or data.get('source_files_unchanged') is not True
            or any(data.get(k) != [] for k in ('changed_source_files', 'dirty_protected_assets', 'new_dirty_packages_outside_destination'))
            or any(data.get(k) is not False for k in ('retimed', 'cropped', 'looped_or_padded'))):
        raise ValueError('Import provenance failed, wrong root or short native motion')
    original, body = data['imported'], data['body_only']
    rate = body['frame_rate']
    mapping = panel().body_mapping(rate['numerator'], rate['denominator'], body['number_of_frames'], body['duration_seconds'])
    if mapping['mode'] != 'crop_first_five_seconds':
        raise ValueError('Short native motion cannot enter this crop-only pilot')
    if (body['frame_rate'] != original['frame_rate'] or body['number_of_frames'] != original['number_of_frames']
            or body['duration_seconds'] != original['duration_seconds']
            or verify.get('all_frame_count') != body['number_of_frames'] + 1
            or verify.get('source_bone_count') != 118 or verify.get('protected_body_bone_count') != 108
            or verify.get('removed_face_track_count') != 10
            or any(verify.get(k) is not True for k in ('face_tracks_absent', 'face_local_pose_is_reference', 'preserved_curve_keys_identical'))):
        raise ValueError('Incomplete full native frame BodyOnly verification')
    errors = verify.get('max_absolute_errors', {})
    if set(errors) != {'protected_bones', 'preserved_curves', 'face_reference_bones'} or any(not math.isfinite(v) or v > 1e-4 or v < 0 for v in errors.values()):
        raise ValueError('BodyOnly verification error exceeds fixed bound')
    names = lambda seq: {str(n).casefold() for n in seq}
    removed = names(data['removed_face_tracks'])
    if (len(original['bone_track_names']) != 118 or len(body['bone_track_names']) != 108
            or removed != set(load('ue_compose_native_face_body_v1.py').FACE_BONES)
            or names(original['bone_track_names']) - names(body['bone_track_names']) != removed
            or removed & names(body['bone_track_names'])):
        raise ValueError('BodyOnly track partition changed')
    if data.get('source_animation') != destination + '/A_' + name + '_Source' or data.get('body_only_animation') != destination + '/A_' + name + '_BodyOnly':
        raise ValueError('Imported source escaped isolated destination')
    package_record(data['source_asset_record'], data['source_animation'])
    original_body = package_record(data['body_only_asset_record'], data['body_only_animation'])
    checked_record(data['source_fbx'])
    for protected in data['protected_sources']:
        checked_record(protected)
    return data, {'source_report': str(path), 'original_body': original_body,
                  'duration_seconds': body['duration_seconds'], 'fps': body['fps']}


def validate_task(value):
    if not isinstance(value, dict) or set(value) != {'schema', 'import_report', 'task'} or value['schema'] != SCHEMA:
        raise ValueError('Exact motion pilot envelope required')
    task = value['task']
    p = panel()
    p.validate_task(task)
    action = task['action_id'] if task['operation'] == 'body_window' else task['body_action_id']
    if not re.fullmatch('ACT_[A-Z0-9_]+', action):
        raise ValueError('Stable action ID required')
    data, source = import_source(value['import_report'], task['sex'])
    if task['operation'] == 'body_window' and Path(task['source_report']).resolve() != Path(source['source_report']).resolve():
        raise ValueError('Task source report differs from bound report')
    if p.output_path(task['report_path']).exists():
        raise ValueError('Refusing existing output report')
    return p, data, source, action


def run(value):
    p, data, source, action = validate_task(value)
    task, proof = value['task'], copy.deepcopy(value['import_report'])
    p.body_sources = lambda: {(task['sex'], action): source}
    old_mapping = p.body_mapping
    def crop_only(*args):
        mapping = old_mapping(*args)
        if mapping['mode'] != 'crop_first_five_seconds':
            raise ValueError('Live source is too short; repeat prohibited')
        return mapping
    p.body_mapping = crop_only
    write = p.write_new
    def write_with_provenance(path, report, *args, **kwargs):
        report = dict(report, motion_source_import_report=proof)
        return write(path, report, *args, **kwargs)
    p.write_new = write_with_provenance
    create_composer = p.composer
    def bound_composer():
        module = create_composer()
        compose = module.run
        module.run = lambda ct: compose(dict(ct, motion_source_import_report=proof))
        return module
    p.composer = bound_composer
    if task['operation'] == 'compose':
        body = read(p.output_path(task['body_window_report']))
        if (body.get('motion_source_import_report') != proof or body.get('original_body') != source['original_body']
                or body.get('mapping', {}).get('mode') != 'crop_first_five_seconds'
                or body.get('destination', '').split('.')[0] != ROOT + '/BodyWindows/' + task['sex'] + '/A_' + body['task']['window_id']):
            raise ValueError('Body window is not bound to this crop-only imported source')
    result = p.run(task)
    import_source(proof, task['sex'])
    return result


def prepare(report_path, action_id):
    p = panel()
    proof = p.file_record(Path(report_path).resolve())
    data, source = import_source(proof)
    sex, name = data['task']['sex'], data['task']['name']
    faces = p.accepted_faces()
    slug = name + '_native5_v1'
    folder = RUN / 'face_pilots' / slug
    body_report = folder / 'body_window_report.json'
    body_task = {'operation': 'body_window', 'sex': sex, 'action_id': action_id, 'window_id': slug,
        'source_report': proof['path'], 'reference_mesh': faces[(sex, 'idle')][0]['reference_mesh'], 'report_path': str(body_report)}
    tasks = [(folder / 'body_window_task.json', body_task)]
    for face_id in p.FACE_IDS:
        tasks.append((folder / (face_id + '_task.json'), {'operation': 'compose', 'sex': sex,
            'face_id': face_id, 'body_action_id': action_id, 'body_window_report': str(body_report),
            'composite_id': face_id + '_' + slug, 'report_path': str(folder / (face_id + '_report.json'))}))
    envelopes = [(path, {'schema': SCHEMA, 'import_report': proof, 'task': task}) for path, task in tasks]
    for path, value in envelopes:
        validate_task(value)
        if path.exists():
            raise ValueError('Refusing existing preparation task')
    manifest = {'schema': SCHEMA, 'source_import_report': proof, 'sex': sex, 'action_id': action_id,
        'native_duration_seconds': source['duration_seconds'], 'selection': p.file_record(p.SELECTION),
        'body_task': str(tasks[0][0]), 'composition_tasks': [str(path) for path, _ in tasks[1:]],
        'body_asset': ROOT + '/BodyWindows/' + sex + '/A_' + slug,
        'composition_assets': [ROOT + '/Composites/' + sex + '/A_' + task['composite_id'] for _, task in tasks[1:]],
        'registry_written': False, 'matrix_coverage': 'pending', 'visual_acceptance': 'pending'}
    manifest_path = folder / 'preparation_manifest.json'
    if manifest_path.exists():
        raise ValueError('Refusing existing preparation manifest')
    for path, value in envelopes:
        p.write_new(path, value)
    p.write_new(manifest_path, manifest)
    return manifest


if __name__ == '__main__':
    task_path = globals().get('DM_MOTION_FACE_PILOT_TASK')
    if isinstance(task_path, str):
        result = run(read(task_path))
        print(json.dumps({'success': result['success'], 'destination': result['destination']}))
    else:
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--prepare-report', required=True)
        parser.add_argument('--action-id', required=True)
        args = parser.parse_args()
        print(json.dumps(prepare(args.prepare_report, args.action_id), indent=2))
