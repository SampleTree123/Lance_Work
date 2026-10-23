"""Forty selectable identities on the existing two-character, 38-slot runtime.

Only the root session dispatches this worker. Source meshes, skeletons, materials,
old maps and follower blueprints remain read-only. Only two selected identities
are loaded; a transaction may briefly retain the previous pair for rollback.
"""
import copy
import gc
import hashlib
import importlib
import json
import os
from pathlib import Path
import uuid

import unreal
import ue_cfd_native_pair_review_v1 as pair
importlib.reload(pair)
import cfd_native_batch40_modular_contract_v1 as identities
importlib.reload(identities)
import run_cfd_native_batch40_transfer_v1 as transfer
import hair_eye_color_runtime_v1 as colors
importlib.reload(colors)

review, fixed, legacy = pair.review, pair.fixed, pair.legacy
ROOT, LEVEL = identities.ROOT, identities.LEVEL
ASSET_ROOT = identities.batch.UE_ROOT + '/ModularReview'
SOURCE_BP_ROOT = '/Game/DataMake/Validation/CFDNativePair20261006/FixedSlotRuntime'
fixed.ROOT = review.ROOT = legacy.ROOT = ROOT
fixed.LEVEL = legacy.LEVEL = LEVEL
fixed.ASSET_ROOT = legacy.ASSET_ROOT = ASSET_ROOT
fixed.BP_ROOT = ASSET_ROOT + '/FixedSlotRuntime'
legacy.CACHE = '_dm_cfd40_modular_cache_v1'
legacy.THROTTLE = '_dm_cfd40_modular_cpu_throttle_v1'
legacy.REFRESH = '_dm_cfd40_modular_legacy_refresh_v1'
review.REFRESH = '_dm_cfd40_modular_refresh_v1'
_load_plan, _state = review.load_plan, review.state
_apply, _restore, _animation = fixed.apply_prepared, review.restore_scene, review.set_animation
_current = review.current_request
_readback = fixed.readback
_checking_colors = True


def current_request(incoming):
    request = _current(incoming)
    catalog = identities.identity_catalog()
    if 'character_ids' not in request:
        request['character_ids'] = {sex: catalog['by_sex'][sex][0]['character_id'] for sex in fixed.SEXES}
    identities.validate_character_ids(request['character_ids'], catalog)
    if request.get('character_registry_sha256', catalog['source']['sha256']) != catalog['source']['sha256']:
        raise ValueError('Character registry changed; reopen the modular review panel')
    request['character_registry_sha256'] = catalog['source']['sha256']
    request['appearance'] = identities.validate_appearance(request.get('appearance', identities.default_appearance()))
    if any(row['face_id'] != 'none' for row in request['appearance'].values()):
        old = ROOT / 'current_case.json'
        previous = identities.read(old).get('request', {}) if old.exists() else {}
        request['playing'] = incoming.get('playing', previous.get('playing', False))
    request.setdefault('face_registry_sha256', None)
    return request


def selected_source(request):
    catalog = identities.identity_catalog()
    identities.validate_character_ids(request['character_ids'], catalog)
    if request['character_registry_sha256'] != catalog['source']['sha256']:
        raise ValueError('Character registry changed during transaction')
    cases = [copy.deepcopy(catalog['by_id'][request['character_ids'][sex]]) for sex in fixed.SEXES]
    for case in cases:
        if fixed.source_record(case['audit_source']['path']) != {k: case['audit_source'][k] for k in ('path', 'sha256')}:
            raise RuntimeError('Selected character import evidence changed')
        for mesh in case['meshes']:
            if not unreal.EditorAssetLibrary.does_asset_exist(mesh['path']):
                raise RuntimeError('Missing selected base component: ' + mesh['path'])
    value = {'schema_version': 1, 'cases': cases, 'character_registry': catalog['source']}
    path = ROOT / 'selected_sources' / (fixed.digest(value) + '.json')
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    fixed.STANDARD = path
    return catalog


