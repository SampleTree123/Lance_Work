"""Root-injected scene survey and collision evidence. SCENE_CAMERA_SEQUENCE §11."""
import json, math
from pathlib import Path
import ue_motion_portrait_scene_pilot_v1 as base
from scene_path_relocation_v1 import resolve_current_path

RUN=base.RUN;A=base.A
MAPS={'gas_station':'/Game/DesertGasStation/Maps/DesertGasStation_01','parking':'/Game/QA_ModularParking/Maps/Map_demonstration','japanese_village':'/Game/Japanese_Village/Levels/L_Showcase'}
MAPS.update(cherry_tree='/Game/CHERRY_TREE/Maps/L_Demo_scene',highway='/Game/Evening_Highway/Maps/demo_level')

def current_map(scene_id):
    return resolve_current_path(MAPS[scene_id])

def survey(u,scene_id,location,target):
    base.clean(u);levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
    source_map=current_map(scene_id)
    source_pin=base.pin(base.package(source_map,'.umap'))
    dest=A+'/Surveys/L_'+scene_id;seqpath=A+'/Surveys/LS_'+scene_id
    assert not u.EditorAssetLibrary.does_asset_exist(dest) and not u.EditorAssetLibrary.does_asset_exist(seqpath)
    assert levels.load_level(source_map)
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    assert u.EditorLoadingAndSavingUtils.save_map(world,dest);assert levels.load_level(dest)
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    removed=[]
    for actor in list(actors.get_all_level_actors()):
        if isinstance(actor,u.LevelSequenceActor):
            removed.append(actor.get_actor_label());assert actors.destroy_actor(actor)
    direction=[b-a for a,b in zip(location,target)]
    rotation=u.Rotator(pitch=math.degrees(math.atan2(direction[2],math.hypot(*direction[:2]))),yaw=math.degrees(math.atan2(direction[1],direction[0])),roll=0)
    camera=actors.spawn_actor_from_class(u.CameraActor,u.Vector(*location),rotation)
    camera.set_actor_label('DM_Scene_Survey_Camera')
    comp=camera.get_component_by_class(u.CameraComponent);comp.set_field_of_view(65.)
    comp.set_editor_property('aspect_ratio',16/9);comp.set_editor_property('constrain_aspect_ratio',True)
    folder,name=seqpath.rsplit('/',1);seq=u.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,u.LevelSequence,u.LevelSequenceFactoryNew())
    seq.set_display_rate(u.FrameRate(30,1));seq.set_tick_resolution_directly(u.FrameRate(24000,1));seq.set_playback_start(0);seq.set_playback_end(30)
    binding=seq.add_possessable(camera);cut=seq.add_track(u.MovieSceneCameraCutTrack).add_section();cut.set_range(0,30);cut.set_camera_binding_id(seq.get_binding_id(binding))
    assert u.EditorAssetLibrary.save_loaded_asset(seq,False);assert levels.save_current_level();base.clean(u)
    assert base.pin(source_pin['path'])==source_pin
    job={'shot_id':'survey_'+scene_id,'map':world.get_path_name(),'sequence':seq.get_path_name()}
    base.save(RUN/'scene_surveys'/(scene_id+'.json'),{'success':True,'job':job,'location':location,'target':target,'source_pin':source_pin,'removed_demo_sequence_actors':removed,'source_unchanged':True})
    return job

