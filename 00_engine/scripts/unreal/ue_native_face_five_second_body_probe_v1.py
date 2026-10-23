"""Isolated first-five-second body crop, then verified native face composition.

Explicit UE dispatch only: DM_NATIVE_FACE_FIVE_SECOND_BODY_PROBE_TASK is a JSON
path. Offline imports and tests never load Unreal. Cropping is a playable-range
crop, preserving existing keys (including curve keys beyond the endpoint).
SetNumberOfFrames is NOT assumed to preserve motion: every local bone and float
curve at every original-rate frame, including 5.0 s, must compare successfully.
No actual UE crop/composition has been validated merely by running offline tests.
"""
from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
import re
import traceback

_spec = importlib.util.spec_from_file_location('_dm_body_probe_contract', Path(__file__).with_name('ue_native_face_five_second_v1.py'))
contract = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(contract)
RUN = contract.RUN
ASSET_ROOT = '/Game/DataMake/Validation/NativeFaceFiveSecond20261008/BodyProbes'
BODY_REPORTS = {
    'female': contract.OLD_RUN / 'compositions/final_v3/female_review_dramatic_sad_act_f06_elevator_greeting_v2.json',
    'male': contract.OLD_RUN / 'compositions/final_v3/male_review_dramatic_sad_act_m05_elevator_greeting_v2.json',
}
FIELDS = {'sex', 'probe_id', 'face_report', 'crop_report_path', 'composition_report_path', 'report_path'}
API_REFERENCE = 'https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Engine/IAnimationDataController/SetNumberOfFrames'


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def run_path(value):
    if not isinstance(value, str) or not value:
        raise ValueError('Expected report path')
    path = Path(value).resolve()
    if not path.is_relative_to(RUN.resolve()) or path.suffix != '.json':
        raise ValueError('Report must be JSON inside the current five-second run')
    return path


def validate_task(task):
    if not isinstance(task, dict) or set(task) != FIELDS:
        raise ValueError('Exact body probe fields required; time/rate overrides forbidden')
    if task['sex'] not in BODY_REPORTS or not isinstance(task['probe_id'], str) or not re.fullmatch('[a-z][a-z0-9_]{0,80}', task['probe_id']):
        raise ValueError('Invalid body probe identity')
    paths = [run_path(task[key]) for key in ('face_report', 'crop_report_path', 'composition_report_path', 'report_path')]
    if len(set(paths)) != 4:
        raise ValueError('Source and output report paths must be distinct')
    if any(path.exists() for path in paths[1:]):
        raise ValueError('All body probe reports must be new; use a unique probe id')
    return task


def frame_grid(numerator, denominator, source_duration):
    if not all(contract.finite(v) and v > 0 for v in (numerator, denominator, source_duration)) or source_duration < 5:
        raise ValueError('Original body must be at least five seconds at a valid frame rate')
    fps = numerator / denominator
    frames = round(5 * fps)
    if frames < 1 or not math.isclose(frames, 5 * fps, abs_tol=1e-8, rel_tol=0):
        raise ValueError('Original body frame rate cannot represent exactly five seconds')
    return fps, frames, [i / fps for i in range(frames + 1)]


def verified_inputs(task):
    body_report = read_json(BODY_REPORTS[task['sex']])
    bt = body_report.get('task', {})
    if body_report.get('success') is not True or bt.get('sex') != task['sex'] or bt.get('body_mode') != 'animation' or body_report.get('verification', {}).get('duration_seconds', 0) < 5:
        raise ValueError('Selected original body lacks a successful >=5 second report')
    body_path = bt['body_animation']
    body_record = next((row for row in body_report.get('sources', []) if row['asset'] == body_path), None)
    if not body_record or not re.fullmatch('[a-f0-9]{64}', body_record.get('sha256', '')):
        raise ValueError('Original body report is missing its source SHA256')
    face_report = read_json(task['face_report'])
    ft = contract.validate_task(face_report.get('task'))
    v = face_report.get('verification', {})
    fps = v.get('fps')
    if face_report.get('success') is not True or face_report.get('sources_unchanged') is not True or ft['sex'] != task['sex'] or not contract.finite(v.get('duration_seconds')) or not math.isclose(v['duration_seconds'], 5, abs_tol=1e-6, rel_tol=0):
        raise ValueError('Face requires a successful same-sex five-second static source report')
    if not contract.finite(fps) or fps <= 0 or v.get('all_frame_count') != round(5 * fps) + 1 or set(face_report.get('face_bones', [])) != contract.EXPECTED_FACE_BONES:
        raise ValueError('Face report lacks complete frame/ten-bone verification')
    expected_face = contract.ASSET_ROOT + '/' + task['sex'] + '/A_' + ft['composite_id']
    if face_report.get('destination') != expected_face:
        raise ValueError('Face report destination does not match its task')
    return body_record, face_report