def load_plan(request, data):
    catalog = selected_source(request)
    plan, prepared = _load_plan(request, data)
    plan['sources']['character_registry'] = catalog['source']
    plan['sources']['appearance_palette'] = identities.appearance_catalog()['source']
    plan['appearance'] = copy.deepcopy(request['appearance'])
    library = identities.face_catalog()
    if library.get('registry_source'):
        plan['sources']['native_face_library'] = library['registry_source']
    has_face = any(r['face_id'] != 'none' for r in request['appearance'].values())
    expected_sha = library.get('registry_source', {}).get('sha256') if has_face else None
    if request.get('face_registry_sha256') != expected_sha:
        raise ValueError('Face registry changed; reopen the panel')
    plan['faces'] = {}
    for sex, entry in prepared.items():
        base = entry.get('review_motion')
        resolved = identities.face_library.resolve(library, sex, request['appearance'][sex]['face_id'],
            identities.body_action_id(data, sex, request['action_index']), body_animation_path=fixed.object_path(base))
        if not resolved['restore_body_only']:
            if not identities.face_library.panel_playback(resolved['playback']):
                raise ValueError('Face playback behavior is unsupported by this panel')
            motion = unreal.load_asset(resolved['animation_path'])
            if (not isinstance(motion, unreal.AnimSequence)
                    or fixed.object_path(motion.get_editor_property('skeleton')) != catalog['skeletons'][sex]):
                raise ValueError('Derived face animation is absent or on the wrong shared skeleton')
            entry['review_motion'] = motion
        entry['face_selection'] = resolved
        plan['faces'][sex] = copy.deepcopy(resolved)
    plan['plan_sha256'] = fixed.digest({k: v for k, v in plan.items() if k != 'plan_sha256'})
    return plan, prepared


def apply_identity(plan, prepared):
    """Outer review transaction snapshots all six parts before this operation."""
    for sex, entry in prepared.items():
        body = fixed.body_for(sex)
        entry['_previous_motion'] = fixed.object_path(body.get_editor_property('animation_data').get_editor_property('anim_to_play'))
        entry['_previous_position'] = body.get_position()
        if body.get_skeletal_mesh_asset() != entry['body_mesh']:
            body.set_skeletal_mesh_asset(entry['body_mesh'])
    global _checking_colors
    # The inherited assembler first proves its original zero-override layout.
    # Colors are installed afterwards; the outer transaction owns rollback.
    _checking_colors = False
    try:
        result = _apply(plan, prepared)
    finally:
        _checking_colors = True
    for sex, slot in (('female', 1), ('male', 2)):
        cs = fixed.actor_components(fixed.actor_for(sex))
        requested = plan['appearance'][sex]
        applied = dict(requested)
        has_hair = any(c.get_skeletal_mesh_asset() is not None for name, c in cs.items() if name.startswith('HairPart'))
        if not has_hair:
            applied['hair_color'] = 'original'
        if any(applied[k + '_color'] != 'original' for k in ('hair', 'eye')):
            colors.apply(applied, cs, slot, ASSET_ROOT)
        # Both-original needs no override: the preceding assembler cleared it.
    return result


