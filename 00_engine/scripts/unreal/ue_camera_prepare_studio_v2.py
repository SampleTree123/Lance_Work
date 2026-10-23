"""Root-injected UE preparation of isolated StudioV2 maps and new sequences.

Imports do not connect to UE. Only prepare(u, selected_ids=None) mutates owned
MapsV2 / SequencesV2 assets. Complete hash-matched shot receipts are resumable;
partial assets and failed evidence are preserved and never overwritten.
"""
from __future__ import annotations
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import re
from pathlib import Path
import traceback

S = Path(__file__).resolve().parent
R = Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/camera_motion_pilot_20261009_v1')
A = '/Game/DataMake/Validation/CameraMotionPilot20261009'
CONTENT = Path('D:/UE/projects/datatry_02/Content')
PLAN = R/'camera_motion_pilot_plan_v3.json'
MANIFESTS = ('prepared_jobs_v1.json','paired_edit_prepared_v1.json','retime_prepared_jobs_v1.json')
FACE_COMPONENTS = {'Body','Eyes','Teeth','Tongue','Tearline','EyeOcclusion'}
HAIR_BOUNDS_PROOFS = ('hair_bounds_pose_probe_v2.json','render_receipts/hair_bounds_probe_v2.json')
GENERATION = 3
FACE_COPY_PREFIX = 'DM_CCWH_SLOT_COPY_'
LEGACY_BINDING_REPR_CODE_SHA256 = '3c74f3f04e4091af5710919191e549233bc4e5ef56e1d124c26a20b4f31e6dbc'


def pin(path):
    path=Path(path).resolve(strict=True)
    return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path,value):
    path=Path(path).resolve()
    if not path.is_relative_to(R.resolve()):
        raise ValueError('Evidence outside owned run')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False)
        f.write('\n')


def check(record):
    if pin(record['path'])['sha256']!=record['sha256']:
        raise RuntimeError('Pinned source/output changed: '+record['path'])


def package(asset,suffix='.uasset'):
    asset=asset.split('.')[0]
    if not asset.startswith(A+'/'):
        raise ValueError('Expected owned camera-pilot source package')
    return CONTENT/(asset.removeprefix('/Game/')+suffix)


