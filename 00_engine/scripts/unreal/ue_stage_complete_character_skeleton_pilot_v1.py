"""Stage two isolated full characters with one existing hair each.

Only the new pilot map is saved. No existing hair, wardrobe, Skeleton,
material or CC project is changed. This is a static review entry.
"""
import importlib.util
import json
from pathlib import Path

import unreal

REPO = Path(__file__).resolve().parents[3]
RUN = REPO / '00_engine/outputs/unreal_character_import/complete_character_skeleton_pilot_20261005_v1'
LEVEL = '/Game/DataMake/Validation/CompleteCharacterSkeleton20261005/L_DM_CompleteCharacterSkeleton_Pilot_v001'
PREFIX = 'DM_CompleteCharacter_'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def path(asset):
    return asset.get_path_name() if asset else None


def spawn(label, cls, location, rotation=None):
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    found = [a for a in subsystem.get_all_level_actors() if a.get_actor_label() == label]
    if len(found) > 1:
        raise RuntimeError('Duplicate review actor ' + label)
    actor = found[0] if found else subsystem.spawn_actor_from_class(cls, location, rotation or unreal.Rotator())
    if actor is None:
        raise RuntimeError('Cannot create ' + label)
    actor.set_actor_label(label)
    actor.set_actor_location(location, False, False)
    actor.set_actor_rotation(rotation or unreal.Rotator(), False)
    return actor


def reference_bones(mesh):
    modifier = unreal.SkeletonModifier()
    if not modifier.set_skeletal_mesh(mesh):
        raise RuntimeError('Cannot read reference bones')
    return {str(n): (str(modifier.get_parent_name(n)), modifier.get_bone_transform(n, False))
            for n in modifier.get_all_bone_names()}


def compatible_for_following(body, follower):
    """Compare actual reference hierarchies/transforms, not Skeleton identity."""
    a, b = reference_bones(body), reference_bones(follower)
    if not set(b).issubset(a):
        raise RuntimeError('Follower has bones absent from leader')
    maximum_cm = 0.0
    for name, (parent, transform) in b.items():
        other_parent, other = a[name]
        if parent != other_parent:
            raise RuntimeError('Follower hierarchy differs at ' + name)
        maximum_cm = max(maximum_cm, (transform.translation - other.translation).length())
        qa, qb = transform.rotation, other.rotation
        dot = abs(sum(getattr(qa, k) * getattr(qb, k) for k in 'xyzw'))
        if abs(1.0 - dot) > 1e-6 or (transform.scale3d - other.scale3d).length() > 1e-5:
            raise RuntimeError('Follower reference rotation/scale differs at ' + name)
    if maximum_cm > 1e-4:
        raise RuntimeError('Follower reference translations differ: ' + str(maximum_cm) + ' cm')
    return {'compared_bones': len(b), 'max_translation_difference_cm': maximum_cm,
            'reference_compatible': True}


