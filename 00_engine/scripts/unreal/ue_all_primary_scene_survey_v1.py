"""Coordinator-executed, read-only UE map survey; no level loads or asset saves.

Start once per already loaded primary map. Slate ticks bound the work. Existing
runtime8 trace/check functions perform the full 1260-shot sampled matrix at the
best candidate, with a bounded alternative attempt if findings remain.
"""
from pathlib import Path
import copy
import json
import math
import time
import traceback
import unreal as u
import scene_site_survey_v1 as offline
import scene_site_review_geometry_v1 as geo
import ue_scene_site_review_v1 as worker

RUN=offline.RUN
LIVE='_dm_all_primary_scene_survey_v1'


def world():return u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
def map_path():return world().get_path_name().split('.')[0]
def xyz(v):return [float(v.x),float(v.y),float(v.z)]
def safe(call):
    try:return worker._plain(call())
    except Exception as exc:return {'unavailable':str(exc)}


def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False),encoding='utf-8')
    temp.replace(path)


def checkpoint(job):
    """Persist recoverable candidate evidence; partial matrices are never passes."""
    data={'schema':'all_primary_scene_survey_checkpoint_v1',**status_snapshot(job),
        'scene':job['scene'],'source_pins':job['source_pins'],
        'scene_signature':job.get('scene_signature_start'),
        'ground_candidates':job['ground_candidates'],'screen_candidates':job['screen_candidates'],
        'completed_full_attempts':job['full_attempts'],
        'resume_policy':'Reuse persisted candidate positions as extra_seeds; restart any incomplete full matrix, never promote partial counters to a pass.'}
    write(Path(job['run'])/'checkpoints'/(job['id']+'.json'),data)


def _job():return getattr(u,LIVE,None)


def ray(a,b):
    j=_job();ignored=j['ignored'] if j else []
    return worker.hit_data(u.SystemLibrary.line_trace_single(world(),u.Vector(*a),u.Vector(*b),
        u.TraceTypeQuery.ECC_VISIBILITY,True,ignored,u.DrawDebugTrace.NONE))


def sphere(a,b,radius):
    j=_job();ignored=j['ignored'] if j else []
    return worker.hit_data(u.SystemLibrary.sphere_trace_single(world(),u.Vector(*a),u.Vector(*b),
        radius,u.TraceTypeQuery.ECC_VISIBILITY,True,ignored,u.DrawDebugTrace.NONE))


def worker_call(function,*args):
    # Reuse runtime8 classification exactly, without changing its UI session or
    # leaving patched trace functions installed between Slate ticks.
    old_ray,old_sphere=worker.ray,worker.sphere
    worker.ray,worker.sphere=ray,sphere
    try:return function(*args)
    finally:worker.ray,worker.sphere=old_ray,old_sphere


def inventory_actor(actor):
    row={'label':safe(actor.get_actor_label),'path':safe(actor.get_path_name),
        'class':safe(lambda:actor.get_class().get_name()),'location':xyz(actor.get_actor_location()),
        'rotation':safe(actor.get_actor_rotation),'collision_enabled':safe(actor.get_actor_enable_collision)}
    try:
        center,extent=actor.get_actor_bounds(False)
        row.update(bounds_origin=xyz(center),bounds_extent=xyz(extent))
    except Exception as exc:row['bounds_unavailable']=str(exc)
    try:
        primitives=actor.get_components_by_class(u.PrimitiveComponent)
        row['primitive_components']=len(primitives)
        row['collisionless_or_visibility_ignored_components']=sum(1 for c in primitives
            if 'NO_COLLISION' in str(c.get_collision_enabled()).upper()
            or 'IGNORE' in str(c.get_collision_response_to_channel(u.CollisionChannel.ECC_VISIBILITY)).upper())
    except Exception:row['collision_components_unavailable']=True
    return row