def ground_grid(u,scene_id,xs,ys,z_top,z_bottom,report_tag='v1',allowed_labels=None,yaw_degrees=0.):
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    assert scene_id in world.get_path_name() or world.get_path_name().split('.')[0]==current_map(scene_id)
    def trace(x,y):
        h=u.SystemLibrary.line_trace_single(world,u.Vector(x,y,z_top),u.Vector(x,y,z_bottom),u.TraceTypeQuery.ECC_VISIBILITY,True,[],u.DrawDebugTrace.NONE)
        if not h:return None
        v=h.to_tuple();return {'position':[v[5].x,v[5].y,v[5].z],'normal':[v[7].x,v[7].y,v[7].z],'actor':v[9].get_actor_label() if v[9] else None}
    points=[]
    angle=math.radians(yaw_degrees);cosine=math.cos(angle);sine=math.sin(angle)
    # Full selected library envelope translated around a common point, with margin.
    for x in xs:
        for y in ys:
            hits=[trace(x+cosine*dx-sine*dy,y+sine*dx+cosine*dy) for dx in (-200,75,350) for dy in (-150,200,520)]
            if not all(hits):continue
            if allowed_labels and any(not any(label.lower() in (h['actor'] or '').lower() for label in allowed_labels) for h in hits):continue
            heights=[h['position'][2] for h in hits]
            point={'root_xy':[x,y],'height_min':min(heights),'height_max':max(heights),'height_range':max(heights)-min(heights),'min_normal_z':min(h['normal'][2] for h in hits),'actors':sorted({h['actor'] for h in hits if h['actor']})}
            if point['height_range']<=5 and point['min_normal_z']>.995:points.append(point)
    report={'scene_id':scene_id,'world':world.get_path_name(),'candidate_count':len(points),'flat_ground_candidates':sorted(points,key=lambda p:p['height_range']),'grid_spacing_note':'Coarse geometric candidates; actor silhouettes/occlusion still need rendering','criteria':{'height_range_cm_max':5,'normal_z_min':.995,'body_envelope_xy_cm':[[-200,350],[-150,520]],'yaw_degrees':yaw_degrees,'allowed_labels':allowed_labels,'x_coordinates':list(xs),'y_coordinates':list(ys),'z_top':z_top,'z_bottom':z_bottom}}
    base.save(RUN/('scene_ground_grid_'+scene_id+'_'+report_tag+'.json'),report)
    return {'candidates':len(points),'first':report['flat_ground_candidates'][:6]}

def clearance(u,scene_id,candidates,report_tag='v1'):
    """Read-only sparse camera sightline/movement screen, no character present."""
    base.clean(u);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    assert scene_id in world.get_path_name() or world.get_path_name().split('.')[0]==current_map(scene_id)
    evidence=RUN/'scene_camera_space_screening_v1.json';data=base.read(evidence)
    reports=[]
    def trans(v,a,yaw):
        theta=math.radians(yaw);c=math.cos(theta);s=math.sin(theta)
        return [a[0]+c*v[0]-s*v[1],a[1]+s*v[0]+c*v[1],a[2]+v[2]]
    def blocked(start,end):
        h=u.SystemLibrary.line_trace_single(world,u.Vector(*start),u.Vector(*end),u.TraceTypeQuery.ECC_VISIBILITY,True,[],u.DrawDebugTrace.NONE)
        if not h:return None
        v=h.to_tuple()
        return {'actor':v[9].get_actor_label() if v[9] else None,'distance':float(v[3]),'point':[v[5].x,v[5].y,v[5].z]}
    for candidate in candidates:
        anchor=candidate['anchor_cm'];yaw=candidate.get('yaw_degrees',0);failures=[];clear=0;sample_count=0;blocked_samples=0
        for path in data['paths']:
            bad=0;first=None;previous=None
            for sample in path['samples']:
                camera=trans(sample['camera_cm'],anchor,yaw);target=trans(sample['look_at_cm'],anchor,yaw)
                hit=blocked(camera,target)
                if hit is None and previous:hit=blocked(previous,camera)
                previous=camera;sample_count+=1
                if hit:
                    bad+=1;blocked_samples+=1
                    if first is None:first=dict(hit,t=sample['t'])
            if bad:failures.append({'motion_id':path['motion_id'],'camera_id':path['camera_id'],'orientation':path['orientation'],'blocked_samples':bad,'first':first})
            else:clear+=1
        reports.append(dict(candidate,clear_paths=clear,total_paths=len(data['paths']),sample_count=sample_count,blocked_samples=blocked_samples,failures=failures))
    result={'scene_id':scene_id,'world':world.get_path_name(),'source_screening':base.pin(evidence),'candidates':reports,'scope':'Visibility collision rays at sparse camera samples and between successive samples; body/near-plane volume and collisionless props still require mesh/render inspection. Zero blocked paths is screening evidence, not final universal visual acceptance.'}
    base.save(RUN/('scene_clearance_'+scene_id+'_'+report_tag+'.json'),result)
    return [{'anchor':r['anchor_cm'],'clear_paths':r['clear_paths'],'total_paths':r['total_paths'],'blocked_samples':r['blocked_samples']} for r in reports]