def appearance_readback(plan):
    """Read persisted material bindings, never apply/repair during inspection."""
    result, allowed_overrides = {}, {}
    for sex, slot in (('female', 1), ('male', 2)):
        cs = fixed.actor_components(fixed.actor_for(sex))
        requested = plan['appearance'][sex]
        rows, eligible, allowed = [], {'hair': 0, 'eye': 0}, set()
        hair_present = any(c.get_skeletal_mesh_asset() is not None for name, c in cs.items() if name.startswith('HairPart'))
        for name, component in cs.items():
            if name != 'Eyes' and not name.startswith('HairPart'):
                continue
            mesh = component.get_skeletal_mesh_asset()
            if mesh is None:
                continue
            materials = list(mesh.get_editor_property('materials'))
            if len(component.get_editor_property('override_materials')) > len(materials):
                raise RuntimeError('Unexpected excess color overrides: ' + sex + '/' + name)
            for index, material_slot in enumerate(materials):
                source = material_slot.material_interface
                source_path = colors._path(source)
                chain = colors._chain(source)
                kind = colors.classify_slot(name, str(material_slot.material_slot_name), source_path, [colors._path(m) for m in chain])
                actual = component.get_material(index)
                preset = requested[kind + '_color'] if kind else 'original'
                rgba = None
                if kind:
                    eligible[kind] += 1
                if preset == 'original':
                    if colors._path(actual) != source_path:
                        raise RuntimeError('Original color/ornament not restored: ' + sex + '/' + name)
                else:
                    expected = colors._name(ASSET_ROOT, slot, source_path, kind, preset)
                    if actual is None or colors._path(actual).split('.', 1)[0] != expected:
                        raise RuntimeError('Wrong isolated color material: ' + sex + '/' + name)
                    source_hash = colors._sha(colors.package_file(source_path))
                    spec = colors._spec(source, source_hash, kind, preset, slot)
                    rgba = colors._verify_instance(actual, source, spec, kind, preset)
                rows.append({'component': name, 'material_index': index, 'kind': kind, 'preset': preset,
                             'source': source_path, 'material': colors._path(actual), 'rgba_readback': rgba})
            allowed.add(name)
        for kind in ('hair', 'eye'):
            if requested[kind + '_color'] != 'original' and not eligible[kind] and (kind != 'hair' or hair_present):
                raise RuntimeError('Requested color has no supported material: ' + sex + '/' + kind)
        result[sex] = {'success': True, 'requested': copy.deepcopy(requested), 'bindings': rows,
                       'hair_color_deferred_without_hair': not hair_present and requested['hair_color'] != 'original',
                       'source_materials_read_only': True, 'face_algorithm_applied': False}
        allowed_overrides[sex] = allowed
    return result, allowed_overrides


def readback(plan, prepared=None):
    result = _readback(plan, prepared)
    if not _checking_colors:
        return result
    checked, allowed = appearance_readback(plan)
    ignored = set()
    for sex, character in result['characters'].items():
        for component in character['components']:
            name = component['component_name']
            if name in allowed[sex]:
                # Exempt only the exact stale-override diagnostic after every
                # actual slot was checked against source or owned color MIC.
                component['errors'] = [e for e in component['errors'] if e != 'stale_material_override']
                component['owned_color_overrides_verified'] = True
                ignored.add(sex + '/' + name + '/stale_material_override')
    result['errors'] = [e for e in result['errors'] if e not in ignored]
    result['success'] = not result['errors']
    result['appearance_readback'] = checked
    return result


def restore_identity(snapshot):
    errors = []
    # Original outfit-only rollback intentionally leaves Body untouched. An
    # identity transaction must restore Body first, then its five support parts.
    for sex, old in snapshot['characters'].items():
        try:
            body_state = next(value for component, value in old['components'] if component == old['body'])
            old['body'].set_skeletal_mesh_asset(body_state['mesh'])
        except Exception as exc:
            errors.append(sex + '/body_identity: ' + str(exc))
    return errors + _restore(snapshot)


def set_animation(request, prepared):
    # The inherited implementation already handles None independently for
    # each sex. Enable its clip path for a face-only static body as well.
    effective = dict(request)
    if any(e.get('review_motion') is not None for e in prepared.values()):
        effective['action_index'] = request['action_index'] or 1
    _animation(effective, prepared)
    for sex, entry in prepared.items():
        motion = entry.get('review_motion')
        same = motion is not None and entry.get('_previous_motion') == fixed.object_path(motion)
        playback = entry.get('face_selection', {}).get('playback')
        if isinstance(playback, dict) and playback.get('mode') == 'oneshot':
            body = fixed.body_for(sex)
            duration = float(motion.get_play_length())
            position = min(max(entry.get('_previous_position', 0.), 0.), duration) if same else 0.
            # Pause/view preserve phase. Play after the end explicitly replays.
            if request['action'] == 'playback' and request['playing'] and position >= duration - 1e-4:
                position = 0.
            playing = bool(request['playing'] and position < duration - 1e-4)
            body.override_animation_data(motion, False, playing, position, 1.)
            instance = body.get_anim_instance()
            if instance is None:
                raise RuntimeError('Native face single-node instance is unavailable')
            instance.set_animation_asset(motion, False, 1.)
            body.set_position(position, False)
            instance.set_playing(playing)
        elif same:
            fixed.body_for(sex).set_position(entry['_previous_position'], False)


