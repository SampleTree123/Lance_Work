"""Isolated review of complete characters, retained outfits/hairs and BodyOnly.

No CC operation, mesh reimport, source Skeleton edit or formal acceptance.
Execute with DM_CC_REVIEW_REQUEST through the companion controller.
"""
import hashlib
import importlib.util
import json
import math
import os
import sys
import uuid
from pathlib import Path
from datetime import datetime, timezone

import unreal

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
REPO = SCRIPTS.parents[2]
ROOT = REPO / '00_engine/outputs/unreal_character_import/complete_character_wardrobe_hair_review_20261005_v1'
SOURCE = REPO / '00_engine/outputs/unreal_character_import/complete_character_skeleton_pilot_20261005_v1/standard_candidate_registry.json'
LEVEL = '/Game/DataMake/Validation/CompleteCharacterWardrobeHair20261005/L_DM_CompleteCharacter_WardrobeHair_Review_v001'
ASSET_ROOT = LEVEL.rsplit('/', 1)[0]
PREFIX = 'DM_CCWH_'
MARKER = 'DM_CC_WARDROBE_HAIR_REVIEW='
THROTTLE = '_dm_ccwh_original_cpu_throttle'
CACHE = '_dm_ccwh_review_cache'
REFRESH = '_dm_ccwh_refresh_handle'
YAW = {'front': -90., 'side': 0., 'back': 90., 'threequarter': -45.}
DEFAULT = {'female_outfit': 1, 'male_outfit': 1, 'hair_index': 2,
           'action_index': 0, 'view': 'front', 'focus': 'both', 'framing': 'full', 'playing': False}


