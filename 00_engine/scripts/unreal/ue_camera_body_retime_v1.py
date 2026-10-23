"""Isolated uniform-10s camera BodyOnly window; explicit root-agent UE dispatch.

Sources >=10s use a contiguous original-speed window. Sources 7–<10s use
uniform body-only slowdown. No body wrapping, freezing or source mutation.
SOURCE evaluation preserves root displacement. Faces are composed afterwards
at their own unchanged five-second clock. Offline import never imports Unreal.
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
RUN = Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/camera_motion_pilot_20261009_v1')
INVENTORY = RUN / 'offline_motion_inventory_v2.json'
INVENTORY_SHA256 = 'aa6bb636cab99ea6d025ba46763dc1ba777e275a3a66e4f9fa1384ca43bfddb0'
ASSET_ROOT = '/Game/DataMake/Validation/CameraMotionPilot20261009'


def body_mapping(numerator, denominator, source_frames, source_duration, source_start_seconds=0.):
    values = (numerator, denominator, source_frames, source_duration)
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 for v in values):
        raise ValueError('Invalid body timing')
    if any(v != int(v) for v in (numerator, denominator, source_frames)):
        raise ValueError('Frame grid must use integer counts')
    if isinstance(source_start_seconds, bool) or not isinstance(source_start_seconds, (int, float)) or not math.isfinite(source_start_seconds) or source_start_seconds < 0:
        raise ValueError('Invalid source window start')
    fps = numerator / denominator
    exact_duration = source_frames / fps
    output_frames = round(10 * fps)
    if not math.isclose(source_duration, exact_duration, abs_tol=1e-5, rel_tol=0):
        raise ValueError('Reported duration differs from native integer frame grid')
    if not math.isclose(output_frames, 10 * fps, abs_tol=1e-8, rel_tol=0):
        raise ValueError('Ten seconds not representable at source frame rate')
    if exact_duration < 7:
        raise ValueError('Sources below seven seconds are excluded')
    slow = exact_duration < 10
    if slow and source_start_seconds != 0:
        raise ValueError('Short eligible body must use its whole clip')
    if not slow and source_start_seconds + 10 > exact_duration + 1e-8:
        raise ValueError('Continuous ten-second window exceeds source')
    rate = exact_duration / 10 if slow else 1.
    times = [i / fps for i in range(output_frames + 1)]
    source_times = [source_start_seconds + t * rate for t in times]
    # Exact frame duration is authoritative; float32 get_play_length is checked
    # separately above. The last slowdown sample reaches the source endpoint.
    source_times[-1] = exact_duration if slow else source_start_seconds + 10
    return {'fps': fps, 'frames': output_frames, 'times': times, 'source_times': source_times,
            'source_duration_seconds': exact_duration, 'reported_source_duration_seconds': source_duration,
            'duration_seconds': 10., 'body_play_rate': rate, 'source_start_seconds': source_start_seconds,
            'source_end_seconds': source_times[-1], 'mode': 'uniform_slowdown' if slow else 'trim_original_rate',
            'body_retimed': slow, 'body_looped': False, 'seams_seconds': [],
            'face_play_rate': 1., 'face_period_seconds': 5., 'face_not_present_in_body_output': True}


def private_module(name):
    spec = importlib.util.spec_from_file_location('_camera_retime_' + name, SCRIPTS / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def record(path):
    path = Path(path).resolve(strict=True)
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def report_path(value):
    path = Path(value).resolve()
    if not path.is_relative_to(RUN.resolve()) or path.suffix != '.json':
        raise ValueError('Camera report must be JSON within owned run')
    return path


def validate_task(task):
    if not isinstance(task, dict) or set(task) != {'sex', 'action_id', 'window_id', 'source_start_seconds', 'report_path'}:
        raise ValueError('Exact camera body task fields required')
    if task['sex'] not in ('female', 'male') or not isinstance(task['action_id'], str):
        raise ValueError('Invalid action identity')
    if not isinstance(task['window_id'], str) or not re.fullmatch('[a-z][a-z0-9_]{0,95}', task['window_id']):
        raise ValueError('Invalid isolated output identifier')
    report_path(task['report_path'])
    return task


def run(task):
    validate_task(task)
    inventory_record = record(INVENTORY)
    if inventory_record['sha256'] != INVENTORY_SHA256:
        raise ValueError('Expected pinned confirmed-ten-second inventory')
    inventory = read(INVENTORY)
    rows = [r['variants'][task['sex']] for r in inventory['entries'] if r['variants'][task['sex']]['action_id'] == task['action_id']]
    if len(rows) != 1 or not rows[0]['current_ten_second_policy']['eligible']:
        raise ValueError('Action is not eligible in confirmed inventory')
    source = rows[0]
    for key in ('body_only_package', 'import_report'):
        if record(source[key]['path'])['sha256'] != source[key]['sha256']:
            raise ValueError('Audited source/report changed')
    module = private_module('ue_compose_native_face_body_v1')
    face_module = private_module('ue_native_face_panel_five_second_v1')
    entry, _ = face_module.accepted_faces()[(task['sex'], 'idle')]
    import unreal as u
    if Path(u.Paths.project_dir()).resolve() != module.PROJECT.resolve():
        raise ValueError('Wrong UE project')
    body, mesh = (u.load_asset(p) for p in (source['body_only_asset'], entry['reference_mesh']))
    if not isinstance(body, u.AnimSequence) or not isinstance(mesh, u.SkeletalMesh) or body.get_editor_property('additive_anim_type') != u.AdditiveAnimationType.AAT_NONE:
        raise ValueError('Require non-additive BodyOnly and accepted reference mesh')
    skeleton = body.get_skeleton()
    expected = '/Game/DataMake/Validation/CFDNativeBatch4020261006/SharedSkeletons/SKEL_CFDShared_' + task['sex'].title() + '_v1'
    if skeleton != mesh.get_editor_property('skeleton') or skeleton.get_path_name().split('.')[0] != expected:
        raise ValueError('Wrong shared skeleton')
    sources = [module.asset_record(a.get_path_name()) for a in (body, mesh, skeleton)]
    if sources[0]['sha256'] != source['body_only_package']['sha256']:
        raise ValueError('Loaded BodyOnly provenance differs')
    before = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if before & {r['asset'].split('.')[0] for r in sources}:
        raise ValueError('Protected sources must be saved')
    destination = ASSET_ROOT + '/BodyWindows/' + task['sex'] + '/A_' + task['window_id']
    output = report_path(task['report_path'])
    if output.exists() or u.EditorAssetLibrary.does_asset_exist(destination):
        raise ValueError('Refusing to overwrite existing camera asset/report')
    rate = body.data_model_interface.get_frame_rate()
    raw_count = body.data_model_interface.get_number_of_frames()
    mapping = body_mapping(rate.numerator, rate.denominator, int(getattr(raw_count, 'value', raw_count)), float(body.get_play_length()), task['source_start_seconds'])
    tracks = {str(n) for n in body.data_model_interface.get_bone_track_names()}
    if tracks & module.FACE_BONES or not {'root', 'pelvis', 'head', 'neck_01', 'neck_02'} <= tracks:
        raise ValueError('Expected audited BodyOnly tracks without facial support tracks')
    if list(u.AnimationLibrary.get_animation_notify_events(body)):
        raise ValueError('Notify timing needs a separately implemented mapping')
    modifier = u.SkeletonModifier()
    if not modifier.set_skeletal_mesh(mesh):
        raise RuntimeError('Cannot inspect reference skeleton')
    bones = sorted(str(n) for n in modifier.get_all_bone_names())
    if len(bones) != 118 or not tracks <= set(bones):
        raise ValueError('Expected audited 118-bone skeleton')
    curves = sorted(module.curve_name_index([str(n) for n in u.AnimationLibrary.get_animation_curve_names(body, u.RawCurveTrackTypes.RCT_FLOAT)]).values())
    options = u.AnimPoseEvaluationOptions()
    options.set_editor_properties({'evaluation_type': u.AnimDataEvalType.SOURCE, 'should_retarget': False,
        'extract_root_motion': False, 'incorporate_root_motion_into_pose': True, 'evaluate_curves': True, 'optional_skeletal_mesh': mesh})

    def sample(asset, t):
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(asset, t, options)
        if not u.AnimPoseExtensions.is_valid(pose) or not set(bones) <= {str(n) for n in u.AnimPoseExtensions.get_bone_names(pose)} or not module.curve_names_present(curves, [str(n) for n in u.AnimPoseExtensions.get_curve_names(pose)]):
            raise RuntimeError('SOURCE evaluator omitted bones or curves')
        transforms = {n: u.AnimPoseExtensions.get_bone_pose(pose, u.Name(n), u.AnimPoseSpaces.LOCAL) for n in bones}
        values = {n: float(u.AnimPoseExtensions.get_curve_weight(pose, u.Name(n))) for n in curves}
        if not all(math.isfinite(v) for t in transforms.values() for v in module.transform_values(t)) or not all(math.isfinite(v) for v in values.values()):
            raise RuntimeError('Nonfinite source/evaluated pose')
        return transforms, values

    report = {'schema': 'camera_body_window_v1', 'success': False, 'task': task, 'destination': destination,
        'inventory': inventory_record, 'original_body': sources[0], 'sources': sources, 'mapping': mapping,
        'source_import_report': source['import_report'], 'bones': bones, 'bone_tracks': sorted(tracks), 'curves': curves,
        'source_evaluation': 'SOURCE without retarget, extract_root_motion=False, incorporate_root_motion_into_pose=True',
        'naturalness_accepted': False, 'faces_included': False}
    try:
        samples = [sample(body, t) for t in mapping['source_times']]
        target = u.EditorAssetLibrary.duplicate_asset(body.get_path_name().split('.')[0], destination)
        if not isinstance(target, u.AnimSequence):
            raise RuntimeError('Body duplication failed')
        target.set_editor_property('rate_scale', 1.)
        controller = target.controller
        controller.open_bracket('Camera ten-second BodyOnly source resampling', False)
        try:
            # Imports remove typed attributes. A nonzero result is an explicit
            # unsupported source, never silently discarded on a successful run.
            if controller.remove_all_attributes(False):
                raise ValueError('Source contains unsupported timed attributes')
            controller.set_number_of_frames(u.FrameNumber(value=mapping['frames']), False)
            for name in sorted(tracks):
                values = [s[0][name] for s in samples]
                if not controller.set_bone_track_keys(u.Name(name), [v.translation for v in values], [v.rotation for v in values], [v.scale3d for v in values], False):
                    raise RuntimeError('Could not resample source bone ' + name)
            for name in curves:
                u.AnimationLibrary.remove_curve(target, u.Name(name), False)
                u.AnimationLibrary.add_curve(target, u.Name(name), u.RawCurveTrackTypes.RCT_FLOAT, False)
                u.AnimationLibrary.add_float_curve_keys(target, u.Name(name), mapping['times'], [s[1][name] for s in samples])
        finally:
            controller.close_bracket(False)
        new_rate = target.data_model_interface.get_frame_rate()
        if (new_rate.numerator, new_rate.denominator) != (rate.numerator, rate.denominator) or not math.isclose(float(target.get_play_length()), 10., abs_tol=1e-6, rel_tol=0):
            raise RuntimeError('Target frame rate or duration differs')
        if {str(n) for n in target.data_model_interface.get_bone_track_names()} != tracks:
            raise RuntimeError('Source bone-track inventory changed')
        if module.curve_name_index([str(n) for n in u.AnimationLibrary.get_animation_curve_names(target, u.RawCurveTrackTypes.RCT_FLOAT)]).keys() != module.curve_name_index(curves).keys():
            raise RuntimeError('Body curve inventory changed')
        if not u.EditorAssetLibrary.save_loaded_asset(target, only_if_is_dirty=False):
            raise RuntimeError('Could not save new body window')
        maxima = {'bones': 0., 'root': 0., 'curves': 0.}
        for i, t in enumerate(mapping['times']):
            actual = sample(target, t)
            for name in bones:
                error = module.transform_error(actual[0][name], samples[i][0][name])
                maxima['bones'] = max(maxima['bones'], error)
                if name == 'root':
                    maxima['root'] = max(maxima['root'], error)
            for name in curves:
                maxima['curves'] = max(maxima['curves'], abs(actual[1][name] - samples[i][1][name]))
        report['verification'] = {'all_frame_count': len(samples), 'bone_count': len(bones), 'track_count': len(tracks),
            'fps': mapping['fps'], 'duration_seconds': float(target.get_play_length()),
            'max_absolute_errors': maxima, 'tolerance': 1e-4, 'root_displacement_mapped_not_zeroed': True,
            'source_root_first': module.transform_values(samples[0][0]['root']), 'source_root_last': module.transform_values(samples[-1][0]['root'])}
        if max(maxima.values()) > 1e-4:
            raise RuntimeError('All-frame mapped source comparison failed')
        report.update(face_module.preservation(module, u, sources, before, destination))
        report['asset_record'] = module.asset_record(target.get_path_name())
        report['success'] = True
    except Exception:
        report['error'] = traceback.format_exc()
        raise
    finally:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
    return report


def compose_accepted_face(body_report_path, face_id, composite_id, output_report_path):
    """Call only after root has verified body-window success; face clock stays 1x."""
    body_path = report_path(body_report_path)
    body = read(body_path)
    verify = body.get('verification', {})
    if body.get('schema') != 'camera_body_window_v1' or body.get('success') is not True or body.get('sources_unchanged') is not True or body.get('new_dirty_packages_outside_target') != [] or body.get('dirty_sources') != [] or body.get('faces_included') is not False or verify.get('duration_seconds') != 10.:
        raise ValueError('Require successful verified isolated ten-second body report')
    fps = verify.get('fps', 0)
    errors = verify.get('max_absolute_errors', {})
    if not isinstance(fps, (int, float)) or not math.isfinite(fps) or fps <= 0 or verify.get('bone_count') != 118 or verify.get('all_frame_count') != round(10*fps)+1 or verify.get('tolerance') != 1e-4 or set(errors) != {'bones', 'root', 'curves'} or any(not math.isfinite(v) or v < 0 or v > 1e-4 for v in errors.values()):
        raise ValueError('Incomplete body all-frame proof')
    sex = body['task']['sex']
    face_module = private_module('ue_native_face_panel_five_second_v1')
    entry, accepted = face_module.accepted_faces()[(sex, face_id)]
    module = private_module('ue_compose_native_face_body_v1')
    module.RUN, module.ASSET_ROOT = RUN, ASSET_ROOT + '/Composites'
    for source in (body['asset_record'], body['original_body']):
        if module.asset_record(source['asset']) != source:
            raise ValueError('Verified body/source asset changed')
    task = {'sex': sex, 'composite_id': composite_id, 'body_animation': body['destination'],
        'face_animation': entry['asset'], 'reference_mesh': entry['reference_mesh'],
        'allowed_face_curve_names': accepted['task']['allowed_face_curve_names'],
        'face_start_seconds': 0, 'face_end_seconds': 5, 'face_rate': 1,
        'face_playback': 'loop', 'body_mode': 'animation', 'report_path': str(report_path(output_report_path)),
        'camera_body_report': record(body_path), 'accepted_face_selection': record(face_module.SELECTION),
        'accepted_selection_entry_id': entry['selection_entry_id']}
    result = module.run(task)
    validator = private_module('ue_cfd40_full_motion_loop_v1')
    validator.validate_composition(result, task, 10., round(10*fps))
    return result


if 'DM_CAMERA_BODY_RETIME_TASK' in globals():
    run(globals()['DM_CAMERA_BODY_RETIME_TASK'])
