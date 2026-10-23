"""Create isolated body/native-face composite AnimSequences; root dispatch only.

No runtime/UI changes. Face and body sources must use the same current shared
Skeleton. Non-facial animated body tracks remain duplicated, never rewritten.
Static mode explicitly freezes the selected body-source pose. Curves are sampled
through UE's source-data evaluator, not invented key patterns or guessed curves.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
import traceback

PROJECT = Path('D:/UE/projects/datatry_02')
RUN = Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/character_runtime_face_library_20261007_v1')
ASSET_ROOT = '/Game/DataMake/Validation/NativeFaceLibrary20261007/Composites'
FACE_BONES = frozenset(('facialbone', 'jawroot', 'upperjaw',
                       'l_eye', 'r_eye', 'teeth01', 'teeth02',
                       'tongue01', 'tongue02', 'tongue03'))
FORBIDDEN_FACE_BONES = frozenset(('root', 'pelvis', 'head', 'neck_01', 'neck_02'))
FACE_TRANSFORM_TOLERANCES = {'translation_cm': .001, 'rotation_degrees': .2, 'scale_abs': 1e-4}


def finite_number(value, label, minimum=0):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < minimum:
        raise ValueError('Invalid ' + label)
    return float(value)


def face_time(output_time, start, end, rate, mode):
    t = finite_number(output_time, 'output time')
    start, end = finite_number(start, 'window start'), finite_number(end, 'window end')
    rate = finite_number(rate, 'face rate', 1e-6)
    if end <= start or mode not in ('loop', 'hold'):
        raise ValueError('Invalid face time window/mode')
    elapsed = t * rate
    return start + (elapsed % (end - start) if mode == 'loop' else min(elapsed, end - start))


def face_envelope(output_time, total_duration, window_duration, rate, mode, fade_seconds, fade_out_seconds=None, intensity=1.):
    """Smoothly return each face cycle and the whole composite to native neutral."""
    fade = finite_number(fade_seconds, 'face fade seconds')
    fade_out = fade if fade_out_seconds is None else finite_number(fade_out_seconds, 'face fade out seconds')
    intensity = finite_number(intensity, 'face intensity')
    if intensity > 1:
        raise ValueError('Face intensity must be in [0,1]')
    if not fade and not fade_out:
        return intensity
    t = finite_number(output_time, 'output time')
    total = finite_number(total_duration, 'total duration', 1e-6)
    period = finite_number(window_duration, 'window duration', 1e-6) / finite_number(rate, 'face rate', 1e-6)
    if mode not in ('loop', 'hold') or fade+fade_out > min(period, total) + 1e-8:
        raise ValueError('Face fade must fit both the facial cycle and composite duration')
    phase = t % period if mode == 'loop' else min(t, period)
    ratios = ([phase/fade,t/fade] if fade else []) + ([(period-phase)/fade_out,(total-t)/fade_out] if fade_out else [])
    x = max(0., min(1., min(ratios)))
    return intensity*x*x*(3.-2.*x)


def blend_transform_values(baseline, native, alpha):
    """Blend local T/S and shortest-path quaternion slerp, no Euler roundtrip."""
    if len(baseline) != 10 or len(native) != 10 or not all(math.isfinite(v) for v in baseline + native):
        raise ValueError('Expected two finite local transforms')
    if not math.isfinite(alpha) or not 0 <= alpha <= 1:
        raise ValueError('Invalid face envelope weight')
    quats = []
    for source in (baseline, native):
        length = math.sqrt(sum(v*v for v in source[3:7]))
        if length < 1e-8:
            raise ValueError('Invalid zero quaternion')
        quats.append([v/length for v in source[3:7]])
    a, b = quats
    dot = sum(x*y for x,y in zip(a,b))
    if dot < 0:
        b = [-v for v in b]
        dot = -dot
    dot = max(-1.,min(1.,dot))
    if dot > .9995:
        q = [(1-alpha)*x+alpha*y for x,y in zip(a,b)]
    else:
        angle = math.acos(dot)
        first = math.sin((1-alpha)*angle)/math.sin(angle)
        second = math.sin(alpha*angle)/math.sin(angle)
        q = [first*x+second*y for x,y in zip(a,b)]
    length = math.sqrt(sum(v*v for v in q))
    result = [(1-alpha)*x+alpha*y for x,y in zip(baseline,native)]
    result[3:7] = [v/length for v in q]
    return result


def select_face_bones(parents):
    """Only allow the known CC facial support branch; never head/neck/root."""
    if not isinstance(parents, dict) or not FACE_BONES.issubset(parents):
        raise ValueError('Expected current CC facial support bones')
    selected = set()
    for bone in parents:
        seen, current = set(), bone
        while current in parents and current not in seen:
            if current == 'facialbone':
                selected.add(bone)
                break
            seen.add(current)
            current = parents[current]
    # Eyes may attach to head on some CC versions; exact names are explicitly
    # approved, but their ancestry still must be the existing head/facial branch.
    for eye in ('l_eye', 'r_eye'):
        if parents[eye] in ('head', 'facialbone'):
            selected.add(eye)
    if selected != FACE_BONES or selected & FORBIDDEN_FACE_BONES:
        raise ValueError('Facial hierarchy differs from the audited ten-bone scope')
    return sorted(selected)


def excluded_body_control_curve(name):
    return name.casefold().startswith(('head_', 'neck_', 'ctrl_expressions_neck'))


def curve_name_index(names, label='curve names'):
    """Compare FName identities without changing the actual API/report spelling."""
    result = {}
    for name in names:
        if not isinstance(name, str) or not re.fullmatch('[A-Za-z0-9_]+', name):
            raise ValueError('Invalid ' + label)
        key = name.casefold()
        if key in result and result[key] != name:
            raise ValueError('Case-insensitive curve collision in ' + label + ': ' + result[key] + ', ' + name)
        result[key] = name
    return result


def curve_names_present(required, actual):
    """A case alias is present; a truly absent evaluator curve must still fail."""
    return curve_name_index(required, 'required curves').keys() <= curve_name_index(actual, 'evaluated curves').keys()


def classify_curve_names(source_names, allowed_names, body_names):
    source = curve_name_index(source_names, 'source curves')
    allowed = curve_name_index(allowed_names, 'approved Morph names')
    body = curve_name_index(body_names, 'body curves')
    if not allowed:
        raise ValueError('Actual approved Morph names are required')
    excluded = {key: name for key, name in {**allowed, **source}.items() if excluded_body_control_curve(name)}
    allowed = {key: name for key, name in allowed.items() if key not in excluded}
    unknown = source.keys() - allowed.keys() - excluded.keys()
    if unknown:
        raise ValueError('Native face source has unclassified curves: ' + ','.join(sorted(source[key] for key in unknown)))
    face = [name for key, name in source.items() if key not in excluded]
    if not face:
        raise ValueError('Native source has no face curves')
    return {'face_curves': sorted(face), 'excluded_curves': sorted(excluded.values()),
            'replace_body_curves': sorted(name for key, name in body.items() if key in allowed),
            'unrelated_curves': sorted(name for key, name in body.items() if key not in allowed)}


def transform_values(value):
    return [float(value.translation.x), float(value.translation.y), float(value.translation.z),
            float(value.rotation.x), float(value.rotation.y), float(value.rotation.z), float(value.rotation.w),
            float(value.scale3d.x), float(value.scale3d.y), float(value.scale3d.z)]


def transform_error(a, b):
    a, b = transform_values(a), transform_values(b)
    sign = -1 if sum(x*y for x, y in zip(a[3:7], b[3:7])) < 0 else 1
    return max([abs(a[i]-b[i]) for i in (0,1,2,7,8,9)] + [abs(a[i]-sign*b[i]) for i in (3,4,5,6)])


def transform_metric_errors(actual, expected):
    """Local pose errors with physical units; quaternion sign is immaterial."""
    if len(actual) != 10 or len(expected) != 10 or not all(math.isfinite(v) for v in actual+expected):
        raise ValueError('Expected finite transforms for metric validation')
    translation = math.sqrt(sum((actual[i]-expected[i])**2 for i in (0,1,2)))
    scale = max(abs(actual[i]-expected[i]) for i in (7,8,9))
    a,b = actual[3:7],expected[3:7]
    la,lb = math.sqrt(sum(v*v for v in a)),math.sqrt(sum(v*v for v in b))
    if min(la,lb) < 1e-8:
        raise ValueError('Cannot validate zero quaternion')
    a,b = [v/la for v in a],[v/lb for v in b]
    if sum(x*y for x,y in zip(a,b)) < 0:
        b = [-v for v in b]
    # Stable near identity; acos(dot) loses precision for tiny rotations.
    difference = math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))
    total = math.sqrt(sum((x+y)**2 for x,y in zip(a,b)))
    angle = math.degrees(4*math.atan2(difference,total))
    return {'translation_cm':translation, 'rotation_degrees':angle, 'scale_abs':scale}


def asset_record(path):
    package = path.split('.', 1)[0]
    if not package.startswith('/Game/') or '..' in package or '\\' in package:
        raise ValueError('Expected an existing /Game asset')
    file = PROJECT / 'Content' / (package.removeprefix('/Game/') + '.uasset')
    return {'asset': path, 'path': str(file), 'sha256': hashlib.sha256(file.read_bytes()).hexdigest()}


def run(task):
    import unreal as u
    if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
        raise ValueError('Wrong UE project')
    sex, slug = task['sex'], task['composite_id']
    if sex not in ('female', 'male') or not re.fullmatch('[a-z][a-z0-9_]{0,95}', slug):
        raise ValueError('Invalid composite identity')
    mode = task.get('body_mode', 'animation')
    if mode not in ('animation', 'static'):
        raise ValueError('Invalid body mode')
    static_reference = task.get('static_use_reference_pose', False)
    if not isinstance(static_reference, bool) or (static_reference and mode != 'static'):
        raise ValueError('static_use_reference_pose requires static mode and a boolean value')
    start = finite_number(task['face_start_seconds'], 'face start')
    end = finite_number(task['face_end_seconds'], 'face end')
    rate = finite_number(task.get('face_rate', 1), 'face rate', 1e-6)
    playback = task.get('face_playback', 'loop')
    envelope_config = task.get('face_envelope')
    if envelope_config is not None and (not isinstance(envelope_config,dict) or set(envelope_config)-{'fade_in_seconds','fade_out_seconds','intensity'}):
        raise ValueError('Invalid face_envelope configuration')
    fade_in = finite_number(envelope_config.get('fade_in_seconds',.3),'fade in',1e-6) if envelope_config is not None else 0.
    fade_out = finite_number(envelope_config.get('fade_out_seconds',.3),'fade out',1e-6) if envelope_config is not None else 0.
    intensity = finite_number(envelope_config.get('intensity',1.),'face intensity') if envelope_config is not None else 1.
    face_time(0, start, end, rate, playback)
    body_time = finite_number(task.get('static_body_time_seconds', 0), 'static body time')
    output = Path(task['report_path']).resolve()
    if not output.is_relative_to(RUN.resolve()) or output.exists():
        raise ValueError('Report must be new and inside the current run')
    destination = ASSET_ROOT + '/' + sex + '/A_' + slug
    if u.EditorAssetLibrary.does_asset_exist(destination):
        raise ValueError('Refusing to overwrite composite')
    body, face, mesh = (u.load_asset(task[k]) for k in ('body_animation', 'face_animation', 'reference_mesh'))
    if not isinstance(body, u.AnimSequence) or not isinstance(face, u.AnimSequence) or not isinstance(mesh, u.SkeletalMesh):
        raise ValueError('Body, native face and reference mesh assets are required')
    skeleton = body.get_skeleton()
    expected = '/Game/DataMake/Validation/CFDNativeBatch4020261006/SharedSkeletons/SKEL_CFDShared_' + sex.title() + '_v1'
    if skeleton.get_path_name().split('.')[0] != expected or face.get_skeleton() != skeleton or mesh.get_editor_property('skeleton') != skeleton:
        raise ValueError('Sources must use the corresponding current shared Skeleton')
    if end > float(face.get_play_length()) + 1e-6 or body_time > float(body.get_play_length()):
        raise ValueError('Requested sample window exceeds source animation')
    for asset in (body, face):
        if asset.get_editor_property('additive_anim_type') != u.AdditiveAnimationType.AAT_NONE:
            raise ValueError('This composer requires non-additive imported sources')
    modifier = u.SkeletonModifier()
    if not modifier.set_skeletal_mesh(mesh):
        raise RuntimeError('Could not inspect reference hierarchy')
    parents = {str(n): str(modifier.get_parent_name(n)) for n in modifier.get_all_bone_names()}
    face_bones = select_face_bones(parents)
    body_tracks = [str(n) for n in body.data_model_interface.get_bone_track_names()]
    face_tracks = [str(n) for n in face.data_model_interface.get_bone_track_names()]
    if not set(face_bones).issubset(face_tracks):
        raise ValueError('Native face source is missing required facial bone tracks')
    protected = sorted((set(parents) if static_reference else set(body_tracks)) - set(face_bones))
    curve_scope = classify_curve_names(
        [str(n) for n in u.AnimationLibrary.get_animation_curve_names(face, u.RawCurveTrackTypes.RCT_FLOAT)],
        task['allowed_face_curve_names'],
        [str(n) for n in u.AnimationLibrary.get_animation_curve_names(body, u.RawCurveTrackTypes.RCT_FLOAT)])
    face_curves = curve_scope['face_curves']
    excluded_curves = curve_scope['excluded_curves']
    unrelated_curves = curve_scope['unrelated_curves']
    source_records = [asset_record(obj.get_path_name()) for obj in (body, face, mesh, skeleton)]
    dirty_before = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if any(obj.get_path_name().split('.')[0] in dirty_before for obj in (body, face, mesh, skeleton)):
        raise ValueError('Source assets must be saved before composition')
    body_rate = body.data_model_interface.get_frame_rate()
    fps = float(body_rate.numerator) / float(body_rate.denominator)
    frames_value = body.data_model_interface.get_number_of_frames()
    frames = int(getattr(frames_value, 'value', frames_value))
    if mode == 'static':
        frames = max(1, round((end-start)/rate*fps))
    elif playback == 'hold' and float(body.get_play_length()) + 1e-6 < (end-start)/rate and not task.get('allow_face_truncation', False):
        raise ValueError('Body clip would truncate the one-shot face; choose an explicit shorter window')
    times = [i/fps for i in range(frames+1)]
    envelope = [face_envelope(t, times[-1], end-start, rate, playback, fade_in, fade_out, intensity) for t in times]
    options = u.AnimPoseEvaluationOptions()
    for key, value in {'evaluation_type': u.AnimDataEvalType.SOURCE, 'should_retarget': False,
                       'extract_root_motion': False, 'incorporate_root_motion_into_pose': True,
                       'evaluate_curves': True, 'optional_skeletal_mesh': mesh}.items():
        options.set_editor_property(key, value)
    def pose(asset, time):
        value = u.AnimPoseExtensions.get_anim_pose_at_time(asset, time, options)
        if not u.AnimPoseExtensions.is_valid(value):
            raise RuntimeError('Source animation pose evaluation failed')
        return value
    def bone(p, name):
        return u.AnimPoseExtensions.get_bone_pose(p, u.Name(name), u.AnimPoseSpaces.LOCAL)
    def weight(p, name):
        return float(u.AnimPoseExtensions.get_curve_weight(p, u.Name(name)))
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {'success': False, 'task': task, 'sources': source_records, 'destination': destination,
              'face_bones': face_bones, 'protected_body_bones': protected, 'face_curves': face_curves,
              'excluded_body_control_curves': sorted(excluded_curves),
              'preserved_non_face_curves': sorted(unrelated_curves),
              'playback_note': 'hold clamps facial source time; runtime must switch back to base body for one-shot completion. Loop suitability remains visual review.'}
    try:
        target = u.EditorAssetLibrary.duplicate_asset(body.get_path_name().split('.')[0], destination)
        if not isinstance(target, u.AnimSequence):
            raise RuntimeError('Could not create isolated composite')
        controller = target.controller
        original_unrelated_keys = {n: u.AnimationLibrary.get_float_keys(body, u.Name(n)) for n in unrelated_curves}
        face_poses = [pose(face, face_time(t, start, end, rate, playback)) for t in times]
        if any(not curve_names_present(face_curves, [str(n) for n in u.AnimPoseExtensions.get_curve_names(p)]) for p in face_poses):
            raise ValueError('Source evaluator omitted native curve names; zero fallback would be unsafe')
        static_pose = pose(body, body_time) if mode == 'static' else None
        reference_pose = static_pose if mode == 'static' else pose(body,0.)
        reference_bone_names = {str(n) for n in u.AnimPoseExtensions.get_bone_names(reference_pose)}
        if static_reference and not set(parents).issubset(reference_bone_names):
            raise ValueError('Reference evaluator omitted body bones; identity fallback would be unsafe')
        static_body_bones = {name:(u.AnimPoseExtensions.get_ref_bone_pose(reference_pose,u.Name(name),u.AnimPoseSpaces.LOCAL)
            if static_reference else bone(static_pose,name)) for name in protected} if mode == 'static' else {}
        if static_reference:
            report['static_body_baseline'] = {'asset':mesh.get_path_name(),
                'method':'AnimPoseExtensions.get_ref_bone_pose LOCAL with optional_skeletal_mesh',
                'local_bones':{n:transform_values(v) for n,v in static_body_bones.items()}}
        if envelope_config is not None and not set(face_bones).issubset({str(n) for n in u.AnimPoseExtensions.get_bone_names(reference_pose)}):
            raise ValueError('Reference evaluator omitted facial bones; identity fallback would be unsafe')
        reference_neutral = {name:u.AnimPoseExtensions.get_ref_bone_pose(reference_pose,u.Name(name),u.AnimPoseSpaces.LOCAL) for name in face_bones} if envelope_config is not None else {}
        expected_face_bones = {}
        for name in face_bones:
            transforms = [bone(p,name) for p in face_poses]
            if envelope_config is not None:
                baseline = transform_values(reference_neutral[name])
                blended = [blend_transform_values(baseline, transform_values(v), a) for v,a in zip(transforms,envelope)]
                transforms = []
                for v in blended:
                    transform = u.Transform()
                    transform.set_editor_properties({'translation':u.Vector(*v[:3]),
                        'rotation':u.Quat(*v[3:7]), 'scale3d':u.Vector(*v[7:])})
                    transforms.append(transform)
            expected_face_bones[name] = transforms
        if envelope_config is not None:
            report['face_envelope'] = {'fade_in_seconds':fade_in, 'fade_out_seconds':fade_out, 'intensity':intensity,'shape':'smoothstep',
                'rotation_blend':'shortest_path_quaternion_slerp_with_near_parallel_nlerp',
                'baseline':{'asset':mesh.get_path_name(), 'method':'AnimPoseExtensions.get_ref_bone_pose LOCAL with optional_skeletal_mesh',
                    'local_bones':{n:transform_values(reference_neutral[n]) for n in face_bones}},
                'curve_baseline':0., 'scope':'each source window and composite start/end',
                'window_envelope':{'period_seconds':(end-start)/rate,'fade_in_seconds':fade_in,'fade_out_seconds':fade_out},
                'composite_envelope':{'duration_seconds':times[-1],'fade_in_seconds':fade_in,'fade_out_seconds':fade_out},
                'combination':'minimum of smoothstep envelope weights, multiplied by intensity',
                'endpoint_weights':[envelope[0],envelope[-1]]}
        expected_curves = {n: [weight(p,n)*a for p,a in zip(face_poses,envelope)] for n in face_curves}
        if not all(math.isfinite(v) for vals in expected_curves.values() for v in vals):
            raise ValueError('Native sampled face contains nonfinite curve values')
        if not any(abs(v) > 1e-8 for vals in expected_curves.values() for v in vals):
            raise ValueError('Selected face window has no evaluated activity')
        controller.open_bracket('Compose real native face with protected body', False)
        try:
            if mode == 'static':
                controller.set_number_of_frames(u.FrameNumber(value=frames), False)
            to_write = sorted(set(face_bones) | (set(protected) if mode == 'static' else set()))
            for name in to_write:
                if name not in body_tracks:
                    controller.add_bone_track(u.Name(name), False)
                transforms = expected_face_bones[name] if name in face_bones else [static_body_bones[name]] * len(times)
                if not controller.set_bone_track_keys(u.Name(name), [v.translation for v in transforms],
                        [v.rotation for v in transforms], [v.scale3d for v in transforms], False):
                    raise RuntimeError('Could not write composite bone: ' + name)
            # Keep curve notifications inside the same bracket as bone writes.
            # Otherwise each change can rebuild compressed animation data.
            # Only replace approved face curves. Preserve unrelated body curves.
            for name in curve_scope['replace_body_curves']:
                u.AnimationLibrary.remove_curve(target, u.Name(name), False)
            for name in face_curves:
                u.AnimationLibrary.add_curve(target, u.Name(name), u.RawCurveTrackTypes.RCT_FLOAT, False)
                u.AnimationLibrary.add_float_curve_keys(target, u.Name(name), times, expected_curves[name])
            if mode == 'static':
                for name in sorted(unrelated_curves):
                    value = weight(static_pose, name)
                    u.AnimationLibrary.remove_curve(target, u.Name(name), False)
                    u.AnimationLibrary.add_curve(target, u.Name(name), u.RawCurveTrackTypes.RCT_FLOAT, False)
                    u.AnimationLibrary.add_float_curve_keys(target, u.Name(name), [0, times[-1]], [value,value])
        finally:
            controller.close_bracket(False)
        if not u.EditorAssetLibrary.save_loaded_asset(target, only_if_is_dirty=False):
            raise RuntimeError('Could not save composite')
        maxima = {'protected_bones': 0., 'face_bones': 0., 'face_curves': 0.}
        face_metric_maxima = {key:0. for key in FACE_TRANSFORM_TOLERANCES}
        face_metric_worst = {}
        for i, time in enumerate(times):
            actual = pose(target, time)
            if not curve_names_present(face_curves, [str(n) for n in u.AnimPoseExtensions.get_curve_names(actual)]):
                raise RuntimeError('Composite evaluator omitted required face curve names')
            expected_body = static_pose if mode == 'static' else pose(body, time)
            for name in protected:
                expected_transform = static_body_bones[name] if mode == 'static' else bone(expected_body,name)
                maxima['protected_bones'] = max(maxima['protected_bones'], transform_error(bone(actual,name), expected_transform))
            for name in face_bones:
                actual_transform, expected_transform = bone(actual,name), expected_face_bones[name][i]
                maxima['face_bones'] = max(maxima['face_bones'], transform_error(actual_transform, expected_transform))
                actual_values, expected_values = transform_values(actual_transform),transform_values(expected_transform)
                for metric,error in transform_metric_errors(actual_values,expected_values).items():
                    if metric not in face_metric_worst or error > face_metric_maxima[metric]:
                        face_metric_maxima[metric] = error
                        face_metric_worst[metric] = {'bone':name,'frame':i,'time_seconds':time,'error':error,
                            'expected_local_transform':expected_values,'actual_local_transform':actual_values}
            for name in face_curves:
                maxima['face_curves'] = max(maxima['face_curves'], abs(weight(actual,name)-expected_curves[name][i]))
        report['verification'] = {'all_frame_count': len(times), 'max_absolute_errors': maxima,
            'face_bone_metric_maxima':face_metric_maxima, 'face_bone_metric_worst':face_metric_worst,
            'face_bone_metric_tolerances':FACE_TRANSFORM_TOLERANCES,
            'face_bone_tolerance_basis':'Local translation 0.001 cm = 0.01 mm, shortest quaternion angle 0.2 degrees, unitless scale 0.0001. UE5.8 Sequencer stores FQuat4f as float Euler channels. Its near-pitch-90 singularity projection has unit-quaternion theoretical angular loss bound 2*acos(sqrt(2*float32(0.4999995)))=0.11535 degrees. Verified examples lost 0.050052 and 0.100910 degrees; storage prediction matched actual quaternion components within 9.42e-8. The fixed 0.2 degree engineering bound includes float conversion/trigonometry margin; larger loss must fail. This is actual representation loss, not display-only error. Evidence: research/ue_quaternion_storage_singularity_evidence_v1.json and research/ue_quaternion_storage_bound_v2.md. Legacy mixed-unit face_bones maximum is diagnostic only. Nonface threshold remains 0.0001.',
            'unrelated_curve_keys_identical': (mode != 'animation' or all(u.AnimationLibrary.get_float_keys(target,u.Name(n)) == v for n,v in original_unrelated_keys.items())),
            'face_curve_cycle_endpoint_max_difference': max(abs(v[-1]-v[0]) for v in expected_curves.values()),
            'duration_seconds': float(target.get_play_length()), 'fps': fps}
        if envelope_config is not None:
            report['verification']['face_bone_endpoint_neutral_max_error'] = max(transform_error(expected_face_bones[n][i],reference_neutral[n]) for n in face_bones for i in (0,-1))
        if maxima['protected_bones'] > 1e-4 or maxima['face_curves'] > 1e-4 or any(
                value > FACE_TRANSFORM_TOLERANCES[key] for key,value in face_metric_maxima.items()) or not report['verification']['unrelated_curve_keys_identical']:
            raise RuntimeError('Composite full-frame source comparison failed')
        report['sources_unchanged'] = all(asset_record(row['asset']) == row for row in source_records)
        report['new_dirty_packages_outside_target'] = sorted(p for p in
            {x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()} - dirty_before if p != destination)
        if not report['sources_unchanged'] or report['new_dirty_packages_outside_target']:
            raise RuntimeError('Source/shared asset preservation failed')
        report['success'] = True
    except Exception:
        report['error'] = traceback.format_exc()
        raise
    finally:
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print('DM_NATIVE_FACE_COMPOSITE='+json.dumps({'success': True, 'asset': destination, 'report_path':str(output)}))
    return report


if __name__ == '__main__':
    path = globals().get('DM_NATIVE_FACE_COMPOSE_TASK')
    if not isinstance(path, str):
        raise ValueError('Set DM_NATIVE_FACE_COMPOSE_TASK to task JSON path')
    run(json.loads(Path(path).read_text(encoding='utf-8')))
