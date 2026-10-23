"""Display and verify the authorized complete-character fixed-slot review pair."""
from __future__ import annotations
import hashlib
import importlib
import json
from pathlib import Path
import uuid

import unreal
import formal_wardrobe_registry_v1 as formal
importlib.reload(formal)
import complete_character_slot_review_contract_v1 as contract
import ue_complete_character_fixed_slot_runtime_v1 as fixed
import ue_complete_character_wardrobe_hair_review_v1 as legacy
for _module in (contract, fixed, legacy):
    importlib.reload(_module)

ROOT = fixed.ROOT / 'tonight_20261006_v1/runtime'
MARKER = 'DM_COMPLETE_SLOT_REVIEW='
VIEWS = {'front': -90., 'side': 0., 'back': 90., 'threequarter': -45.}
REFRESH = '_dm_complete_slot_review_refresh_v1'


def write(name, value):
    destination = ROOT / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')
    return destination


def current_request(incoming):
    old = ROOT / 'current_case.json'
    previous = json.loads(old.read_text(encoding='utf-8-sig')).get('request', {}) if old.exists() else {}
    request = dict(action='show', action_index=0, playing=False,
                   view='front', focus='both', framing='full', save=False)
    request.update(previous)
    request.update(incoming)
    request['action'] = incoming.get('action', 'show')
    request['save'] = incoming.get('save', False)
    if request.get('action') not in {'show', 'view', 'playback', 'status', 'sample', 'save', 'reload', 'restore'}:
        raise ValueError('Unsupported fixed-slot review action')
    if request['view'] not in VIEWS or request['focus'] not in {'female', 'male', 'both'}:
        raise ValueError('Invalid review view/focus')
    if request['framing'] not in {'full', 'head', 'torso', 'legs', 'feet'}:
        raise ValueError('Invalid framing')
    if type(request['action_index']) is not int or not 0 <= request['action_index'] <= 5:
        raise ValueError('Action index must be 0..5')
    if type(request['playing']) is not bool or type(request['save']) is not bool:
        raise ValueError('Playback/save flags must be boolean')
    if not request['action_index']:
        request['playing'] = False
    return request


def load_plan(request, data):
    if set(request.get('choices', {})) != {'female', 'male'}:
        raise ValueError('Explicit female and male choices are required')
    source_sha = legacy.CONTRACT._source(Path(data['sources']['registry']['path']))['sha256']
    if request.get('registry_sha256', source_sha) != source_sha:
        raise ValueError('Registry changed since the panel opened; reopen the panel')
    canonical = {sex: contract.to_runtime_choice(sex, choice) for sex, choice in request['choices'].items()}
    plan = fixed.make_plan(data['sources']['registry']['path'], canonical)
    if not (plan['sources']['registry']['sha256'] == data['sources']['registry']['sha256'] == source_sha):
        raise ValueError('Registry changed while preparing the complete selection')
    prepared = fixed.preflight(plan)
    # Resolve all required preview clips before changing either character.
    if request['action_index']:
        for sex, entry in prepared.items():
            entry['review_motion'] = legacy.action_asset(entry, data['actions_by_sex'][sex][request['action_index'] - 1])
    return plan, prepared


def set_animation(request, prepared):
    for sex, entry in prepared.items():
        body = fixed.body_for(sex)
        motion = entry.get('review_motion') if request['action_index'] else None
        previous = body.get_editor_property('animation_data').get_editor_property('anim_to_play')
        body.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        body.set_enable_animation(True)
        body.set_component_tick_enabled(True)
        body.set_update_animation_in_editor(True)
        fixed._set_instance_property(body, 'pause_anims', False)
        if motion is None:
            body.override_animation_data(None, False, False, 0., 1.)
            instance = body.get_anim_instance()
            if instance is not None:
                instance.set_animation_asset(None, False, 1.)
                instance.set_playing(False)
        else:
            position = body.get_position() if previous == motion else 0.
            if previous != motion or body.get_anim_instance() is None:
                body.play_animation(motion, True)
            body.override_animation_data(motion, True, request['playing'], position, 1.)
            instance = body.get_anim_instance()
            if instance is None:
                raise RuntimeError('BodyOnly preview instance did not initialize')
            instance.set_animation_asset(motion, True, 1.)
            instance.set_playing(request['playing'])
            body.set_position(position, False)


