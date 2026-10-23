"""Read-only live scene/binding provenance audit; owner: Scene Camera section 7.

Root explicitly calls main(unreal) while MRQ is idle. No asset save, actor edit,
or dirty-package discard is permitted. Loading saved owned maps is intentional.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re

RUN = Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/camera_motion_pilot_20261009_v1')
PROJECT = Path('D:/UE/projects/datatry_02')
ROOT = '/Game/DataMake/Validation/CameraMotionPilot20261009/'
MOUNTS = {'/Game/': PROJECT / 'Content', '/Engine/': Path('D:/UE/UE_5.8/Engine/Content'),
          '/InterchangeAssets/': Path('D:/UE/UE_5.8/Engine/Plugins/Interchange/Assets/Content')}
MANIFESTS = ('prepared_jobs_v1.json', 'paired_edit_prepared_v1.json', 'retime_prepared_jobs_v1.json')
FACE_COMPONENTS = ('Tongue', 'Eyes', 'Teeth', 'Tearline', 'EyeOcclusion')
ACTOR_COPY_PREFIX = 'DM_CCWH_SLOT_COPY_'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def pin(path):
    path = Path(path).resolve()
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return {'path': str(path), 'sha256': digest.hexdigest()}


def package_file(asset_path, extension='.uasset'):
    if not isinstance(asset_path, str) or not re.fullmatch(r'/[A-Za-z0-9_/]+(?:\.[A-Za-z0-9_]+)?', asset_path):
        raise ValueError('Not a saved asset package: ' + str(asset_path))
    package = asset_path.split('.')[0]
    mount = next((m for m in MOUNTS if package.startswith(m)), None)
    if mount is None or extension not in {'.uasset', '.umap'}:
        raise ValueError('Unsupported mount/extension: ' + asset_path)
    root = MOUNTS[mount].resolve()
    result = (root / (package[len(mount):] + extension)).resolve()
    if not result.is_relative_to(root):
        raise ValueError('Package escapes mount')
    return result


def load_jobs(run=RUN, revised=False):
    run = Path(run)
    documents = [read(run / name) for name in MANIFESTS]  # Missing is fatal.
    groups = [documents[0]['jobs'], [documents[1]['job']], documents[2]['jobs']]
    if [len(group) for group in groups] != [30, 1, 3]:
        raise ValueError('Expected exactly 30 primary, 1 paired and 3 supplemental jobs')
    jobs = [dict(job) for group in groups for job in group]
    for field in ('shot_id', 'map', 'sequence'):
        values = [str(job[field]).casefold() for job in jobs]
        if len(set(values)) != len(values):
            raise ValueError('Duplicate ' + field + ' in audit scope')
    for job in jobs:
        for field in ('map', 'sequence'):
            if not job[field].startswith(ROOT):
                raise ValueError('Audit job is outside owned pilot: ' + job[field])
            package_file(job[field], '.umap' if field == 'map' else '.uasset')
    plan = read(run / 'camera_motion_pilot_plan_v1.json')
    expected = {shot['shot_id']: shot['sex'] for shot in plan['shots']}
    if set(expected) != {job['shot_id'] for job in groups[0]}:
        raise ValueError('Primary job IDs do not match frozen plan')
    expected[documents[1]['job']['shot_id']] = documents[1]['shot']['sex']
    input_pins = [pin(run / name) for name in MANIFESTS] + [pin(run / 'camera_motion_pilot_plan_v1.json')]
    if revised:
        revised_path = run / 'prepared_jobs_v2.json'
        revised_manifest = read(revised_path)
        current_plan = run / 'camera_motion_pilot_plan_v3.json'
        if revised_manifest['plan'] != pin(current_plan):
            raise ValueError('Revised plan pin does not match current v3 camera-motion plan')
        supplied = revised_manifest['source_manifests']
        originals = {str(Path(p['path']).resolve()): p['sha256'] for p in input_pins[:3]}
        if len(supplied) != 3 or {str(Path(p['path']).resolve()): p['sha256'] for p in supplied} != originals:
            raise ValueError('Revised manifest must pin exactly the original three source manifests')
        revised_jobs = revised_manifest['jobs']
        if len(revised_jobs) != 34 or {j['shot_id'] for j in revised_jobs} != {j['shot_id'] for j in jobs}:
            raise ValueError('Revised jobs must retain exactly all original 34 shot IDs')
        revised_shots = read(current_plan)['shots']
        revised_sexes = {shot['shot_id']: shot['sex'] for shot in revised_shots}
        if revised_sexes != {shot['shot_id']: shot['sex'] for shot in plan['shots']}:
            raise ValueError('Revised main plan must preserve original primary IDs and sex scope')
        for field in ('map', 'sequence'):
            if len({str(j[field]).casefold() for j in revised_jobs}) != 34:
                raise ValueError('Duplicate revised ' + field)
        for job in revised_jobs:
            if not job['map'].startswith(ROOT + 'MapsV2/') or not job['sequence'].startswith(ROOT):
                raise ValueError('Revised maps must be new MapsV2; sequences must remain owned pilot assets')
            package_file(job['map'], '.umap')
            package_file(job['sequence'])
        jobs = [dict(job) for job in revised_jobs]
        input_pins += [pin(revised_path), pin(current_plan)]
    return jobs, expected, input_pins


def xyz(value):
    return [float(value.x), float(value.y), float(value.z)]


def pyr(value):
    return [float(value.pitch), float(value.yaw), float(value.roll)]


def identity_transform(location, rotation, scale, tolerance=1e-4):
    numbers = location + rotation + scale
    return (all(math.isfinite(v) for v in numbers)
            and all(abs(v) <= tolerance for v in location + rotation)
            and all(abs(v - 1) <= tolerance for v in scale))


def hair_bounds_readback(component, body, required=False):
    """Static saved-component policy only; does not prove every rendered frame."""
    parent = component.get_attach_parent()
    leader = component.get_editor_property('leader_pose_component')
    record = {'name': component.get_name(), 'component': component.get_path_name(),
              'attach_parent': parent.get_path_name() if parent else None,
              'leader_pose_component': leader.get_path_name() if leader else None,
              'parent_is_exact_body': parent == body, 'leader_is_exact_body': leader == body,
              'use_attach_parent_bound': bool(component.get_editor_property('use_attach_parent_bound')),
              'use_bounds_from_leader_pose_component': bool(component.get_editor_property('use_bounds_from_leader_pose_component')),
              'component_use_fixed_skel_bounds': bool(component.get_editor_property('component_use_fixed_skel_bounds')),
              'bounds_scale': float(component.get_editor_property('bounds_scale')),
              'forced_lod_model': int(component.get_editor_property('forced_lod_model')),
              'render_static': bool(component.get_editor_property('render_static')),
              'visible': bool(component.is_visible()),
              'hidden_in_game': bool(component.get_editor_property('hidden_in_game'))}
    record['revised_hair_bounds_policy_pass'] = bool(record['parent_is_exact_body']
        and record['leader_is_exact_body'] and record['use_attach_parent_bound'])
    if required and not record['revised_hair_bounds_policy_pass']:
        raise RuntimeError('Revised hair requires exact Body parent/leader and use_attach_parent_bound=True: '
                           + json.dumps(record, ensure_ascii=False))
    return record


def attached_component_bounds_readback(component, body, required=False):
    """Bounds policy is independent of animation strategy, including face tracks."""
    parent = component.get_attach_parent()
    leader = component.get_editor_property('leader_pose_component')
    record = {'name': component.get_name(), 'component': component.get_path_name(),
              'attach_parent': parent.get_path_name() if parent else None,
              'leader_pose_component': leader.get_path_name() if leader else None,
              'parent_is_exact_body': parent == body,
              'use_attach_parent_bound': bool(component.get_editor_property('use_attach_parent_bound')),
              'use_bounds_from_leader_pose_component': bool(component.get_editor_property('use_bounds_from_leader_pose_component')),
              'component_use_fixed_skel_bounds': bool(component.get_editor_property('component_use_fixed_skel_bounds')),
              'bounds_scale': float(component.get_editor_property('bounds_scale'))}
    record['parent_bounds_policy_applicable'] = component != body and parent == body
    record['parent_bounds_policy_pass'] = (not record['parent_bounds_policy_applicable']
                                           or record['use_attach_parent_bound'])
    if required and not record['parent_bounds_policy_pass']:
        raise RuntimeError('Revised populated non-Body component attached to Body requires parent bounds: '
                           + json.dumps(record, ensure_ascii=False))
    return record


def face_route_readback(component, actor_tags, required=False):
    name = component.get_name()
    if name not in FACE_COMPONENTS:
        raise ValueError('Expected one of the five independent face components')
    leader = component.get_editor_property('leader_pose_component')
    expected_tag = ACTOR_COPY_PREFIX + name
    record = {'name': name, 'component': component.get_path_name(),
              'leader_pose_component': leader.get_path_name() if leader else None,
              'leader_is_none': leader is None, 'expected_actor_route_tag': expected_tag,
              'actor_route_tag_present': expected_tag in actor_tags,
              'route_meaning': 'existing ConstructionScript clear-Leader branch; independent Sequence animation track'}
    record['independent_face_route_pass'] = record['leader_is_none'] and record['actor_route_tag_present']
    if required and not record['independent_face_route_pass']:
        raise RuntimeError('Revised independent face requires Leader=None and persistent actor route tag: '
                           + json.dumps(record, ensure_ascii=False))
    return record


def dirty(u):
    return {'maps': sorted(p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()),
            'content': sorted(p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages())}


def require_clean_maps(u, initial_content):
    observed = dirty(u)
    if observed['maps']:
        raise RuntimeError('Refusing to load/discard any dirty map: ' + repr(observed['maps']))
    if observed['content'] != initial_content:
        raise RuntimeError('Dirty content changed during read-only audit; inspect without saving/discarding')


def main(u=None, run=RUN, revised=False):
    if u is None:
        import unreal as u
    run = Path(run).resolve()
    if run != RUN.resolve():
        raise ValueError('Only this owned Run may receive the audit')
    output = run / ('scene_binding_audit_v2.json' if revised else 'scene_binding_audit_v1.json')
    if output.exists():
        raise ValueError('Audit receipt already exists; inspect instead of overwriting')
    report = {'schema': 'camera_scene_binding_audit_v1', 'created_at': datetime.now(timezone.utc).isoformat(),
              'success': False, 'jobs': [], 'errors': [], 'scope': '34 saved pilot scenes; direct meshes/skeletons/material parent chains, not recursive textures',
              'restore': {'attempted': False, 'success': False}, 'asset_pins': [],
              'revised_studio_v2': bool(revised)}
    start_map = None
    changed_map = False
    content_before = None
    package_cache = {}
    levels = None

    def asset_record(asset, extension='.uasset'):
        name = asset.get_path_name() if hasattr(asset, 'get_path_name') else str(asset)
        file = package_file(name, extension)
        key = str(file)
        if key not in package_cache:
            package_cache[key] = pin(file)
        return {'asset': name, 'package': package_cache[key]}

    def material_chain(material):
        chain, seen = [], set()
        while material is not None:
            name = material.get_path_name()
            if name in seen or len(chain) >= 32:
                raise RuntimeError('Cyclic/oversized material parent chain: ' + name)
            seen.add(name)
            chain.append(asset_record(material))
            material = material.get_editor_property('parent') if isinstance(material, u.MaterialInstance) else None
        return chain

    try:
        if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
            raise ValueError('Wrong Unreal project')
        subsystem = u.get_editor_subsystem(u.MoviePipelineQueueSubsystem)
        if subsystem.is_rendering() or subsystem.get_active_executor() is not None:
            raise RuntimeError('MRQ must be idle')
        jobs, expected_sex, report['input_manifests'] = load_jobs(run, revised=revised)
        report['expected_job_count'] = len(jobs)
        baseline = read(run / 'stage_recovery_v1.json')['original_restored_package']
        report['review_map_recovery_baseline'] = baseline
        report['review_map_before'] = pin(baseline['path'])
        if report['review_map_before'] != baseline:
            raise RuntimeError('Original review map differs from post-recovery baseline')
        before = dirty(u)
        report['dirty_before'] = before
        content_before = before['content']
        require_clean_maps(u, content_before)
        editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
        levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
        actorsub = u.get_editor_subsystem(u.EditorActorSubsystem)
        start_map = editor.get_editor_world().get_path_name().split('.')[0]
        report['entry_map'] = start_map
        if not start_map.startswith(ROOT):
            raise RuntimeError('Enter from a saved owned pilot map, not a user review map')
        for job in jobs:
            require_clean_maps(u, content_before)
            row = {'shot_id': job['shot_id'], 'success': False, 'map': asset_record(job['map'], '.umap'),
                   'sequence': asset_record(job['sequence']), 'bindings': [], 'components': []}
            report['jobs'].append(row)
            changed_map = True  # Also restore if LoadLevel only partially succeeds.
            if not levels.load_level(job['map'].split('.')[0]):
                raise RuntimeError('Could not load scene: ' + job['map'])
            world = editor.get_editor_world()
            if world.get_path_name().split('.')[0] != job['map'].split('.')[0]:
                raise RuntimeError('Wrong current world after explicit LoadLevel')
            characters = [a for a in actorsub.get_all_level_actors() if a.get_actor_label() in
                          {'DM_CCWH_female_Character', 'DM_CCWH_male_Character'}]
            visible = [a for a in characters if not bool(a.get_editor_property('hidden'))]
            if len(visible) != 1:
                raise RuntimeError('Expected exactly one non-hidden character')
            actor = visible[0]
            sex = 'female' if actor.get_actor_label() == 'DM_CCWH_female_Character' else 'male'
            if job['shot_id'] in expected_sex and sex != expected_sex[job['shot_id']]:
                raise RuntimeError('Visible character sex differs from plan')
            row.update(sex=sex, actor=actor.get_path_name(), actor_transform={
                'location': xyz(actor.get_actor_location()), 'rotation_pitch_yaw_roll': pyr(actor.get_actor_rotation()),
                'scale': xyz(actor.get_actor_scale3d())})
            tr = row['actor_transform']
            if not identity_transform(tr['location'], tr['rotation_pitch_yaw_roll'], tr['scale']):
                raise RuntimeError('Actor transform differs from planner identity coordinates')
            bodies = [c for c in actor.get_components_by_class(u.SkeletalMeshComponent) if c.get_name() == 'Body']
            if len(bodies) != 1:
                raise RuntimeError('Expected exactly one Body')
            body = bodies[0]
            actor_tags = [str(tag) for tag in actor.get_editor_property('tags')]
            row['actor_copy_route_tags'] = sorted(tag for tag in actor_tags if tag.startswith(ACTOR_COPY_PREFIX))
            face_components = [c for c in actor.get_components_by_class(u.SkeletalMeshComponent)
                               if c.get_name() in FACE_COMPONENTS and c.get_skeletal_mesh_asset() is not None]
            if revised and sorted(c.get_name() for c in face_components) != sorted(FACE_COMPONENTS):
                raise RuntimeError('Revised scene requires all five populated independent face components')
            row['face_route_readback'] = [face_route_readback(c, actor_tags, required=revised) for c in face_components]
            transform = body.get_relative_transform()
            rel = {'location': xyz(transform.translation), 'rotation_pitch_yaw_roll': pyr(transform.rotation.rotator()),
                   'scale': xyz(transform.scale3d)}
            row['body_relative_transform'] = rel
            if not identity_transform(rel['location'], rel['rotation_pitch_yaw_roll'], rel['scale']):
                raise RuntimeError('Body relative transform differs from planner identity coordinates')
            row['body_identity_mesh'] = asset_record(body.get_skeletal_mesh_asset())
            row['hair_bounds_readback'] = [hair_bounds_readback(c, body, required=revised)
                for c in actor.get_components_by_class(u.SkeletalMeshComponent)
                if c.get_name().startswith('HairPart') and c.get_skeletal_mesh_asset() is not None]
            row['attached_component_bounds_readback'] = [attached_component_bounds_readback(c, body, required=revised)
                for c in actor.get_components_by_class(u.SkeletalMeshComponent)
                if c != body and c.get_skeletal_mesh_asset() is not None]
            for component in actor.get_components_by_class(u.MeshComponent):
                if not component.is_visible() or component.get_editor_property('hidden_in_game'):
                    continue
                if isinstance(component, u.SkeletalMeshComponent):
                    mesh = component.get_skeletal_mesh_asset()
                elif isinstance(component, u.StaticMeshComponent):
                    mesh = component.get_editor_property('static_mesh')
                else:
                    raise RuntimeError('Unsupported visible mesh component: ' + component.get_path_name())
                if mesh is None:
                    continue
                entry = {'name': component.get_name(), 'path': component.get_path_name(), 'mesh': asset_record(mesh),
                         'materials': [{'slot': i, 'chain': material_chain(material)}
                                       for i, material in enumerate(component.get_materials())]}
                if isinstance(component, u.SkeletalMeshComponent):
                    entry['skeleton'] = asset_record(mesh.get_editor_property('skeleton'))
                row['components'].append(entry)
            if not any(c['name'] == 'Body' for c in row['components']):
                raise RuntimeError('Body is not a visible populated mesh')
            sequence = u.load_asset(job['sequence'])
            if not isinstance(sequence, u.LevelSequence):
                raise RuntimeError('Expected LevelSequence')
            body_bindings = 0
            for binding in sequence.get_bindings():
                objects = list(u.MovieSceneSequenceExtensions.locate_bound_objects(sequence, binding, world))
                paths = [obj.get_path_name() for obj in objects]
                if len(objects) != 1 or not all(path.startswith(world.get_path_name() + ':') for path in paths):
                    raise RuntimeError('Binding missing, ambiguous or outside current world: ' + str(binding.get_display_name()))
                is_body = objects[0] == body
                body_bindings += int(is_body)
                row['bindings'].append({'id': str(binding.get_id()), 'name': str(binding.get_display_name()),
                                        'objects': paths, 'is_exact_current_body': is_body})
                for track in binding.get_tracks():
                    if isinstance(track, u.MovieSceneSkeletalAnimationTrack):
                        if objects[0] == actor:
                            raise RuntimeError('Animation incorrectly bound to whole modular actor')
                        for section in track.get_sections():
                            animation = section.get_editor_property('params').get_editor_property('animation')
                            asset_record(animation)
            if body_bindings != 1:
                raise RuntimeError('Expected one binding of the exact current scene Body')
            require_clean_maps(u, content_before)
            row['success'] = True
        report['all_jobs_passed'] = len(report['jobs']) == len(jobs) and all(row['success'] for row in report['jobs'])
    except Exception as exc:
        report['errors'].append(str(exc))
    finally:
        if changed_map and start_map and levels is not None:
            report['restore']['attempted'] = True
            try:
                require_clean_maps(u, content_before)
                if not levels.load_level(start_map):
                    raise RuntimeError('Entry pilot map restore failed')
                current = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world().get_path_name().split('.')[0]
                if current != start_map:
                    raise RuntimeError('Restored world does not match entry')
                require_clean_maps(u, content_before)
                report['restore']['success'] = True
            except Exception as exc:
                report['errors'].append('Restore not safe/completed; no dirty state discarded: ' + str(exc))
        elif start_map:
            report['restore']['success'] = True
        try:
            if 'review_map_recovery_baseline' in report:
                report['review_map_after'] = pin(report['review_map_recovery_baseline']['path'])
                if report['review_map_after'] != report['review_map_recovery_baseline']:
                    raise RuntimeError('Review map post-recovery baseline changed')
            report['asset_pins'] = list(package_cache.values())
            report['all_read_package_pins_unchanged'] = all(pin(p['path']) == p for p in package_cache.values())
            if not report['all_read_package_pins_unchanged']:
                raise RuntimeError('A read package changed during audit')
        except Exception as exc:
            report['errors'].append(str(exc))
        report['success'] = bool(report.get('all_jobs_passed') and report['restore']['success'] and not report['errors'])
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
        with output.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
    return report


if __name__ == '__main__':
    result = main()
    print(json.dumps({'success': result['success'], 'checked_jobs': len(result['jobs']), 'errors': result['errors']}))
