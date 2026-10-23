"""Root-only, injected-Unreal preparation of camera-library expansion samples.

Import and inputs() are offline/read-only. prepare(unreal, selected_ids=None)
copies existing approved StudioV2 scenes; it never rebuilds characters or motion.
New assets are append-only; failed partial assets require explicit inspection.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import traceback
from datetime import datetime, timezone
from pathlib import Path

S = Path(__file__).resolve().parent
OUTPUT = Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import')
R = OUTPUT/'camera_library_expansion_20261010_v1'
OLD = OUTPUT/'camera_motion_pilot_20261009_v1'
A = '/Game/DataMake/Validation/CameraLibraryExpansion20261010'
OLD_A = '/Game/DataMake/Validation/CameraMotionPilot20261009'
CONTENT = Path('D:/UE/projects/datatry_02/Content')
PLAN = R/'expansion_plan_v1.json'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def pin(path):
    path = Path(path).resolve(strict=True)
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def check(record):
    if pin(record['path']) != record:
        raise RuntimeError('Pinned file changed: '+record['path'])


def save(path, value):
    path = Path(path).resolve()
    if not path.is_relative_to(R.resolve()):
        raise ValueError('Evidence must stay in the expansion run')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def module(name):
    spec = importlib.util.spec_from_file_location('_camera_library_'+name, S/(name+'.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def package(asset, suffix='.uasset'):
    name = asset.split('.')[0]
    if not re.fullmatch(r'/Game/[A-Za-z0-9_/]+', name):
        raise ValueError('Invalid project package path')
    return CONTENT/(name.removeprefix('/Game/')+suffix)


def inputs():
    manifest_path = OLD/'prepared_jobs_v2.json'
    manifest = read(manifest_path)
    if manifest.get('success') is not True or manifest.get('generation') != 3:
        raise ValueError('Expected successful v003 StudioV2 source manifest')
    jobs = {j['shot_id']: j for j in manifest['jobs']}
    receipt_pins = {Path(p['path']).name: p for p in manifest['sequence_receipts']}
    plan = read(PLAN)
    builder = module('ue_camera_sequence_builder_v1')
    rows = []
    seen = set()
    for shot in plan['shots']:
        sid = shot['shot_id']
        if not re.fullmatch(r'[A-Za-z0-9_]+', sid) or sid in seen:
            raise ValueError('Invalid or duplicate new shot id')
        seen.add(sid)
        builder.key_rows(shot)
        source_id = shot['source_shot_id']
        job = jobs[source_id]
        receipt_path = OLD/'sequences_v3'/(source_id+'.json')
        check(receipt_pins[receipt_path.name])
        receipt = read(receipt_path)
        if receipt.get('success') is not True or receipt['job'] != job:
            raise ValueError('Source receipt does not match source manifest')
        if not job['map'].startswith(OLD_A+'/MapsV2/') or not job['sequence'].startswith(OLD_A+'/SequencesV2/'):
            raise ValueError('Source must be the saved v003 StudioV2 scene')
        for record in receipt['asset_files']:
            check(record)
        animation = receipt['sequence_report']['animation_path']
        start = float(receipt['sequence_report']['source_start_seconds'])
        if float(shot.get('window_start_seconds', 0)) != start:
            raise ValueError('Expansion may not change the source animation window')
        if receipt['character_label'] != 'DM_CCWH_'+shot['sex']+'_Character':
            raise ValueError('Expansion sex differs from source character')
        # Carry original body/face composition provenance, including retiming.
        provenance = receipt['spec']['source_files'][0]
        check(provenance)
        original = read(provenance['path'])
        source_files = [pin(receipt_path), pin(package(job['map'], '.umap')),
                        pin(package(job['sequence'])), pin(package(animation)), provenance]
        rows.append({'shot': shot, 'source_job': job, 'source_receipt': receipt,
                     'animation_path': animation, 'source_files': source_files,
                     'composition_provenance': original.get('composition', original.get('sequence_report'))})
    if not rows:
        raise ValueError('No expansion shots')
    return {'plan': pin(PLAN), 'source_manifest': pin(manifest_path), 'rows': rows}


def clean(u):
    dirty = list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())
    dirty += list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    if dirty:
        raise RuntimeError('Dirty packages exist; refusing implicit save/discard: '+str([p.get_name() for p in dirty]))


def actors(u, label):
    all_actors = list(u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors())
    characters = [a for a in all_actors if a.get_actor_label() == label]
    cameras = [a for a in all_actors if a.get_actor_label() == 'DM_CCWH_Camera']
    if len(characters) != 1 or len(cameras) != 1:
        raise RuntimeError('Expected exactly the source character and camera')
    return characters[0], cameras[0]


def normalized(value, world_path):
    return json.loads(json.dumps(value).replace(world_path, '<CURRENT_WORLD>'))


def audit(u, helper, actor, animation):
    face = helper.audit_face_animation(u, actor, animation)
    if face['all_six_animation_data_readable'] is not True:
        raise RuntimeError('All six independent animation assets must be readable')
    return {'hair': helper.audit_hair_bounds(u, actor),
            'parent_bounds': helper.audit_component_parent_bounds(u, actor),
            'face': face, 'tags': [str(t) for t in actor.get_editor_property('tags')]}


def sequence_animation_audit(u, sequence, animation, start):
    rows = []
    tick = sequence.get_tick_resolution()
    for binding in sequence.get_bindings():
        for track in binding.get_tracks():
            if not isinstance(track, u.MovieSceneSkeletalAnimationTrack):
                continue
            for section in track.get_sections():
                params = section.get_editor_property('params')
                anim = params.get_editor_property('animation')
                rate = u.MovieSceneTimeWarpExtensions.to_fixed_play_rate(params.get_editor_property('play_rate'))
                offset = params.get_editor_property('first_loop_start_frame_offset').value
                if (anim is None or anim.get_path_name() != animation or abs(rate-1.) > 1e-8
                        or offset != round(start*tick.numerator/tick.denominator)
                        or section.get_start_frame() != 0 or section.get_end_frame() != 300):
                    raise RuntimeError('Saved skeletal track differs from source animation window')
                rows.append({'binding': binding.get_id().to_string(), 'animation': animation,
                             'play_rate': rate, 'source_offset_ticks': offset})
    if len(rows) != 6:
        raise RuntimeError('Expected exactly six independent animation tracks')
    return rows


def prepare(u, selected_ids=None):
    if Path(u.Paths.project_dir()).resolve() != CONTENT.parent.resolve():
        raise ValueError('Wrong UE project')
    queue = u.get_editor_subsystem(u.MoviePipelineQueueSubsystem)
    if queue.is_rendering() or queue.get_active_executor() is not None:
        raise RuntimeError('MRQ executor is active')
    clean(u)
    entry = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world().get_path_name()
    if not entry.startswith('/Game/') or not package(entry, '.umap').exists():
        raise RuntimeError('Entry world must already be saved for safe restoration')
    source = inputs()
    builder = module('ue_camera_sequence_builder_v1')
    helper = module('ue_camera_prepare_studio_v2')
    builder.ALLOWED_PREFIX = A+'/'
    helper.A = A
    code = [pin(__file__), pin(builder.__file__), pin(helper.__file__)]
    known = {r['shot']['shot_id'] for r in source['rows']}
    selected = known if selected_ids is None else set(selected_ids)
    if not selected <= known or not selected:
        raise ValueError('Unknown or empty selected shot ids')
    jobs = []
    restore = {'entry_world': entry, 'restored': False}
    try:
        for row in source['rows']:
            shot = row['shot']; sid = shot['shot_id']
            if sid not in selected:
                continue
            clean(u)
            map_path = A+'/MapsV2/L_'+sid+'_v001'
            seq_path = A+'/Sequences/LS_'+sid+'_v001'
            receipt_path = R/'sequences_v1'/(sid+'.json')
            spec = {'plan': source['plan'], 'source_manifest': source['source_manifest'],
                    'source_files': row['source_files'], 'source_shot_id': shot['source_shot_id'],
                    'code': code, 'map': map_path, 'sequence': seq_path,
                    'trajectory_sha256': shot['trajectory_sha256']}
            if receipt_path.exists():
                receipt = read(receipt_path)
                if receipt.get('success') is not True or receipt['spec'] != spec:
                    raise RuntimeError('Existing receipt differs; no overwrite')
                for record in receipt['asset_files']:
                    check(record)
                world = helper._load(u, map_path)
                actor, _ = actors(u, row['source_receipt']['character_label'])
                if audit(u, helper, actor, row['animation_path']) != receipt['saved_reload_audit']:
                    raise RuntimeError('Resumed scene audit changed')
                sequence = u.load_asset(seq_path)
                if helper.binding_readback(u, sequence, world) != receipt['binding_readback']:
                    raise RuntimeError('Resumed bindings changed')
                sequence_animation_audit(u, sequence, row['animation_path'], float(shot.get('window_start_seconds', 0)))
                jobs.append(receipt['job'])
                continue
            if u.EditorAssetLibrary.does_asset_exist(map_path) or u.EditorAssetLibrary.does_asset_exist(seq_path):
                raise RuntimeError('Partial assets exist; inspect before retry: '+sid)
            report = {'success': False, 'spec': spec}
            try:
                old_world = helper._load(u, row['source_job']['map'])
                old_actor, _ = actors(u, row['source_receipt']['character_label'])
                helper.A = OLD_A
                before = normalized(audit(u, helper, old_actor, row['animation_path']), old_world.get_path_name())
                helper.A = A
                clean(u)
                if not u.EditorLoadingAndSavingUtils.save_map(old_world, map_path):
                    raise RuntimeError('Could not copy source studio map')
                world = helper._load(u, map_path)  # SaveMap does NOT switch the editor world.
                actor, camera = actors(u, row['source_receipt']['character_label'])
                if normalized(audit(u, helper, actor, row['animation_path']), world.get_path_name()) != before:
                    raise RuntimeError('Copied scene changed character relationships')
                first = shot['frames'][0]
                camera.set_actor_location(u.Vector(*first['position']), False, False)
                camera.set_actor_rotation(u.Rotator(*first['rotation_pitch_yaw_roll']), False)
                camera.get_component_by_class(u.CameraComponent).set_field_of_view(first['horizontal_fov_degrees'])
                motion = u.load_asset(row['animation_path'])
                built = builder.build_sequence(u, shot, actor, camera, motion, seq_path)
                for name in sorted(helper.FACE_COMPONENTS-{'Body'}):
                    builder.add_animation_component_track(u, built['sequence'], built['actor_binding'],
                        helper.fresh_component(u, actor, name), motion,
                        source_start_seconds=float(shot.get('window_start_seconds', 0)))
                if not u.EditorAssetLibrary.save_loaded_asset(built['sequence'], False):
                    raise RuntimeError('Sequence save failed')
                u.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
                if not u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level():
                    raise RuntimeError('Expansion map save failed')
                clean(u)
                world = helper._load(u, map_path)
                actor, _ = actors(u, row['source_receipt']['character_label'])
                after = audit(u, helper, actor, row['animation_path'])
                if normalized(after, world.get_path_name()) != before:
                    raise RuntimeError('Saved/reloaded character differs from source')
                sequence = u.load_asset(seq_path)
                bindings = helper.binding_readback(u, sequence, world)
                tracks = sequence_animation_audit(u, sequence, row['animation_path'], float(shot.get('window_start_seconds', 0)))
                for record in row['source_files']+[source['plan'], source['source_manifest']]+code:
                    check(record)
                job = {'shot_id': sid, 'map': world.get_path_name(), 'sequence': sequence.get_path_name()}
                report.update({'schema': 'camera_library_prepared_shot_v1', 'success': True,
                    'job': job, 'sequence_report': built['report'], 'binding_readback': bindings,
                    'saved_reload_audit': after, 'six_skeletal_tracks': tracks,
                    'composition_provenance': row['composition_provenance'],
                    'source_unchanged': True, 'human_visual_acceptance': 'pending',
                    'asset_files': [pin(package(map_path, '.umap')), pin(package(seq_path))]})
                save(receipt_path, report); jobs.append(job)
                print('Prepared camera expansion '+sid)
            except Exception:
                report['error'] = traceback.format_exc()
                save(R/'prepare_failures'/(sid+'_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json'), report)
                raise
        for row in source['rows']:
            for record in row['source_files']:
                check(record)
        paths = [R/'sequences_v1'/(r['shot']['shot_id']+'.json') for r in source['rows']]
        if all(p.exists() for p in paths):
            receipts = [read(p) for p in paths]
            if not all(r.get('success') is True and r['spec']['plan'] == source['plan'] and r['spec']['code'] == code for r in receipts):
                raise RuntimeError('Aggregate contains stale receipts')
            for receipt in receipts:
                for record in receipt['asset_files']:
                    check(record)
            final = {'schema': 'camera_library_prepared_jobs_v1', 'success': True,
                     'plan': source['plan'], 'jobs': [r['job'] for r in receipts],
                     'sequence_receipts': [pin(p) for p in paths], 'code': code,
                     'source_unchanged': True, 'human_visual_acceptance': 'pending'}
            target = R/'prepared_jobs_v1.json'
            if target.exists():
                if read(target) != final:
                    raise RuntimeError('Existing aggregate differs')
            else:
                save(target, final)
    finally:
        # Never discard an unexpected dirty package to restore the old world.
        try:
            clean(u)
            restored = helper._load(u, entry)
            restore.update({'restored': restored.get_path_name() == entry, 'world': restored.get_path_name()})
        except Exception:
            restore['error'] = traceback.format_exc()
        save(R/'restore_receipts'/('restore_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json'), restore)
        if not restore['restored']:
            raise RuntimeError('Entry-world restoration blocked; preserved dirty state. '+restore.get('error', ''))
    return jobs
