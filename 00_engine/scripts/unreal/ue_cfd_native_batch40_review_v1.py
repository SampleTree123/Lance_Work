"""Eight-slot static comparison map for the bounded native CFD batch.

Five pages: male A/B/L/W then female A/B/L/W at group index 1..5.
Existing outfit/hair assets are read-only. This does not record human approval.
"""
import copy
import hashlib
import json
from pathlib import Path

import unreal
import cfd_native_batch40_contract_v1 as contract
import run_cfd_native_pair_transfer_v1 as sources
import formal_wardrobe_registry_v1 as formal
import complete_character_slot_review_contract_v1 as choices
import ue_complete_character_fixed_slot_runtime_v1 as fixed
import run_cfd_native_batch40_transfer_v1 as transfer

legacy = contract.module('ue_complete_character_wardrobe_hair_review_v1')
legacy.ROOT = contract.RUN / 'runtime'
legacy.LEVEL = contract.LEVEL
legacy.ASSET_ROOT = contract.UE_ROOT
legacy.PREFIX = 'DM_CFD40_'
legacy.CACHE = '_dm_cfd40_review_cache_v1'
PREFIX = legacy.PREFIX
MARKER = 'DM_CFD40_REVIEW='


def reference_choices(hair):
    data = choices.catalog()
    result = {}
    for sex,index in (('female',46),('male',11)):
        matches = [row for row in data['presets_by_sex'][sex] if row['index'] == index]
        if len(matches) != 1:
            raise RuntimeError('Expected retained basic outfit preset is unavailable')
        value = copy.deepcopy(matches[0]['choice'])
        value['hair_id'] = 'HAIR_HB1_02' if hair else None
        result[sex] = choices.to_runtime_choice(sex,value)
    return data,result


def copy_pose_asset(mesh):
    suffix = hashlib.sha256(mesh.get_editor_property('skeleton').get_path_name().encode()).hexdigest()[:12]
    path = '/Game/DataMake/Validation/CompleteCharacterWardrobeHair20261005/Followers/ABP_CCWH_CopyPose_' + suffix
    asset = unreal.load_asset(path)
    if not isinstance(asset,unreal.AnimBlueprint) or asset.get_editor_property('target_skeleton') != mesh.get_editor_property('skeleton'):
        raise RuntimeError('Previously validated follower CopyPose asset is unavailable: ' + path)
    return asset


def preflight(request):
    """Resolve source records and paths without loading the next page's assets."""
    registry = contract.read(contract.REGISTRY)
    page = contract.page_cases(registry['cases'],request['page'])
    data,reference = reference_choices(request['hair'])
    formal_path = formal.current_registry_path()
    library = formal.read_registry(formal_path)
    planned = []
    for index,case in enumerate(page,1):
        if request['focus'] != 'all' and str(index) != request['focus']:
            continue
        if not case.get('standard_candidate_ready') or sources.source(case['audit_source']['path']) != case['audit_source']:
            raise RuntimeError('Imported character evidence changed')
        by_role = {row['role']:row for row in case['meshes']}
        if set(by_role) != set(fixed.BASE_ROLES) or len(case['meshes']) != 6:
            raise RuntimeError('Character does not have all six imported base components')
        resolved,followers = fixed._selection(library,case['sex'],reference[case['sex']])
        assignments = [{'component_name':fixed.BASE_ROLES[role],'mesh_path':row['path'],'kind':'face_support'}
                       for role,row in by_role.items() if role != 'body'] + followers
        if request['framing'] == 'head':
            assignments = [row for row in assignments if row['kind'] != 'clothing']
        for path in [by_role['body']['path']] + [row['mesh_path'] for row in assignments]:
            if not unreal.EditorAssetLibrary.does_asset_exist(path):
                raise RuntimeError('Missing review mesh: ' + path)
        planned.append({'slot':index,'case':case,'body_path':by_role['body']['path'],
                        'assignments':assignments,'resolved':resolved})
    return page,planned,{'registry':sources.source(formal_path),'imported_characters':sources.source(contract.REGISTRY),
                        'basic_outfit_presets':{'female':46,'male':11},'hair':'HAIR_HB1_02' if request['hair'] else None}


