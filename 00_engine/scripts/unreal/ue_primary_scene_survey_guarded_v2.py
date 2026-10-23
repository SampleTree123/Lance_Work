"""Separate root-executed survey entry with a Slate callback reentrancy guard.

The frozen v1 search, source verification, scene signature and full matrix are
unchanged. Nested callbacks skip advancement while the current generator is
executing; the next ordinary tick resumes it. This module never loads a map.
"""
from pathlib import Path
import ue_all_primary_scene_survey_v1 as survey
import scene_site_survey_v1 as offline
import scene_site_review_geometry_v1 as geo


def tick(delta):
    job=survey._job()
    if not job or job.get('status')!='running':return
    if job.get('guard_callback_active'):
        job['guard_nested_callback_skips']=job.get('guard_nested_callback_skips',0)+1
        return
    job['guard_callback_active']=True
    try:
        survey.tick(delta)
    finally:
        job['guard_callback_active']=False
        if job.get('status')!='running':
            offline.write(Path(job['run'])/'guard_receipts'/(job['id']+'.json'),{
                'schema':'primary_scene_survey_callback_guard_receipt_v2',
                'attempt_id':job['id'],'status':job['status'],
                'nested_callback_skips':job.get('guard_nested_callback_skips',0),
                'policy':'skip nested callbacks only; resume generator on later ticks',
                'matrix_or_scene_verification_relaxed':False,
                'report':geo.pin(job['report_path']) if job.get('report_path') else None})


def _attach():
    job=survey._job()
    if not job or job.get('status')!='running':raise ValueError('A fresh running survey is required')
    if job.get('handle'):
        survey.u.unregister_slate_post_tick_callback(job['handle']);job['handle']=None
    job['guard_callback_active']=False;job['guard_nested_callback_skips']=0
    binding=Path(job['run'])/'guard_bindings'/(job['id']+'.json')
    if binding.exists():raise ValueError('Guard binding already exists; do not overwrite evidence')
    offline.write(binding,{'schema':'primary_scene_survey_callback_guard_binding_v2',
        'attempt_id':job['id'],'guard_source':geo.pin(__file__),
        'frozen_survey_source':geo.pin(survey.__file__),
        'policy':'job flag plus try/finally around the unchanged v1 tick',
        'search_checks_source_pins_scene_signature_unchanged':True})
    job['source_pins'] += [geo.pin(__file__),geo.pin(binding)]
    try:job['handle']=survey.u.register_slate_post_tick_callback(tick)
    except Exception:
        survey.finish(job,'failed','Could not register guarded callback')
        raise
    survey.checkpoint(job)
    return survey.status_snapshot(job)


def start(map_name=None,*,run_root=offline.RUN,round_index=1,extra_seeds=(),max_full_attempts=1):
    survey.start(map_name,run_root=run_root,round_index=round_index,
        extra_seeds=extra_seeds,max_full_attempts=max_full_attempts)
    return _attach()


def start_candidate(report_path,position,yaw,*,allow_nonzero_screen=False,justification=None,run_root=offline.RUN):
    import ue_primary_scene_candidate_retry_v2 as retry
    retry.start(report_path,position,yaw,allow_nonzero_screen=allow_nonzero_screen,
        justification=justification,run_root=run_root)
    return _attach()


def poll():return survey.poll()


def cancel():return survey.cancel()