def lighting_actor(actor):
    result=[]
    for c in actor.get_components_by_class(u.LightComponentBase):
        row={'actor':actor.get_actor_label(),'component':c.get_path_name(),'class':c.get_class().get_name()}
        for key in ('intensity','intensity_units','light_color','temperature','use_temperature','attenuation_radius','indirect_lighting_intensity','volumetric_scattering_intensity','visible'):
            row[key]=safe(lambda key=key:c.get_editor_property(key))
        result.append(row)
    if isinstance(actor,u.PostProcessVolume):
        settings=actor.get_editor_property('settings')
        row={'actor':actor.get_actor_label(),'class':'PostProcessVolume'}
        for key in ('unbound','priority','blend_radius','blend_weight'):
            row[key]=safe(lambda key=key:actor.get_editor_property(key))
        for key in ('override_auto_exposure_method','auto_exposure_method','override_auto_exposure_bias','auto_exposure_bias',
            'auto_exposure_min_brightness','auto_exposure_max_brightness','auto_exposure_apply_physical_camera_exposure',
            'override_white_temp','white_temp','exposure_compensation_curve'):
            row[key]=safe(lambda key=key:settings.get_editor_property(key))
        result.append(row)
    return result


def _ground_candidate(seed,job):
    p=seed['position'];h=ray([p[0],p[1],p[2]+300],[p[0],p[1],p[2]-5000])
    yield
    if not h:return {'seed':seed,'eligible':False,'reason':'no_visibility_channel_ground_hit'}
    point=h['point'];findings=[]
    if h['normal'][2]<offline.POLICY['ground_min_normal_z']:findings.append({'kind':'ground_slope','hit':h})
    radius=offline.POLICY['ground_probe_radius_cm']
    for dx,dy in ((-1,-1),(-1,0),(-1,1),(0,-1),(0,0),(0,1),(1,-1),(1,0),(1,1)):
        probe=ray([point[0]+dx*radius,point[1]+dy*radius,point[2]+40],
            [point[0]+dx*radius,point[1]+dy*radius,point[2]-100]);yield
        if not probe:findings.append({'kind':'ground_missing','offset':[dx*radius,dy*radius]})
        elif abs(probe['point'][2]-point[2])>offline.POLICY['ground_flat_tolerance_cm']:
            findings.append({'kind':'ground_height','hit':probe})
        elif probe['normal'][2]<offline.POLICY['ground_min_normal_z']:findings.append({'kind':'ground_slope','hit':probe})
    hit=sphere([point[0],point[1],point[2]+40],[point[0],point[1],point[2]+145],25.);yield
    if hit:findings.append({'kind':'standing_clearance','hit':hit})
    return {'seed':seed,'position':point,'support_hit':h,'eligible':not findings,
        'findings':findings,'scope':'Visibility-channel standing-region screen; not mesh clearance proof'}


def _screen(position,yaw,job):
    p=position;transform=lambda value:geo.transform_point(value,p,yaw)
    record={'position':p,'yaw':yaw,'counts':{},'findings':[],'query_count':0}
    def finding(kind,query,hit=None):
        record['counts'][kind]=record['counts'].get(kind,0)+1
        if len(record['findings'])<40:record['findings'].append({'kind':kind,'query':query,'hit':hit})
    for probe in job['proxies']['ground']:
        q=transform(probe['position']);h=ray([q[0],q[1],p[2]+80],[q[0],q[1],p[2]-150]);record['query_count']+=1;yield
        if not h:finding('ground_missing',probe)
        elif abs(h['point'][2]-p[2])>5:finding('ground_height',probe,h)
        elif h['normal'][2]<.7:finding('ground_slope',probe,h)
    for segment in job['proxies']['body']:
        a,b=transform(segment['a']),transform(segment['b']);h=sphere(a,b,3.);record['query_count']+=1;yield
        if h:finding('body_collision',segment,h)
    for camera in job['proxies']['cameras']:
        q,target=transform(camera['position']),transform(camera['look_at'])
        h=sphere(q,[q[0]+.01,q[1],q[2]],8.);record['query_count']+=1;yield
        if h:finding('camera_collision',camera,h)
        h=ray(q,target);record['query_count']+=1;yield
        if h:finding('occlusion',camera,h)
    record['score']=offline.score_screen(record)
    record['assessment']='screening_only_suspected_findings'
    return record