def main():
    registry = read(RUN / 'standard_candidate_registry.json')
    if len(registry['cases']) != 2:
        raise RuntimeError('Two audited imported characters required')
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    current = world.get_path_name().split('.')[0] if world else None
    if current != LEVEL:
        if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():
            raise RuntimeError('Current map has unsaved changes; preserve it before staging')
        if not (levels.load_level(LEVEL) if unreal.EditorAssetLibrary.does_asset_exist(LEVEL) else levels.new_level(LEVEL)):
            raise RuntimeError('Cannot open isolated review level')
    spec = importlib.util.spec_from_file_location('dm_complete_character_wardrobe_contract',
            Path(__file__).with_name('formal_wardrobe_registry_v1.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    inventory = module.read_registry()
    hair = next(h for h in inventory['hair_assets'] if h['hair_id'] == 'HAIR_HB1_02')
    report = {'success': False, 'level': LEVEL, 'scope': 'Static component and existing-hair assembly; no animation or human visual acceptance',
              'hair_registry': str(module.current_registry_path()), 'cases': []}
    for case in registry['cases']:
        audit = read(case['audit'])
        if not audit.get('success'):
            raise RuntimeError('Import audit is not successful')
        sex = case['sex']
        location = unreal.Vector(0, -100 if sex == 'female' else 100, 0)
        rotation = unreal.Rotator(yaw=-90)
        body_row = next(row for row in audit['meshes'] if row['role'] == 'body')
        body_mesh = unreal.load_asset(body_row['path'])
        body_actor = spawn(PREFIX + sex + '_Body', unreal.SkeletalMeshActor, location, rotation)
        body = body_actor.get_editor_property('skeletal_mesh_component')
        body.set_skeletal_mesh_asset(body_mesh)
        body.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        components = []
        items = [(row['role'], row['path'], False) for row in audit['meshes'] if row['role'] != 'body']
        items += [('Hair_' + str(i), row['path'], True) for i, row in enumerate(module.hair_fit(hair, sex)['meshes'])]
        for role, mesh_path, is_hair in items:
            mesh = unreal.load_asset(mesh_path)
            if not isinstance(mesh, unreal.SkeletalMesh):
                raise RuntimeError('Missing component mesh ' + mesh_path)
            compatibility = compatible_for_following(body_mesh, mesh)
            actor = spawn(PREFIX + sex + '_' + role, unreal.SkeletalMeshActor, location, rotation)
            actor.attach_to_actor(body_actor, '', unreal.AttachmentRule.SNAP_TO_TARGET,
                    unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET)
            component = actor.get_editor_property('skeletal_mesh_component')
            component.set_skeletal_mesh_asset(mesh)
            component.set_leader_pose_component(body, True)
            component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            if component.get_editor_property('leader_pose_component') != body:
                raise RuntimeError('Follower pose was not applied')
            components.append({'role': role, 'mesh': mesh_path, 'skeleton': path(mesh.get_editor_property('skeleton')),
                               'is_existing_hair': is_hair, 'leader_pose_readback': True, **compatibility})
        report['cases'].append({'sex': sex, 'body': body_row['path'], 'skeleton': audit['skeleton'],
                                'hair_id': hair['hair_id'], 'components': components})
    floor = spawn(PREFIX + 'Floor', unreal.StaticMeshActor, unreal.Vector(0, 0, -5))
    floor.set_actor_scale3d(unreal.Vector(6, 7, .05))
    floor.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
    wall = spawn(PREFIX + 'Wall', unreal.StaticMeshActor, unreal.Vector(-220, 0, 180))
    wall.set_actor_scale3d(unreal.Vector(.05, 7, 4))
    wall.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
    light = spawn(PREFIX + 'Key', unreal.DirectionalLight, unreal.Vector(0, 0, 300), unreal.Rotator(pitch=-35, yaw=-35))
    light.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property('intensity', .7)
    for name, x, yaw, intensity in [('Fill', 200, 180, 100), ('Back', -140, 0, 70)]:
        actor = spawn(PREFIX + name, unreal.RectLight, unreal.Vector(x, 0, 190), unreal.Rotator(yaw=yaw))
        actor.get_component_by_class(unreal.RectLightComponent).set_editor_properties({'intensity': float(intensity),
                'source_width': 350., 'source_height': 300.})
    volume = spawn(PREFIX + 'Exposure', unreal.PostProcessVolume, unreal.Vector())
    volume.set_editor_property('unbound', True)
    settings = volume.get_editor_property('settings')
    settings.set_editor_properties({'override_auto_exposure_method': True, 'auto_exposure_method': unreal.AutoExposureMethod.AEM_MANUAL,
            'override_auto_exposure_apply_physical_camera_exposure': True, 'auto_exposure_apply_physical_camera_exposure': False,
            'override_auto_exposure_bias': True, 'auto_exposure_bias': -.8})
    volume.set_editor_property('settings', settings)
    camera = spawn(PREFIX + 'Camera', unreal.CameraActor, unreal.Vector(480, 0, 130), unreal.Rotator(yaw=180))
    camera.get_component_by_class(unreal.CameraComponent).set_editor_properties({'field_of_view': 50., 'constrain_aspect_ratio': False})
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(unreal.Vector(480, 0, 130), unreal.Rotator(yaw=180))
    if not levels.save_current_level():
        raise RuntimeError('Cannot save pilot review map')
    report['success'] = True
    output = RUN / 'runtime/static_assembly_report.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('Complete-character static review level saved')
    return report


if globals().get('DM_COMPLETE_CHARACTER_STAGE'):
    main()
