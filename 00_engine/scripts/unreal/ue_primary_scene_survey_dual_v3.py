"""Survey-only collision-proxy stability plus complete raw appearance evidence.

Only the actual GrassInstancedStaticMeshComponent class, with NO_COLLISION and
Visibility IGNORE, is omitted from the collision-proxy hash. Raw snapshots and
all changes remain saved. This never modifies the global runtime8 worker.
"""
from pathlib import Path
import importlib.util
import uuid
import unreal as u
import ue_all_primary_scene_survey_v1 as survey
import scene_site_survey_v1 as offline
import scene_site_review_geometry_v1 as geo
import ue_scene_signature_diff_probe_v1 as diff_probe

POLICY={'id':'survey_collision_proxy_and_raw_appearance_v3',
    'excluded_actual_class':'GrassInstancedStaticMeshComponent',
    'required_collision':'<CollisionEnabled.NO_COLLISION: 0>',
    'required_visibility_response':'<CollisionResponseType.ECR_IGNORE: 0>',
    'all_actor_fields_dirty_packages_and_other_components_preserved':True,
    'raw_scene_unchanged_claim':False,'rendered_grass_visibility_review_required':True,
    'other_particles_or_collisionless_components_excluded':False}


def eligible_grass(actual_class,record):
    return (actual_class==POLICY['excluded_actual_class']
        and record.get('get_collision_enabled')==POLICY['required_collision']
        and record.get('visibility_response')==POLICY['required_visibility_response'])