def module(name):
    spec = importlib.util.spec_from_file_location('ccwh_' + name, SCRIPTS / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


CONTRACT = module('complete_character_review_contract_v1')
REFERENCE = module('ue_stage_complete_character_skeleton_pilot_v1')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(name, value):
    ROOT.mkdir(parents=True, exist_ok=True)
    p = ROOT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    temporary = p.with_name(p.name + '.partial')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(p)


def now():
    return datetime.now(timezone.utc).isoformat()


def path(value):
    return value.get_path_name() if value else None


def vector(value):
    return [value.x, value.y, value.z]


def actors():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def world_path():
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    return w.get_path_name().split(':')[0].split('.')[0] if w else None


def find(label):
    rows = [a for a in actors().get_all_level_actors() if a.get_actor_label() == label]
    if len(rows) > 1:
        raise RuntimeError('Duplicate review actor: ' + label)
    return rows[0] if rows else None


def assert_legacy_review_unmigrated():
    """Reject legacy writes only when an owned fixed-slot actor is in this map.

    A built Blueprint, saved migration receipt, or an unrelated label is not
    proof of migration. Inspect the current map's actual actor identity. One
    owned actor is enough to protect a partially migrated pair as well.
    """
    if world_path() != LEVEL:
        return
    for candidate in actors().get_all_level_actors():
        label = candidate.get_actor_label()
        if label not in (PREFIX + 'female_Character', PREFIX + 'male_Character'):
            continue
        if 'DM_CCWH_FIXED_SLOT_V1' not in [str(tag) for tag in candidate.get_editor_property('tags')]:
            continue
        sex = 'Female' if label == PREFIX + 'female_Character' else 'Male'
        name = f'BP_DM_Complete_{sex}_FixedSlots_v001'
        expected_class = ASSET_ROOT + '/FixedSlotRuntime/' + name + '.' + name + '_C'
        if path(candidate.get_class()) == expected_class:
            raise RuntimeError('当前关卡已存在迁移后的固定槽位角色，旧审查入口不能重新显示散装角色。'
                               '请使用 open_complete_character_slot_review_v1.ps1。')


def actor(label, cls, location, rotation=None):
    found = find(label)
    if found is None:
        found = actors().spawn_actor_from_class(cls, location, rotation or unreal.Rotator())
        if found is None:
            raise RuntimeError('Cannot create review actor: ' + label)
        found.set_actor_label(label)
    return found


def component(a):
    return a.get_editor_property('skeletal_mesh_component')


def cache():
    if not hasattr(unreal, CACHE):
        setattr(unreal, CACHE, {'compatibility': {}, 'animations': {}})
    return getattr(unreal, CACHE)


def compatibility(body_mesh, follower):
    key = path(body_mesh) + '|' + path(follower)
    saved = cache()['compatibility']
    if key in saved:
        return saved[key]
    a, b = REFERENCE.reference_bones(body_mesh), REFERENCE.reference_bones(follower)
    extra = sorted(set(b) - set(a))
    if not set(a).intersection(b):
        raise RuntimeError('Follower has no common body bones')
    maximum_cm = maximum_degrees = maximum_scale = 0.
    different = []
    for name, (parent, transform) in b.items():
        values = vector(transform.translation) + vector(transform.scale3d) + [getattr(transform.rotation, n) for n in 'xyzw']
        if not all(math.isfinite(v) for v in values):
            raise RuntimeError('Non-finite reference transform: ' + name)
        if name not in a:
            continue
        other_parent, other = a[name]
        if parent != other_parent:
            raise RuntimeError('Follower common-bone hierarchy differs: ' + path(follower) + ':' + name)
        delta = (transform.translation - other.translation).length()
        dot = abs(sum(getattr(transform.rotation, n) * getattr(other.rotation, n) for n in 'xyzw'))
        # Normalize quaternions to avoid turning rounding noise into angles.
        norm_a = math.sqrt(sum(getattr(transform.rotation, n) ** 2 for n in 'xyzw'))
        norm_b = math.sqrt(sum(getattr(other.rotation, n) ** 2 for n in 'xyzw'))
        angle = math.degrees(2 * math.acos(min(1., dot / max(1e-30, norm_a * norm_b))))
        scale = (transform.scale3d - other.scale3d).length()
        maximum_cm, maximum_degrees, maximum_scale = max(maximum_cm, delta), max(maximum_degrees, angle), max(maximum_scale, scale)
        if delta > 1e-4 or angle > .001 or scale > 1e-5:
            different.append(name)
    result = {'mapped_bones': len(set(a).intersection(b)), 'hierarchy_match': True,
              'extra_reference_bones': extra, 'follow_mode': 'copy_pose' if extra else 'leader_pose',
              'max_reference_translation_cm': maximum_cm, 'max_reference_rotation_degrees': maximum_degrees,
              'max_reference_scale_delta': maximum_scale, 'different_reference_bones': different,
              'reference_exact': not different and not extra,
              'scope': 'prototype_following_only_visual_fit_pending'}
    saved[key] = result
    return result


def normalize_request(request, catalog):
    previous = read(ROOT / 'current_case.json').get('request', {}) if (ROOT / 'current_case.json').exists() else {}
    result = {**DEFAULT, **previous, **request}
    result.setdefault('action', 'show')
    for sex in ('female', 'male'):
        value = result[sex + '_outfit'] = int(result[sex + '_outfit'])
        if not 0 <= value <= len(catalog[sex + '_outfits']):
            raise ValueError('Outfit index outside catalogue: ' + sex)
    result['hair_index'] = int(result['hair_index'])
    result['action_index'] = int(result['action_index'])
    if not 0 <= result['hair_index'] <= len(catalog['hairs']):
        raise ValueError('Hair index outside catalogue')
    if not 0 <= result['action_index'] <= min(len(v) for v in catalog['actions_by_sex'].values()):
        raise ValueError('Action index outside catalogue')
    if result['view'] not in YAW or result['focus'] not in ('both', 'female', 'male') or result['framing'] not in ('full', 'head'):
        raise ValueError('Invalid camera selection')
    if result['action_index'] == 0:
        result['playing'] = False
    return result


def prepare(request, catalog):
    cases = {c['sex']: c for c in read(SOURCE)['cases']}
    prepared = {}
    for sex in ('female', 'male'):
        case = cases[sex]
        body_path = next(m['path'] for m in case['meshes'] if m['role'] == 'body')
        body_mesh = unreal.load_asset(body_path)
        if not isinstance(body_mesh, unreal.SkeletalMesh) or path(body_mesh.get_editor_property('skeleton')) != case['skeleton']:
            raise RuntimeError('Complete character identity binding changed: ' + sex)
        number = request[sex + '_outfit']
        outfit = catalog[sex + '_outfits'][number - 1] if number else None
        items = [('Part_' + row['role'], row['path'], 'face_support') for row in case['meshes'] if row['role'] != 'body']
        if outfit:
            items += [('Cloth_' + row['target_component'], row['mesh_path'], 'clothing') for row in outfit['resolved']['assignments']]
        denied = bool(outfit and outfit['hair_deny'])
        hair = catalog['hairs'][request['hair_index'] - 1] if request['hair_index'] else None
        hair_fit = CONTRACT.formal.hair_fit(hair, sex) if hair and not denied else None
        if hair_fit:
            items += [('Hair_' + f'{i:02d}', row['path'], 'hair') for i, row in enumerate(hair_fit['meshes'])]
        loaded = []
        for label, mesh_path, kind in items:
            mesh = unreal.load_asset(mesh_path)
            if not isinstance(mesh, unreal.SkeletalMesh):
                raise RuntimeError('Missing follower mesh: ' + mesh_path)
            slots = mesh.get_editor_property('materials')
            if not slots or any(s.get_editor_property('material_interface') is None for s in slots):
                raise RuntimeError('Missing follower material: ' + mesh_path)
            loaded.append({'label': label, 'mesh': mesh, 'kind': kind, 'compatibility': compatibility(body_mesh, mesh)})
        prepared[sex] = {'case': case, 'body_mesh': body_mesh, 'outfit': outfit, 'followers': loaded,
                         'hair_id': hair['hair_id'] if hair_fit else None,
                         'requested_hair_id': hair['hair_id'] if hair else None,
                         'blocked_hair_reason': 'outfit_deny_all' if denied and hair else None}
    return prepared


def ensure_level():
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    original = world_path()
    if original != LEVEL:
        dirty = [path(p) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
        if dirty:
            raise RuntimeError('Current map has unsaved changes; preserving it: ' + repr(dirty))
        if not (ROOT / 'entry_context.json').exists():
            location, rotation = unreal.EditorLevelLibrary.get_level_viewport_camera_info()
            write('entry_context.json', {'level': original, 'pid': os.getpid(), 'camera_position': vector(location),
                                       'camera_rotation': [rotation.pitch, rotation.yaw, rotation.roll], 'at': now()})
        levels.eject_pilot_level_actor()
        if not (levels.load_level(LEVEL) if unreal.EditorAssetLibrary.does_asset_exist(LEVEL) else levels.new_level(LEVEL)):
            raise RuntimeError('Cannot open independent review map')
    return levels


def environment():
    floor = actor(PREFIX + 'Floor', unreal.StaticMeshActor, unreal.Vector(0, 0, -5))
    floor.set_actor_scale3d(unreal.Vector(6, 7, .05))
    floor.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
    wall = actor(PREFIX + 'Background', unreal.StaticMeshActor, unreal.Vector(-240, 0, 180))
    wall.set_actor_scale3d(unreal.Vector(.05, 7, 4))
    wall.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
    light = actor(PREFIX + 'Key', unreal.DirectionalLight, unreal.Vector(0, 0, 300), unreal.Rotator(pitch=-35, yaw=-35))
    light.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property('intensity', .7)
    for name, x, yaw, intensity in [('Fill', 200, 180, 100.), ('Back', -150, 0, 70.)]:
        light = actor(PREFIX + name, unreal.RectLight, unreal.Vector(x, 0, 190), unreal.Rotator(yaw=yaw))
        light.get_component_by_class(unreal.RectLightComponent).set_editor_properties({'intensity': intensity, 'source_width': 350., 'source_height': 300.})
    volume = actor(PREFIX + 'Exposure', unreal.PostProcessVolume, unreal.Vector())
    volume.set_editor_property('unbound', True)
    settings = volume.get_editor_property('settings')
    settings.set_editor_properties({'override_auto_exposure_method': True, 'auto_exposure_method': unreal.AutoExposureMethod.AEM_MANUAL,
        'override_auto_exposure_apply_physical_camera_exposure': True, 'auto_exposure_apply_physical_camera_exposure': False,
        'override_auto_exposure_bias': True, 'auto_exposure_bias': -.8})
    volume.set_editor_property('settings', settings)
    camera = actor(PREFIX + 'Camera', unreal.CameraActor, unreal.Vector(480, 0, 110), unreal.Rotator(yaw=180))
    camera.get_component_by_class(unreal.CameraComponent).set_editor_properties({'field_of_view': 50., 'constrain_aspect_ratio': False})


def stage(prepared):
    assert_legacy_review_unmigrated()
    for sex, entry in prepared.items():
        prefix = PREFIX + sex + '_'
        location = unreal.Vector(0, -95 if sex == 'female' else 95, 0)
        a = actor(prefix + 'Body', unreal.SkeletalMeshActor, location, unreal.Rotator(yaw=-90))
        a.set_actor_location(location, False, False)
        a.set_actor_scale3d(unreal.Vector(1, 1, 1))
        body = component(a)
        body.set_skeletal_mesh_asset(entry['body_mesh'])
        body.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        body.set_editor_property('propagate_curves_to_followers', True)
        wanted = set()
        for row in entry['followers']:
            label = prefix + row['label']
            wanted.add(label)
            follower = actor(label, unreal.SkeletalMeshActor, location)
            follower.attach_to_actor(a, '', unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET)
            follower.set_is_temporarily_hidden_in_editor(False)
            follower.set_actor_hidden_in_game(False)
            comp = component(follower)
            comp.set_editor_property('override_materials', [])
            comp.set_skeletal_mesh_asset(row['mesh'])
            if row['compatibility']['follow_mode'] == 'copy_pose':
                comp.set_leader_pose_component(None, True)
                comp.set_animation_mode(unreal.AnimationMode.ANIMATION_BLUEPRINT)
                comp.set_anim_instance_class(row['copy_blueprint'].generated_class())
                comp.set_update_animation_in_editor(True)
                comp.set_enable_animation(True)
                comp.add_tick_prerequisite_component(body)
            else:
                comp.set_anim_instance_class(None)
                comp.set_leader_pose_component(body, True)
            comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            comp.set_component_tick_enabled(True)
        # Never remove source or unrelated actors. Clear only this map's pool.
        for follower in actors().get_all_level_actors():
            label = follower.get_actor_label()
            if label.startswith(prefix) and label != prefix + 'Body' and isinstance(follower, unreal.SkeletalMeshActor) and label not in wanted:
                component(follower).set_skeletal_mesh_asset(None)
                follower.set_actor_hidden_in_game(True)
                follower.set_is_temporarily_hidden_in_editor(True)


def copy_pose_path(mesh):
    suffix = hashlib.sha256(path(mesh.get_editor_property('skeleton')).encode()).hexdigest()[:12]
    return ASSET_ROOT + '/Followers/ABP_CCWH_CopyPose_' + suffix


def copy_pose_blueprint(mesh):
    """Keep extra hair bones in local reference pose while copying body bones.

    This preserves the imported hierarchy; it does not fix wrong attachment
    parents or introduce hair physics. Only new review assets are saved.
    """
    from editor_toolset.toolsets.blueprint import BlueprintTools
    target = copy_pose_path(mesh)
    blueprint = unreal.load_asset(target)
    skeleton = mesh.get_editor_property('skeleton')
    if blueprint is None:
        factory = unreal.AnimBlueprintFactory()
        factory.set_editor_properties({'target_skeleton': skeleton, 'parent_class': unreal.AnimInstance,
                                       'preview_skeletal_mesh': mesh})
        folder, name = target.rsplit('/', 1)
        blueprint = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.AnimBlueprint, factory)
        graph = unreal.BlueprintEditorLibrary.find_graph(blueprint, 'AnimGraph')
        roots = [n for n in BlueprintTools.find_nodes(graph) if isinstance(n, unreal.AnimGraphNode_Root)]
        if len(roots) != 1:
            raise RuntimeError('Copy Pose blueprint has no unique output')
        candidates = []
        for query in ('Copy Pose', '\u590d\u5236\u59ff\u52bf'):
            candidates += [t for t in BlueprintTools.find_node_types(graph, query) if t not in candidates]
        node = None
        for candidate in candidates:
            attempt = BlueprintTools.create_node(graph, candidate, unreal.IntPoint(-300, 0))
            if isinstance(attempt, unreal.AnimGraphNode_CopyPoseFromMesh):
                node = attempt
                break
            if attempt is not None:
                BlueprintTools.delete_node(attempt)
        if node is None:
            raise RuntimeError('Copy Pose node unavailable')
        settings = node.get_editor_property('node')
        settings.set_editor_properties({'use_attached_parent': True, 'use_mesh_pose': False,
                                       'copy_curves': True, 'copy_custom_attributes': False})
        node.set_editor_property('node', settings)
        outputs = [p for p in node.list_all_pins() if str(p.get_pin_name()) == 'Pose']
        inputs = [p for p in roots[0].list_all_pins() if str(p.get_pin_name()) == 'Result']
        if len(outputs) != 1 or len(inputs) != 1 or not outputs[0].try_create_connection(inputs[0]):
            raise RuntimeError('Cannot connect Copy Pose output')
        unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
        if blueprint.generated_class() is None or not unreal.EditorAssetLibrary.save_loaded_asset(blueprint, False):
            raise RuntimeError('Cannot compile/save Copy Pose review blueprint')
    if blueprint.get_editor_property('target_skeleton') != skeleton:
        raise RuntimeError('Copy Pose blueprint Skeleton differs')
    graph = unreal.BlueprintEditorLibrary.find_graph(blueprint, 'AnimGraph')
    nodes = [n for n in BlueprintTools.find_nodes(graph) if isinstance(n, unreal.AnimGraphNode_CopyPoseFromMesh)]
    if len(nodes) != 1 or not nodes[0].get_editor_property('node').get_editor_property('use_attached_parent'):
        raise RuntimeError('Saved Copy Pose blueprint is incomplete')
    return blueprint


def package_file(asset_path):
    return Path(unreal.Paths.project_content_dir()) / (asset_path.split('.')[0].removeprefix('/Game/') + '.uasset')


def file_hash(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sampled_tracks(animation):
    """UE5.8 sequencer models can return an empty legacy bone-track array.

    Use the supported evaluator and explicit track names; an empty array must
    never count as proof that keys were copied.
    """
    names = list(animation.data_model_interface.get_bone_track_names())
    if not names:
        raise RuntimeError('Animation contains no bone tracks')
    values = {str(name): [] for name in names}
    for frame in range(animation.data_model_interface.get_number_of_frames() + 1):
        poses = unreal.AnimationLibrary.get_bone_poses_for_frame(animation, names, frame, False)
        if len(poses) != len(names):
            raise RuntimeError('Animation evaluator returned incomplete track data')
        for name, pose in zip(names, poses):
            values[str(name)].append(pose)
    return names, values


def compare_tracks(source_values, target):
    names, actual = sampled_tracks(target)
    if set(actual) != set(source_values):
        raise RuntimeError('Copied clip bone-track set differs')
    maxima = {'translation_cm': 0., 'rotation_degrees': 0., 'scale_delta': 0.}
    for name, reference in source_values.items():
        if len(reference) != len(actual[name]):
            raise RuntimeError('Copied clip key count differs')
        for a, b in zip(reference, actual[name]):
            d = (a.translation - b.translation).length()
            ds = (a.scale3d - b.scale3d).length()
            qa, qb = a.rotation.normalized(), b.rotation.normalized()
            dot = abs(sum(getattr(qa, n) * getattr(qb, n) for n in 'xyzw'))
            norm_a = math.sqrt(sum(getattr(qa, n) ** 2 for n in 'xyzw'))
            norm_b = math.sqrt(sum(getattr(qb, n) ** 2 for n in 'xyzw'))
            angle = math.degrees(2 * math.acos(min(1., dot / max(1e-30, norm_a * norm_b))))
            if not all(math.isfinite(v) for v in (d, ds, angle)):
                raise RuntimeError('Non-finite copied animation pose')
            maxima['translation_cm'] = max(maxima['translation_cm'], d)
            maxima['rotation_degrees'] = max(maxima['rotation_degrees'], angle)
            maxima['scale_delta'] = max(maxima['scale_delta'], ds)
    # These are reconstructed preview clips, not a claim of bit-identical
    # source keys. Bound float/Euler roundtrip error for this visual pilot.
    # Translation is bounded at 0.01 mm. 0.05 degrees corresponds to
    # <0.9 mm at a one-metre lever arm; this is a visual preview bound.
    maxima['preview_limits'] = {'translation_cm': 1e-3, 'rotation_degrees': .05, 'scale_delta': 1e-5}
    if maxima['translation_cm'] > 1e-3 or maxima['rotation_degrees'] > .05 or maxima['scale_delta'] > 1e-5:
        raise RuntimeError('Copied local animation poses exceed numeric reconstruction tolerance: ' + repr(maxima))
    return maxima


def action_asset(entry, action):
    """Reconstruct sampled BodyOnly tracks targeting this preview Skeleton.

    AnimationAsset.skeleton is read-only in Python. Do not set it, change the
    source Skeleton, or add compatible Skeletons to a production mesh.
    """
    source = unreal.load_asset(action['path'])
    if not isinstance(source, unreal.AnimSequence):
        raise RuntimeError('Missing old BodyOnly clip: ' + action['path'])
    skeleton = entry['body_mesh'].get_editor_property('skeleton')
    model = source.data_model_interface
    names = [str(n) for n in model.get_bone_track_names()]
    if not set(names).issubset(REFERENCE.reference_bones(entry['body_mesh'])):
        raise RuntimeError('BodyOnly clip has unmapped bone tracks')
    if unreal.AnimationLibrary.get_animation_curve_names(source, unreal.RawCurveTrackTypes.RCT_FLOAT):
        raise RuntimeError('Expected curve-free BodyOnly clip')
    sex = entry['case']['sex']
    name = 'A_CCWH_' + action['action_id'].replace('ACT_', '') + '_v002'
    folder = ASSET_ROOT + '/Animations/' + sex.title()
    target_path = folder + '/' + name
    source_hash = file_hash(package_file(path(source)))
    report_path = ROOT / ('animations/' + action['action_id'] + '_v002.json')
    target = unreal.load_asset(target_path)
    if target is not None and report_path.exists():
        previous_report = read(report_path)
        if (previous_report['source_package_sha256'] != source_hash
                or previous_report['target_package_sha256'] != file_hash(package_file(path(target)))
                or target.get_editor_property('skeleton') != skeleton
                or {str(n) for n in target.data_model_interface.get_bone_track_names()} != set(names)):
            raise RuntimeError('Existing review animation or its source changed')
        return target
    needs_population = target is None or target.data_model_interface.get_num_bone_tracks() == 0
    source_names, source_values = sampled_tracks(source)
    if target is None:
        factory = unreal.AnimSequenceFactory()
        factory.set_editor_property('target_skeleton', skeleton)
        target = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.AnimSequence, factory)
        if not isinstance(target, unreal.AnimSequence):
            raise RuntimeError('Cannot create isolated review animation')
    if needs_population:
        if target.get_editor_property('skeleton') != skeleton:
            raise RuntimeError('Unfinished review animation targets another Skeleton')
        controller = target.controller
        controller.open_bracket('Copy retained BodyOnly tracks for complete-character review', False)
        try:
            controller.set_frame_rate(model.get_frame_rate(), False)
            controller.set_number_of_frames(unreal.FrameNumber(model.get_number_of_frames()), False)
            for name in source_names:
                poses = source_values[str(name)]
                controller.add_bone_track(name, False)
                positions = [pose.translation for pose in poses]
                rotations = [pose.rotation for pose in poses]
                scales = [pose.scale3d for pose in poses]
                if not controller.set_bone_track_keys(name, positions, rotations, scales, False):
                    raise RuntimeError('Cannot copy BodyOnly keys: ' + str(name))
        finally:
            controller.close_bracket(False)
        if hasattr(controller, 'notify_populated'):
            controller.notify_populated()
        target.set_editor_property('enable_root_motion', False)
        if not unreal.EditorAssetLibrary.save_loaded_asset(target, False):
            raise RuntimeError('Cannot save isolated review clip')
    if target.get_editor_property('skeleton') != skeleton:
        raise RuntimeError('Review clip targets another Skeleton')
    comparison = compare_tracks(source_values, target)
    if target.data_model_interface.get_number_of_frames() != model.get_number_of_frames() or target.get_play_length() != source.get_play_length():
        raise RuntimeError('Review clip timing differs')
    write('animations/' + action['action_id'] + '_v002.json', {'source': path(source), 'target': path(target),
        'source_skeleton': path(source.get_editor_property('skeleton')), 'target_skeleton': path(skeleton),
        'source_package_sha256': source_hash, 'target_package_sha256': file_hash(package_file(path(target))),
        'bone_tracks': len(names), 'frames': model.get_number_of_frames(), 'numeric_comparison': comparison,
        'duration_seconds': target.get_play_length(), 'body_tracks_reconstructed_at_source_frames': True,
        'scope': 'local_tracks_reconstructed_no_retargeting_visual_validation_pending', 'at': now()})
    return target


def animation(request, catalog, prepared):
    for sex, entry in prepared.items():
        body = component(find(PREFIX + sex + '_Body'))
        number = request['action_index']
        motion = entry.get('review_motion') if number else None
        previous = body.get_editor_property('animation_data').get_editor_property('anim_to_play')
        body.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        body.set_enable_animation(True)
        body.set_component_tick_enabled(True)
        body.set_update_animation_in_editor(True)
        body.set_editor_property('pause_anims', False)
        if motion is None:
            body.override_animation_data(None, False, False, 0., 1.)
            instance = body.get_anim_instance()
            if instance is not None:
                # OverrideAnimationData serializes data, but an already-live
                # single-node instance can retain its previous asset.
                instance.set_animation_asset(None, False, 1.)
                instance.set_playing(False)
        else:
            position = body.get_position() if previous == motion else 0.
            if previous != motion or body.get_anim_instance() is None:
                body.play_animation(motion, True)
            body.override_animation_data(motion, True, bool(request['playing']), position, 1.)
            instance = body.get_anim_instance()
            if instance is None:
                raise RuntimeError('Live BodyOnly animation instance did not initialize')
            instance.set_animation_asset(motion, True, 1.)
            instance.set_playing(bool(request['playing']))
            body.set_position(position, False)


def set_view(request):
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    settings = unreal.load_object(None, '/Script/UnrealEd.Default__EditorPerformanceSettings')
    if not hasattr(unreal, THROTTLE):
        setattr(unreal, THROTTLE, settings.get_editor_property('bThrottleCPUWhenNotForeground'))
    settings.set_editor_property('bThrottleCPUWhenNotForeground', False)
    for sex in ('female', 'male'):
        find(PREFIX + sex + '_Body').set_actor_rotation(unreal.Rotator(yaw=YAW[request['view']]), False)
    selected = ['female', 'male'] if request['focus'] == 'both' else [request['focus']]
    y = 0 if len(selected) == 2 else (-95 if selected[0] == 'female' else 95)
    head = request['framing'] == 'head'
    x = (280 if len(selected) == 2 else 170) if head else (490 if len(selected) == 2 else 350)
    z = 110.
    if head:
        z = sum(component(find(PREFIX + sex + '_Body')).get_socket_location('head').z + 7. for sex in selected) / len(selected)
    camera = find(PREFIX + 'Camera')
    location, rotation = unreal.Vector(x, y, z), unreal.Rotator(yaw=180)
    camera.set_actor_location(location, False, False)
    camera.set_actor_rotation(rotation, False)
    camera.get_component_by_class(unreal.CameraComponent).set_editor_property('field_of_view', 45. if head else 50.)
    actors().set_selected_level_actors([])
    levels.editor_set_viewport_realtime(True)
    levels.editor_set_game_view(True)
    levels.pilot_level_actor(camera)
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(location, rotation)
    levels.editor_invalidate_viewports()


def bindings(prepared):
    rows = []
    for sex, entry in prepared.items():
        leader_actor = find(PREFIX + sex + '_Body')
        body = component(leader_actor)
        if path(body.get_skeletal_mesh_asset()) != path(entry['body_mesh']):
            raise RuntimeError('Review replaced the complete character identity')
        followers = []
        for item in entry['followers']:
            follower = component(find(PREFIX + sex + '_' + item['label']))
            copy_mode = item['compatibility']['follow_mode'] == 'copy_pose'
            blueprint = unreal.load_asset(copy_pose_path(item['mesh'])) if copy_mode else None
            follow_ok = (blueprint is not None and follower.get_editor_property('anim_class') == blueprint.generated_class()
                         and follower.get_editor_property('leader_pose_component') is None) if copy_mode else follower.get_editor_property('leader_pose_component') == body
            if not follow_ok or path(follower.get_skeletal_mesh_asset()) != path(item['mesh']):
                raise RuntimeError('Follower binding does not match requested selection')
            followers.append({'kind': item['kind'], 'mesh': path(item['mesh']), 'leader_pose_match': not copy_mode,
                'follow_mode': item['compatibility']['follow_mode'], 'follow_configuration_match': True,
                'extra_bone_world': {name: vector(follower.get_socket_location(name)) for name in item['compatibility']['extra_reference_bones']},
                'compatibility': item['compatibility'], 'head_world': vector(follower.get_socket_location('head'))})
        wanted = {PREFIX + sex + '_' + item['label'] for item in entry['followers']}
        for pooled in actors().get_all_level_actors():
            label = pooled.get_actor_label()
            if label.startswith(PREFIX + sex + '_') and label != PREFIX + sex + '_Body' and isinstance(pooled, unreal.SkeletalMeshActor) and label not in wanted:
                if component(pooled).get_skeletal_mesh_asset() is not None:
                    raise RuntimeError('Previous outfit/hair mesh remains in review pool: ' + label)
        motion = body.get_editor_property('animation_data').get_editor_property('anim_to_play')
        instance = body.get_anim_instance()
        if instance is not None and instance.get_animation_asset() != motion:
            raise RuntimeError('Live animation asset differs from saved review selection')
        bone_names = {str(body.get_bone_name(i)) for i in range(body.get_num_bones())}
        samples = {name: vector(body.get_socket_location(name)) for name in ('root', 'pelvis', 'head', 'hand_l', 'hand_r', 'foot_l', 'foot_r') if name in bone_names}
        rows.append({'sex': sex, 'body': path(body.get_skeletal_mesh_asset()), 'skeleton': entry['case']['skeleton'],
            'outfit_index': entry['outfit']['index'] if entry['outfit'] else 0,
            'outfit_label': entry['outfit']['label'] if entry['outfit'] else 'No outfit',
            'hair_id': entry['hair_id'], 'requested_hair_id': entry['requested_hair_id'],
            'blocked_hair_reason': entry['blocked_hair_reason'], 'followers': followers,
            'unused_pool_meshes_cleared': True,
            'animation': path(motion), 'playing': bool(body.is_playing()) if motion else False,
            'position': float(body.get_position()) if motion else 0., 'bones': samples})
    return rows


def state(request, catalog, prepared):
    return {'schema_version': 1, 'success': True, 'level': world_path(), 'editor_pid': os.getpid(),
            'at': now(), 'request': request, 'sources': catalog['sources'], 'bindings': bindings(prepared),
            'visual_acceptance': 'pending', 'scope': 'prototype_outfit_hair_bodyonly_review'}


def restore():
    if hasattr(unreal, REFRESH):
        unreal.unregister_slate_post_tick_callback(getattr(unreal, REFRESH))
        delattr(unreal, REFRESH)
    if hasattr(unreal, THROTTLE):
        settings = unreal.load_object(None, '/Script/UnrealEd.Default__EditorPerformanceSettings')
        settings.set_editor_property('bThrottleCPUWhenNotForeground', getattr(unreal, THROTTLE))
        delattr(unreal, THROTTLE)
    return {'success': True, 'level': world_path(), 'action': 'restore', 'editor_closed': False}


def refresh(request, catalog, prepared):
    if hasattr(unreal, REFRESH):
        unreal.unregister_slate_post_tick_callback(getattr(unreal, REFRESH))
    ticks = [0]
    def tick(delta):
        ticks[0] += 1
        if world_path() != LEVEL or ticks[0] >= 4:
            if world_path() == LEVEL:
                result = state(request, catalog, prepared)
                result['viewport_refresh_pending'] = False
                write('current_case.json', result)
            unreal.unregister_slate_post_tick_callback(getattr(unreal, REFRESH))
            delattr(unreal, REFRESH)
    setattr(unreal, REFRESH, unreal.register_slate_post_tick_callback(tick))


def main():
    incoming = globals().get('DM_CC_REVIEW_REQUEST', {})
    action = incoming.get('action', 'show')
    if action == 'restore':
        return restore()
    if action in ('show', 'view', 'playback', 'reload'):
        # Check before loading old choices or creating any preview resources.
        assert_legacy_review_unmigrated()
    catalog = CONTRACT.catalog()
    request = normalize_request(incoming, catalog)
    prepared = prepare(request, catalog)
    if action in ('status', 'sample'):
        if world_path() != LEVEL:
            raise RuntimeError('Open the independent review map first')
        result = state(request, catalog, prepared)
        write('playback_sample.json' if action == 'sample' else 'status.json', result)
        return result
    if action == 'audit':
        rows = []
        start, count = int(incoming.get('start', 0)), int(incoming.get('count', 40))
        if start < 0 or not 1 <= count <= 40:
            raise ValueError('Audit requires bounded chunks of 1..40 meshes')
        unique = {}
        for sex in ('female', 'male'):
            for look in catalog[sex + '_outfits']:
                for item in look['resolved']['assignments']:
                    unique[(sex, item['mesh_path'])] = 'clothing'
            for hair in catalog['hairs']:
                for item in CONTRACT.formal.hair_fit(hair, sex)['meshes']:
                    unique[(sex, item['path'])] = 'hair'
        pairs = sorted(unique)[start:start + count]
        for sex, mesh_path in pairs:
            mesh = unreal.load_asset(mesh_path)
            try:
                if not isinstance(mesh, unreal.SkeletalMesh):
                    raise RuntimeError('Missing mesh')
                result = compatibility(prepared[sex]['body_mesh'], mesh)
                rows.append({'sex': sex, 'mesh': mesh_path, 'kind': unique[(sex, mesh_path)], 'success': True, **result})
            except Exception as exc:
                rows.append({'sex': sex, 'mesh': mesh_path, 'success': False, 'error': str(exc)})
        # The API queues collection at frame end, so the chunk cap matters.
        # Return between chunks instead of collecting the whole library in one
        # frame (SkeletonModifier creates editable mesh descriptions).
        unreal.SystemLibrary.collect_garbage()
        result = {'success': all(r['success'] for r in rows), 'total': len(unique), 'start': start, 'checked': len(rows),
                  'rows': rows, 'sources': catalog['sources'], 'visual_acceptance': 'pending'}
        write(f'audit/chunk_{start:04d}.json', result)
        return result
    if action not in ('show', 'view', 'playback', 'reload'):
        raise ValueError('Unknown review action')
    # Validate both preview clips before changing either visible character.
    if request['action_index']:
        for sex, entry in prepared.items():
            entry['review_motion'] = action_asset(entry, catalog['actions_by_sex'][sex][request['action_index'] - 1])
    for entry in prepared.values():
        for row in entry['followers']:
            if row['compatibility']['follow_mode'] == 'copy_pose':
                row['copy_blueprint'] = copy_pose_blueprint(row['mesh'])
    levels = ensure_level()
    # The requested map may have been loaded from another current map above.
    assert_legacy_review_unmigrated()
    if action == 'reload':
        if not levels.save_current_level() or not levels.load_level(LEVEL):
            raise RuntimeError('Independent review save/reload failed')
        # Inspect the serialized actors before any repair/reassembly can mask a failure.
        readback = state(request, catalog, prepared)
        readback['inspection_before_reassembly'] = True
        write('saved_reload_readback.json', readback)
    environment()
    stage(prepared)
    animation(request, catalog, prepared)
    set_view(request)
    if not levels.save_current_level():
        raise RuntimeError('Cannot save independent review map')
    result = state(request, catalog, prepared)
    result['viewport_refresh_pending'] = True
    write('current_case.json', result)
    refresh(request, catalog, prepared)
    unreal.SystemLibrary.collect_garbage()
    return result


if 'DM_CC_REVIEW_REQUEST' in globals():
    try:
        result = main()
    except Exception as exc:
        write('last_error.json', {'success': False, 'error': str(exc), 'at': now()})
        print(MARKER + json.dumps({'success': False, 'error': str(exc)}, ensure_ascii=False))
        raise
    else:
        reply_name = 'replies/' + uuid.uuid4().hex + '.json'
        write(reply_name, result)
        print(MARKER + json.dumps({'success': True, 'result_file': str(ROOT / reply_name)}, ensure_ascii=False))