def state(request, data, plan, prepared):
    effective = dict(request)
    if any(e.get('review_motion') is not None for e in prepared.values()):
        effective['action_index'] = request['action_index'] or 1
    result = _state(effective, data, plan, prepared)
    result['request'] = request
    result['sources'] = dict(result['sources'], character_registry=plan['sources']['character_registry'],
                             appearance_palette=plan['sources']['appearance_palette'])
    result['appearance_readback'] = result['bindings']['appearance_readback']
    if 'native_face_library' in plan['sources']:
        result['sources']['native_face_library'] = plan['sources']['native_face_library']
    result['face_readback'] = {}
    for sex, selection in plan.get('faces', {}).items():
        motion = result['animation'][sex]
        expected = selection['animation_path']
        looping = bool(fixed.body_for(sex).get_editor_property('animation_data').get_editor_property('saved_looping'))
        playback = selection.get('playback')
        oneshot = isinstance(playback, dict) and playback.get('mode') == 'oneshot'
        duration = float(prepared[sex]['review_motion'].get_play_length()) if oneshot else None
        completed = bool(oneshot and abs(motion['position'] - duration) <= 1e-4 and not motion['playing'])
        if completed and request['playing']:
            motion['expected_playing'] = False
            result['animation_errors'] = [e for e in result['animation_errors'] if e != sex + '/playback_state_mismatch']
        ok = motion['animation'] == expected and (not expected or looping == (not oneshot))
        result['face_readback'][sex] = {'success': ok, 'face_id': selection['face_id'],
            'body_action_id': identities.body_action_id(data, sex, request['action_index']),
            'animation': motion['animation'], 'expected_animation': expected, 'looping': looping,
            'playback': playback, 'completed_hold_last': completed,
            'native_follower_curves': True, 'python_morph_broadcast': False}
        if not ok:
            result['success'] = False
            result['animation_errors'].append(sex + '/native_face_clip_or_loop_mismatch')
    result['success'] = result['bindings']['success'] and not result.get('animation_errors', [])
    for sex, row in result['bindings']['characters'].items():
        row['character_id'] = plan['characters'][sex]['case']['character_id']
        row['body_skeleton'] = fixed.object_path(fixed.body_for(sex).get_skeletal_mesh_asset().get_editor_property('skeleton'))
        row['expected_body_skeleton'] = plan['characters'][sex]['case']['skeleton']
        if row['body_skeleton'] != row['expected_body_skeleton']:
            result['success'] = result['bindings']['success'] = False
            result['bindings']['errors'].append(sex + '/shared_skeleton_mismatch')
    result['identity_switch'] = {'base_components_switched_together': list(fixed.BASES),
                                 'outfit_hair_motion_preserved': True,
                                 'source_assets_modified': False}
    return result


review.current_request, review.load_plan, review.state = current_request, load_plan, state
review.restore_scene, review.set_animation = restore_identity, set_animation
fixed.apply_prepared = apply_identity
fixed.readback = readback