def capture_payloads(worker):
    raw_rows=[];proxy_rows=[];grass=[]
    for actor in worker.actors().get_all_level_actors():
        if actor.get_actor_label().startswith(worker.PREFIX):continue
        components=[];proxy=[]
        try:
            for component in actor.get_components_by_class(u.PrimitiveComponent):
                record=worker._component_state(component);components.append(record)
                actual_class=worker._safe(lambda component=component:component.get_class().get_name())
                if eligible_grass(actual_class,record):
                    grass.append({'actor':worker._safe(actor.get_path_name),
                        'actual_class':actual_class,'component':record})
                else:proxy.append(record)
            components.sort(key=lambda r:str(r['path']));proxy.sort(key=lambda r:str(r['path']))
        except Exception:
            # Exactly the original raw payload fallback. An unavailable actor
            # never obtains a grass exemption from a partial component read.
            components=[{'unavailable':True}];proxy=[{'unavailable':True}]
            actor_path=worker._safe(actor.get_path_name)
            grass=[g for g in grass if g['actor']!=actor_path]
        row={'path':worker._safe(actor.get_path_name),'location':worker._safe(actor.get_actor_location),
            'rotation':worker._safe(actor.get_actor_rotation),'scale':worker._safe(actor.get_actor_scale3d),
            'hidden':worker._safe(lambda actor=actor:actor.get_editor_property('hidden')),
            'components':components}
        raw_rows.append(row);proxy_rows.append(dict(row,components=proxy))
    dirty=worker._safe(lambda:[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
        +[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()])
    dirty=sorted(dirty) if isinstance(dirty,list) else dirty
    raw={'actors':sorted(raw_rows,key=lambda r:str(r['path'])),'dirty_packages':dirty}
    proxy={'actors':sorted(proxy_rows,key=lambda r:str(r['path'])),'dirty_packages':dirty}
    return raw,proxy,sorted(grass,key=lambda g:str(g['component']['path']))


def _capture_signature():
    job=survey._job()
    if not job or not job.get('dual_v3_active'):raise ValueError('Dual signature called outside its bound survey job')
    raw,proxy,grass=capture_payloads(job['dual_private_worker'])
    snapshot={'schema':'survey_dual_signature_snapshot_v3','attempt_id':job['id'],
        'geometry_signature_policy':POLICY,'binding':job['dual_binding'],
        'raw_scene_signature':geo.canonical_sha(raw),'collision_proxy_signature':geo.canonical_sha(proxy),
        'raw_payload':raw,'collision_proxy_payload':proxy,'excluded_grass_components':grass,
        'captured_at_original_scene_signature_call':True}
    path=Path(job['run'])/'dual_signature_snapshots'/(job['id']+f"_{len(job['dual_snapshots'])+1:02d}.json")
    offline.write(path,snapshot);pin=geo.pin(path)
    job['dual_snapshots'].append(pin);job['source_pins'].append(pin)
    return snapshot['collision_proxy_signature']


def _finish_evidence(job):
    pins=job['dual_snapshots'];first=offline.read(pins[0]['path']) if pins else None
    last=offline.read(pins[-1]['path']) if len(pins)>=2 else None
    base=offline.read(job['report_path']) if job.get('report_path') else {}
    index=base.get('selected_full_attempt_index');full=base.get('full_attempts',[])
    result=full[index] if isinstance(index,int) and 0<=index<len(full) else None
    sampled=bool(result and result['summary'].get('full_matrix_sampled') is True
        and result['summary'].get('matrix_combinations')==1260
        and result['summary'].get('sample_items_completed')==result['summary'].get('total_sample_items'))
    stable=bool(first and last and first['collision_proxy_signature']==last['collision_proxy_signature'])
    changed=bool(first and last and first['raw_scene_signature']!=last['raw_scene_signature'])
    raw_diff=diff_probe.differences(first['raw_payload'],last['raw_payload']) if first and last else []
    proxy_diff=diff_probe.differences(first['collision_proxy_payload'],last['collision_proxy_payload']) if first and last else []
    qualified=base.get('status')=='complete' and sampled and stable
    status=('collision_proxy_stable_visual_grass_pending' if changed else 'collision_proxy_stable_visual_review_pending') if qualified else 'unqualified_point_or_attempt_not_scene_rejection'
    record={'schema':'primary_scene_survey_dual_evidence_v3','status':status,
        'attempt_id':job['id'],'map':job['map'],'base_report':geo.pin(job['report_path']) if job.get('report_path') else None,
        'base_report_status':base.get('status'),'geometry_signature_policy':POLICY,
        'scene_signature_field_in_base_report':'collision_proxy_signature,not raw scene signature',
        'geometry_proxy_stable':stable,'collision_proxy_qualified':qualified,
        'full_matrix_sampled':sampled,'summary':result.get('summary') if result else None,
        'site':base.get('site') if qualified else None,'raw_scene_changed':changed,
        'raw_before_signature':first['raw_scene_signature'] if first else None,
        'raw_after_signature':last['raw_scene_signature'] if last else None,
        'raw_before_after_changes':raw_diff,'collision_proxy_changes':proxy_diff,
        'excluded_grass_before':first['excluded_grass_components'] if first else [],
        'excluded_grass_after':last['excluded_grass_components'] if last else [],
        'snapshots':pins,'binding':job['dual_binding'],'source_pins':job['source_pins'],
        'nested_callback_skips':job.get('dual_nested_callback_skips',0),
        'visual_warning':'Landscape自动草层不参与碰撞代理稳定性判断；原始场景变化与草层明细全部保留，角色/背景遮挡及曝光仍须渲染检查。',
        'raw_scene_unchanged_certified':False,'rendered_visibility_or_exposure_passed':False,
        'scene_rejected':False,'confirmed_exclusions':[]}
    path=Path(job['run'])/'dual_signature_reports'/(job['id']+'.json')
    offline.write(path,record);job['dual_report_path']=str(path);job['dual_evidence_status']=status


def _restore(job):
    if survey.worker is job.get('dual_private_worker'):survey.worker=job['dual_original_worker']
    job['dual_v3_active']=False


def tick(delta):
    job=survey._job()
    if not job or job.get('status')!='running' or not job.get('dual_v3_active'):return
    if job.get('dual_callback_active'):
        job['dual_nested_callback_skips']+=1;return
    job['dual_callback_active']=True
    try:job['dual_delegate'](delta)
    finally:
        job['dual_callback_active']=False
        if job.get('status')!='running':
            try:_finish_evidence(job)
            finally:_restore(job)


def _start(entry,delegate,*args,**kwargs):
    if survey._job() and survey._job().get('status')=='running':raise ValueError('Finish current survey first')
    original=survey.worker
    spec=importlib.util.spec_from_file_location('_dm_private_survey_worker_'+uuid.uuid4().hex,original.__file__)
    private=importlib.util.module_from_spec(spec);spec.loader.exec_module(private)
    private.scene_signature=_capture_signature;survey.worker=private
    try:
        entry(*args,**kwargs);job=survey._job()
        if job.get('handle'):u.unregister_slate_post_tick_callback(job['handle']);job['handle']=None
        binding_path=Path(job['run'])/'dual_signature_bindings'/(job['id']+'.json')
        offline.write(binding_path,{'schema':'survey_dual_signature_binding_v3','attempt_id':job['id'],
            'geometry_signature_policy':POLICY,'entry_source':geo.pin(__file__),
            'original_worker_source':geo.pin(original.__file__),'diff_source':geo.pin(diff_probe.__file__),
            'private_worker_only':True,'original_global_worker_functions_modified':False})
        binding=geo.pin(binding_path)
        job.update(dual_v3_active=True,dual_original_worker=original,dual_private_worker=private,
            dual_delegate=delegate,dual_callback_active=False,dual_nested_callback_skips=0,
            dual_binding=binding,dual_snapshots=[])
        job['source_pins'] += [geo.pin(__file__),geo.pin(diff_probe.__file__),binding]
        job['handle']=u.register_slate_post_tick_callback(tick);survey.checkpoint(job)
        return poll()
    except Exception:
        try:
            if survey._job() and survey._job().get('status')=='running':survey.cancel()
        finally:survey.worker=original
        raise


def start(map_name=None,*,run_root=offline.RUN,round_index=3,extra_seeds=(),max_full_attempts=1):
    return _start(survey.start,survey.tick,map_name,run_root=run_root,round_index=round_index,
        extra_seeds=extra_seeds,max_full_attempts=max_full_attempts)


def start_candidate(report_path,position,yaw,*,allow_nonzero_screen=False,justification=None,run_root=offline.RUN):
    import ue_primary_scene_candidate_retry_v2 as retry
    return _start(retry.start,survey.tick,report_path,position,yaw,
        allow_nonzero_screen=allow_nonzero_screen,justification=justification,run_root=run_root)


def start_point(position,yaw,*,reason,allow_screen_findings=False,run_root=offline.RUN,round_index=3):
    import ue_primary_scene_explicit_point_v1 as point
    return _start(point.start,point.tick,position,yaw,reason=reason,
        allow_screen_findings=allow_screen_findings,run_root=run_root,round_index=round_index)


def poll():
    result=survey.poll();job=survey._job()
    if job and 'dual_binding' in job:
        result.update(geometry_signature_policy=POLICY['id'],dual_report_path=job.get('dual_report_path'),
            dual_evidence_status=job.get('dual_evidence_status'),raw_snapshot_count=len(job['dual_snapshots']))
    return result


def cancel():
    job=survey._job()
    survey.cancel()
    if job and job.get('dual_v3_active'):
        try:_finish_evidence(job)
        finally:_restore(job)
    return poll()