def compose_task(task, face_report, cropped_asset):
    ft = face_report['task']
    return {'sex': task['sex'], 'composite_id': task['probe_id'], 'body_animation': cropped_asset,
            'face_animation': face_report['destination'], 'reference_mesh': ft['reference_mesh'],
            'allowed_face_curve_names': ft['allowed_face_curve_names'], 'face_start_seconds': 0,
            'face_end_seconds': 5, 'face_rate': 1, 'face_playback': 'hold', 'body_mode': 'animation',
            'report_path': task['composition_report_path']}


def ensure_preserved(module, u, records, dirty_before, allowed_targets):
    unchanged = all(module.asset_record(row['asset']) == row for row in records)
    dirty_now = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    outside = sorted(dirty_now - dirty_before - set(allowed_targets))
    dirty_sources = sorted({row['asset'].split('.')[0] for row in records} & dirty_now)
    if not unchanged or outside or dirty_sources:
        raise RuntimeError('Source/shared asset preservation failed')
    return {'sources_unchanged': unchanged, 'new_dirty_packages_outside_targets': outside, 'dirty_sources': dirty_sources}


def write_report(path, report):
    # Paths were required to be new before starting; never overwrite prior runs.
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def run(task):
    validate_task(task)
    body_record, face_report = verified_inputs(task)
    module = contract.composer_module()
    module.RUN, module.ASSET_ROOT = RUN, ASSET_ROOT + '/Composites'
    import unreal as u
    if Path(u.Paths.project_dir()).resolve() != module.PROJECT.resolve():
        raise ValueError('Wrong UE project')
    body, face, mesh = (u.load_asset(path) for path in (body_record['asset'], face_report['destination'], face_report['task']['reference_mesh']))
    if not isinstance(body, u.AnimSequence) or not isinstance(face, u.AnimSequence) or not isinstance(mesh, u.SkeletalMesh):
        raise ValueError('Expected original body, verified face and reference mesh')
    skeleton = body.get_skeleton()
    expected_skeleton = '/Game/DataMake/Validation/CFDNativeBatch4020261006/SharedSkeletons/SKEL_CFDShared_' + task['sex'].title() + '_v1'
    if skeleton.get_path_name().split('.')[0] != expected_skeleton or face.get_skeleton() != skeleton or mesh.get_editor_property('skeleton') != skeleton:
        raise ValueError('All probe sources must share the current same-sex skeleton')
    if any(asset.get_editor_property('additive_anim_type') != u.AdditiveAnimationType.AAT_NONE for asset in (body, face)) or not math.isclose(float(face.get_play_length()), 5, abs_tol=1e-6, rel_tol=0):
        raise ValueError('Require non-additive original body and five-second face')
    records = [module.asset_record(asset.get_path_name()) for asset in (body, face, mesh, skeleton)]
    if records[0]['sha256'] != body_record['sha256']:
        raise ValueError('Original body changed since its accepted source report')
    dirty_before = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if any(row['asset'].split('.')[0] in dirty_before for row in records):
        raise ValueError('Save source assets before probing')
    cropped_path = ASSET_ROOT + '/' + task['sex'] + '/A_' + task['probe_id'] + '_body'
    composed_path = module.ASSET_ROOT + '/' + task['sex'] + '/A_' + task['probe_id']
    if any(u.EditorAssetLibrary.does_asset_exist(path) for path in (cropped_path, composed_path)):
        raise ValueError('Refusing to overwrite a body probe asset')
    rate = body.data_model_interface.get_frame_rate()
    fps, frames, times = frame_grid(rate.numerator, rate.denominator, float(body.get_play_length()))
    modifier = u.SkeletonModifier()
    if not modifier.set_skeletal_mesh(mesh):
        raise RuntimeError('Cannot inspect full reference skeleton')
    bones = sorted(str(n) for n in modifier.get_all_bone_names())
    curve_index = module.curve_name_index([str(n) for n in u.AnimationLibrary.get_animation_curve_names(body, u.RawCurveTrackTypes.RCT_FLOAT)], 'original body curves')
    curves = sorted(curve_index.values())
    options = u.AnimPoseEvaluationOptions()
    options.set_editor_properties({'evaluation_type': u.AnimDataEvalType.SOURCE, 'should_retarget': False,
        'extract_root_motion': False, 'incorporate_root_motion_into_pose': True, 'evaluate_curves': True, 'optional_skeletal_mesh': mesh})

    def sample(asset, time):
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(asset, time, options)
        if not u.AnimPoseExtensions.is_valid(pose) or not set(bones).issubset({str(n) for n in u.AnimPoseExtensions.get_bone_names(pose)}) or not module.curve_names_present(curves, [str(n) for n in u.AnimPoseExtensions.get_curve_names(pose)]):
            raise RuntimeError('Source evaluator omitted required bones/curves')
        return ({n: u.AnimPoseExtensions.get_bone_pose(pose, u.Name(n), u.AnimPoseSpaces.LOCAL) for n in bones},
                {n: float(u.AnimPoseExtensions.get_curve_weight(pose, u.Name(n))) for n in curves})

    report = {'success': False, 'task': task, 'original_body_report': str(BODY_REPORTS[task['sex']]),
              'original_body': body_record, 'sources': records, 'face_source_report': task['face_report'],
              'crop_asset': cropped_path, 'composite_asset': composed_path}
    crop = {'success': False, 'original_body': body_record, 'sources': records, 'destination': cropped_path,
            'method': 'duplicate then set_number_of_frames; original fps, playable range [0,5], no bone/curve key rewrites',
            'api_reference': API_REFERENCE, 'all_bones': bones, 'float_curves': curves}
    try:
        expected = [sample(body, time) for time in times]
        target = u.EditorAssetLibrary.duplicate_asset(body_record['asset'].split('.')[0], cropped_path)
        if not isinstance(target, u.AnimSequence):
            raise RuntimeError('Could not duplicate body')
        target.controller.open_bracket('Crop original-rate body playable range to five seconds', False)
        try:
            target.controller.set_number_of_frames(u.FrameNumber(value=frames), False)
        finally:
            target.controller.close_bracket(False)
        new_rate = target.data_model_interface.get_frame_rate()
        if (new_rate.numerator, new_rate.denominator) != (rate.numerator, rate.denominator) or not math.isclose(float(target.get_play_length()), 5, abs_tol=1e-6, rel_tol=0):
            raise RuntimeError('Body crop changed rate or did not produce five seconds')
        target_curve_index = module.curve_name_index([str(n) for n in u.AnimationLibrary.get_animation_curve_names(target, u.RawCurveTrackTypes.RCT_FLOAT)], 'cropped body curves')
        if {str(n) for n in target.data_model_interface.get_bone_track_names()} != {str(n) for n in body.data_model_interface.get_bone_track_names()} or target_curve_index.keys() != curve_index.keys():
            raise RuntimeError('Body crop altered track inventory')
        if not u.EditorAssetLibrary.save_loaded_asset(target, only_if_is_dirty=False):
            raise RuntimeError('Could not save body crop')
        bone_max = curve_max = endpoint_curve_max = 0.0
        for index, time in enumerate(times):
            actual_bones, actual_curves = sample(target, time)
            expected_bones, expected_curves = expected[index]
            for name in bones:
                a, b = module.transform_values(actual_bones[name]), module.transform_values(expected_bones[name])
                if not all(math.isfinite(v) for v in a + b):
                    raise RuntimeError('Nonfinite body transform')
                bone_max = max(bone_max, module.transform_error(actual_bones[name], expected_bones[name]))
            for name in curves:
                if not all(math.isfinite(v) for v in (actual_curves[name], expected_curves[name])):
                    raise RuntimeError('Nonfinite body curve')
                error = abs(actual_curves[name] - expected_curves[name])
                curve_max = max(curve_max, error)
                if index == frames:
                    endpoint_curve_max = max(endpoint_curve_max, error)
        crop['verification'] = {'all_frame_count': len(times), 'fps': fps, 'duration_seconds': float(target.get_play_length()),
            'all_bone_max_absolute_error': bone_max, 'float_curve_max_absolute_error': curve_max,
            'endpoint_curve_max_absolute_error': endpoint_curve_max, 'tolerance': 1e-4,
            'time_mapping': 'output_time == original_body_time, inclusive [0,5]', 'retimed': False}
        if bone_max > 1e-4 or curve_max > 1e-4:
            raise RuntimeError('Body crop all-frame original-source comparison failed')
        crop.update(ensure_preserved(module, u, records, dirty_before, [cropped_path]))
        crop['success'] = True
        write_report(run_path(task['crop_report_path']), crop)
        composition = module.run(compose_task(task, face_report, cropped_path))
        if composition.get('success') is not True or not math.isclose(composition['verification']['duration_seconds'], 5, abs_tol=1e-6, rel_tol=0):
            raise RuntimeError('Five-second moving-body composition failed')
        report.update(ensure_preserved(module, u, records, dirty_before, [cropped_path, composed_path]))
        report.update(success=True, composition_report=task['composition_report_path'], crop_report=task['crop_report_path'])
    except Exception:
        report['error'] = traceback.format_exc()
        if not run_path(task['crop_report_path']).exists():
            crop['error'] = report['error']
            write_report(run_path(task['crop_report_path']), crop)
        raise
    finally:
        write_report(run_path(task['report_path']), report)
    return report


if __name__ == '__main__':
    path = globals().get('DM_NATIVE_FACE_FIVE_SECOND_BODY_PROBE_TASK')
    if not isinstance(path, str):
        raise ValueError('Set DM_NATIVE_FACE_FIVE_SECOND_BODY_PROBE_TASK to a new task JSON path')
    run(read_json(path))
