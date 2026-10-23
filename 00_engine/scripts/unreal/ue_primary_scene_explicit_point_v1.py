"""Root-executed forced XY/yaw check, without fallback anchor selection.

Original standing-region, screening, full-matrix and freshness checks are
reused unchanged. Requested Z is a trace anchor; measured support Z is saved.
No level/asset edits, loads, marker creation or acceptance decisions occur.
"""
from pathlib import Path
import math
import ue_all_primary_scene_survey_v1 as survey
import scene_site_survey_v1 as offline
import scene_site_review_geometry_v1 as geo


def _forced_checks(job,request):
    seed={'position':request['position'],'kind':'explicit_forced_anchor',
        'source_actor':'coordinator','priority':0,'explicit_request':request}
    job['phase']='explicit_ground_standing'
    ground=yield from survey._ground_candidate(seed,job)
    job['ground_candidates'].append(ground);survey.checkpoint(job)
    if not ground.get('eligible'):
        job['explicit_outcome']='ground_or_standing_rejected';return
    measured=ground['position']
    if max(abs(measured[k]-request['position'][k]) for k in (0,1))>.01:
        raise ValueError('Ground trace changed forced XY; no fallback is allowed')
    job['phase']='explicit_screen'
    candidate=yield from survey._screen(measured,request['yaw'],job)
    candidate['explicit_point_provenance']={'request':request,
        'measured_ground_position':measured,'ground_checks_preserved':True,
        'no_xy_or_yaw_fallback':True}
    job['screen_candidates'].append(candidate);survey.checkpoint(job)
    if candidate['score']!=0 and request['allow_screen_findings'] is not True:
        job['explicit_outcome']='screen_findings_require_explicit_opt_in';return
    job['phase']='explicit_full_matrix'
    result=yield from survey._full(candidate,job)
    job['full_attempts'].append(result)
    job['explicit_outcome']='full_matrix_measured_pending_visual_review'
    survey.checkpoint(job)


def _work(job,request):
    job['phase']='explicit_inventory'
    for actor in job.pop('actor_handles'):
        if actor.get_actor_label().startswith(survey.worker.PREFIX):continue
        job['actor_inventory'].append(survey.inventory_actor(actor))
        try:job['lighting'].extend(survey.lighting_actor(actor))
        except Exception as exc:job['lighting_errors'].append({'actor':actor.get_actor_label(),'error':str(exc)})
        yield
    job['scene_signature_start']=survey.worker.scene_signature()
    survey.checkpoint(job);yield
    yield from _forced_checks(job,request)


def _receipt(job):
    path=Path(job['run'])/'explicit_point_receipts'/(job['id']+'.json')
    offline.write(path,{'schema':'primary_scene_explicit_point_receipt_v1',
        'attempt_id':job['id'],'status':job['status'],
        'request':job['explicit_request'],'point_outcome':job.get('explicit_outcome','execution_incomplete'),
        'nested_callback_skips':job.get('explicit_nested_callback_skips',0),
        'report':geo.pin(job['report_path']) if job.get('report_path') else None,
        'scene_rejected':False,'confirmed_exclusions':[],
        'interpretation':'A rejected point does not reject the map. Complete sampled traces do not certify rendered visibility or exposure.'})
    job['explicit_receipt_path']=str(path)


def tick(delta):
    job=survey._job()
    if not job or job.get('status')!='running':return
    if job.get('explicit_callback_active'):
        job['explicit_nested_callback_skips']+=1;return
    job['explicit_callback_active']=True
    try:survey.tick(delta)
    finally:
        job['explicit_callback_active']=False
        if job.get('status')!='running':_receipt(job)


def start(position,yaw,*,reason,allow_screen_findings=False,run_root=offline.RUN,round_index=2):
    position=[float(v) for v in position];yaw=float(yaw)
    if len(position)!=3 or not all(math.isfinite(v) for v in [*position,yaw]):
        raise ValueError('Require finite XYZ and yaw')
    if not isinstance(reason,str) or not reason.strip():raise ValueError('Require explicit point-selection reason')
    if not isinstance(allow_screen_findings,bool):raise ValueError('allow_screen_findings must be boolean')
    request={'position':position,'yaw':yaw,'reason':reason.strip(),
        'allow_screen_findings':allow_screen_findings,
        'z_policy':'original vertical ground trace; persist measured support Z; no XY/yaw fallback'}
    survey.start(run_root=run_root,round_index=round_index,extra_seeds=[position],max_full_attempts=1)
    job=survey._job()
    if job.get('handle'):survey.u.unregister_slate_post_tick_callback(job['handle']);job['handle']=None
    binding=Path(job['run'])/'explicit_point_bindings'/(job['id']+'.json')
    offline.write(binding,{'schema':'primary_scene_explicit_point_binding_v1',
        'attempt_id':job['id'],'map':job['map'],'request':request,
        'entry_source':geo.pin(__file__),'frozen_survey_source':geo.pin(survey.__file__),
        'ground_standing_screen_full_matrix_and_signature_checks_unchanged':True})
    job['source_pins'] += [geo.pin(__file__),geo.pin(binding)]
    job['explicit_request']=request;job['explicit_callback_active']=False;job['explicit_nested_callback_skips']=0
    job['iterator']=_work(job,request)
    try:job['handle']=survey.u.register_slate_post_tick_callback(tick)
    except Exception:
        survey.finish(job,'failed','Could not register guarded explicit-point callback');_receipt(job);raise
    survey.checkpoint(job)
    return poll()


def poll():
    result=survey.poll();job=survey._job()
    if job and job.get('explicit_request'):
        result.update(explicit_point_outcome=job.get('explicit_outcome'),
            explicit_request=job['explicit_request'],explicit_receipt_path=job.get('explicit_receipt_path'))
    return result


def cancel():
    survey.cancel();job=survey._job()
    if job and job.get('explicit_request'):_receipt(job)
    return poll()