def prepare(request, plan=None):
    page,planned,evidence = plan if plan is not None else preflight(request)
    loaded = []
    for item in planned:
        body = unreal.load_asset(item['body_path'])
        if not isinstance(body,unreal.SkeletalMesh) or body.get_editor_property('skeleton').get_path_name() != item['case']['skeleton']:
            raise RuntimeError('Body is missing or its shared Skeleton changed')
        entry = {'slot':item['slot'],'case':item['case'],'body':body,'followers':[], 'resolved':item['resolved']}
        for row in item['assignments']:
            mesh = unreal.load_asset(row['mesh_path'])
            if not isinstance(mesh,unreal.SkeletalMesh):
                raise RuntimeError('Missing review follower')
            compatibility = legacy.compatibility(body,mesh)
            slots = mesh.get_editor_property('materials')
            if not slots or any(slot.get_editor_property('material_interface') is None for slot in slots):
                raise RuntimeError('Missing follower materials')
            entry['followers'].append({**row,'mesh':mesh,'compatibility':compatibility,
                'copy_pose':copy_pose_asset(mesh) if compatibility['follow_mode'] == 'copy_pose' else None})
        loaded.append(entry)
    return page,loaded,evidence


def displayed_case_ids():
    """Read live slots, including a restored saved page; retain only identity strings."""
    cases = contract.validate_spec(contract.read(contract.SPEC))
    prefixes = {contract.UE_ROOT+'/'+c['character_id']+'/':c['character_id'] for c in cases}
    result = set()
    for actor in legacy.actors().get_all_level_actors():
        if actor.get_actor_label().startswith(PREFIX+'Slot') and isinstance(actor,unreal.SkeletalMeshActor):
            mesh = legacy.component(actor).get_skeletal_mesh_asset()
            if mesh is not None:
                path = mesh.get_path_name()
                result.update(identifier for prefix,identifier in prefixes.items() if path.startswith(prefix))
    return result


def clear_slot_actors():
    for actor in legacy.actors().get_all_level_actors():
        if actor.get_actor_label().startswith(PREFIX+'Slot') and isinstance(actor,unreal.SkeletalMeshActor):
            component = legacy.component(actor)
            component.set_leader_pose_component(None,True)
            component.set_anim_instance_class(None)
            component.set_skeletal_mesh_asset(None)
            component.set_editor_property('override_materials',[])
            component.set_component_tick_enabled(False)
            actor.set_actor_hidden_in_game(True)
            actor.set_is_temporarily_hidden_in_editor(True)


def load_page(request):
    plan = preflight(request)
    levels = legacy.ensure_level()
    old_ids = displayed_case_ids()
    new_ids = {case['character_id'] for case in plan[0]}
    shared = transfer.shared_runtime()
    shared.verify_baseline()
    legacy.cache()['compatibility'].clear()
    clear_slot_actors()
    releases = []
    try:
        for identifier in sorted(old_ids-new_ids):
            releases.append(transfer.release_saved_case_packages(identifier))
    finally:
        shared.verify_baseline()
    page,loaded,evidence = prepare(request,plan)
    return levels,page,loaded,evidence,releases


