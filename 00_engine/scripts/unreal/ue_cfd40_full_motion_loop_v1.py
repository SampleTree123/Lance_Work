"""Full-length body playback with native five-second faces repeated for review.

Install only in an isolated motion-review worker. Existing catalogs, accepted
five-second clips, shared skeletons and source animations remain read-only.
Derived clips are generated on demand; looping does not imply seamless motion.
Technical owner: ANIMATION_EXPRESSION_MORPH.md, full-motion loop review.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
RUN = Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/full_motion_loop_review_20261009_v1')
ASSET_ROOT = '/Game/DataMake/Validation/FullMotionLoopReview20261009'
POLICY = 'full_body_original_speed_face_five_second_repeat_v1'


def runtime_policy():
    return {'policy': POLICY, 'body': 'full_original_duration', 'rate': 1.,
            'repeat': True, 'face_period_seconds': 5.,
            'face_restart_at_body_loop': True, 'seamless_loop_verified': False}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def record(path):
    path = Path(path).resolve(strict=True)
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def check_record(value):
    if record(value['path'])['sha256'] != value['sha256']:
        raise ValueError('Full-motion loop dependency changed: ' + value['path'])


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def private_module(name):
    spec = importlib.util.spec_from_file_location('_full_motion_loop_' + name, SCRIPTS / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def composer():
    module = private_module('ue_compose_native_face_body_v1')
    module.RUN, module.ASSET_ROOT = RUN, ASSET_ROOT + '/Composites'
    return module


def accepted_faces():
    module = private_module('ue_native_face_panel_five_second_v1')
    return module.accepted_faces(), record(module.SELECTION)


def object_path(asset):
    return asset if '.' in asset else asset + '.' + asset.rsplit('/', 1)[1]


def validate_composition(report, task, expected_duration, expected_frames):
    verify = report.get('verification', {})
    errors = verify.get('max_absolute_errors', {})
    if (report.get('success') is not True or report.get('sources_unchanged') is not True
            or report.get('task') != task or report.get('new_dirty_packages_outside_target') != []
            or not math.isclose(verify.get('duration_seconds', -1), expected_duration, rel_tol=0, abs_tol=1e-6)
            or verify.get('all_frame_count') != expected_frames + 1
            or verify.get('unrelated_curve_keys_identical') is not True
            or not math.isfinite(errors.get('protected_bones', math.inf))
            or not math.isfinite(errors.get('face_curves', math.inf))
            or errors.get('protected_bones', math.inf) > 1e-4
            or errors.get('face_curves', math.inf) > 1e-4
            or len(report.get('face_bones', [])) != 10):
        raise ValueError('Full-motion composite lacks complete source-preservation proof')
    maxima, tolerances = verify.get('face_bone_metric_maxima', {}), verify.get('face_bone_metric_tolerances', {})
    approved = {'translation_cm': .001, 'rotation_degrees': .2, 'scale_abs': 1e-4}
    if tolerances != approved or set(maxima) != set(approved) or any(
            not math.isfinite(v) or v > approved[k] for k, v in maxima.items()):
        raise ValueError('Full-motion composite face bone verification failed')


def validate_cache(receipt, spec, task, expected_duration, expected_frames):
    if (receipt.get('schema') != 'full_motion_loop_cache_v1'
            or receipt.get('success') is not True or receipt.get('spec') != spec
            or receipt.get('key') != digest(spec) or receipt.get('runtime_policy') != runtime_policy()):
        raise ValueError('Full-motion loop cache identity mismatch')
    check_record(receipt['composition_report'])
    check_record(receipt['asset'])
    report = read(receipt['composition_report']['path'])
    validate_composition(report, task, expected_duration, expected_frames)
    if 'sources' in spec and isinstance(spec['sources'], list) and report.get('sources') != spec['sources']:
        raise ValueError('Full-motion loop cache source bindings mismatch')
    if (object_path(report['destination']) != object_path(receipt['asset']['asset'])
            or receipt['asset']['asset'] != receipt['animation_path']):
        raise ValueError('Full-motion loop cache destination mismatch')
    for source in report['sources']:
        check_record(source)
    return receipt


def write_new(path, value):
    path = Path(path)
    if not path.resolve().is_relative_to(RUN.resolve()):
        raise ValueError('Loop evidence must remain in this run')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def ensure_composite(u, sex, action, choice, accepted_report, selection_record):
    module = composer()
    body_path, face_path = action['path'], choice['asset']
    body = u.load_asset(body_path)
    face = u.load_asset(face_path)
    if not isinstance(body, u.AnimSequence) or not isinstance(face, u.AnimSequence):
        raise ValueError('Expected saved full-body and accepted-face animations')
    if body.get_skeleton() != face.get_skeleton():
        raise ValueError('Body/face skeleton mismatch')
    duration = float(body.get_play_length())
    if not math.isfinite(duration) or duration <= 0 or not math.isclose(float(face.get_play_length()), 5., abs_tol=1e-6, rel_tol=0):
        raise ValueError('Invalid full-body/accepted-face duration')
    raw_frames = body.data_model_interface.get_number_of_frames()
    frames = int(getattr(raw_frames, 'value', raw_frames))
    body_rate = body.data_model_interface.get_frame_rate()
    fps = float(body_rate.numerator) / float(body_rate.denominator)
    # UE exposes duration as float32; a 34 s source can differ by >1e-6 s
    # from its exact integer-frame ratio. This does not alter pose tolerances.
    if frames < 1 or not math.isclose(frames / fps, duration, abs_tol=1e-5, rel_tol=0):
        raise ValueError('Full-body frame count/duration differs')
    source_records = [module.asset_record(object_path(path)) for path in (
        body_path, face_path, choice['reference_mesh'], body.get_skeleton().get_path_name())]
    dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if any(row['asset'].split('.')[0] in dirty for row in source_records):
        raise ValueError('Loop source asset or shared skeleton is dirty')
    spec = {'policy': runtime_policy(), 'sex': sex, 'action_id': action['action_id'],
            'face_id': choice['face_id'], 'duration_seconds': duration, 'frames': frames, 'fps': fps,
            'sources': source_records, 'accepted_selection': selection_record,
            'accepted_static_report': choice['evidence']['composition_report'],
            'code': [record(__file__), record(module.__file__),
                     record(SCRIPTS / 'ue_native_face_panel_five_second_v1.py')]}
    key = digest(spec)
    slug = 'full_' + key[:32]
    report_path = RUN / 'compositions' / (sex + '_' + slug + '.json')
    receipt_path = RUN / 'cache' / (key + '.json')
    destination = module.ASSET_ROOT + '/' + sex + '/A_' + slug
    task = {'sex': sex, 'composite_id': slug, 'body_animation': body_path,
            'face_animation': face_path, 'reference_mesh': choice['reference_mesh'],
            'allowed_face_curve_names': accepted_report['task']['allowed_face_curve_names'],
            'face_start_seconds': 0, 'face_end_seconds': 5, 'face_rate': 1,
            'face_playback': 'loop', 'body_mode': 'animation', 'report_path': str(report_path),
            'full_motion_loop_spec': spec}
    if receipt_path.exists():
        receipt = validate_cache(read(receipt_path), spec, task, duration, frames)
    else:
        if report_path.exists() or u.EditorAssetLibrary.does_asset_exist(destination):
            raise ValueError('Previous loop generation is incomplete; preserve it and inspect before retry')
        report = module.run(task)
        validate_composition(report, task, duration, frames)
        if report['destination'] != destination:
            raise ValueError('Composer returned another destination')
        for row in source_records:
            check_record(row)
        asset = module.asset_record(object_path(destination))
        receipt = {'schema': 'full_motion_loop_cache_v1', 'success': True, 'key': key,
                   'spec': spec, 'runtime_policy': runtime_policy(),
                   'animation_path': asset['asset'], 'asset': asset,
                   'composition_report': record(report_path)}
        write_new(receipt_path, receipt)
        validate_cache(receipt, spec, task, duration, frames)
    motion = u.load_asset(receipt['animation_path'])
    if (not isinstance(motion, u.AnimSequence) or motion.get_skeleton() != body.get_skeleton()
            or not math.isclose(float(motion.get_play_length()), duration, rel_tol=0, abs_tol=1e-6)
            or destination in dirty):
        raise ValueError('Cached loop asset type/skeleton/duration/dirty state differs')
    return motion, {'kind': 'full_body_repeated_face', 'duration_seconds': duration,
                    'fullbody_duration_seconds': duration,
                    'original_body': source_records[0], 'accepted_face': source_records[1],
                    'cache_receipt': record(receipt_path), 'animation_path': receipt['animation_path']}


def install_worker(app):
    """Wrap a fresh adapter.worker; call before app.run, never a shared module."""
    if getattr(app, '_full_motion_loop_installed', False):
        raise ValueError('Full-motion loop worker already installed')
    old_plan, old_state = app.load_plan, app.state

    def plan(request, data):
        result, prepared = old_plan(request, data)
        choices, selection_record = accepted_faces()
        details = {}
        for sex, entry in prepared.items():
            face_id = request['appearance'][sex]['face_id']
            index = request['action_index']
            selection = copy.deepcopy(entry['face_selection'])
            if index:
                action = data['actions_by_sex'][sex][index - 1]
                if action['index'] != index:
                    raise ValueError('Full-motion action index mismatch')
                if face_id != 'none':
                    choice, accepted_report = choices[(sex, face_id)]
                    motion, detail = ensure_composite(app.unreal, sex, action, choice, accepted_report, selection_record)
                    entry['review_motion'] = motion
                    selection['animation_path'] = app.fixed.object_path(motion)
                    # Old five-second proof is not proof of this new derived clip.
                    for old_proof in ('evidence', 'package', 'non_face_validation', 'user_acceptance'):
                        selection.pop(old_proof, None)
                    selection['user_acceptance'] = 'pending_full_motion_loop_review'
                    selection['full_motion_loop_evidence'] = detail
                else:
                    motion = entry['review_motion']
                    detail = {'kind': 'full_body_without_face', 'animation_path': app.fixed.object_path(motion),
                              'duration_seconds': float(motion.get_play_length()),
                              'fullbody_duration_seconds': float(motion.get_play_length()),
                              'original_body': composer().asset_record(action['path'])}
            elif face_id != 'none':
                choice, _ = choices[(sex, face_id)]
                motion = entry['review_motion']
                if app.fixed.object_path(motion) != object_path(choice['asset']):
                    raise ValueError('Static loop must use the accepted five-second face')
                detail = {'kind': 'static_body_face_repeat', 'animation_path': app.fixed.object_path(motion),
                          'duration_seconds': 5., 'fullbody_duration_seconds': 0., 'accepted_selection': selection_record,
                          'accepted_face': composer().asset_record(choice['asset'])}
            else:
                detail = {'kind': 'static_without_animation', 'animation_path': None, 'duration_seconds': 0.,
                          'fullbody_duration_seconds': 0.}
            if selection['animation_path']:
                selection['playback'] = {'mode': 'loop', 'end_behavior': 'repeat', 'rate': 1.,
                                         'runtime_policy': POLICY, 'seamless_loop_verified': False}
            selection['review_loop_policy'] = runtime_policy()
            entry['face_selection'] = selection
            result['faces'][sex] = copy.deepcopy(selection)
            details[sex] = detail
        result['full_motion_loop'] = {'runtime_policy': runtime_policy(), 'characters': details}
        result['plan_sha256'] = app.fixed.digest({k: v for k, v in result.items() if k != 'plan_sha256'})
        return result, prepared

    def state(request, data, plan, prepared):
        result = old_state(request, data, plan, prepared)
        checks = {}
        for sex, detail in plan['full_motion_loop']['characters'].items():
            body = app.fixed.body_for(sex)
            saved = body.get_editor_property('animation_data')
            looping = bool(saved.get_editor_property('saved_looping'))
            rate = float(saved.get_editor_property('saved_play_rate'))
            motion = prepared[sex].get('review_motion')
            duration = float(motion.get_play_length()) if motion else 0.
            actual = result['animation'][sex]['animation']
            ok = (actual == detail['animation_path']
                  and looping == bool(motion)
                  and math.isclose(rate, 1., rel_tol=0, abs_tol=1e-6)
                  and math.isclose(duration, detail['duration_seconds'], rel_tol=0, abs_tol=1e-6))
            checks[sex] = {**copy.deepcopy(detail), 'success': ok, 'looping': looping, 'rate': rate,
                           'actual_animation': actual, 'actual_duration_seconds': duration,
                           'position_seconds': result['animation'][sex].get('position'),
                           'playing': result['animation'][sex].get('playing')}
        success = all(row['success'] for row in checks.values())
        result['full_motion_loop_readback'] = {'policy': POLICY, 'runtime_policy': runtime_policy(),
                                              'success': success, 'characters': checks}
        result['success'] = bool(result.get('success')) and success
        return result

    app.load_plan = app.review.load_plan = plan
    app.state = app.review.state = state
    app._full_motion_loop_installed = True
    return app
