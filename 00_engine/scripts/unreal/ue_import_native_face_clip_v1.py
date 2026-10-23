"""Import an isolated native CC FBX as animation only on a current shared rig.

Root dispatch only. Set DM_NATIVE_FACE_IMPORT_TASK to a JSON path before runpy.
No map loads, source edits, actor edits, existing-asset replacement or source
Skeleton save. Reports imported curves and sampled facial/body-support poses;
successful import is not visual acceptance or body/face composition acceptance.
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
ASSET_ROOT = '/Game/DataMake/Validation/NativeFaceLibrary20261007'
SKELETONS = {sex: '/Game/DataMake/Validation/CFDNativeBatch4020261006/SharedSkeletons/SKEL_CFDShared_' + title + '_v1'
             for sex, title in (('female', 'Female'), ('male', 'Male'))}
DEFAULT_PIPELINE = '/Interchange/Pipelines/DefaultFBXOBJAssetsPipeline'


def file_record(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def validate_task(task):
    if not isinstance(task, dict):
        raise ValueError('Expected task object')
    sex, clip = task.get('sex'), task.get('clip_id')
    if sex not in SKELETONS or not isinstance(clip, str) or not re.fullmatch('[a-z][a-z0-9_]{0,63}', clip):
        raise ValueError('Invalid sex or clip_id')
    source = task['source_fbx']
    if not isinstance(source, dict) or not re.fullmatch('[0-9a-f]{64}', source.get('sha256', '')):
        raise ValueError('Source FBX must have a lowercase SHA256')
    path = Path(source['path']).resolve()
    if not path.is_relative_to(Path('D:/UE').resolve()) or path.suffix.lower() != '.fbx':
        raise ValueError('Source FBX must be inside D:/UE')
    if file_record(path)['sha256'] != source['sha256']:
        raise ValueError('Source FBX SHA changed')
    output = Path(task['report_path']).resolve()
    if not output.is_relative_to(RUN.resolve()) or output.suffix.lower() != '.json' or output.exists():
        raise ValueError('Report must be a new JSON file under the current run')
    return sex, clip, path, output


def object_record(obj):
    return {'path': obj.get_path_name(), 'class': obj.get_class().get_name()}


def transform_record(value):
    return {'translation': [float(value.translation.x), float(value.translation.y), float(value.translation.z)],
            'rotation': [float(value.rotation.x), float(value.rotation.y), float(value.rotation.z), float(value.rotation.w)],
            'scale': [float(value.scale3d.x), float(value.scale3d.y), float(value.scale3d.z)]}


def inspect_animation(u, animation):
    model = animation.data_model_interface
    frames_value = model.get_number_of_frames()
    frames = int(getattr(frames_value, 'value', frames_value))
    rate = model.get_frame_rate()
    tracks = [str(name) for name in model.get_bone_track_names()]
    curves = []
    for name in u.AnimationLibrary.get_animation_curve_names(animation, u.RawCurveTrackTypes.RCT_FLOAT):
        times, values = u.AnimationLibrary.get_float_keys(animation, name)
        times, values = [float(v) for v in times], [float(v) for v in values]
        if len(times) != len(values) or not all(math.isfinite(v) for v in times + values):
            raise ValueError('Invalid imported curve data: ' + str(name))
        curves.append({'name': str(name), 'key_count': len(values),
                       'min': min(values, default=0), 'max': max(values, default=0),
                       'active': any(abs(v) > 1e-8 for v in values),
                       'varying': max(values, default=0) - min(values, default=0) > 1e-8,
                       'times': times, 'values': values})
    sampled_frames = sorted(set(round(frames * index / 12) for index in range(13)))
    selected_bones = [name for name in tracks if name in ('root', 'pelvis', 'head', 'neck_01', 'neck_02')
                      or any(part in name.casefold() for part in ('facial', 'jaw', 'eye', 'teeth', 'tongue'))]
    poses = []
    for frame in sampled_frames:
        values = u.AnimationLibrary.get_bone_poses_for_frame(animation, [u.Name(n) for n in selected_bones], frame, False)
        if len(values) != len(selected_bones):
            raise ValueError('Imported bone pose readback length mismatch')
        poses.append({'frame': frame, 'bones': {name: transform_record(value) for name, value in zip(selected_bones, values)}})
    return {**object_record(animation), 'skeleton': animation.get_skeleton().get_path_name(),
            'duration_seconds': float(animation.get_play_length()), 'number_of_frames': frames,
            'frame_rate': {'numerator': int(rate.numerator), 'denominator': int(rate.denominator)},
            'bone_track_names': tracks, 'curve_count': len(curves), 'curves': curves,
            'active_curve_names': [r['name'] for r in curves if r['active']],
            'sampled_bone_poses': poses,
            'pose_sampling_scope': 'Thirteen evenly spaced frames including endpoints; not all-frame activity proof.'}


def run(task):
    import unreal as u
    sex, clip, source, output = validate_task(task)
    if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
        raise ValueError('Native face import requires datatry_02')
    destination = ASSET_ROOT + '/' + sex + '/' + clip
    pipeline_path = destination + '/ImportPipeline'
    if u.EditorAssetLibrary.list_assets(destination, recursive=True, include_folder=False):
        raise ValueError('Refusing to reuse populated native face destination: ' + destination)
    skeleton = u.load_asset(SKELETONS[sex])
    if not isinstance(skeleton, u.Skeleton):
        raise ValueError('Current shared Skeleton unavailable')
    skeleton_package = SKELETONS[sex]
    skeleton_file = PROJECT / 'Content' / (skeleton_package.removeprefix('/Game/') + '.uasset')
    skeleton_before = file_record(skeleton_file)
    dirty_before = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if skeleton_package in dirty_before:
        raise ValueError('Current shared Skeleton is already dirty')
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {'success': False, 'task': task, 'source': file_record(source), 'destination': destination,
              'skeleton_before': skeleton_before, 'scope': 'Native animation import/readback only; no visual or composition acceptance.'}
    try:
        u.EditorAssetLibrary.make_directory(destination)
        pipeline = u.EditorAssetLibrary.duplicate_asset(DEFAULT_PIPELINE, pipeline_path)
        if pipeline is None:
            raise RuntimeError('Unable to create isolated animation import pipeline')
        mesh = pipeline.get_editor_property('mesh_pipeline')
        common = pipeline.get_editor_property('common_skeletal_meshes_and_animations_properties')
        animation_pipeline = pipeline.get_editor_property('animation_pipeline')
        material = pipeline.get_editor_property('material_pipeline')
        texture = material.get_editor_property('texture_pipeline')
        settings = [
            (mesh, 'import_skeletal_meshes', False), (mesh, 'import_static_meshes', False),
            (mesh, 'create_physics_asset', False), (mesh, 'physics_asset', None),
            (common, 'skeleton', skeleton), (common, 'try_auto_select_skeleton', False),
            (common, 'import_only_animations', True), (common, 'use_t0_as_ref_pose', False),
            (common, 'add_curve_metadata_to_skeleton', False),
            (animation_pipeline, 'import_animations', True), (animation_pipeline, 'import_bone_tracks', True),
            (animation_pipeline, 'animation_range', u.InterchangeAnimationRange.TIMELINE),
            (animation_pipeline, 'use30_hz_to_bake_bone_animation', False),
            (animation_pipeline, 'custom_bone_animation_sample_rate', 0),
            (animation_pipeline, 'import_custom_attribute', True),
            (animation_pipeline, 'remove_curve_redundant_keys', False),
            (animation_pipeline, 'do_not_import_curve_with_zero', False),
            (material, 'import_materials', False), (texture, 'import_textures', False),
        ]
        for obj, name, value in settings:
            obj.set_editor_property(name, value)
            if obj.get_editor_property(name) != value:
                raise RuntimeError('Import setting readback failed: ' + name)
        report['pipeline_settings'] = {name: (value.get_path_name() if isinstance(value, u.Object) else str(value)) for _, name, value in settings}
        if not u.EditorAssetLibrary.save_loaded_asset(pipeline, only_if_is_dirty=False):
            raise RuntimeError('Could not save isolated import pipeline')
        before_paths = set(u.EditorAssetLibrary.list_assets(destination, recursive=True, include_folder=False))
        manager = u.InterchangeManager.get_interchange_manager_scripted()
        source_data = manager.create_source_data(str(source))
        if source_data is None:
            raise RuntimeError('Could not create source data')
        params = u.ImportAssetParameters()
        params.set_editor_property('is_automated', True)
        params.set_editor_property('force_show_dialog', False)
        params.set_editor_property('replace_existing', False)
        params.set_editor_property('destination_name', 'A_Native_' + clip)
        params.set_editor_property('override_pipelines', [u.SoftObjectPath(pipeline.get_path_name())])
        world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        cvar = 'Interchange.FeatureFlags.Import.FBX'
        previous_cvar = u.SystemLibrary.get_console_variable_int_value(cvar)
        try:
            if previous_cvar != 1:
                u.SystemLibrary.execute_console_command(world, cvar + ' 1')
            if u.SystemLibrary.get_console_variable_int_value(cvar) != 1:
                raise RuntimeError('Could not enable Interchange FBX for this import')
            returned = manager.import_asset(destination, source_data, params) or []
        finally:
            if previous_cvar != 1:
                u.SystemLibrary.execute_console_command(world, cvar + ' ' + str(previous_cvar))
        report['returned_objects'] = [object_record(obj) for obj in returned]
        after_paths = set(u.EditorAssetLibrary.list_assets(destination, recursive=True, include_folder=False))
        new_assets = [u.load_asset(path) for path in sorted(after_paths - before_paths)]
        report['new_assets'] = [object_record(obj) for obj in new_assets if obj is not None]
        if not new_assets or any(not isinstance(obj, u.AnimSequence) for obj in new_assets):
            raise RuntimeError('Expected only new AnimSequence assets; unexpected outputs retained for diagnosis')
        if any(obj.get_skeleton() != skeleton for obj in new_assets):
            raise RuntimeError('Imported animation has wrong shared Skeleton')
        report['animations'] = [inspect_animation(u, obj) for obj in new_assets]
        if not any(r['active_curve_names'] for r in report['animations']):
            raise RuntimeError('Native performance import has no active Morph curves')
        for obj in new_assets:
            if not u.EditorAssetLibrary.save_loaded_asset(obj, only_if_is_dirty=False):
                raise RuntimeError('Could not save imported animation')
        dirty_after = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
        report['new_dirty_packages_outside_destination'] = sorted(p for p in dirty_after - dirty_before if not p.startswith(destination + '/'))
        report['skeleton_after'] = file_record(skeleton_file)
        report['source_unchanged'] = file_record(source) == report['source']
        report['skeleton_file_unchanged'] = report['skeleton_after'] == skeleton_before
        if not report['source_unchanged'] or not report['skeleton_file_unchanged'] or report['new_dirty_packages_outside_destination']:
            raise RuntimeError('Import affected protected source/shared assets; see report')
        report['success'] = True
    except Exception:
        report['error'] = traceback.format_exc()
        raise
    finally:
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print('DM_NATIVE_FACE_IMPORT=' + json.dumps({'success': True, 'report_path': str(output), 'animation_count': len(report['animations'])}))
    return report


if __name__ == '__main__':
    task_path = globals().get('DM_NATIVE_FACE_IMPORT_TASK')
    if not isinstance(task_path, str):
        raise ValueError('Set DM_NATIVE_FACE_IMPORT_TASK to a task JSON path')
    run(json.loads(Path(task_path).read_text(encoding='utf-8')))