def show(request):
    request = contract.normalize_request(request)
    levels,page,loaded,evidence,releases = load_page(request)
    legacy.environment()
    focused = request['focus'] != 'all'
    head_mode = request['framing'] == 'head'
    yaw = {'front':-90.,'side':0.,'back':90.}[request['view']]
    records = []
    for entry in loaded:
        index = entry['slot']
        top = index <= 4
        column = (index-1)%4
        location = unreal.Vector(0.,0. if focused else (column-1.5)*(90. if head_mode else 170.),
                                 0. if focused or not top else (100. if head_mode else 225.))
        label = PREFIX+f'Slot{index:02d}_'
        actor = legacy.actor(label+'Body',unreal.SkeletalMeshActor,location,unreal.Rotator(yaw=yaw))
        actor.set_actor_location(location,False,False)
        actor.set_actor_rotation(unreal.Rotator(yaw=yaw),False)
        actor.set_is_temporarily_hidden_in_editor(False)
        actor.set_actor_hidden_in_game(False)
        body = legacy.component(actor)
        body.set_editor_property('override_materials',[])
        body.set_skeletal_mesh_asset(entry['body'])
        body.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        body.override_animation_data(None,False,False,0.,1.)
        body.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        body.set_editor_property('propagate_curves_to_followers',True)
        body.set_component_tick_enabled(True)
        body.show_all_material_sections(0)
        framing_sections = []
        if head_mode:
            # Component-only framing, reversed on every full-body switch. No
            # mesh, material, topology, outfit occlusion or source asset edits.
            slots = entry['body'].get_editor_property('materials')
            names = [str(slot.get_editor_property('material_slot_name')) for slot in slots]
            allowed = {'Std_Skin_Head_Pbr','Std_Eyelash_Pbr'}
            if 'Std_Skin_Head_Pbr' not in names:
                raise RuntimeError('Cannot frame head without the exact source head material slot')
            subsystem = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
            for section in range(subsystem.get_num_sections(entry['body'],0)):
                material_index = subsystem.get_lod_material_slot(entry['body'],0,section)
                if not 0 <= material_index < len(names):
                    raise RuntimeError('Head framing has no valid section material index')
                visible = names[material_index] in allowed
                body.show_material_section(material_index,section,visible,0)
                if body.is_material_section_shown(material_index,0) != visible:
                    raise RuntimeError('Head framing component visibility readback failed')
                framing_sections.append({'section':section,'material':names[material_index],'visible':visible})
            actual_head = body.get_socket_location('head')
            target_head_z = 30. if focused or not top else 130.
            location.z += target_head_z - actual_head.z
            actor.set_actor_location(location,False,False)
        actual = []
        for row in entry['followers']:
            follower = legacy.actor(label+row['component_name'],unreal.SkeletalMeshActor,location)
            follower.attach_to_actor(actor,'',unreal.AttachmentRule.SNAP_TO_TARGET,
                                     unreal.AttachmentRule.SNAP_TO_TARGET,unreal.AttachmentRule.SNAP_TO_TARGET)
            follower.set_is_temporarily_hidden_in_editor(False)
            follower.set_actor_hidden_in_game(False)
            comp = legacy.component(follower)
            comp.set_editor_property('override_materials',[])
            comp.set_skeletal_mesh_asset(row['mesh'])
            if row['copy_pose']:
                comp.set_leader_pose_component(None,True)
                comp.set_animation_mode(unreal.AnimationMode.ANIMATION_BLUEPRINT)
                comp.set_anim_instance_class(row['copy_pose'].generated_class())
                comp.set_update_animation_in_editor(True)
                comp.add_tick_prerequisite_component(body)
            else:
                comp.set_anim_instance_class(None)
                comp.set_leader_pose_component(body,True)
            comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            comp.set_component_tick_enabled(True)
            if comp.get_skeletal_mesh_asset() != row['mesh']:
                raise RuntimeError('Follower assignment readback failed')
            actual.append({'component':row['component_name'],'mesh':row['mesh_path'],
                           'compatibility':row['compatibility']})
        records.append({'slot':index,'character_id':entry['case']['character_id'],'sex':entry['case']['sex'],
                        'group':entry['case']['group'],'body':entry['body'].get_path_name(),
                        'skeleton':entry['case']['skeleton'],'followers':actual,
                        'head_framing_component_sections':framing_sections})
    # Two comparison rows share one orthographic camera and lighting setup.
    camera = legacy.find(PREFIX+'Camera')
    comp = camera.get_component_by_class(unreal.CameraComponent)
    full_page = not focused
    width = (415. if head_mode else 790.) if full_page else (65. if head_mode else 175.)
    center_z = (92. if head_mode else 205.) if full_page else (42. if head_mode else 92.)
    camera.set_actor_location(unreal.Vector(900.,0.,center_z),False,False)
    camera.set_actor_rotation(unreal.Rotator(yaw=180.),False)
    comp.set_editor_properties({'projection_mode':unreal.CameraProjectionMode.ORTHOGRAPHIC,
        'ortho_width':width,'constrain_aspect_ratio':True,'aspect_ratio':1.65 if full_page else .75})
    floor = legacy.find(PREFIX+'Floor')
    floor.set_actor_scale3d(unreal.Vector(6.,14.,.05))
    floor.set_actor_hidden_in_game(head_mode)
    floor.set_is_temporarily_hidden_in_editor(head_mode)
    wall = legacy.find(PREFIX+'Background')
    wall.set_actor_location(unreal.Vector(-240.,0.,225.),False,False)
    wall.set_actor_scale3d(unreal.Vector(.05,14.,6.))
    levels.pilot_level_actor(camera)
    levels.editor_invalidate_viewports()
    if request['save'] and not levels.save_current_level():
        raise RuntimeError('Could not save batch review level')
    result = {'success':True,'level':contract.LEVEL,'request':request,'displayed':records,
              'page_order':[{'slot':i+1,'character_id':c['character_id'],'sex':c['sex'],'group':c['group']} for i,c in enumerate(page)],
              'sources':evidence,'package_release':releases,'human_acceptance':'pending','scope':'Static review only; individual clothing/hair fit remains visual review.'}
    contract.write(contract.RUN/'runtime/current_case.json',result)
    unreal.SystemLibrary.collect_garbage()
    return result


if __name__ == '__main__':
    result = show(globals().get('DM_CFD40_REQUEST',{}))
    print(MARKER+json.dumps({'success':result['success'],'result_file':str(contract.RUN/'runtime/current_case.json')},ensure_ascii=False))
