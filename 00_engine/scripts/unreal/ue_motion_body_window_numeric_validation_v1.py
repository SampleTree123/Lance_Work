"""Read-only physical-unit validation of the isolated male walk window.

Keeps the original stricter mixed-component failure unchanged. Bounds are
explicitly derived from the local UE 5.8 Sequencer/ControlRig tolerance paths;
this is not a claim of bit-exact or pixel-exact reproduction.
Owner: SCENE_CAMERA_SEQUENCE.md, motion/portrait/location pilot 2026-10-11.
"""
from pathlib import Path
import hashlib
import json
import math

import ue_motion_body_window_v1 as window

RUN = window.RUN
LIMITS = {'translation_cm': .00035, 'rotation_degrees': .025, 'scale_abs': .00001}
ENGINE_SOURCES = [
    ('D:/UE/UE_5.8/Engine/Plugins/Animation/AnimationData/Source/AnimationData/Private/AnimSequencerController.cpp', '2787-2942', 'SetBoneCurveKeys uses 1e-4 per-channel constancy and stores constant defaults.'),
    ('D:/UE/UE_5.8/Engine/Plugins/Animation/ControlRig/Source/ControlRig/Public/Rigs/RigHierarchyElements.h', '476-480', 'FRigComputedTransform::Equals uses 1e-4 translation/quaternion/scale component tolerance.'),
    ('D:/UE/UE_5.8/Engine/Plugins/Animation/ControlRig/Source/ControlRig/Private/Rigs/RigHierarchy.cpp', '5454-5460', 'Non-forced nearly-equal hierarchy transforms skip updates.'),
    ('D:/UE/UE_5.8/Engine/Plugins/Animation/AnimationData/Source/AnimationData/Private/AnimSequencerDataModel.cpp', '357-360', 'Deprecated raw track getter returns an empty placeholder; not a valid absence-of-track test.')]


