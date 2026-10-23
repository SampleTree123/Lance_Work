"""Isolated six-head comparison for user-owned sex-specific hairstyle grouping."""
import copy
import importlib
import json
import os
from pathlib import Path

import unreal
import cfd_native_batch40_contract_v1 as batch
import hair_group_color_review_contract_v1 as contract
importlib.reload(contract)
import formal_wardrobe_registry_v1 as formal
importlib.reload(formal)
import ue_complete_character_fixed_slot_runtime_v1 as fixed

previous = batch.module('ue_cfd_native_batch40_review_v1')
legacy = previous.legacy
legacy.ROOT, legacy.LEVEL, legacy.ASSET_ROOT = contract.ROOT, contract.LEVEL, contract.ASSET_ROOT
legacy.PREFIX = previous.PREFIX = 'DM_HairGroupColor_'
legacy.CACHE = '_dm_hair_group_color_review_v1'
PREFIX = legacy.PREFIX


def ensure_level():
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    original = legacy.world_path()
    if original != contract.LEVEL:
        dirty = [p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
        if dirty:
            raise RuntimeError('Current map has unsaved changes; preserving it: ' + repr(dirty))
        if not (contract.ROOT / 'entry_context.json').exists():
            legacy.write('entry_context.json', {'level': original, 'pid': os.getpid(), 'at': legacy.now()})
        levels.eject_pilot_level_actor()
        opened = (levels.load_level(contract.LEVEL) if unreal.EditorAssetLibrary.does_asset_exist(contract.LEVEL)
                  else levels.new_level(contract.LEVEL))
        if not opened:
            raise RuntimeError('Cannot open independent hair grouping map')
    return levels


def prepare(request, data):
    page = contract.page_hairs(data, request)
    case = data['characters_by_sex'][request['sex']]
    by_role = {row['role']: row for row in case['meshes']}
    library = formal.read_registry(formal.current_registry_path())
    plans = []
    for slot, hair in enumerate(page, 1):
        if request['focus'] != 'all' and str(slot) != request['focus']:
            continue
        resolved, followers = fixed._selection(library, request['sex'], {'hair_id': hair['hair_id']})
        assignments = [{'component_name': fixed.BASE_ROLES[role], 'mesh_path': row['path'], 'kind': 'face_support'}
                       for role, row in by_role.items() if role != 'body'] + followers
        plans.append({'slot': slot, 'case': case, 'body_path': by_role['body']['path'],
                      'assignments': assignments, 'resolved': resolved})
    _, loaded, _ = previous.prepare({}, ([case] * len(page), plans, data['sources']))
    return page, loaded


def head_sections(body):
    mesh = body.get_skeletal_mesh_asset()
    names = [str(slot.get_editor_property('material_slot_name')) for slot in mesh.get_editor_property('materials')]
    if 'Std_Skin_Head_Pbr' not in names:
        raise RuntimeError('The selected body has no verified head material section')
    body.set_forced_lod(1)
    body.show_all_material_sections(0)
    subsystem = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
    mask = unreal.load_asset('/Game/DataMake/CharacterFactory/FixedHeadHair_20261004_v1/Shared/Materials/M_Coverage_ZeroMask')
    if mask is None:
        raise RuntimeError('Missing verified coverage mask for persistent head framing')
    result = []
    for section in range(subsystem.get_num_sections(mesh, 0)):
        index = subsystem.get_lod_material_slot(mesh, 0, section)
        if not 0 <= index < len(names):
            raise RuntimeError('Invalid head framing material section')
        visible = names[index] in {'Std_Skin_Head_Pbr', 'Std_Eyelash_Pbr'}
        # Section visibility is transient in UE. A component-only mask also
        # preserves the head crop after reopening the saved review map.
        if not visible:
            body.set_material(index, mask)
        body.show_material_section(index, section, visible, 0)
        if body.is_material_section_shown(index, 0) != visible:
            raise RuntimeError('Head-only component section visibility did not apply')
        result.append({'section': section, 'material': names[index], 'visible': visible})
    return result


def apply_colors(request, components, slot):
    if request['hair_color'] == 'original' and request['eye_color'] == 'original':
        return {'hair': 'original', 'eyes': 'original', 'source_materials_unchanged': True}
    import hair_eye_color_runtime_v1 as colors
    importlib.reload(colors)
    return colors.apply(request, components, slot, contract.ASSET_ROOT)


def studio_background():
    path = contract.ASSET_ROOT + '/M_HairReview_Background_v001'
    material = unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
    if material is None:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            'M_HairReview_Background_v001', contract.ASSET_ROOT, unreal.Material, unreal.MaterialFactoryNew())
        material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
        node = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionConstant3Vector)
        node.set_editor_property('constant', unreal.LinearColor(.12, .12, .12, 1.))
        unreal.MaterialEditingLibrary.connect_material_property(node, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        unreal.EditorAssetLibrary.set_metadata_tag(material, 'HairGroupingOwner', 'background_v1')
        unreal.MaterialEditingLibrary.recompile_material(material)
        if not unreal.EditorAssetLibrary.save_loaded_asset(material, False):
            raise RuntimeError('Cannot save the independent neutral background material')
    if unreal.EditorAssetLibrary.get_metadata_tag(material, 'HairGroupingOwner') != 'background_v1':
        raise RuntimeError('Unrecognized review background material')
    legacy.find(PREFIX + 'Background').static_mesh_component.set_material(0, material)
    # Large, centered lights keep both comparison rows under the same lighting.
    for name, x, yaw, intensity in [('Fill', 400., 180., 140.), ('Back', -300., 0., 35.)]:
        actor = legacy.find(PREFIX + name)
        actor.set_actor_location(unreal.Vector(x, 0., 80.), False, False)
        actor.set_actor_rotation(unreal.Rotator(yaw=yaw), False)
        actor.get_component_by_class(unreal.RectLightComponent).set_editor_properties(
            {'intensity': intensity, 'source_width': 700., 'source_height': 500.})


def show(incoming):
    data = contract.catalog()
    if globals().get('DM_HAIR_REVIEW_SOURCES') != data['sources']:
        raise RuntimeError('Hair review source contract changed; reopen the panel')
    request = contract.normalize_request(incoming, data)
    page, loaded = prepare(request, data)
    # Resolve optional color support before changing an existing comparison.
    if request['hair_color'] != 'original' or request['eye_color'] != 'original':
        import hair_eye_color_runtime_v1 as colors
        importlib.reload(colors)
        colors.validate_request(request)
    levels = ensure_level()
    legacy.environment()
    studio_background()
    previous.clear_slot_actors()
    for old in legacy.actors().get_all_level_actors():
        if old.get_actor_label().startswith(PREFIX + 'Slot') and isinstance(old, unreal.TextRenderActor):
            old.set_actor_hidden_in_game(True)
            old.set_is_temporarily_hidden_in_editor(True)
    focused = request['focus'] != 'all'
    yaw = {'front': -90., 'side': 0., 'back': 90., 'threequarter': -45.}[request['view']]
    records = []
    for entry in loaded:
        slot = entry['slot']
        upper = slot <= 3
        column = (slot - 1) % 3
        location = unreal.Vector(0., 0. if focused else (1 - column) * 90., 0.)
        label = PREFIX + f'Slot{slot:02d}_'
        actor = legacy.actor(label + 'Body', unreal.SkeletalMeshActor, location, unreal.Rotator(yaw=yaw))
        actor.set_actor_location(location, False, False)
        actor.set_actor_rotation(unreal.Rotator(yaw=yaw), False)
        actor.set_actor_hidden_in_game(False)
        actor.set_is_temporarily_hidden_in_editor(False)
        body = legacy.component(actor)
        body.set_editor_property('override_materials', [])
        body.set_skeletal_mesh_asset(entry['body'])
        body.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        body.override_animation_data(None, False, False, 0., 1.)
        body.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        body.set_cast_shadow(False)
        body.set_editor_property('propagate_curves_to_followers', True)
        body.set_component_tick_enabled(True)
        sections = head_sections(body)
        target_z = 30. if focused or not upper else 130.
        location.z += target_z - body.get_socket_location('head').z
        actor.set_actor_location(location, False, False)
        components, actual = {}, []
        for row in entry['followers']:
            follower = legacy.actor(label + row['component_name'], unreal.SkeletalMeshActor, location)
            follower.attach_to_actor(actor, '', unreal.AttachmentRule.SNAP_TO_TARGET,
                                     unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET)
            follower.set_actor_hidden_in_game(False)
            follower.set_is_temporarily_hidden_in_editor(False)
            comp = legacy.component(follower)
            comp.set_editor_property('override_materials', [])
            comp.set_skeletal_mesh_asset(row['mesh'])
            if row['copy_pose']:
                comp.set_leader_pose_component(None, True)
                comp.set_animation_mode(unreal.AnimationMode.ANIMATION_BLUEPRINT)
                comp.set_anim_instance_class(row['copy_pose'].generated_class())
                comp.set_update_animation_in_editor(True)
                comp.add_tick_prerequisite_component(body)
            else:
                comp.set_anim_instance_class(None)
                comp.set_leader_pose_component(body, True)
            comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            comp.set_component_tick_enabled(True)
            if comp.get_skeletal_mesh_asset() != row['mesh']:
                raise RuntimeError('Hair review follower assignment failed')
            components[row['component_name']] = comp
            actual.append({'component': row['component_name'], 'mesh': row['mesh_path'],
                           'kind': row['kind'], 'follow_mode': row['compatibility']['follow_mode']})
        hair = page[slot - 1]
        number = legacy.actor(label + 'Number', unreal.TextRenderActor,
                              unreal.Vector(8., location.y, target_z - 39.))
        number.set_actor_location(unreal.Vector(8., location.y, target_z - 39.), False, False)
        number.set_actor_rotation(unreal.Rotator(), False)
        number.set_actor_hidden_in_game(False)
        number.set_is_temporarily_hidden_in_editor(False)
        text = number.get_component_by_class(unreal.TextRenderComponent)
        text.set_text(f"{hair['index']:02d}")
        text.set_world_size(9.)
        text.set_text_render_color(unreal.Color(230, 230, 230, 255))
        color_result = apply_colors(request, components, slot)
        records.append({'slot': slot, 'hair_id': hair['hair_id'], 'index': hair['index'],
                        'character_id': entry['case']['character_id'], 'sex': request['sex'],
                        'body': entry['body'].get_path_name(), 'skeleton': entry['case']['skeleton'],
                        'followers': actual, 'head_framing_sections': sections, 'colors': color_result})
    camera = legacy.find(PREFIX + 'Camera')
    camera.set_actor_location(unreal.Vector(900., 0., 20. if focused else 80.), False, False)
    camera.set_actor_rotation(unreal.Rotator(yaw=180.), False)
    camera.get_component_by_class(unreal.CameraComponent).set_editor_properties({
        'projection_mode': unreal.CameraProjectionMode.ORTHOGRAPHIC,
        'ortho_width': 90. if focused else 350., 'constrain_aspect_ratio': True,
        'aspect_ratio': .75 if focused else 1.35})
    floor = legacy.find(PREFIX + 'Floor')
    floor.set_actor_hidden_in_game(True)
    floor.set_is_temporarily_hidden_in_editor(True)
    wall = legacy.find(PREFIX + 'Background')
    wall.set_actor_location(unreal.Vector(-240., 0., 100.), False, False)
    wall.set_actor_scale3d(unreal.Vector(.05, 8., 5.))
    legacy.actors().set_selected_level_actors([])
    levels.editor_set_viewport_realtime(True)
    levels.editor_set_game_view(True)
    levels.pilot_level_actor(camera)
    levels.editor_invalidate_viewports()
    if request['save'] and not levels.save_current_level():
        raise RuntimeError('Cannot save isolated hair grouping map')
    result = {'success': True, 'level': contract.LEVEL, 'request': request, 'displayed': records,
              'page_order': [{'slot': i + 1, 'index': hair['index'], 'hair_id': hair['hair_id'],
                              'label': hair['label'], 'sex': request['sex']} for i, hair in enumerate(page)],
              'sources': data['sources'], 'human_grouping': 'not_required_user_decision_20261007',
              'scope': 'hair silhouette comparison and isolated material color experiments'}
    legacy.write('current_case.json', result)
    unreal.SystemLibrary.collect_garbage()
    return result