def set_view(request):
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    settings = unreal.load_object(None, '/Script/UnrealEd.Default__EditorPerformanceSettings')
    if not hasattr(unreal, legacy.THROTTLE):
        setattr(unreal, legacy.THROTTLE, settings.get_editor_property('bThrottleCPUWhenNotForeground'))
    settings.set_editor_property('bThrottleCPUWhenNotForeground', False)
    for sex in ('female', 'male'):
        fixed.actor_for(sex).set_actor_rotation(unreal.Rotator(yaw=VIEWS[request['view']]), False)
    sexes = ['female', 'male'] if request['focus'] == 'both' else [request['focus']]
    y = sum(fixed.actor_for(sex).get_actor_location().y for sex in sexes) / len(sexes)
    framing = request['framing']
    x, z, fov = {'full': (490. if len(sexes) == 2 else 400., 110. if len(sexes) == 2 else 85., 50.),
                 'torso': (310. if len(sexes) == 2 else 185., 112., 45.),
                 'legs': (310. if len(sexes) == 2 else 250., 65. if len(sexes) == 2 else 50., 45.),
                 'feet': (280. if len(sexes) == 2 else 120., 22. if len(sexes) == 2 else 15., 45.),
                 'head': (280. if len(sexes) == 2 else 170., 170., 45.)}[framing]
    if framing == 'head':
        z = sum(fixed.body_for(sex).get_socket_location('head').z + 7. for sex in sexes) / len(sexes)
    camera = legacy.find(legacy.PREFIX + 'Camera')
    if camera is None:
        raise RuntimeError('Existing review camera is missing')
    location, rotation = unreal.Vector(x, y, z), unreal.Rotator(yaw=180)
    camera.set_actor_location(location, False, False)
    camera.set_actor_rotation(rotation, False)
    camera.get_component_by_class(unreal.CameraComponent).set_editor_property('field_of_view', fov)
    legacy.actors().set_selected_level_actors([])
    levels.editor_set_viewport_realtime(True)
    levels.editor_set_game_view(True)
    levels.pilot_level_actor(camera)
    unreal.EditorLevelLibrary.set_level_viewport_camera_info(location, rotation)
    levels.editor_invalidate_viewports()


def animation_readback():
    rows = {}
    for sex in ('female', 'male'):
        body = fixed.body_for(sex)
        instance = body.get_anim_instance()
        names = ('pelvis', 'spine_02', 'head', 'hand_l', 'hand_r', 'foot_l', 'foot_r')
        missing = [name for name in names if body.get_bone_index(name) < 0]
        if missing:
            raise RuntimeError('Body motion sample has missing bones: ' + str(missing))
        bones = {name: legacy.vector(body.get_socket_location(name)) for name in names}
        rows[sex] = {'body_component': fixed.object_path(body), 'position': body.get_position(),
                     'animation': fixed.object_path(body.get_editor_property('animation_data').get_editor_property('anim_to_play')),
                     'instance': fixed.object_path(instance),
                     'playing': bool(instance and body.is_playing()), 'bone_world_locations': bones}
    return rows


def state(request, data, plan, prepared):
    readback = fixed.readback(plan, prepared)
    motions = animation_readback()
    animation_errors = []
    for sex, row in motions.items():
        expected = fixed.object_path(prepared[sex].get('review_motion')) if request['action_index'] else None
        row['expected_animation'] = expected
        row['expected_playing'] = bool(expected and request['playing'])
        if row['animation'] != expected:
            animation_errors.append(sex + '/wrong_or_missing_body_motion')
        if row['playing'] != row['expected_playing']:
            animation_errors.append(sex + '/playback_state_mismatch')
    return {'schema_version': 1, 'success': readback['success'] and not animation_errors, 'at': legacy.now(),
            'level': legacy.world_path(), 'request': request, 'sources': data['sources'],
            'plan_sha256': plan['plan_sha256'], 'bindings': readback,
            'animation': motions, 'animation_errors': animation_errors, 'human_acceptance': 'pending',
            'limitations': plan['limitations']}


def refresh(request, data, plan, prepared):
    if hasattr(unreal, REFRESH):
        unreal.unregister_slate_post_tick_callback(getattr(unreal, REFRESH))
    ticks = [0]
    def tick(_delta):
        ticks[0] += 1
        if legacy.world_path() != fixed.LEVEL or ticks[0] >= 4:
            try:
                if legacy.world_path() == fixed.LEVEL:
                    write('current_case.json', state(request, data, plan, prepared))
            finally:
                unreal.unregister_slate_post_tick_callback(getattr(unreal, REFRESH))
                delattr(unreal, REFRESH)
    setattr(unreal, REFRESH, unreal.register_slate_post_tick_callback(tick))