def pin(path):
    path = Path(path)
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def run():
    import unreal as u
    helper = window.module('ue_compose_native_face_body_v1')
    face = window.module('ue_native_face_panel_five_second_v1')
    path = RUN / 'body_windows/walk_male_v1.json'
    diag_path = RUN / 'body_windows/walk_male_numeric_diagnosis_v1.json'
    output = RUN / 'body_windows/walk_male_physical_validation_v1.json'
    if output.exists():
        raise FileExistsError(output)
    old = json.loads(path.read_text(encoding='utf-8'))
    diagnostic = json.loads(diag_path.read_text(encoding='utf-8'))
    assert old['success'] is False and 'Mapped source comparison failed' in old['error']
    assert old['sources_unchanged'] and not old['dirty_sources'] and not old['new_dirty_packages_outside_target']
    assert diagnostic['source_report']['sha256'] == pin(path)['sha256']
    assert Path(u.Paths.project_dir()).resolve() == window.PROJECT.resolve()
    source, target = [u.load_asset(p) for p in (old['original_body']['asset'], old['destination'])]
    entry, _ = face.accepted_faces()[('male', 'idle')]
    mesh = u.load_asset(entry['reference_mesh'])
    assert isinstance(source, u.AnimSequence) and isinstance(target, u.AnimSequence)
    assert source.get_skeleton() == target.get_skeleton() == mesh.get_editor_property('skeleton')
    records = [helper.asset_record(a.get_path_name()) for a in (source, target, mesh, source.get_skeleton())]
    assert records == diagnostic['source_target_records'], 'Source/target changed after failed-window diagnosis'
    before = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    assert not before & {r['asset'].split('.')[0] for r in records}
    source_names = {str(n) for n in source.data_model_interface.get_bone_track_names()}
    target_names = {str(n) for n in target.data_model_interface.get_bone_track_names()}
    assert source_names == target_names and len(source_names) == 108
    assert not helper.FACE_BONES & target_names
    assert abs(float(target.get_play_length()) - 10.) < 1e-6
    target_count = target.data_model_interface.get_number_of_frames()
    assert int(getattr(target_count, 'value', target_count)) == 600
    modifier = u.SkeletonModifier(); assert modifier.set_skeletal_mesh(mesh)
    names = sorted(str(n) for n in modifier.get_all_bone_names()); assert len(names) == 118
    options = u.AnimPoseEvaluationOptions()
    options.set_editor_properties({'evaluation_type': u.AnimDataEvalType.SOURCE, 'should_retarget': False,
        'extract_root_motion': False, 'incorporate_root_motion_into_pose': True, 'evaluate_curves': True, 'optional_skeletal_mesh': mesh})
    curves = [str(n) for n in u.AnimationLibrary.get_animation_curve_names(source, u.RawCurveTrackTypes.RCT_FLOAT)]
    assert set(curves) == {str(n) for n in u.AnimationLibrary.get_animation_curve_names(target, u.RawCurveTrackTypes.RCT_FLOAT)}
    maxima = {k: 0. for k in LIMITS}
    worst = {}
    mixed_max = root_max = curve_max = 0.
    failures = []
    def pose(asset, t):
        value = u.AnimPoseExtensions.get_anim_pose_at_time(asset, t, options)
        assert u.AnimPoseExtensions.is_valid(value)
        assert set(names) <= {str(n) for n in u.AnimPoseExtensions.get_bone_names(value)}
        assert helper.curve_names_present(curves, [str(n) for n in u.AnimPoseExtensions.get_curve_names(value)])
        return value
    for index, (time, source_time) in enumerate(zip(old['mapping']['times'], old['mapping']['source_times'])):
        expected, actual = pose(source, source_time), pose(target, time)
        for name in names:
            source_transform = u.AnimPoseExtensions.get_bone_pose(expected, u.Name(name), u.AnimPoseSpaces.LOCAL)
            target_transform = u.AnimPoseExtensions.get_bone_pose(actual, u.Name(name), u.AnimPoseSpaces.LOCAL)
            a, b = helper.transform_values(target_transform), helper.transform_values(source_transform)
            metric = helper.transform_metric_errors(a, b)
            component = helper.transform_error(target_transform, source_transform)
            mixed_max = max(mixed_max, component)
            if name == 'root': root_max = max(root_max, component)
            for key, error in metric.items():
                if error > maxima[key]:
                    maxima[key] = error
                    worst[key] = {'bone': name, 'frame': index, 't': time, 'source_t': source_time, 'error': error}
            if any(metric[k] > LIMITS[k] for k in LIMITS):
                failures.append({'bone': name, 'frame': index, 'errors': metric})
        for name in curves:
            a, b = [float(u.AnimPoseExtensions.get_curve_weight(p, u.Name(name))) for p in (actual, expected)]
            assert math.isfinite(a) and math.isfinite(b)
            curve_max = max(curve_max, abs(a-b))
    assert before == {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    assert records == [helper.asset_record(a.get_path_name()) for a in (source, target, mesh, source.get_skeleton())]
    result = {'schema': 'motion_window_physical_validation_v1', 'success': not failures and root_max <= 1e-4 and curve_max <= 1e-4,
        'original_failed_report': pin(path), 'numeric_diagnosis': pin(diag_path), 'original_failure_unchanged': True,
        'source_target_records': records, 'destination': old['destination'], 'mapping': old['mapping'],
        'all_frame_count': 601, 'bone_count': 118, 'track_count': 108, 'curve_count': len(curves),
        'limits': LIMITS, 'maximum_errors': maxima, 'worst': worst, 'failures': failures,
        'legacy_mixed_component_max': mixed_max, 'legacy_mixed_component_gate_pass': mixed_max <= 1e-4,
        'root_component_max': root_max, 'root_component_limit': 1e-4, 'curve_max': curve_max, 'curve_limit': 1e-4,
        'engine_precision_basis': [dict(pin(p), lines=lines, reason=reason) for p, lines, reason in ENGINE_SOURCES],
        'tolerance_derivation': {'translation': '2*sqrt(3)*1e-4 cm = 0.00034641 cm, rounded to 0.00035 cm; two native per-component near-equality stages.',
            'rotation': 'Four quaternion components each differing by 1e-4 give norm difference <=2e-4, angle about 0.022918 degrees; 0.025 includes float/Euler conversion margin.',
            'scale': '1e-5 retained as a stricter scale-specific check; not expanded to the engine default.'},
        'sources_unchanged': True, 'target_unchanged': True, 'dirty_packages_unchanged': True,
        'human_naturalness_acceptance': 'pending',
        'scope': 'Read-only bounded local-pose numerical equivalence for this male walk asset. Not bit-exact, mesh-silhouette, pixel-exact, or user visual acceptance.'}
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({'report': str(output), 'success': result['success'], 'maximum_errors': maxima, 'root_component_max': root_max}))
    return result


if __name__ == '__main__':
    run()