def module(name):
    spec=importlib.util.spec_from_file_location('_studio_v2_prepare_'+name,S/(name+'.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m


def inputs():
    """Offline-readable exact source selection and immutable source manifest pins."""
    main,pair,extra=[read(R/name) for name in MANIFESTS]
    plan=read(PLAN)
    if len(main['jobs'])!=30 or len(extra['jobs'])!=3 or len(plan['shots'])!=30:
        raise ValueError('Expected 30 main, one pair and three supplemental jobs')
    shots={s['shot_id']:s for s in plan['shots']}
    pair_shot=copy.deepcopy(shots[pair['source_shot_id']])
    pair_shot['shot_id']=pair['job']['shot_id']
    pair_shot['paired_edit_of']=pair['source_shot_id']
    shots[pair_shot['shot_id']]=pair_shot
    extra_plans=[extra['plan']]+extra.get('additional_plans',[])
    for p in extra_plans:
        check(p)
        for shot in read(p['path'])['shots']:
            if shot['shot_id'] in shots:
                raise ValueError('Duplicate shot id')
            shots[shot['shot_id']]=shot
    jobs=main['jobs']+[pair['job']]+extra['jobs']
    if len({j['shot_id'] for j in jobs})!=34 or set(shots)!={j['shot_id'] for j in jobs}:
        raise ValueError('Shot/job identities do not cover exactly 34 entries')
    rows=[]
    for job in jobs:
        sid=job['shot_id']
        if sid==pair['job']['shot_id']:
            receipt_path=R/'paired_edit_prepared_v1.json';receipt=pair
        elif sid in {j['shot_id'] for j in main['jobs']}:
            receipt_path=R/'sequences'/(sid+'.json');receipt=read(receipt_path)
        else:
            receipt_path=R/'retime_sequences'/(sid+'.json');receipt=read(receipt_path)
        if receipt['job']!=job:
            raise ValueError('Source receipt binds a different job')
        for asset in receipt.get('asset_files',[]):
            check(asset)
        animation=receipt['sequence_report']['animation_path']
        sources=[pin(receipt_path),pin(package(job['map'],'.umap')),pin(package(job['sequence'])),pin(package(animation))]
        rows.append({'shot':shots[sid],'source_job':job,'animation_path':animation,'source_files':sources})
    return {'plan':pin(PLAN),'source_manifests':[pin(R/name) for name in MANIFESTS],
            'additional_plan_pins':extra_plans,'rows':rows}


def binding_readback(u,sequence,world):
    prefix=world.get_path_name()+':'
    evidence=[]
    for binding in sequence.get_bindings():
        objects=list(u.MovieSceneSequenceExtensions.locate_bound_objects(sequence,binding,world))
        paths=[o.get_path_name() for o in objects]
        if len(paths)!=1 or not all(path.startswith(prefix) and 'TRASH' not in path for path in paths):
            raise RuntimeError('Sequence binding does not resolve once in current world: '+str(paths))
        guid=binding.get_id().to_string().lower()
        if re.fullmatch(r'[0-9a-f]{32}',guid) is None:
            raise RuntimeError('Binding GUID is not canonical 32-hex text')
        evidence.append({'binding':guid,'objects':paths})
    if len(evidence)!=9:
        raise RuntimeError('Expected character, six skeletal components, camera and camera component bindings')
    if len({row['binding'] for row in evidence})!=9:
        raise RuntimeError('Duplicate sequence binding GUID')
    return sorted(evidence,key=lambda row:row['binding'])


def _legacy_spec_compatible(old,current):
    """Only migrate this script's known GUID repr bug; every other pin exact."""
    if old==current:return False
    revised=copy.deepcopy(old)
    previous=revised.get('code',[])
    if (len(previous)!=3 or len(current.get('code',[]))!=3
            or previous[0].get('sha256')!=LEGACY_BINDING_REPR_CODE_SHA256
            or previous[0].get('path')!=current['code'][0]['path']):
        raise ValueError('Receipt is not the explicitly supported binding-repr version')
    previous[0]=copy.deepcopy(current['code'][0])
    if revised!=current:
        raise ValueError('Legacy receipt has changes beyond verifier implementation')
    return True


def _object_bindings(rows):
    objects=sorted(tuple(row['objects']) for row in rows)
    if len(objects)!=9 or any(len(row)!=1 for row in objects) or len(set(objects))!=9:
        raise RuntimeError('Expected nine unique one-object binding resolutions')
    return objects


def _spec_for(row,source,code):
    shot=row['shot'];sid=shot['shot_id']
    return {'shot_id':sid,'generation':GENERATION,'plan':source['plan'],'source_manifests':source['source_manifests'],
        'additional_plan_pins':source['additional_plan_pins'],'source_files':row['source_files'],
        'code':code,'studio_helper_source':code[2],'trajectory_sha256':shot['trajectory_sha256'],
        'source_job':row['source_job'],'animation_path':row['animation_path'],
        'map_package':A+'/MapsV2/L_'+sid+'_v003','sequence_package':A+'/SequencesV2/LS_'+sid+'_v003'}


def fresh_component(u,actor,name):
    """Property edits may reconstruct every Blueprint component: never cache."""
    found=[c for c in actor.get_components_by_class(u.SkeletalMeshComponent) if c.get_name()==name]
    if len(found)!=1 or 'TRASH' in found[0].get_path_name() or not found[0].get_path_name().startswith(actor.get_path_name()+'.'):
        raise RuntimeError('Expected one live component on current actor: '+name)
    return found[0]


def audit_hair_bounds(u,actor,expected_names=None):
    """Read-only interface for immediate or saved/reloaded scene validation."""
    if not actor.get_path_name().startswith(A+'/MapsV2/'):
        raise ValueError('Hair bounds audit is limited to owned StudioV2 instances')
    names=sorted(c.get_name() for c in actor.get_components_by_class(u.SkeletalMeshComponent)
        if c.get_name().startswith('HairPart') and c.get_editor_property('skeletal_mesh_asset'))
    if len(names)!=len(set(names)) or (expected_names is not None and names!=sorted(expected_names)):
        raise RuntimeError('Hair component inventory changed')
    results=[]
    for name in names:
        body=fresh_component(u,actor,'Body');c=fresh_component(u,actor,name)
        if c.get_attach_parent()!=body or c.get_editor_property('leader_pose_component')!=body:
            raise RuntimeError('Hair must already attach to and follow the same live Body: '+name)
        if c.get_editor_property('use_attach_parent_bound') is not True:
            raise RuntimeError('Hair parent-bound flag did not persist: '+name)
        mesh=c.get_editor_property('skeletal_mesh_asset')
        results.append({'name':name,'component':c.get_path_name(),'mesh':mesh.get_path_name(),
            'attach_parent':body.get_path_name(),'leader_pose_component':body.get_path_name(),
            'use_attach_parent_bound':True})
    return {'scope':'current owned map instance; source Blueprint and meshes not edited',
            'hair_component_names':names,'components':results,'success':True}


def prepare_hair_bounds(u,actor):
    """Enable parent bounds only for populated HairPart instances; no reparent."""
    if not actor.get_path_name().startswith(A+'/MapsV2/'):
        raise ValueError('Hair bounds edits are limited to owned StudioV2 instances')
    names=sorted(c.get_name() for c in actor.get_components_by_class(u.SkeletalMeshComponent)
        if c.get_name().startswith('HairPart') and c.get_editor_property('skeletal_mesh_asset'))
    if len(names)!=len(set(names)):
        raise RuntimeError('Duplicate HairPart names')
    before=[];mesh_pins=[]
    for name in names:
        body=fresh_component(u,actor,'Body');c=fresh_component(u,actor,name)
        if c.get_attach_parent()!=body or c.get_editor_property('leader_pose_component')!=body:
            raise RuntimeError('Hair parent/leader must already be Body: '+name)
        mesh=c.get_editor_property('skeletal_mesh_asset')
        mesh_path=mesh.get_path_name()
        if not mesh_path.startswith('/Game/'):
            raise RuntimeError('Unexpected non-project hair mesh')
        mesh_pin=pin(CONTENT/(mesh_path.split('.')[0].removeprefix('/Game/')+'.uasset'))
        before.append({'name':name,'mesh':mesh_path,'use_attach_parent_bound':bool(c.get_editor_property('use_attach_parent_bound'))})
        mesh_pins.append(mesh_pin)
        # The next property edit can invalidate c, body, and every prior ref.
        # Retain only the stable name and reacquire before every operation.
        fresh_component(u,actor,name).set_editor_property('use_attach_parent_bound',True)
        current=fresh_component(u,actor,name);current_body=fresh_component(u,actor,'Body')
        if (current.get_editor_property('skeletal_mesh_asset').get_path_name()!=mesh_path
                or current.get_attach_parent()!=current_body
                or current.get_editor_property('leader_pose_component')!=current_body
                or current.get_editor_property('use_attach_parent_bound') is not True):
            raise RuntimeError('Reconstructed hair state did not read back correctly: '+name)
    after=audit_hair_bounds(u,actor,names)
    for source in mesh_pins:check(source)
    return {'before':before,'after':after,'source_meshes_unchanged':mesh_pins,
        'parent_changed':False,'blueprint_asset_edited':False,
        'evidence':[pin(R/name) for name in HAIR_BOUNDS_PROOFS],
        'save_reload_validation':'caller must invoke audit_hair_bounds after explicit map reload'}


def _parent_bound_names(u,actor):
    names=[]
    for c in actor.get_components_by_class(u.SkeletalMeshComponent):
        if c.get_name()=='Body' or not c.get_editor_property('skeletal_mesh_asset'):
            continue
        if c.get_attach_parent()==fresh_component(u,actor,'Body'):
            names.append(c.get_name())
    if len(names)!=len(set(names)):raise RuntimeError('Duplicate parent-bound component names')
    return sorted(names)


def _component_source_state(u,actor,name):
    c=fresh_component(u,actor,name);body=fresh_component(u,actor,'Body')
    if c.get_attach_parent()!=body:raise RuntimeError('Component is no longer attached to Body: '+name)
    leader=c.get_editor_property('leader_pose_component')
    anim_class=c.get_editor_property('anim_class')
    class_path=anim_class.get_path_name() if anim_class is not None else None
    mode=str(c.get_editor_property('animation_mode'))
    if leader is not None and leader!=body:raise RuntimeError('Unexpected non-Body leader: '+name)
    if leader is None and name not in FACE_COMPONENTS:
        # Do not silently convert a follower's original animation relationship.
        # An explicitly named CopyPose class can remain independently animated.
        if not class_path or not any(word in class_path.casefold() for word in ('copypose','copy_pose')):
            raise RuntimeError('Non-face follower lacks Body leader or explicit CopyPose class: '+name)
    return {'name':name,'mesh':c.get_editor_property('skeletal_mesh_asset').get_path_name(),
        'attach_parent':body.get_path_name(),'leader_pose_component':leader.get_path_name() if leader is not None else None,
        'animation_class':class_path,'animation_mode':mode}


def audit_component_parent_bounds(u,actor,expected_names=None):
    """Read-only reload audit for clothing, hair and independently animated face."""
    if not actor.get_path_name().startswith(A+'/MapsV2/'):
        raise ValueError('Only owned StudioV2 map instances may be inspected')
    names=_parent_bound_names(u,actor)
    if expected_names is not None and names!=sorted(expected_names):
        raise RuntimeError('Body-attached populated component inventory changed')
    rows=[]
    for name in names:
        state=_component_source_state(u,actor,name)
        c=fresh_component(u,actor,name)
        if c.get_editor_property('use_attach_parent_bound') is not True:
            raise RuntimeError('Body-attached component lost parent bounds: '+name)
        state.update({'component':c.get_path_name(),'use_attach_parent_bound':True})
        rows.append(state)
    return {'success':True,'component_names':names,'components':rows,
        'scope':'populated non-Body SkeletalMesh components already attached to Body'}


def prepare_component_parent_bounds(u,actor):
    """Change only instance bounds flags, preserving parent/leader/animation."""
    if not actor.get_path_name().startswith(A+'/MapsV2/'):
        raise ValueError('Only owned StudioV2 map instances may be changed')
    names=_parent_bound_names(u,actor);before=[];source_meshes=[]
    for name in names:
        state=_component_source_state(u,actor,name)
        was_enabled=bool(fresh_component(u,actor,name).get_editor_property('use_attach_parent_bound'))
        before.append(dict(state,use_attach_parent_bound=was_enabled))
        if not state['mesh'].startswith('/Game/'):raise RuntimeError('Non-project component mesh')
        source_meshes.append(pin(CONTENT/(state['mesh'].split('.')[0].removeprefix('/Game/')+'.uasset')))
        if not was_enabled:
            fresh_component(u,actor,name).set_editor_property('use_attach_parent_bound',True)
        if _component_source_state(u,actor,name)!=state:
            raise RuntimeError('Reconstruction changed parent, leader, mesh or animation: '+name)
        if fresh_component(u,actor,name).get_editor_property('use_attach_parent_bound') is not True:
            raise RuntimeError('Bounds readback failed: '+name)
    after=audit_component_parent_bounds(u,actor,names)
    for item in source_meshes:check(item)
    return {'before':before,'after':after,'source_meshes_unchanged':source_meshes,
        'parent_changed':False,'leader_changed':False,'animation_changed':False,'blueprint_asset_edited':False,
        'evidence':pin(R/'studio_three_pose_probe_v2.json'),'generation':GENERATION}


def prepare_face_route_tags(u,actor):
    """Persist UCS's existing leader=None route; do not set a CopyPose class."""
    if not actor.get_path_name().startswith(A+'/MapsV2/'):
        raise ValueError('Face routing tags are limited to owned map instances')
    before=[str(tag) for tag in actor.get_editor_property('tags')]
    required=[FACE_COPY_PREFIX+name for name in sorted(FACE_COMPONENTS-{'Body'})]
    after=before+[tag for tag in required if tag not in before]
    if after!=before:
        actor.set_editor_property('tags',[u.Name(tag) for tag in after])
    actual=[str(tag) for tag in actor.get_editor_property('tags')]
    if not set(required)<=set(actual) or not set(before)<=set(actual):
        raise RuntimeError('Actor COPY route tags did not persist without dropping prior tags')
    return {'before':before,'after':actual,'required_face_tags':required,
        'scope':'saved actor-instance routing only; original Blueprint branch reused, no CopyPose class assignment',
        'construction_source':pin(S/'ue_complete_character_fixed_slot_runtime_v1.py')}


def audit_face_animation(u,actor,expected_animation):
    """Check five independent face components and Body after explicit reload."""
    tags=[str(tag) for tag in actor.get_editor_property('tags')]
    required=[FACE_COPY_PREFIX+name for name in sorted(FACE_COMPONENTS-{'Body'})]
    if not set(required)<=set(tags):
        raise RuntimeError('Reload lost persistent independent-face routing tags')
    rows=[]
    for name in sorted(FACE_COMPONENTS):
        c=fresh_component(u,actor,name)
        if c.get_editor_property('leader_pose_component') is not None:
            raise RuntimeError('Body/independent face unexpectedly follows a leader: '+name)
        row={'name':name,'component':c.get_path_name(),'leader_pose_component':None,
            'animation_mode':str(c.get_editor_property('animation_mode'))}
        try:
            animation=c.get_editor_property('animation_data').get_editor_property('anim_to_play')
        except (AttributeError,RuntimeError) as exc:
            row.update({'animation_data_readable':False,'readback_limitation':str(exc)})
        else:
            actual=animation.get_path_name() if animation is not None else None
            if actual is None or actual.split('.')[0]!=expected_animation.split('.')[0]:
                raise RuntimeError('Saved independent animation clip differs: '+name+' '+str(actual))
            row.update({'animation_data_readable':True,'animation_path':actual})
        rows.append(row)
    return {'success':True,'required_face_tags':required,'components':rows,
        'all_six_animation_data_readable':all(row['animation_data_readable'] for row in rows)}


def _load(u,path):
    package_name=path.split('.')[0]
    u.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
    levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if not levels.load_level(package_name):
        raise RuntimeError('Could not explicitly load '+package_name)
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    if world.get_path_name().split('.')[0]!=package_name:
        raise RuntimeError('Current world differs after explicit load')
    return world


def _resume(u,path,spec):
    receipt=read(path)
    if receipt.get('success') is not True:
        raise ValueError('Existing StudioV2 receipt is not successful')
    legacy=_legacy_spec_compatible(receipt.get('spec'),spec)
    for record in receipt['asset_files']:
        check(record)
    world=_load(u,receipt['job']['map'])
    actors=list(u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors())
    selected=[a for a in actors if a.get_actor_label()==receipt['character_label']]
    if len(selected)!=1:
        raise RuntimeError('Resumed map lacks exact character')
    hair=audit_hair_bounds(u,selected[0],receipt['hair_bounds']['after']['hair_component_names'])
    if hair!=receipt['hair_bounds_saved_reload']:
        raise RuntimeError('Saved hair bounds readback changed')
    components=audit_component_parent_bounds(u,selected[0],receipt['component_parent_bounds']['after']['component_names'])
    if components!=receipt['component_parent_bounds_saved_reload']:
        raise RuntimeError('Saved clothing/face/hair parent bounds changed')
    face=audit_face_animation(u,selected[0],spec['animation_path'])
    if face!=receipt['face_animation_saved_reload']:
        raise RuntimeError('Saved independent face animation changed')
    sequence=u.load_asset(receipt['job']['sequence'])
    actual=binding_readback(u,sequence,world)
    if legacy:
        if _object_bindings(actual)!=_object_bindings(receipt['binding_readback']):
            raise RuntimeError('Legacy StudioV2 binding object resolutions changed')
    elif actual!=sorted(receipt['binding_readback'],key=lambda row:row['binding']):
        raise RuntimeError('Existing StudioV2 bindings changed')
    if legacy:
        # No save or asset edit: hash both packages again after readback, and
        # preserve the original receipt byte-for-byte. This separate evidence
        # upgrades only unverifiable memory-address reprs to real GUID text.
        for record in receipt['asset_files']:check(record)
        audit={'schema':'camera_binding_guid_resume_audit_v1','success':True,
            'migration':'known Python GUID memory repr to stable to_string; verifier only',
            'shot_id':receipt['job']['shot_id'],'legacy_receipt':pin(path),
            'legacy_prepare_sha256':LEGACY_BINDING_REPR_CODE_SHA256,'current_spec':spec,
            'asset_files_unchanged':receipt['asset_files'],'binding_readback':actual,
            'object_bindings_equal':True,'hair_bounds_unchanged':True,
            'component_parent_bounds_unchanged':True,'independent_face_animation_unchanged':True,
            'assets_rewritten':False,'legacy_receipt_rewritten':False}
        audit_path=R/'binding_resume_audits_v1'/(receipt['job']['shot_id']+'.json')
        if audit_path.exists():
            if read(audit_path)!=audit:raise RuntimeError('Existing GUID continuation audit differs')
        else:save(audit_path,audit)
    return receipt['job']


def prepare(u,selected_ids=None):
    if Path(u.Paths.project_dir()).resolve()!=CONTENT.parent.resolve():
        raise ValueError('Wrong UE project')
    queue=u.get_editor_subsystem(u.MoviePipelineQueueSubsystem)
    if queue.is_rendering() or queue.get_active_executor() is not None:
        raise RuntimeError('Cannot prepare while render executor is active')
    if list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages()):
        raise RuntimeError('A dirty map exists; no implicit save/discard')
    source=inputs();builder=module('ue_camera_sequence_builder_v1');studio=module('ue_camera_studio_lighting_v2')
    code=[pin(__file__),pin(builder.__file__),pin(studio.__file__)]
    selected={r['shot']['shot_id'] for r in source['rows']} if selected_ids is None else set(selected_ids)
    known={r['shot']['shot_id'] for r in source['rows']}
    if not selected<=known:
        raise ValueError('Unknown selected shot ids: '+str(selected-known))
    jobs=[]
    for row in source['rows']:
        shot=row['shot'];sid=shot['shot_id']
        if sid not in selected:
            continue
        map_path=A+'/MapsV2/L_'+sid+'_v003'
        seq_path=A+'/SequencesV2/LS_'+sid+'_v003'
        receipt_path=R/'sequences_v3'/(sid+'.json')
        spec=_spec_for(row,source,code)
        if receipt_path.exists():
            jobs.append(_resume(u,receipt_path,spec));continue
        if u.EditorAssetLibrary.does_asset_exist(map_path) or u.EditorAssetLibrary.does_asset_exist(seq_path):
            raise RuntimeError('Partial StudioV2 asset exists; inspect without overwrite: '+sid)
        report={'schema':'camera_studio_prepared_shot_v2','success':False,'spec':spec}
        try:
            original_world=_load(u,row['source_job']['map'])
            if not u.EditorLoadingAndSavingUtils.save_map(original_world,map_path):
                raise RuntimeError('Could not clone old scene')
            world=_load(u,map_path)
            lighting=studio.apply(u,world)
            actors=list(u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors())
            actor_list=[a for a in actors if a.get_actor_label()=='DM_CCWH_'+shot['sex']+'_Character']
            cameras=[a for a in actors if a.get_actor_label()=='DM_CCWH_Camera']
            if len(actor_list)!=1 or len(cameras)!=1:
                raise RuntimeError('Expected exact same-sex actor and camera')
            actor,camera=actor_list[0],cameras[0]
            for a in actors:
                if a.get_actor_label().endswith('_Character'):
                    a.set_actor_hidden_in_game(a!=actor)
                    a.set_actor_location(u.Vector(0,0,0),False,False)
                    a.set_actor_rotation(u.Rotator(0,0,0),False)
                    a.set_actor_scale3d(u.Vector(1,1,1))
            motion=u.load_asset(row['animation_path'])
            if not isinstance(motion,u.AnimSequence):
                raise RuntimeError('Source composite is not an animation')
            # Tags select the existing UCS leader=None branch before later
            # reconstruction-causing component writes and before map reload.
            face_route_tags=prepare_face_route_tags(u,actor)
            hair_bounds=prepare_hair_bounds(u,actor)
            component_parent_bounds=prepare_component_parent_bounds(u,actor)
            # All editor-property writes happen by stable name. The Blueprint
            # may reconstruct other components as well as the one being set.
            component_names=[c.get_name() for c in actor.get_components_by_class(u.SkeletalMeshComponent)
                if 'TRASH' not in c.get_path_name()]
            for name in component_names:
                fresh_component(u,actor,name).set_editor_property('visibility_based_anim_tick_option',u.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
            found=FACE_COMPONENTS & set(component_names)
            if found!=FACE_COMPONENTS:
                raise RuntimeError('Incomplete body and five facial components')
            for name in sorted(FACE_COMPONENTS):
                fresh_component(u,actor,name).set_leader_pose_component(None,True,False)
                fresh_component(u,actor,name).override_animation_data(motion,False,False,0.,1.)
            # Snapshot followers only after all reconstruction-causing edits.
            followers=[fresh_component(u,actor,name) for name in sorted(FACE_COMPONENTS-{'Body'})]
            hair_bounds['after']=audit_hair_bounds(u,actor,hair_bounds['after']['hair_component_names'])
            component_parent_bounds['after']=audit_component_parent_bounds(u,actor,component_parent_bounds['after']['component_names'])
            face_animation_before_save=audit_face_animation(u,actor,row['animation_path'])
            comp=camera.get_component_by_class(u.CameraComponent)
            comp.set_editor_property('aspect_ratio',16/9);comp.set_editor_property('constrain_aspect_ratio',True)
            first=shot['frames'][0]
            camera.set_actor_location(u.Vector(*first['position']),False,False)
            camera.set_actor_rotation(u.Rotator(*first['rotation_pitch_yaw_roll']),False)
            comp.set_field_of_view(first['horizontal_fov_degrees'])
            built=builder.build_sequence(u,shot,actor,camera,motion,seq_path)
            for c in followers:
                builder.add_animation_component_track(u,built['sequence'],built['actor_binding'],c,motion,
                    source_start_seconds=float(shot.get('window_start_seconds',0)))
            bindings=binding_readback(u,built['sequence'],world)
            if not u.EditorAssetLibrary.save_loaded_asset(built['sequence'],False):
                raise RuntimeError('Cannot save rebuilt sequence')
            u.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
            if not u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level():
                raise RuntimeError('Cannot save StudioV2 scene')
            # Reopen from disk to prove flags and bindings survive persistence.
            character_label=actor.get_actor_label()
            world=_load(u,map_path)
            reloaded_actors=list(u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors())
            selected_actors=[a for a in reloaded_actors if a.get_actor_label()==character_label]
            if len(selected_actors)!=1:raise RuntimeError('Saved map character did not reload uniquely')
            hair_saved=audit_hair_bounds(u,selected_actors[0],hair_bounds['after']['hair_component_names'])
            component_bounds_saved=audit_component_parent_bounds(u,selected_actors[0],component_parent_bounds['after']['component_names'])
            face_animation_saved=audit_face_animation(u,selected_actors[0],row['animation_path'])
            for source_mesh in hair_bounds['source_meshes_unchanged']:check(source_mesh)
            for source_mesh in component_parent_bounds['source_meshes_unchanged']:check(source_mesh)
            sequence=u.load_asset(seq_path)
            bindings=binding_readback(u,sequence,world)
            for record in row['source_files']+source['source_manifests']+code+[source['plan']]:check(record)
            job={'shot_id':sid,'map':world.get_path_name(),'sequence':sequence.get_path_name()}
            report.update({'success':True,'status':'prepared_pending_render_and_visual_review','job':job,
                'plan':source['plan'],'studio_helper_source':code[2],'source_manifests':source['source_manifests'],
                'sequence_report':built['report'],'face_component_tracks':sorted(FACE_COMPONENTS-{'Body'}),
                'character_label':character_label,'hair_bounds':hair_bounds,'hair_bounds_saved_reload':hair_saved,
                'generation':GENERATION,'component_parent_bounds':component_parent_bounds,
                'component_parent_bounds_saved_reload':component_bounds_saved,
                'face_route_tags':face_route_tags,'face_animation_before_save':face_animation_before_save,
                'face_animation_saved_reload':face_animation_saved,
                'binding_readback':bindings,'lighting_report':lighting,'human_visual_acceptance':'pending',
                'asset_files':[pin(package(map_path,'.umap')),pin(package(seq_path))]})
            save(receipt_path,report);jobs.append(job)
            print('Prepared StudioV2 '+sid)
        except Exception:
            report['error']=traceback.format_exc()
            failure=R/'sequences_v3_failures'/(sid+'_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
            save(failure,report)
            raise
    # Only publish the aggregate if all 34 unique receipts exist and still bind
    # this exact v3 plan, source-manifest list, helper code, map and sequence.
    all_jobs=[];all_receipts=[];migration_audits=[]
    for row in source['rows']:
        receipt_path=R/'sequences_v3'/(row['shot']['shot_id']+'.json')
        if not receipt_path.exists():break
        receipt=read(receipt_path)
        if receipt.get('success') is not True:
            raise RuntimeError('Aggregate contains stale StudioV2 receipt')
        expected_spec=_spec_for(row,source,code)
        legacy=_legacy_spec_compatible(receipt['spec'],expected_spec)
        for record in receipt['asset_files']:check(record)
        if legacy:
            audit_path=R/'binding_resume_audits_v1'/(row['shot']['shot_id']+'.json')
            audit=read(audit_path)
            if (audit.get('success') is not True or audit.get('current_spec')!=expected_spec
                    or audit.get('legacy_receipt')!=pin(receipt_path)
                    or audit.get('asset_files_unchanged')!=receipt['asset_files']
                    or audit.get('object_bindings_equal') is not True
                    or audit.get('assets_rewritten') is not False
                    or audit.get('legacy_receipt_rewritten') is not False
                    or _object_bindings(audit['binding_readback'])!=_object_bindings(receipt['binding_readback'])):
                raise RuntimeError('Legacy receipt lacks exact read-only GUID continuation audit')
            migration_audits.append(pin(audit_path))
        all_jobs.append(receipt['job']);all_receipts.append(pin(receipt_path))
    if len(all_jobs)==34:
        final={'schema':'camera_pilot_prepared_jobs_v2','generation':GENERATION,'success':True,'status':'prepared_pending_render_and_visual_review',
            'plan':source['plan'],'source_manifests':source['source_manifests'],'jobs':all_jobs,
            'job_count':34,'sequence_receipts':all_receipts,'code':code,'studio_helper_source':code[2],
            'binding_guid_resume_audits':migration_audits,
            'legacy_binding_repr_receipt_count':len(migration_audits),
            'human_visual_acceptance':'pending'}
        aggregate=R/'prepared_jobs_v2.json'
        if aggregate.exists():
            if read(aggregate)!=final:raise RuntimeError('Existing final manifest differs; refusing overwrite')
        else:save(aggregate,final)
    return jobs
