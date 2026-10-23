"""Isolated source-window bake for the motion/location pilot; root dispatch only.

Generalises the existing camera BodyOnly SOURCE/controller method without
changing its frozen ten-second contract or any accepted animation asset.
Owner: SCENE_CAMERA_SEQUENCE.md, motion/portrait/location pilot 2026-10-11.
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
PROJECT = Path('D:/UE/projects/datatry_02')
RUN = Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/motion_portrait_scene_pilot_20261011_v1')
ASSET_ROOT = '/Game/DataMake/Validation/MotionPortraitScenePilot20261011/BodyWindows'
PHYSICAL_LIMITS = {'translation_cm': .00035, 'rotation_degrees': .025, 'scale_abs': .00001}


def mapping(numerator, denominator, source_frames, source_duration, start, end, output_duration):
    values = (numerator, denominator, source_frames, source_duration, end, output_duration)
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 for v in values):
        raise ValueError('Invalid finite positive timing')
    if any(v != int(v) for v in (numerator, denominator, source_frames)):
        raise ValueError('Frame grid needs integer values')
    if isinstance(start, bool) or not isinstance(start, (int, float)) or not math.isfinite(start) or not 0 <= start < end:
        raise ValueError('Invalid source start/end')
    fps = numerator / denominator
    exact_duration = source_frames / fps
    if abs(exact_duration - source_duration) > 1e-5 or end > exact_duration + 1e-8:
        raise ValueError('Source window exceeds exact frame duration')
    count = round(output_duration * fps)
    if not math.isclose(count / fps, output_duration, abs_tol=1e-8, rel_tol=0):
        raise ValueError('Output duration must be native-frame representable')
    times = [i / fps for i in range(count + 1)]
    speed = (end - start) / output_duration
    source_times = [start + t * speed for t in times]
    source_times[-1] = end
    return {'fps': fps, 'frames': count, 'times': times, 'source_times': source_times,
            'source_start_seconds': start, 'source_end_seconds': end,
            'source_duration_seconds': exact_duration, 'duration_seconds': output_duration,
            'body_play_rate': speed, 'body_retimed': abs(speed - 1) > 1e-8,
            'body_looped': False, 'root_trajectory_modified': False,
            'face_play_rate': 1., 'face_not_present_in_body_output': True}


def module(name):
    spec = importlib.util.spec_from_file_location('_motion_location_' + name, SCRIPTS / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def run(task):
    required = {'sex', 'motion_id', 'source', 'start_seconds', 'end_seconds', 'output_duration_seconds', 'window_id', 'report_path'}
    if not required <= set(task) or set(task) - required - {'validation_policy'} or task['sex'] not in ('female', 'male'):
        raise ValueError('Require exact window task fields and sex')
    validation_policy = task.get('validation_policy', 'legacy_mixed_component_v1')
    if validation_policy not in ('legacy_mixed_component_v1', 'sequencer_physical_v2'):
        raise ValueError('Unknown explicit numerical validation policy')
    if not re.fullmatch('[a-z][a-z0-9_]{0,95}', task['window_id']):
        raise ValueError('Invalid isolated window name')
    output = Path(task['report_path']).resolve()
    if not output.is_relative_to(RUN.resolve()) or output.suffix != '.json' or output.exists():
        raise ValueError('Require new JSON report inside owned run')
    source_pin = task['source']
    if set(source_pin) != {'asset', 'path', 'sha256'}:
        raise ValueError('Source must pin exact asset/path/SHA')
    expected_file = PROJECT / 'Content' / (source_pin['asset'].split('.')[0].removeprefix('/Game/') + '.uasset')
    if not source_pin['asset'].startswith('/Game/') or expected_file.resolve() != Path(source_pin['path']).resolve():
        raise ValueError('Source package does not match asset')
    if hashlib.sha256(expected_file.read_bytes()).hexdigest() != source_pin['sha256']:
        raise ValueError('Source package changed')
    composer = module('ue_compose_native_face_body_v1')
    face = module('ue_native_face_panel_five_second_v1')
    entry, _ = face.accepted_faces()[(task['sex'], 'idle')]
    import unreal as u
    if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
        raise ValueError('Wrong project')
    body, mesh = (u.load_asset(p) for p in (source_pin['asset'], entry['reference_mesh']))
    if not isinstance(body, u.AnimSequence) or not isinstance(mesh, u.SkeletalMesh):
        raise ValueError('Require source animation/reference mesh')
    skeleton = body.get_skeleton()
    if skeleton != mesh.get_editor_property('skeleton') or body.get_editor_property('additive_anim_type') != u.AdditiveAnimationType.AAT_NONE:
        raise ValueError('Require same shared skeleton and non-additive source')
    sources = [composer.asset_record(a.get_path_name()) for a in (body, mesh, skeleton)]
    assert sources[0]['sha256'] == source_pin['sha256']
    before = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if before & {r['asset'].split('.')[0] for r in sources}:
        raise ValueError('Protected sources are dirty')
    destination = ASSET_ROOT + '/' + task['sex'] + '/A_' + task['window_id']
    if u.EditorAssetLibrary.does_asset_exist(destination):
        raise ValueError('Refusing existing target')
    rate = body.data_model_interface.get_frame_rate()
    raw_count = body.data_model_interface.get_number_of_frames()
    mapped = mapping(rate.numerator, rate.denominator, int(getattr(raw_count, 'value', raw_count)),
                     float(body.get_play_length()), task['start_seconds'], task['end_seconds'], task['output_duration_seconds'])
    tracks = {str(n) for n in body.data_model_interface.get_bone_track_names()}
    if tracks & composer.FACE_BONES or not {'root', 'pelvis', 'head'} <= tracks:
        raise ValueError('Require BodyOnly track partition')
    if list(u.AnimationLibrary.get_animation_notify_events(body)):
        raise ValueError('Notify timing is unsupported')
    modifier = u.SkeletonModifier()
    if not modifier.set_skeletal_mesh(mesh):
        raise ValueError('Cannot inspect reference mesh')
    bones = sorted(str(n) for n in modifier.get_all_bone_names())
    assert len(bones) == 118 and tracks <= set(bones)
    curves = sorted(composer.curve_name_index([str(n) for n in u.AnimationLibrary.get_animation_curve_names(body, u.RawCurveTrackTypes.RCT_FLOAT)]).values())
    options = u.AnimPoseEvaluationOptions()
    options.set_editor_properties({'evaluation_type': u.AnimDataEvalType.SOURCE, 'should_retarget': False,
        'extract_root_motion': False, 'incorporate_root_motion_into_pose': True, 'evaluate_curves': True, 'optional_skeletal_mesh': mesh})

    def sample(asset, t):
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(asset, t, options)
        if not u.AnimPoseExtensions.is_valid(pose) or not set(bones) <= {str(n) for n in u.AnimPoseExtensions.get_bone_names(pose)} or not composer.curve_names_present(curves, [str(n) for n in u.AnimPoseExtensions.get_curve_names(pose)]):
            raise RuntimeError('Invalid source/evaluated pose')
        transforms = {n: u.AnimPoseExtensions.get_bone_pose(pose, u.Name(n), u.AnimPoseSpaces.LOCAL) for n in bones}
        values = {n: float(u.AnimPoseExtensions.get_curve_weight(pose, u.Name(n))) for n in curves}
        if not all(math.isfinite(v) for tr in transforms.values() for v in composer.transform_values(tr)) or not all(math.isfinite(v) for v in values.values()):
            raise ValueError('Nonfinite bone/curve')
        return transforms, values

    report = {'schema': 'motion_location_body_window_v2' if validation_policy == 'sequencer_physical_v2' else 'motion_location_body_window_v1',
              'validation_policy': validation_policy, 'success': False, 'task': task,
              'sources': sources, 'original_body': sources[0], 'destination': destination,
              'mapping': mapped, 'faces_included': False, 'human_naturalness_acceptance': 'pending'}
    try:
        expected = [sample(body, t) for t in mapped['source_times']]
        target = u.EditorAssetLibrary.duplicate_asset(body.get_path_name().split('.')[0], destination)
        if not isinstance(target, u.AnimSequence):
            raise RuntimeError('Could not duplicate source')
        target.set_editor_property('rate_scale', 1.)
        controller = target.controller
        controller.open_bracket('Isolated continuous BodyOnly window and explicit time mapping', False)
        try:
            if controller.remove_all_attributes(False):
                raise ValueError('Timed attributes are unsupported')
            controller.set_number_of_frames(u.FrameNumber(value=mapped['frames']), False)
            for name in sorted(tracks):
                values = [s[0][name] for s in expected]
                if not controller.set_bone_track_keys(u.Name(name), [v.translation for v in values], [v.rotation for v in values], [v.scale3d for v in values], False):
                    raise RuntimeError('Bone bake failed: ' + name)
            for name in curves:
                u.AnimationLibrary.remove_curve(target, u.Name(name), False)
                u.AnimationLibrary.add_curve(target, u.Name(name), u.RawCurveTrackTypes.RCT_FLOAT, False)
                u.AnimationLibrary.add_float_curve_keys(target, u.Name(name), mapped['times'], [s[1][name] for s in expected])
        finally:
            controller.close_bracket(False)
        assert abs(float(target.get_play_length()) - mapped['duration_seconds']) < 1e-5
        assert tracks == {str(n) for n in target.data_model_interface.get_bone_track_names()}
        assert set(curves) == {str(n) for n in u.AnimationLibrary.get_animation_curve_names(target, u.RawCurveTrackTypes.RCT_FLOAT)}
        if not u.EditorAssetLibrary.save_loaded_asset(target, only_if_is_dirty=False):
            raise RuntimeError('Could not save isolated body window')
        maxima = {'bones': 0., 'root': 0., 'curves': 0.}
        physical = {key: 0. for key in PHYSICAL_LIMITS}
        physical_worst = {}
        for i, t in enumerate(mapped['times']):
            actual = sample(target, t)
            for name in bones:
                error = composer.transform_error(actual[0][name], expected[i][0][name])
                maxima['bones'] = max(maxima['bones'], error)
                if name == 'root':
                    maxima['root'] = max(maxima['root'], error)
                values = composer.transform_metric_errors(composer.transform_values(actual[0][name]), composer.transform_values(expected[i][0][name]))
                for key, value in values.items():
                    if value > physical[key]:
                        physical[key] = value
                        physical_worst[key] = {'bone': name, 'frame': i, 'time_seconds': t, 'error': value}
            for name in curves:
                maxima['curves'] = max(maxima['curves'], abs(actual[1][name] - expected[i][1][name]))
        report['verification'] = {'all_frame_count': len(expected), 'bone_count': len(bones), 'track_count': len(tracks),
            'fps': mapped['fps'], 'duration_seconds': float(target.get_play_length()),
            'max_absolute_errors': maxima, 'tolerance': 1e-4, 'root_displacement_mapped_not_zeroed': True,
            'source_root_first': composer.transform_values(expected[0][0]['root']), 'source_root_last': composer.transform_values(expected[-1][0]['root'])}
        legacy_pass = max(maxima.values()) <= 1e-4
        if validation_policy == 'sequencer_physical_v2':
            # This policy is explicit, versioned, and never rewrites the legacy
            # gate in existing reports. Root/curve tests stay unchanged.
            numeric = module('ue_motion_body_window_numeric_validation_v1')
            report['verification']['physical_validation'] = {
                'limits': PHYSICAL_LIMITS, 'maximum_errors': physical, 'worst': physical_worst,
                'legacy_mixed_component_gate_pass': legacy_pass,
                'engine_precision_basis': [dict(numeric.pin(p), lines=lines, reason=reason) for p, lines, reason in numeric.ENGINE_SOURCES],
                'translation_budget': 'Two 1e-4 per-axis engine near-equality stages: 2*sqrt(3)*1e-4 cm, rounded to 0.00035 cm.',
                'rotation_budget': 'Quaternion component tolerance 1e-4 implies about 0.022918 degrees, plus float/Euler roundoff margin to 0.025 degrees.',
                'all_118_bones_included': True, 'root_and_curve_component_limits': 1e-4,
                'scope': 'Bounded local-pose numerical equivalence; not bit-exact or pixel-exact.'}
            if any(physical[k] > PHYSICAL_LIMITS[k] for k in physical) or maxima['root'] > 1e-4 or maxima['curves'] > 1e-4:
                raise RuntimeError('Mapped source physical comparison failed')
        elif not legacy_pass:
            raise RuntimeError('Mapped source comparison failed')
        report['asset_record'] = composer.asset_record(target.get_path_name())
        report['success'] = True
    except Exception:
        report['error'] = traceback.format_exc()
        raise
    finally:
        try:
            report.update(face.preservation(composer, u, sources, before, destination))
        except Exception:
            report['success'] = False
            report['protection_error'] = traceback.format_exc()
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
    if not report['success']:
        raise RuntimeError('Source preservation failed; inspect report')
    return report


if 'DM_MOTION_BODY_WINDOW_TASK' in globals():
    run(globals()['DM_MOTION_BODY_WINDOW_TASK'])