def _full(candidate,job):
    placed=geo.place_geometry(job['local'],candidate['position'],candidate['yaw'])
    actions=placed['actions'];shots=placed['shots']
    check={'site_z':candidate['position'][2],'issues':[],'seen':set(),'unmeasured_visibility_samples':0,
        'action_samples':{a['motion_id']:{r['frame_index']:r for r in a['samples']} for a in actions}}
    total=sum(len(a['samples']) for a in actions)+sum(len(s['samples']) for s in shots)
    job['full_check']={'completed':0,'total':total,'candidate':len(job['full_attempts'])+1}
    for action in actions:
        for sample in action['samples']:
            worker_call(worker.check_action_sample,check,action,sample)
            job['full_check']['completed']+=1;yield
    for shot in shots:
        for ix,row in enumerate(shot['samples']):
            worker_call(worker.check_shot_sample,check,shot,row,ix)
            job['full_check']['completed']+=1;yield
    assessments=offline.combination_assessment(job['local'],check['issues'])
    count=sum(r['assessment']=='no_conflict_detected_at_sampled_proxies' for r in assessments)
    return {'candidate':candidate,'issues':check['issues'],'combinations':assessments,
        'summary':{'matrix_combinations':1260,'sample_items_completed':total,'total_sample_items':total,
            'full_matrix_sampled':True,'no_proxy_conflict_combinations':count,
            'suspected_conflict_combinations':1260-count,
            'unmeasured_visibility_samples':check['unmeasured_visibility_samples']},
        'sampling':'runtime8 exact body-ground, bone-segment3cm, camera-path8cm and visible-landmark traces at0.5s plus endpoint',
        'confirmed_exclusions':[],'human_acceptance':'pending'}


def _work(job):
    job['phase']='inventory'
    for actor in job.pop('actor_handles'):
        if actor.get_actor_label().startswith(worker.PREFIX):continue
        job['actor_inventory'].append(inventory_actor(actor))
        try:job['lighting'].extend(lighting_actor(actor))
        except Exception as exc:job['lighting_errors'].append({'actor':actor.get_actor_label(),'error':str(exc)})
        yield
    job['scene_signature_start']=worker.scene_signature();yield
    checkpoint(job)
    saved=[s['site'] for path in sorted((geo.RUN/'sites').glob('*.json'))
        for s in [offline.read(path)] if s.get('site',{}).get('map')==job['map']]
    seeds=offline.anchor_seeds(job['actor_inventory'],saved,job['extra_seeds'],round_index=job['round_index'])
    job['phase']='ground_anchors'
    for seed in seeds:
        result=yield from _ground_candidate(seed,job)
        job['ground_candidates'].append(result)
    good=[r for r in job['ground_candidates'] if r['eligible']]
    # An expanded set of surface corners is attempted before reporting a failed
    # search. No scene is marked unsuitable when both bounded searches fail.
    if not good and job['round_index']==0:
        job['automatic_expanded_anchor_retry']=True
        retry=offline.anchor_seeds(job['actor_inventory'],saved,job['extra_seeds'],round_index=1)
        old={tuple(s['position']) for s in seeds}
        for seed in retry:
            if tuple(seed['position']) in old:continue
            result=yield from _ground_candidate(seed,job);job['ground_candidates'].append(result)
        good=[r for r in job['ground_candidates'] if r['eligible']]
    checkpoint(job)
    positions=[r['position'] for r in good]
    if not positions:return
    chosen=offline.farthest_indices(positions,offline.POLICY['max_grounded_positions'])
    job['phase']='candidate_screen'
    yaws=offline.POLICY['retry_yaw_degrees'] if job['round_index'] else offline.POLICY['yaw_degrees']
    for ix in chosen:
        for yaw in yaws:
            result=yield from _screen(positions[ix],yaw,job)
            job['screen_candidates'].append(result)
    ordered=sorted(job['screen_candidates'],key=lambda c:(-c['score'],c['position'],c['yaw']))
    checkpoint(job)
    job['phase']='full_matrix'
    # Prefer an alternative position over tiny orientation variations on the
    # same failed location when a second complete matrix is justified.
    attempts=[]
    for candidate in ordered:
        if attempts and any(sum((a-b)**2 for a,b in zip(candidate['position'],r['position']))<200**2 for r in attempts):continue
        attempts.append(candidate)
        if len(attempts)>=job['max_full_attempts']:break
    if not attempts:attempts=ordered[:1]
    for candidate in attempts:
        result=yield from _full(candidate,job)
        job['full_attempts'].append(result)
        checkpoint(job)
        if result['summary']['no_proxy_conflict_combinations']==1260:break


