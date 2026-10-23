"""Targeted, private object-type ground adapter; original sources stay intact.

Only four ray call sites in three ground domains are adapted. Body/standing
spheres and every camera/occlusion function remain original Visibility logic.
"""
from pathlib import Path
import ast
import importlib.util
import uuid
import unreal as u
import ue_all_primary_scene_survey_v1 as original_survey
import scene_site_survey_v1 as offline
import scene_site_review_geometry_v1 as geo

S=Path(__file__).resolve().parent
_session=None


def _load(stem):
    spec=importlib.util.spec_from_file_location('_dm_ground_private_'+uuid.uuid4().hex,S/(stem+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def _adapt_ground_function(module,name,screen=False):
    tree=ast.parse(Path(module.__file__).read_text(encoding='utf-8-sig'))
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    class Replace(ast.NodeTransformer):
        count=0
        def visit_Call(self,n):
            if isinstance(n.func,ast.Name) and n.func.id=='ray':
                domain=('anchor' if self.count==0 else 'nine_probes') if name=='_ground_candidate' else ('screen_ground' if screen else 'full_ground')
                n.func.id='_ground_object_ray';n.keywords.append(ast.keyword(arg='domain',value=ast.Constant(domain)));self.count+=1
            return self.generic_visit(n)
    replace=Replace()
    if screen:
        expected=ast.dump(ast.parse("job['proxies']['ground']",mode='eval').body)
        loops=[n for n in node.body if isinstance(n,ast.For) and ast.dump(n.iter)==expected]
        if len(loops)!=1:raise ValueError('Original screen ground loop changed')
        replace.visit(loops[0])
    else:replace.visit(node)
    expected_count=2 if name=='_ground_candidate' else 1
    if replace.count!=expected_count:raise ValueError('Original ground call sites changed: '+name)
    ast.fix_missing_locations(node)
    exec(compile(ast.Module(body=[node],type_ignores=[]),module.__file__+'::<object-ground>','exec'),module.__dict__)


def _targets(actor_label,mesh_path,component_path):
    records=[]
    for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
        if actor_label and actor.get_actor_label()!=actor_label:continue
        if component_path and actor.get_path_name()!=component_path.rsplit('.',1)[0]:continue
        for c in actor.get_components_by_class(u.PrimitiveComponent):
            if component_path and c.get_path_name()!=component_path:continue
            mesh=original_survey.worker._safe(lambda:c.get_editor_property('static_mesh'))
            if mesh_path and mesh!=mesh_path:continue
            if not mesh_path and not component_path:continue
            kind=c.get_collision_object_type()
            if kind not in (u.CollisionChannel.ECC_WORLD_STATIC,u.CollisionChannel.ECC_WORLD_DYNAMIC):
                raise ValueError('Named ground must actually be WorldStatic or WorldDynamic; no Pawn/Vehicle query')
            records.append({'actor':actor.get_actor_label(),'actor_path':actor.get_path_name(),
                'component_path':c.get_path_name(),'actual_class':c.get_class().get_name(),
                'static_mesh':mesh,'object_type':str(kind),
                'is_world_dynamic':kind==u.CollisionChannel.ECC_WORLD_DYNAMIC,
                'collision_enabled':str(c.get_collision_enabled()),
                'visibility_response':str(c.get_collision_response_to_channel(u.CollisionChannel.ECC_VISIBILITY))})
    if not records:raise ValueError('Exact intended ground component/mesh was not found; do not substitute another surface')
    return records


def _object_ray(ps,a,b,domain):
    job=ps._job();state=job['ground_object_state'];state['trace_count']+=1
    state['trace_count_by_domain'][domain]+=1
    raw=u.SystemLibrary.line_trace_single_for_objects(ps.world(),u.Vector(*a),u.Vector(*b),
        job['ground_object_types'],True,job['ignored'],u.DrawDebugTrace.NONE)
    hit=ps.worker.hit_data(raw)
    if not hit:state['miss_count']+=1;return None
    component=raw.to_tuple()[10]
    if not component:raise ValueError('Ground object hit lacks component identity')
    path=component.get_path_name()
    detail={'component_path':path,'object_type':str(component.get_collision_object_type()),
        'static_mesh':ps.worker._safe(lambda:component.get_editor_property('static_mesh')),
        'visibility_response':str(component.get_collision_response_to_channel(u.CollisionChannel.ECC_VISIBILITY))}
    hit.update(detail);hit['ground_query_kind']='object_type_complex'
    state['hit_components'].setdefault(path,dict(detail,actor=hit['actor'],hit_count=0))['hit_count']+=1
    return hit


def _ground_receipt(job):
    path=Path(job['run'])/'ground_object_reports'/(job['id']+'.json')
    record={'schema':'primary_scene_object_ground_evidence_v1','attempt_id':job['id'],'map':job['map'],
        'status':job['status'],'ground_query_policy':job['ground_object_policy'],
        'binding':job['ground_object_binding'],'adapter_source':geo.pin(__file__),
        'base_report':geo.pin(job['report_path']) if job.get('report_path') else None,
        'queries':job['ground_object_state'],'target_components':job['ground_object_targets'],
        'query_statistics':dict(job['ground_object_state']['trace_count_by_domain'],
            body_camera_visibility_unchanged=True,standing_visibility_unchanged=True),
        'ground_candidates':job['ground_candidates'],
        'body_camera_occlusion_and_standing_changed':False,
        'original_thresholds_and_full1260_changed':False,'old_reports_requalified':False,
        'scope_note':'Ground uses object types; body/standing/camera/occlusion retain original Visibility queries. No rendered visibility or mesh-safety pass.'}
    offline.write(path,record);pin=geo.pin(path);job['source_pins'].append(pin)
    job['ground_object_receipt_pin']=pin;return pin


def _add_report_fields(dual):
    tree=ast.parse(Path(dual.__file__).read_text(encoding='utf-8-sig'))
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_finish_evidence')
    matches=[i for i,n in enumerate(node.body) if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id=='record' for t in n.targets)]
    if len(matches)!=1:raise ValueError('Original dual evidence constructor changed')
    node.body[matches[0]+1:matches[0]+1]=ast.parse("record.update(ground_query_policy=job['ground_object_policy'], ground_query_evidence=job['ground_object_receipt_pin'], ground_adapter_source=job['ground_object_adapter_pin'])").body
    ast.fix_missing_locations(node)
    exec(compile(ast.Module(body=[node],type_ignores=[]),dual.__file__+'::<ground-evidence>','exec'),dual.__dict__)
    constructor=dual._finish_evidence
    def finish(job):_ground_receipt(job);constructor(job)
    dual._finish_evidence=finish


def _adapt_point_entry(point):
    """Correct inherited descriptions in the private forced-point binding."""
    tree=ast.parse(Path(point.__file__).read_text(encoding='utf-8-sig'))
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='start')
    changed=0
    for item in ast.walk(node):
        if not isinstance(item,ast.Dict):continue
        for i,key in enumerate(item.keys):
            if not isinstance(key,ast.Constant):continue
            if key.value=='ground_standing_screen_full_matrix_and_signature_checks_unchanged':
                item.values[i]=ast.Constant(False);changed+=1
            if key.value=='z_policy':
                item.values[i]=ast.Constant('Object-type vertical ground trace; persist measured support Z; no XY/yaw fallback; see attempt-bound ground query evidence');changed+=1
    if changed!=2:raise ValueError('Original forced-point descriptions changed')
    ast.fix_missing_locations(node)
    exec(compile(ast.Module(body=[node],type_ignores=[]),point.__file__+'::<ground-descriptions>','exec'),point.__dict__)


