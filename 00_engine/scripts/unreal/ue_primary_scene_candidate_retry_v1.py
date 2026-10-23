"""Root-executed full-matrix retry of one persisted candidate; no anchor search.

The frozen survey module is reused unchanged. The prior report, selected screen
record and all input pins remain explicit provenance; current scene inventory
and the complete sampled matrix are measured again. Never loads/saves a map.
"""
from pathlib import Path
import copy
import ue_all_primary_scene_survey_v1 as survey
import scene_site_survey_v1 as offline
import scene_site_review_geometry_v1 as geo


def _retry_work(job,candidate):
    job['phase']='retry_inventory'
    for actor in job.pop('actor_handles'):
        if actor.get_actor_label().startswith(survey.worker.PREFIX):continue
        job['actor_inventory'].append(survey.inventory_actor(actor))
        try:job['lighting'].extend(survey.lighting_actor(actor))
        except Exception as exc:job['lighting_errors'].append({'actor':actor.get_actor_label(),'error':str(exc)})
        yield
    job['scene_signature_start']=survey.worker.scene_signature()
    survey.checkpoint(job);yield
    job['phase']='retry_full_matrix'
    result=yield from survey._full(candidate,job)
    job['full_attempts'].append(result)
    survey.checkpoint(job)


def select_candidate(report,position,yaw):
    position=[float(v) for v in position];yaw=float(yaw)
    matches=[r for r in report['screen_candidates']
        if len(position)==3 and max(abs(a-b) for a,b in zip(r['position'],position))<1e-6
        and abs(r['yaw']-yaw)<1e-6]
    if len(matches)!=1:raise ValueError('Exact candidate position/yaw must occur once in persisted screening')
    if matches[0]['score']!=0:raise ValueError('This bounded retry entry requires a zero-finding screening candidate')
    return copy.deepcopy(matches[0])


def start(report_path,position=(-5114.,7686.,100.),yaw=0.,*,run_root=offline.RUN):
    report_path=Path(report_path).resolve();report=offline.read(report_path)
    if report.get('schema')!='all_primary_scene_site_survey_v1' or report.get('status')!='complete':
        raise ValueError('Require completed original survey evidence')
    geo.verify_sources(report['source_pins'])
    if survey.map_path()!=report['map']:raise ValueError('Coordinator must load the original primary map before retry')
    candidate=select_candidate(report,position,yaw)
    candidate['retry_provenance']={'source_report':geo.pin(report_path),
        'source_scene_signature':report['scene_signature'],
        'selected_screen_record_sha256':geo.canonical_sha(candidate),
        'selection':'explicit coordinator choice; prior screen is provenance only, full checks are repeated'}
    survey.start(report['map'],run_root=run_root,round_index=int(report.get('round_index',0))+1,
        extra_seeds=[list(position)],max_full_attempts=1)
    job=survey._job()
    job['source_pins'] += [geo.pin(report_path),geo.pin(__file__)]
    job['ground_candidates']=copy.deepcopy(report['ground_candidates'])
    job['screen_candidates']=copy.deepcopy(report['screen_candidates'])
    # Replace the not-yet-started generator in the same UE command, before the
    # next Slate tick. Current scene inventory and all1260 checks run fresh.
    job['iterator']=_retry_work(job,candidate)
    return survey.status_snapshot(job)


def poll():return survey.poll()


def cancel():return survey.cancel()