def finish(job,status='complete',error=None):
    if job.get('handle'):u.unregister_slate_post_tick_callback(job['handle']);job['handle']=None
    if status=='complete':
        if map_path()!=job['map']:status='stale';error='Loaded map changed'
        elif worker.scene_signature()!=job.get('scene_signature_start'):status='stale';error='Scene changed during survey'
        try:geo.verify_sources(job['source_pins'])
        except Exception as exc:status='stale';error=str(exc)
    job['status']=status
    best=max(job['full_attempts'],key=lambda r:(r['summary']['no_proxy_conflict_combinations'],r['candidate']['score']),default=None)
    site=None
    if best and status=='complete':
        candidate=best['candidate'];site={'site_id':job['site_id'],'scene_label':job['scene']['label'],
            'name':job['scene']['label']+' / 自动候选点','map':job['map'],
            'position':dict(zip(('x','y','z'),candidate['position'])),'yaw':candidate['yaw'],
            'exposure_compensation':0.,'exclusions':[],
            'exclusion_assessment':'proxy findings remain suspected until visual/explicit review',
            'human_acceptance':'pending'}
    report={'schema':'all_primary_scene_site_survey_v1','status':status,'error':error,
        'map':job['map'],'scene':job['scene'],'attempt_id':job['id'],'site':site,
        'search_result':'candidate_pending_visual_review' if site else 'unresolved_search_not_scene_rejection',
        'primary_scope':'existing primary=True; no map-purpose reclassification',
        'policy':offline.POLICY,'round_index':job['round_index'],
        'ground_candidates':job['ground_candidates'],'screen_candidates':job['screen_candidates'],
        'full_attempts':job['full_attempts'],'selected_full_attempt_index':job['full_attempts'].index(best) if best else None,
        'actor_inventory':job['actor_inventory'],'lighting_configuration':job['lighting'],
        'lighting_read_errors':job['lighting_errors'],'exposure_assessment':{
            'exposure_compensation':0.,'configuration_read_only':True,'rendered_luminance_assessed':False,
            'status':'requires character/background visual exposure review; no automatic light changes'},
        'collision_visibility_limitations':{'components_without_visibility_collision':sum(a.get('collisionless_or_visibility_ignored_components',0) for a in job['actor_inventory']),
            'clear_traces_certify_mesh_safety':False},
        'source_pins':job['source_pins'],'scene_signature':job.get('scene_signature_start'),
        'limitations':['Sparse body/camera proxies and Visibility collision only; collisionless scenery, clothing/hair and between-sample events can be missed.',
            'Suspected conflicts are not confirmed exclusions. Failed bounded search is not an unusable-scene decision.',
            'Lighting settings are configuration evidence only; lighting/exposure quality needs rendered character visual review.'],
        'confirmed_exclusions':[],'human_acceptance':'pending'}
    path=Path(job['run'])/'surveys'/(job['id']+'.json');offline.write(path,report)
    job['report_path']=str(path)
    if site:offline.write(Path(job['run'])/'candidate_sites'/(job['id']+'.json'),{'site':site,'survey':geo.pin(path)})
    checkpoint(job)
    write(Path(job['run'])/'survey_progress.json',status_snapshot(job))


def status_snapshot(job):
    return {'success':job['status'] not in ('failed','stale'),'status':job['status'],
        'map':job['map'],'attempt_id':job['id'],'phase':job.get('phase'),
        'ground_candidates':len(job['ground_candidates']),'screen_candidates':len(job['screen_candidates']),
        'full_attempts':len(job['full_attempts']),'full_check':job.get('full_check'),
        'report_path':job.get('report_path'),'elapsed_seconds':round(time.monotonic()-job['started'],2)}