def snapshot_scene():
    camera = legacy.find(legacy.PREFIX + 'Camera')
    if camera is None:
        raise RuntimeError('Review camera is missing before scene mutation')
    snapshot = {'characters': {}, 'camera': camera,
                'camera_location': camera.get_actor_location(), 'camera_rotation': camera.get_actor_rotation(),
                'camera_fov': camera.get_component_by_class(unreal.CameraComponent).get_editor_property('field_of_view')}
    for sex in ('female', 'male'):
        actor = fixed._owned_actor(sex)
        components = fixed.actor_components(actor)
        body = components['Body']
        data = body.get_editor_property('animation_data')
        snapshot['characters'][sex] = {
            'actor': actor, 'rotation': actor.get_actor_rotation(), 'body': body,
            'actor_tags': list(actor.get_editor_property('tags')),
            'components': [(c, fixed._snapshot(c)) for c in components.values()],
            'animation_mode': body.get_editor_property('animation_mode'),
            'animation': data.get_editor_property('anim_to_play'),
            'looping': data.get_editor_property('saved_looping'),
            'playing': bool(body.get_anim_instance() and body.is_playing()),
            'position': body.get_position(), 'rate': data.get_editor_property('saved_play_rate')}
    return snapshot


def restore_scene(snapshot):
    errors = []
    for sex, old in snapshot['characters'].items():
        try:
            fixed._set_instance_property(old['actor'], 'tags', old['actor_tags'])
            if list(old['actor'].get_editor_property('tags')) != old['actor_tags']:
                raise RuntimeError('Actor tag rollback did not match snapshot')
            for component, value in old['components']:
                fixed._restore(component, value, old['body'])
            body = old['body']
            body.override_animation_data(old['animation'], old['looping'], old['playing'], old['position'], old['rate'])
            instance = body.get_anim_instance()
            if instance is not None and hasattr(instance, 'set_animation_asset'):
                instance.set_animation_asset(old['animation'], old['looping'], old['rate'])
                instance.set_playing(old['playing'])
                body.set_position(old['position'], False)
            # OverrideAnimationData forces Single Node; restore the original
            # mode last so a pre-animation Blueprint/None body remains so.
            body.set_animation_mode(old['animation_mode'])
            old['actor'].set_actor_rotation(old['rotation'], False)
        except Exception as exc:
            errors.append(sex + ': ' + str(exc))
    try:
        camera = snapshot['camera']
        camera.set_actor_location(snapshot['camera_location'], False, False)
        camera.set_actor_rotation(snapshot['camera_rotation'], False)
        camera.get_component_by_class(unreal.CameraComponent).set_editor_property('field_of_view', snapshot['camera_fov'])
    except Exception as exc:
        errors.append('camera: ' + str(exc))
    return errors


def run(incoming):
    request = current_request(incoming)
    if request['action'] == 'restore':
        if hasattr(unreal, REFRESH):
            unreal.unregister_slate_post_tick_callback(getattr(unreal, REFRESH))
            delattr(unreal, REFRESH)
        return legacy.restore()
    fixed._assert_level()
    data = contract.catalog()
    plan, prepared = load_plan(request, data)
    action = request['action']
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if action in {'show', 'view', 'playback'}:
        snapshot = snapshot_scene()
        try:
            fixed.apply_prepared(plan, prepared)
            set_animation(request, prepared)
            set_view(request)
            verification = state(request, data, plan, prepared)
            if not verification['success']:
                raise RuntimeError('Scene readback mismatch: ' + str(verification['animation_errors']) + str(verification['bindings']['errors']))
        except Exception as exc:
            rollback_errors = restore_scene(snapshot)
            write('last_transaction_failure.json', {'at': legacy.now(), 'error': str(exc),
                  'rollback_errors': rollback_errors, 'partial_failure': bool(rollback_errors), 'request': request})
            raise
    if action in {'save', 'reload'} or request['save']:
        dirty = [p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
        if any(p != fixed.LEVEL for p in dirty):
            raise RuntimeError('Unrelated dirty map exists; refusing broad save')
        if not levels.save_current_level():
            raise RuntimeError('Could not save current review map')
    if action == 'reload':
        if not levels.load_level(fixed.LEVEL):
            raise RuntimeError('Could not reload review map')
        # Read saved component bindings before any repair/reapplication.
        result = state(request, data, plan, prepared)
        result['inspection_before_reassembly'] = True
        write('saved_reload_readback.json', result)
    else:
        result = state(request, data, plan, prepared)
    if not result['success']:
        raise RuntimeError('Fixed-slot readback failed: ' + str(result['bindings']['errors']) + str(result['animation_errors']))
    if action not in {'sample', 'status'}:
        write('current_case.json', result)
        refresh(request, data, plan, prepared)
    unreal.SystemLibrary.collect_garbage()
    return result


if __name__ == '__main__':
    try:
        incoming = globals().get('DM_SLOT_REVIEW_REQUEST', globals().get('DM_TONIGHT_REQUEST', {}))
        result = run(incoming)
        result_file = write('replies/' + uuid.uuid4().hex + '.json', result)
        print(MARKER + json.dumps({'success': result.get('success', False), 'result_file': str(result_file)}))
    except Exception as exc:
        write('last_error.json', {'success': False, 'at': legacy.now(), 'error': str(exc)})
        raise
