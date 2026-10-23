"""Import one new full-length CC motion and verify its isolated BodyOnly copy.

Root dispatch: runpy.run_path(__file__, init_globals={
    'DM_MOTION_LIBRARY_EXPANSION_TASK': '<new task JSON>'}, run_name='__main__')
No CC, map, actor, shared-Skeleton save, retiming, crop or panel integration.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import traceback

SCRIPTS = Path(__file__).absolute().parent
PROJECT = Path('D:/UE/projects/datatry_02')
WORKSPACE = Path('D:/UE')
RUN = Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/motion_library_expansion_20261009_v1')
ROOT = '/Game/DataMake/Validation/MotionLibraryExpansion20261009'
SELECTION = RUN.parent / 'native_face_five_second_20261008_v1/accepted_face_selection_v1.json'
DEFAULT_PIPELINE = '/Interchange/Pipelines/DefaultFBXOBJAssetsPipeline'
SKELETONS = {s: '/Game/DataMake/Validation/CFDNativeBatch4020261006/SharedSkeletons/SKEL_CFDShared_' + s.title() + '_v1' for s in ('female', 'male')}
REFERENCE_MESHES = {s: '/Game/DataMake/Validation/CFDNativeBatch4020261006/' + actor + '/Meshes/cc_base_body.cc_base_body' for s, actor in (('female', 'CFD40_AF_001'), ('male', 'CFD40_AM_001'))}
TOLERANCE = 1e-4


def load_helper(filename):
    spec = importlib.util.spec_from_file_location('_dm_motion_expansion_' + Path(filename).stem, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CONTRACT = load_helper('ue_compose_native_face_body_v1.py')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def file_record(path):
    path = Path(path).resolve()
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}


def asset_record(asset):
    package = asset.get_path_name().split('.')[0]
    if not package.startswith('/Game/'):
        raise ValueError('Expected /Game asset')
    return {'asset': asset.get_path_name(), **file_record(PROJECT / 'Content' / (package[6:] + '.uasset'))}


def validate_task(task):
    required = {'sex', 'name', 'source_fbx', 'report_path'}
    if not isinstance(task, dict) or not required <= task.keys() or task.keys() - required - {'asset_root', 'candidate_id'}:
        raise ValueError('Unexpected/missing task fields; time or import overrides are not supported')
    sex, name = task['sex'], task['name']
    if sex not in SKELETONS or not isinstance(name, str) or not re.fullmatch('[a-z][a-z0-9_]{0,63}', name):
        raise ValueError('Invalid sex/name')
    root = task.get('asset_root', ROOT)
    if not isinstance(root, str) or not (root == ROOT or root.startswith(ROOT + '/')) or not re.fullmatch('/Game/(?:[A-Za-z0-9_]+/)*[A-Za-z0-9_]+', root):
        raise ValueError('Asset root must stay inside the new motion expansion root')
    source = task['source_fbx']
    if not isinstance(source, dict) or not {'path', 'sha256'} <= source.keys() or source.keys() - {'path', 'sha256', 'bytes'} or not isinstance(source['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', source['sha256']):
        raise ValueError('Require source FBX path and lowercase SHA256')
    path = Path(source['path']).resolve()
    if not path.is_relative_to(WORKSPACE.resolve()) or path.suffix.lower() != '.fbx':
        raise ValueError('FBX must be inside D:/UE')
    record = file_record(path)
    if record['sha256'] != source['sha256'] or ('bytes' in source and (isinstance(source['bytes'], bool) or source['bytes'] != record['bytes'])):
        raise ValueError('Source FBX changed')
    output = Path(task['report_path']).resolve()
    if not output.is_relative_to(RUN.resolve()) or output.suffix.lower() != '.json' or output.exists():
        raise ValueError('Report must be a new JSON file in the motion expansion run')
    return path, output, root + '/' + sex + '/' + name


def frame_grid(numerator, denominator, frames, duration):
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 for v in (numerator, denominator, frames, duration)):
        raise ValueError('Require finite positive frame grid')
    if any(int(v) != v for v in (numerator, denominator, frames)):
        raise ValueError('Frame rate and frame count must be integral')
    fps = numerator / denominator
    if not math.isclose(frames / fps, duration, rel_tol=0, abs_tol=1e-5):
        raise ValueError('Duration does not match the original frame grid')
    return fps, [i / fps for i in range(int(frames) + 1)]


def classify_body_curves(curves, allowed_morphs):
    source = CONTRACT.curve_name_index(curves, 'imported motion curves')
    allowed = CONTRACT.curve_name_index(allowed_morphs, 'verified CC Morph inventory')
    if not allowed:
        raise ValueError('Missing verified CC Morph inventory')
    remove, preserve, unknown = [], [], []
    for key, actual in source.items():
        if CONTRACT.excluded_body_control_curve(actual):
            preserve.append(actual)
        elif key in allowed:
            remove.append(actual)
        else:
            unknown.append(actual)
    if unknown:
        raise ValueError('Unclassified curves require explicit review: ' + ', '.join(sorted(unknown)))
    return sorted(remove), sorted(preserve)


def body_partition(parents, tracks):
    face = CONTRACT.select_face_bones(parents)
    track_index = CONTRACT.curve_name_index(tracks, 'bone tracks')
    if len(parents) != 118 or set(track_index) != {n.casefold() for n in parents}:
        raise ValueError('Imported source must contain exactly the audited 118 bone tracks')
    protected = sorted(set(parents) - set(face))
    if len(protected) != 108 or not CONTRACT.FORBIDDEN_FACE_BONES <= set(protected):
        raise ValueError('Head/neck/root/body partition differs')
    return face, protected, track_index


def approved_curve_inventory(sex):
    selection = read(SELECTION)
    matches = [r for r in selection['entries'] if r['sex'] == sex and r['face_id'] == 'idle' and r.get('selection_accepted') is True]
    if selection.get('selection_accepted') is not True or len(matches) != 1:
        raise ValueError('Verified same-sex CC curve inventory unavailable')
    evidence = matches[0]['evidence']['composition_report']
    if file_record(evidence['path'])['sha256'] != evidence['sha256']:
        raise ValueError('Verified CC profile report changed')
    report = read(evidence['path'])
    if report.get('success') is not True or report['task']['reference_mesh'] != REFERENCE_MESHES[sex]:
        raise ValueError('Wrong reference mesh/profile proof')
    return report['task']['allowed_face_curve_names'], evidence


def curve_keys(u, animation, name):
    times, values = u.AnimationLibrary.get_float_keys(animation, u.Name(name))
    times, values = list(map(float, times)), list(map(float, values))
    if len(times) != len(values) or not all(math.isfinite(v) for v in times + values):
        raise ValueError('Nonfinite/mismatched curve keys: ' + name)
    return {'times': times, 'values': values}


def inspect(u, animation):
    model = animation.data_model_interface
    rate = model.get_frame_rate()
    count = model.get_number_of_frames()
    frames = int(getattr(count, 'value', count))
    duration = float(animation.get_play_length())
    fps, times = frame_grid(int(rate.numerator), int(rate.denominator), frames, duration)
    curves = [str(n) for n in u.AnimationLibrary.get_animation_curve_names(animation, u.RawCurveTrackTypes.RCT_FLOAT)]
    CONTRACT.curve_name_index(curves)
    # UE5.8 AnimCurveTypes.h1048 marks RCT_Vector Hidden. It is not exposed
    # to Python; AnimationBlueprintLibrary.cpp185-210 only supports Float
    # and Transform in GetAnimationCurveNames. No independent vector bank.
    other = {'transform': [str(n) for n in u.AnimationLibrary.get_animation_curve_names(
        animation, u.RawCurveTrackTypes.RCT_TRANSFORM)]}
    if any(other.values()):
        raise ValueError('Unexpected transform curves: ' + repr(other))
    return {'asset': animation.get_path_name(), 'duration_seconds': duration, 'number_of_frames': frames,
            'frame_rate': {'numerator': int(rate.numerator), 'denominator': int(rate.denominator)}, 'fps': fps,
            'bone_track_names': [str(n) for n in model.get_bone_track_names()],
            'float_curves': {name: curve_keys(u, animation, name) for name in curves},
            'other_curve_types': other}, times


def protected_state(u, records, dirty_before, destination):
    dirty_after = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    changed = [r['path'] for r in records if file_record(r['path'])['sha256'] != r['sha256']]
    source_dirty = sorted(r['asset'].split('.')[0] for r in records if 'asset' in r and r['asset'].split('.')[0] in dirty_after)
    outside = sorted(p for p in dirty_after - dirty_before if not p.startswith(destination + '/'))
    return {'source_files_unchanged': not changed, 'changed_source_files': changed,
            'dirty_protected_assets': source_dirty, 'new_dirty_packages_outside_destination': outside}


def require_protected(state):
    if not state['source_files_unchanged'] or state['dirty_protected_assets'] or state['new_dirty_packages_outside_destination']:
        raise RuntimeError('Protected FBX/shared assets changed or became dirty')


def source_evaluation_options(u, mesh=None):
    options = u.AnimPoseEvaluationOptions()
    options.set_editor_properties({'evaluation_type': u.AnimDataEvalType.SOURCE, 'should_retarget': False,
        'extract_root_motion': False, 'incorporate_root_motion_into_pose': True, 'evaluate_curves': True,
        'optional_skeletal_mesh': mesh})
    return options


def shared_face_reference(u, animation, face_bones):
    # AnimSequence.cpp:1795-1829 initializes missing tracks from authored/Skeleton
    # ref transforms when retargeting is disabled. AnimPose.cpp:636-655 instead
    # caches mesh ref transforms when OptionalSkeletalMesh is supplied. Therefore
    # the body comparison keeps its mesh, while this baseline explicitly omits it.
    pose = u.AnimPoseExtensions.get_anim_pose_at_time(animation, 0., source_evaluation_options(u))
    if (not u.AnimPoseExtensions.is_valid(pose)
            or not set(face_bones) <= {str(n) for n in u.AnimPoseExtensions.get_bone_names(pose)}):
        raise RuntimeError('Shared Skeleton reference omitted required facial bones')
    result = {name: u.AnimPoseExtensions.get_ref_bone_pose(pose, u.Name(name), u.AnimPoseSpaces.LOCAL)
              for name in face_bones}
    if not all(math.isfinite(v) for transform in result.values() for v in CONTRACT.transform_values(transform)):
        raise RuntimeError('Nonfinite shared Skeleton reference transform')
    return result


def run(task):
    source, output, destination = validate_task(task)
    allowed_curves, curve_proof = approved_curve_inventory(task['sex'])
    import unreal as u
    if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
        raise ValueError('Wrong UE project')
    if u.EditorAssetLibrary.list_assets(destination, recursive=True, include_folder=False):
        raise ValueError('Refusing populated import destination')
    sex = task['sex']
    skeleton, mesh = u.load_asset(SKELETONS[sex]), u.load_asset(REFERENCE_MESHES[sex])
    if not isinstance(skeleton, u.Skeleton) or not isinstance(mesh, u.SkeletalMesh) or mesh.get_editor_property('skeleton') != skeleton:
        raise ValueError('Same-sex shared Skeleton/reference mesh unavailable')
    records = [file_record(source), asset_record(skeleton), asset_record(mesh)]
    dirty_before = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if any(r['asset'].split('.')[0] in dirty_before for r in records if 'asset' in r):
        raise ValueError('Shared sources already dirty; refusing import')
    modifier = u.SkeletonModifier()
    if not modifier.set_skeletal_mesh(mesh):
        raise RuntimeError('Could not inspect reference hierarchy')
    parents = {str(n): str(modifier.get_parent_name(n)) for n in modifier.get_all_bone_names()}
    # Inspection only: never commit SkeletonModifier changes.
    if len(parents) != 118:
        raise ValueError('Reference hierarchy must contain 118 bones')
    pipeline_path, raw_path, body_path = (destination + suffix for suffix in ('/ImportPipeline', '/A_' + task['name'] + '_Source', '/A_' + task['name'] + '_BodyOnly'))
    report = {'schema_version': 1, 'success': False, 'task': task, 'destination': destination,
              'source_fbx': records[0], 'protected_sources': records[1:], 'curve_inventory_proof': curve_proof,
              'source_animation': raw_path, 'body_only_animation': body_path,
              'scope': 'Full original-rate import and body-only numeric validation; no five-second crop, visual acceptance or panel integration.',
              'retimed': False, 'cropped': False, 'looped_or_padded': False}
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        u.EditorAssetLibrary.make_directory(destination)
        pipeline = u.EditorAssetLibrary.duplicate_asset(DEFAULT_PIPELINE, pipeline_path)
        if pipeline is None:
            raise RuntimeError('Could not create isolated pipeline')
        helper = load_helper('ue_modular_outfit_motion_validation_v1.py')
        helper.configure_animation_pipeline(pipeline, skeleton)
        common = pipeline.get_editor_property('common_skeletal_meshes_and_animations_properties')
        animation_pipeline = pipeline.get_editor_property('animation_pipeline')
        settings = [(common, 'use_t0_as_ref_pose', False), (common, 'add_curve_metadata_to_skeleton', False),
                    (animation_pipeline, 'import_bone_tracks', True), (animation_pipeline, 'animation_range', u.InterchangeAnimationRange.TIMELINE),
                    (animation_pipeline, 'use30_hz_to_bake_bone_animation', False), (animation_pipeline, 'custom_bone_animation_sample_rate', 0),
                    (animation_pipeline, 'import_custom_attribute', True), (animation_pipeline, 'remove_curve_redundant_keys', False),
                    (animation_pipeline, 'do_not_import_curve_with_zero', False)]
        for obj, key, value in settings:
            obj.set_editor_property(key, value)
            if obj.get_editor_property(key) != value:
                raise RuntimeError('Import setting readback failed: ' + key)
        report['pipeline_settings'] = {key: str(value) for _, key, value in settings}
        if not u.EditorAssetLibrary.save_loaded_asset(pipeline, only_if_is_dirty=False):
            raise RuntimeError('Could not save new pipeline')
        before = set(u.EditorAssetLibrary.list_assets(destination, recursive=True, include_folder=False))
        manager = u.InterchangeManager.get_interchange_manager_scripted()
        source_data = manager.create_source_data(str(source))
        if source_data is None:
            raise RuntimeError('Could not create FBX source data')
        parameters = u.ImportAssetParameters()
        parameters.set_editor_properties({'is_automated': True, 'force_show_dialog': False, 'replace_existing': False,
                                         'destination_name': raw_path.rsplit('/', 1)[1],
                                         'override_pipelines': [u.SoftObjectPath(pipeline.get_path_name())]})
        world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        cvar = 'Interchange.FeatureFlags.Import.FBX'
        old_cvar = u.SystemLibrary.get_console_variable_int_value(cvar)
        try:
            if old_cvar != 1:
                u.SystemLibrary.execute_console_command(world, cvar + ' 1')
            if u.SystemLibrary.get_console_variable_int_value(cvar) != 1:
                raise RuntimeError('Interchange FBX could not be enabled')
            try:
                manager.import_asset(destination, source_data, parameters)
            except RuntimeError as exc:
                # Existing importer reports some auxiliary tracks this way.
                # Acceptance still requires exactly one 118-track same-rig asset.
                report['interchange_diagnostic'] = str(exc)
        finally:
            if old_cvar != 1:
                u.SystemLibrary.execute_console_command(world, cvar + ' ' + str(old_cvar))
        added = sorted(set(u.EditorAssetLibrary.list_assets(destination, recursive=True, include_folder=False)) - before)
        imported = [u.load_asset(p) for p in added]
        report['imported_assets'] = added
        if len(imported) != 1 or not isinstance(imported[0], u.AnimSequence):
            raise RuntimeError('Expected exactly one new animation and no other imported asset')
        raw = imported[0]
        if raw.get_skeleton() != skeleton or raw.get_editor_property('additive_anim_type') != u.AdditiveAnimationType.AAT_NONE:
            raise RuntimeError('Imported source has wrong Skeleton or additive animation')
        if raw.get_path_name().split('.')[0] != raw_path:
            if u.EditorAssetLibrary.does_asset_exist(raw_path) or not u.EditorAssetLibrary.rename_asset(raw.get_path_name().split('.')[0], raw_path):
                raise RuntimeError('Could not give new imported animation its isolated name')
            raw = u.load_asset(raw_path)
        imported_info, times = inspect(u, raw)
        report['imported'] = imported_info
        face, protected, track_index = body_partition(parents, imported_info['bone_track_names'])
        remove_curves, preserve_curves = classify_body_curves(imported_info['float_curves'], allowed_curves)
        report.update(removed_face_tracks=face, protected_body_bones=protected,
                      removed_face_curves=remove_curves, preserved_body_control_curves=preserve_curves)
        require_protected(protected_state(u, records, dirty_before, destination))
        if not u.EditorAssetLibrary.save_loaded_asset(raw, only_if_is_dirty=False):
            raise RuntimeError('Could not save new raw motion')
        raw_record = asset_record(raw)
        records.append(raw_record)
        target = u.EditorAssetLibrary.duplicate_asset(raw_path, body_path)
        if not isinstance(target, u.AnimSequence):
            raise RuntimeError('Could not create isolated BodyOnly copy')
        target.controller.open_bracket('Remove only facial support tracks and classified facial curves', False)
        try:
            for name in face:
                if not target.controller.remove_bone_track(u.Name(track_index[name.casefold()]), False):
                    raise RuntimeError('Could not remove facial track: ' + name)
            # Match existing BodyOnly logic for typed attributes; retain ordinary
            # head/neck control curves and verify their exact keys below.
            report['removed_attribute_count'] = target.controller.remove_all_attributes(False)
        finally:
            target.controller.close_bracket(False)
        for name in remove_curves:
            u.AnimationLibrary.remove_curve(target, u.Name(name), False)
        target_info, target_times = inspect(u, target)
        report['body_only'] = target_info
        target_tracks = CONTRACT.curve_name_index(target_info['bone_track_names'])
        if set(target_tracks) != {n.casefold() for n in protected} or target.get_skeleton() != skeleton:
            raise RuntimeError('BodyOnly did not retain exactly the 108 protected tracks')
        if target_info['frame_rate'] != imported_info['frame_rate'] or target_times != times or not math.isclose(target_info['duration_seconds'], imported_info['duration_seconds'], rel_tol=0, abs_tol=1e-6):
            raise RuntimeError('BodyOnly timing changed')
        remaining_index = CONTRACT.curve_name_index(target_info['float_curves'])
        if set(remaining_index) != {n.casefold() for n in preserve_curves}:
            raise RuntimeError('BodyOnly curve removal/preservation mismatch')
        for name in preserve_curves:
            if target_info['float_curves'][remaining_index[name.casefold()]] != imported_info['float_curves'][name]:
                raise RuntimeError('Protected body curve keys changed: ' + name)
        if not u.EditorAssetLibrary.save_loaded_asset(target, only_if_is_dirty=False):
            raise RuntimeError('Could not save new BodyOnly')
        options = source_evaluation_options(u, mesh)
        face_reference = shared_face_reference(u, target, face)
        maxima = {'protected_bones': 0., 'preserved_curves': 0., 'face_reference_bones': 0.}
        worst = {}

        def pose(asset, time, required_curves):
            value = u.AnimPoseExtensions.get_anim_pose_at_time(asset, time, options)
            if not u.AnimPoseExtensions.is_valid(value) or not set(parents) <= {str(n) for n in u.AnimPoseExtensions.get_bone_names(value)} or not CONTRACT.curve_names_present(required_curves, [str(n) for n in u.AnimPoseExtensions.get_curve_names(value)]):
                raise RuntimeError('SOURCE evaluation omitted required bone/curve; no zero fallback allowed')
            return value

        def checked_bone(value, name, reference=False):
            method = u.AnimPoseExtensions.get_ref_bone_pose if reference else u.AnimPoseExtensions.get_bone_pose
            transform = method(value, u.Name(name), u.AnimPoseSpaces.LOCAL)
            if not all(math.isfinite(v) for v in CONTRACT.transform_values(transform)):
                raise RuntimeError('Nonfinite SOURCE bone transform')
            return transform

        for index, time in enumerate(times):
            expected = pose(raw, time, imported_info['float_curves'])
            actual = pose(target, time, preserve_curves)
            for name in parents:
                source_bone = checked_bone(expected, name)
                actual_bone = checked_bone(actual, name)
                kind = 'face_reference_bones' if name in face else 'protected_bones'
                baseline = face_reference[name] if name in face else source_bone
                error = CONTRACT.transform_error(actual_bone, baseline)
                if error > maxima[kind]:
                    maxima[kind], worst[kind] = error, {'bone': name, 'frame': index, 'time_seconds': time}
            for name in preserve_curves:
                a, b = (float(u.AnimPoseExtensions.get_curve_weight(p, u.Name(name))) for p in (actual, expected))
                if not all(math.isfinite(v) for v in (a, b)):
                    raise RuntimeError('Nonfinite protected curve')
                error = abs(a - b)
                if error > maxima['preserved_curves']:
                    maxima['preserved_curves'], worst['preserved_curves'] = error, {'curve': name, 'frame': index, 'time_seconds': time}
        report['verification'] = {'all_frame_count': len(times), 'source_bone_count': 118,
            'protected_body_bone_count': 108, 'removed_face_track_count': 10,
            'duration_seconds': target_info['duration_seconds'], 'fps': target_info['fps'],
            'time_mapping': 'target_time == original_imported_source_time; entire inclusive native frame grid',
            'max_absolute_errors': maxima, 'worst': worst, 'tolerance': TOLERANCE,
            'preserved_curve_keys_identical': True, 'face_tracks_absent': True,
            'face_local_pose_is_reference': maxima['face_reference_bones'] <= TOLERANCE,
            'face_reference_baseline': {'asset': skeleton.get_path_name(),
                'method': 'SOURCE evaluation with optional_skeletal_mesh=None; get_ref_bone_pose LOCAL',
                'body_comparison_optional_skeletal_mesh': mesh.get_path_name(),
                'reason': 'Missing tracks use shared Skeleton fallback; mesh reference proportions can differ.'}}
        if any(v > TOLERANCE for v in maxima.values()):
            raise RuntimeError('BodyOnly all-frame source/reference verification failed')
        report.update(source_asset_record=raw_record, body_only_asset_record=asset_record(target))
        duration = target_info['duration_seconds']
        report['eligible_for_native_five_seconds'] = duration >= 5 - 1e-6
        report['duration_selection_reason'] = 'native_duration_at_least_five_seconds' if report['eligible_for_native_five_seconds'] else 'short_native_motion_excluded_no_retime_loop_or_padding'
        report['success'] = True
    except Exception:
        report['error'] = traceback.format_exc()
        raise
    finally:
        try:
            report.update(protected_state(u, records, dirty_before, destination))
            require_protected(report)
        except Exception:
            report['success'] = False
            report['protection_error'] = traceback.format_exc()
        with output.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
    if not report['success']:
        raise RuntimeError('Motion expansion protection check failed; inspect new report')
    print('DM_MOTION_LIBRARY_EXPANSION=' + json.dumps({'report': str(output), 'success': True,
        'body_only_animation': body_path, 'eligible_for_native_five_seconds': report['eligible_for_native_five_seconds']}))
    return report


if __name__ == '__main__':
    task_path = globals().get('DM_MOTION_LIBRARY_EXPANSION_TASK')
    if not isinstance(task_path, str):
        raise ValueError('Set DM_MOTION_LIBRARY_EXPANSION_TASK to a new task JSON path')
    run(read(task_path))