def tick(delta):
    job=_job()
    if not job or job['status']!='running':return
    if map_path()!=job['map']:finish(job,'stale','Map changed during survey');return
    if (Path(job['run'])/'STOP').exists():finish(job,'cancelled','STOP requested');return
    try:
        started=time.monotonic();count=0
        while time.monotonic()-started<offline.POLICY['tick_budget_seconds'] and count<offline.POLICY['max_trace_calls_per_tick']:
            next(job['iterator']);count+=1
        if time.monotonic()-job.get('last_progress',0)>2:
            job['last_progress']=time.monotonic();write(Path(job['run'])/'survey_progress.json',status_snapshot(job))
        if time.monotonic()-job.get('last_checkpoint',0)>15:
            job['last_checkpoint']=time.monotonic();checkpoint(job)
    except StopIteration:finish(job)
    except Exception as exc:finish(job,'failed',str(exc)+'\n'+traceback.format_exc())


def start(map_name=None,*,run_root=RUN,round_index=0,extra_seeds=(),max_full_attempts=None):
    if _job() and _job().get('status')=='running':raise ValueError('A survey is already running')
    if u.get_editor_subsystem(u.MoviePipelineQueueSubsystem).is_rendering():raise ValueError('Finish rendering before scene survey')
    existing=getattr(u,worker.LIVE,None)
    if existing and (existing.get('job') or {}).get('status')=='running':raise ValueError('Finish existing site checker first')
    if existing and existing.get('playback',{}).get('playing'):raise ValueError('Stop point preview playback before survey')
    run=Path(run_root).resolve();inventory=offline.read(run/'survey_inventory_v1.json')
    sources=[*inventory['sources'],inventory['geometry'],inventory['proxies'],geo.pin(run/'survey_inventory_v1.json'),geo.pin(__file__),geo.pin(worker.__file__)]
    geo.verify_sources(sources)
    selected=map_name or map_path()
    if selected!=map_path():raise ValueError('Coordinator must load the target map first; survey never loads levels')
    matches=[s for s in inventory['scenes'] if s['map_path']==selected and s['primary'] is True]
    if len(matches)!=1:raise ValueError('Loaded map must be one of the exact 26 primary entries')
    local=offline.read(inventory['geometry']['path']);proxies=offline.read(inventory['proxies']['path'])
    if len(local['shots'])!=1260 or len(local['actions'])!=30:raise ValueError('Expected complete frozen matrix')
    limit=offline.POLICY['default_max_full_attempts'] if max_full_attempts is None else int(max_full_attempts)
    if not 1<=limit<=3:raise ValueError('Bounded full attempts must be 1..3')
    index=inventory['scenes'].index(matches[0]);identifier=f'primary_{index:02d}_r{int(round_index)}_'+time.strftime('%Y%m%d_%H%M%S')
    actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    job={'id':identifier,'site_id':f'primary_{index:02d}_site_v1','scene':matches[0],'map':selected,
        'run':str(run),'status':'running','started':time.monotonic(),'round_index':int(round_index),
        'extra_seeds':[list(p) for p in extra_seeds],'max_full_attempts':limit,'source_pins':sources,
        'local':local,'proxies':proxies,'ignored':[a for a in actors if a.get_actor_label().startswith(worker.PREFIX)],
        'actor_handles':actors,'actor_inventory':[],'lighting':[],'lighting_errors':[],
        'ground_candidates':[],'screen_candidates':[],'full_attempts':[]}
    setattr(u,LIVE,job);job['iterator']=_work(job)
    job['handle']=u.register_slate_post_tick_callback(tick)
    return status_snapshot(job)


def poll():
    job=_job();return status_snapshot(job) if job else {'status':'idle'}


def cancel():
    job=_job()
    if job and job['status']=='running':finish(job,'cancelled','Coordinator cancelled')
    return poll()