def start_point(position,yaw,*,reason,support_actor_label=None,support_mesh_path=None,
                support_component_path=None,allow_screen_findings=False,run_root=offline.RUN,round_index=5):
    global _session
    if original_survey._job() and original_survey._job().get('status')=='running':raise ValueError('Finish current survey first')
    if not support_component_path and not(support_actor_label and support_mesh_path):
        raise ValueError('Require exact component path,or intended actor label plus mesh path')
    targets=_targets(support_actor_label,support_mesh_path,support_component_path)
    dynamic=any(t['is_world_dynamic'] for t in targets)
    # This installed5.8 uses ECC_* ScriptName aliases for object queries;
    # never cast collision-channel ordinals to EObjectTypeQuery.
    object_types=[u.ObjectTypeQuery.ECC_WORLD_STATIC]
    if dynamic:object_types.append(u.ObjectTypeQuery.ECC_WORLD_DYNAMIC)
    policy={'id':'targeted_object_type_ground_v1','object_types':['WorldStatic']+(['WorldDynamic'] if dynamic else []),
        'dynamic_enabled_only_from_named_actual_target_type':dynamic,
        'target_component_paths':[t['component_path'] for t in targets],
        'ground_domains':['anchor_and_nine_probes','screen_ground_probes','full_action_ground_probes'],
        'trace_complex':True,'body_standing_camera_occlusion':'original Visibility logic unchanged',
        'flat_region_tolerance_cm':3.,'standing_probe_radius_cm':80.,'ground_probe_count':9,
        'full_action_ground_height_tolerance_cm':5.,'full_matrix_combinations':1260,
        'query_capability_note':'NoCollision/PhysicsOnly still cannot be queried; object filtering does not create collision or authorize water/roof support.'}
    ps=_load('ue_all_primary_scene_survey_v1');point=_load('ue_primary_scene_explicit_point_v1');dual=_load('ue_primary_scene_survey_dual_v3')
    point.survey=ps;dual.survey=ps;_add_report_fields(dual);_adapt_point_entry(point)
    ps._ground_object_ray=lambda a,b,domain:_object_ray(ps,a,b,domain)
    _adapt_ground_function(ps,'_ground_candidate');_adapt_ground_function(ps,'_screen',screen=True)
    ground=ps._ground_candidate
    def checked_ground(seed,job):
        row=yield from ground(seed,job)
        if row.get('support_hit') and row['support_hit'].get('component_path') not in policy['target_component_paths']:
            row['eligible']=False;row.setdefault('findings',[]).append({'kind':'unexpected_ground_support','hit':row['support_hit']})
            row['reason']='object_query_hit_is_not_named_intended_ground'
        if row.get('reason')=='no_visibility_channel_ground_hit':row['reason']='no_ground_object_query_hit'
        row['ground_query_policy']=policy
        row['scope']='Object-type ground and original Visibility standing screen; no mesh/visual guarantee'
        return row
    ps._ground_candidate=checked_ground
    def entry(*args,**kwargs):
        worker=ps.worker;worker._ground_object_ray=ps._ground_object_ray
        _adapt_ground_function(worker,'check_action_sample')
        state=worker._component_state
        def component_state(c):
            result=state(c);result['get_collision_object_type']=worker._safe(c.get_collision_object_type);return result
        worker._component_state=component_state
        result=point.start(*args,**kwargs)
        job=ps._job();binding_path=Path(job['run'])/'ground_object_bindings'/(job['id']+'.json')
        binding={'schema':'primary_scene_object_ground_binding_v1','attempt_id':job['id'],'map':job['map'],
            'ground_query_policy':policy,'target_components':targets,'adapter_source':geo.pin(__file__),
            'frozen_sources':[geo.pin(S/n) for n in ('ue_all_primary_scene_survey_v1.py','ue_scene_site_review_v1.py','ue_primary_scene_survey_dual_v3.py')],
            'signature_additional_field':'get_collision_object_type on every primitive component',
            'private_entry_descriptions_corrected':True,
            'inherited_base_sampling_text':'Ground references to Visibility in the frozen base sampling description are superseded by this explicit ground_query_policy; body/camera/occlusion stay Visibility.',
            'local_api_sources':[geo.pin(Path('D:/UE/UE_5.8/Engine')/n) for n in (
                'Build/Build.version','Source/Runtime/Engine/Classes/Kismet/KismetSystemLibrary.h',
                'Source/Runtime/Engine/Private/Collision/CollisionProfile.cpp')]}
        offline.write(binding_path,binding);binding_pin=geo.pin(binding_path);adapter_pin=geo.pin(__file__)
        job.update(ground_object_policy=policy,ground_object_binding=binding_pin,
            ground_object_adapter_pin=adapter_pin,ground_object_types=object_types,
            ground_object_targets=targets,ground_object_state={'trace_count':0,'miss_count':0,'hit_components':{},
                'trace_count_by_domain':{'anchor':0,'nine_probes':0,'screen_ground':0,'full_ground':0}})
        job['source_pins'] += [adapter_pin,binding_pin,*binding['local_api_sources']]
        return result
    _session=dual
    try:
        dual._start(entry,point.tick,position,yaw,reason=reason,allow_screen_findings=allow_screen_findings,
            run_root=run_root,round_index=round_index)
        return poll()
    except Exception:
        if ps._job() and ps._job().get('status')=='running':dual.cancel()
        raise


def poll():
    if not _session:return {'status':'idle'}
    result=_session.poll();job=_session.survey._job()
    if job and job.get('ground_object_policy'):
        result.update(ground_query_policy=job['ground_object_policy'],ground_query_evidence=job.get('ground_object_receipt_pin'))
    return result


def cancel():
    if _session:return _session.cancel()
    return poll()