def ensure_level():
    """Keep the map guard; an unavailable optional viewport is not a blocker."""
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    original = legacy.world_path()
    if original != LEVEL:
        dirty = [legacy.path(p) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
        if dirty:
            raise RuntimeError('Current map has unsaved changes; preserving it: ' + repr(dirty))
        if not (ROOT / 'entry_context.json').exists():
            record = {'level': original, 'pid': os.getpid(), 'at': legacy.now(),
                      'camera_unavailable': True}
            try:
                camera = unreal.EditorLevelLibrary.get_level_viewport_camera_info()
                if camera is not None:
                    location, rotation = camera
                    record.update(camera_unavailable=False, camera_position=legacy.vector(location),
                                  camera_rotation=[rotation.pitch, rotation.yaw, rotation.roll])
                else:
                    record['camera_unavailable_reason'] = 'viewport_camera_info_returned_none'
            except Exception as exc:
                record['camera_unavailable_reason'] = str(exc)
            review.write('entry_context.json', record)
        levels.eject_pilot_level_actor()
        opened = (levels.load_level(LEVEL) if unreal.EditorAssetLibrary.does_asset_exist(LEVEL)
                  else levels.new_level(LEVEL))
        if not opened:
            raise RuntimeError('Cannot open independent modular review map')
    return levels


def cancel_refresh():
    if hasattr(unreal, review.REFRESH):
        unreal.unregister_slate_post_tick_callback(getattr(unreal, review.REFRESH))
        delattr(unreal, review.REFRESH)


def displayed_ids():
    if legacy.world_path() != LEVEL:
        return set()
    catalog = identities.identity_catalog()
    body_paths = {next(m['path'] for m in case['meshes'] if m['role'] == 'body'): identifier
                  for identifier, case in catalog['by_id'].items()}
    return {body_paths[path] for sex in fixed.SEXES if fixed.actor_for(sex) is not None
            for path in [fixed.object_path(fixed.body_for(sex).get_skeletal_mesh_asset())] if path in body_paths}


def release_departed(old_ids, current_ids):
    """Call only after transaction locals/snapshots have been discarded."""
    legacy.cache()['compatibility'].clear()
    gc.collect()
    receipts = []
    for identifier in sorted(old_ids - current_ids):
        receipts.append(transfer.release_saved_case_packages(identifier))
    return receipts


def loaded_batch_ids():
    prefix = identities.batch.UE_ROOT + '/'
    known = set(identities.identity_catalog()['by_id'])
    return {p.get_path_name()[len(prefix):].split('/', 1)[0]
            for p in unreal.ObjectIterator(unreal.Package)
            if p.get_path_name().startswith(prefix)
            and p.get_path_name()[len(prefix):].split('/', 1)[0] in known}


def unique_template_handles(bp, subsystem):
    """UE may return the same subobject handle twice; names alone aren't identity."""
    base, result, paths = fixed._base(), {}, {}
    for handle in subsystem.k2_gather_subobject_data_for_blueprint(bp):
        data, component = base.get_data(handle), base.get_component(handle)
        if not isinstance(component, unreal.SkeletalMeshComponent):
            continue
        name = str(unreal.SubobjectDataBlueprintFunctionLibrary.get_variable_name(data))
        path = component.get_path_name()
        if name not in fixed.COMPONENTS:
            raise RuntimeError('Unknown component in modular Blueprint: ' + name)
        if name in paths and paths[name] != path:
            raise RuntimeError('Same component name refers to distinct objects: ' + name)
        if path in paths.values() and name not in paths:
            raise RuntimeError('One component object has multiple variable names: ' + path)
        paths[name] = path
        result.setdefault(name, handle)
    if set(result) != set(fixed.COMPONENTS):
        raise RuntimeError('Blueprint does not contain exactly 38 unique fixed components')
    return result


def template_fingerprint(handles):
    result = {}
    for name, handle in handles.items():
        c = fixed._base().get_component(handle)
        result[name] = {'mesh': fixed.object_path(c.get_skeletal_mesh_asset()),
                        'materials': [fixed.object_path(m) for m in c.get_editor_property('override_materials')],
                        'anim_class': fixed.object_path(c.get_editor_property('anim_class'))}
    return result


def recovery_metadata(bp):
    fields = (fixed.OWNER_TAG, fixed.COPY_ROUTING_TAG, fixed.BUILD_STATE_TAG,
              'CFD40ModularRegistry', 'CompleteSourceSHA256')
    return {name: str(unreal.EditorAssetLibrary.get_metadata_tag(bp, name) or '') for name in fields}


def stamp_clone_metadata(bp, plan):
    # DuplicateAsset copies the graph and templates but not these package tags.
    unreal.EditorAssetLibrary.set_metadata_tag(bp, fixed.OWNER_TAG, fixed.digest(list(fixed.COMPONENTS)))
    unreal.EditorAssetLibrary.set_metadata_tag(bp, fixed.COPY_ROUTING_TAG, fixed.COPY_ROUTING_VERSION)
    unreal.EditorAssetLibrary.set_metadata_tag(bp, 'CompleteSourceSHA256', plan['sources']['standard_candidate']['sha256'])


def authorize_interrupted_clone(bp, bp_source, destination, source, source_hash, sex, subsystem):
    """Resume only a receipt-bound, inspected copy interrupted before initialization."""
    authorization_path = ROOT / 'clone_recovery_authorization_v1.json'
    if not authorization_path.is_file():
        raise RuntimeError('Incomplete clone has no inspected recovery authorization')
    authorization = fixed.read_json(authorization_path)
    probe = ROOT / 'controller/clone_component_probe_remote.json'
    metadata_probe = ROOT / 'controller/clone_metadata_probe_remote.json'
    if (authorization.get('destination') != destination or authorization.get('source') != source
            or authorization.get('source_sha256') != source_hash
            or authorization.get('probe_sha256') != fixed.source_record(probe)['sha256']
            or authorization.get('metadata_probe_sha256') != fixed.source_record(metadata_probe)['sha256']
            or fixed.actor_for(sex) is not None
            or recovery_metadata(bp) != authorization.get('destination_metadata')
            or bp.get_editor_property('status') != unreal.BlueprintStatus.BS_UP_TO_DATE):
        raise RuntimeError('Incomplete clone differs from the inspected interruption')
    dirty = {legacy.path(p) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if dirty != {destination}:
        raise RuntimeError('Recovery requires only the inspected destination Blueprint to be dirty')
    handles = unique_template_handles(bp, subsystem)
    if template_fingerprint(handles) != template_fingerprint(unique_template_handles(bp_source, subsystem)):
        raise RuntimeError('Incomplete clone templates changed after the duplication-only interruption')
    review.write('clone_recovery_used_v1.json', {'authorization': fixed.source_record(authorization_path),
                 'destination': destination, 'source_sha256': source_hash, 'at': legacy.now()})
    return handles


def clone_blueprints(plan):
    records = {}
    for sex in fixed.SEXES:
        destination = fixed.blueprint_path(sex)
        source = SOURCE_BP_ROOT + '/' + destination.rsplit('/', 1)[-1]
        bp_source = unreal.load_asset(source)
        if (not isinstance(bp_source, unreal.Blueprint)
                or unreal.EditorAssetLibrary.get_metadata_tag(bp_source, fixed.OWNER_TAG) != fixed.digest(list(fixed.COMPONENTS))
                or unreal.EditorAssetLibrary.get_metadata_tag(bp_source, fixed.COPY_ROUTING_TAG) != fixed.COPY_ROUTING_VERSION
                or bp_source.get_editor_property('status') != unreal.BlueprintStatus.BS_UP_TO_DATE):
            raise RuntimeError('Validated source slot Blueprint unavailable')
        source_hash = legacy.file_hash(legacy.package_file(source))
        subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        resumed = False
        if unreal.EditorAssetLibrary.does_asset_exist(destination):
            bp = unreal.load_asset(destination)
            if not isinstance(bp, unreal.Blueprint):
                raise RuntimeError('Refusing to overwrite an unrecognized modular Blueprint')
            if str(unreal.EditorAssetLibrary.get_metadata_tag(bp, fixed.BUILD_STATE_TAG)) == 'complete':
                if (unreal.EditorAssetLibrary.get_metadata_tag(bp, fixed.OWNER_TAG) != fixed.digest(list(fixed.COMPONENTS))
                        or unreal.EditorAssetLibrary.get_metadata_tag(bp, fixed.COPY_ROUTING_TAG) != fixed.COPY_ROUTING_VERSION
                        or unreal.EditorAssetLibrary.get_metadata_tag(bp, 'CFD40ModularRegistry') != plan['sources']['character_registry']['sha256']
                        or bp.get_editor_property('status') != unreal.BlueprintStatus.BS_UP_TO_DATE):
                    raise RuntimeError('Completed modular Blueprint changed')
                unique_template_handles(bp, subsystem)
                records[sex] = {'destination': destination, 'reused': True}
                continue
            handles = authorize_interrupted_clone(bp, bp_source, destination, source, source_hash, sex, subsystem)
            resumed = True
        else:
            bp = unreal.EditorAssetLibrary.duplicate_asset(source, destination)
            if not isinstance(bp, unreal.Blueprint):
                raise RuntimeError('Cannot duplicate modular review Blueprint')
            unreal.EditorAssetLibrary.set_metadata_tag(bp, fixed.BUILD_STATE_TAG, 'in_progress')
            handles = unique_template_handles(bp, subsystem)
        stamp_clone_metadata(bp, plan)
        for handle in handles.values():
            component = fixed._base().get_component(handle)
            component.set_skeletal_mesh_asset(None)
            component.set_editor_property('override_materials', [])
            component.set_anim_instance_class(None)
            component.override_animation_data(None, False, False, 0., 1.)
            component.set_visibility(False, False)
            component.set_hidden_in_game(True)
        unreal.EditorAssetLibrary.set_metadata_tag(bp, 'CFD40ModularRegistry', plan['sources']['character_registry']['sha256'])
        unreal.EditorAssetLibrary.set_metadata_tag(bp, 'CompleteSourceSHA256', plan['sources']['standard_candidate']['sha256'])
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        if bp.get_editor_property('status') != unreal.BlueprintStatus.BS_UP_TO_DATE:
            raise RuntimeError('Cloned modular review Blueprint failed to compile')
        unreal.EditorAssetLibrary.set_metadata_tag(bp, fixed.BUILD_STATE_TAG, 'complete')
        if not unreal.EditorAssetLibrary.save_loaded_asset(bp, False):
            raise RuntimeError('Cannot save independent modular Blueprint')
        if legacy.file_hash(legacy.package_file(source)) != source_hash:
            raise RuntimeError('Source Blueprint changed unexpectedly')
        records[sex] = {'source': source, 'source_sha256': source_hash, 'destination': destination,
                        'reused': False, 'resumed_inspected_copy': resumed,
                        'blank_identity_templates': True, 'component_count': len(handles)}
    return records


def stage(incoming):
    transfer.shared_runtime().verify_baseline()
    levels = ensure_level()
    # Leaving the old eight-person map must not retain its earlier pages.
    # Only completed, saved identity packages are eligible for this release.
    keep_ids = set(current_request(incoming)['character_ids'].values()) | displayed_ids()
    cleanup = release_departed(loaded_batch_ids(), keep_ids)
    legacy.environment()
    request = current_request(dict(incoming, action='show', save=False))
    data = review.contract.catalog()
    plan, prepared = load_plan(request, data)
    build = clone_blueprints(plan)
    for sex in fixed.SEXES:
        if fixed.actor_for(sex) is None:
            bp = unreal.load_asset(fixed.blueprint_path(sex))
            actor = legacy.actors().spawn_actor_from_class(bp.generated_class(),
                unreal.Vector(0, -95 if sex == 'female' else 95, 0), unreal.Rotator(yaw=-90))
            if actor is None:
                raise RuntimeError('Cannot spawn modular review character')
            actor.set_actor_label(fixed.actor_label(sex))
            fixed._set_instance_property(actor, 'tags', [unreal.Name(fixed.OWNER_TAG)])
    snapshot = review.snapshot_scene()
    try:
        apply_identity(plan, prepared)
        set_animation(request, prepared)
        review.set_view(request)
        result = state(request, data, plan, prepared)
        if not result['success']:
            raise RuntimeError('Modular stage binding verification failed: ' + str(result))
        transfer.shared_runtime().verify_baseline()
        if not levels.save_current_level():
            raise RuntimeError('Cannot save isolated modular review level')
    except Exception:
        review.write('stage_rollback.json', {'rollback_errors': restore_identity(snapshot)})
        raise
    result['blueprints'] = build
    result['previous_page_package_release'] = cleanup
    review.write('current_case.json', result)
    review.write('stage_result.json', result)
    return result


def run(incoming):
    cancel_refresh()
    transfer.shared_runtime().verify_baseline()
    old_ids = displayed_ids()
    # review.run owns its own snapshot. Once it returns no old mesh references
    # are held here, permitting the established audited-package unload routine.
    result = review.run(incoming)
    if incoming.get('action') != 'restore':
        result['package_release'] = release_departed(old_ids, displayed_ids())
        transfer.shared_runtime().verify_baseline()
    return result


if __name__ == '__main__':
    try:
        incoming = globals().get('DM_SLOT_REVIEW_REQUEST', {})
        result = stage(incoming) if globals().get('DM_CFD_BATCH40_MODULAR_STAGE') else run(incoming)
        result_file = review.write('replies/' + uuid.uuid4().hex + '.json', result)
        print(review.MARKER + json.dumps({'success': result.get('success', False), 'result_file': str(result_file)}))
    except Exception as exc:
        review.write('last_error.json', {'success': False, 'at': legacy.now(), 'error': str(exc)})
        raise
