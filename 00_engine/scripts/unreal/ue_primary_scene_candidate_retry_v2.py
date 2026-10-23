"""Explicit opt-in full retry of a measured candidate with screening findings.

V1 and its pinned historical reports remain unchanged. Nonzero candidates need
an explicit flag and recorded reason; screening findings are never erased.
"""
from pathlib import Path
import copy
import ue_primary_scene_candidate_retry_v1 as previous
import ue_all_primary_scene_survey_v1 as survey
import scene_site_survey_v1 as offline
import scene_site_review_geometry_v1 as geo


def select_candidate(report,position,yaw,*,allow_nonzero_screen=False,justification=None):
    position=[float(v) for v in position];yaw=float(yaw)
    matches=[r for r in report['screen_candidates'] if len(position)==3
        and max(abs(a-b) for a,b in zip(r['position'],position))<1e-6 and abs(r['yaw']-yaw)<1e-6]
    if len(matches)!=1:raise ValueError('Exact candidate must occur once in persisted screening')
    row=matches[0]
    if row['score']!=0 and (allow_nonzero_screen is not True or not isinstance(justification,str) or not justification.strip()):
        raise ValueError('Nonzero screening candidate requires explicit opt-in and justification')
    return copy.deepcopy(row)


def start(report_path,position,yaw,*,allow_nonzero_screen=False,justification=None,run_root=offline.RUN):
    path=Path(report_path).resolve();report=offline.read(path)
    if report.get('schema')!='all_primary_scene_site_survey_v1' or report.get('status')!='complete':
        raise ValueError('Require complete source survey')
    geo.verify_sources(report['source_pins'])
    if survey.map_path()!=report['map']:raise ValueError('Coordinator must load target map first')
    candidate=select_candidate(report,position,yaw,allow_nonzero_screen=allow_nonzero_screen,justification=justification)
    candidate['retry_provenance']={'source_report':geo.pin(path),
        'source_scene_signature':report['scene_signature'],'selected_screen_record_sha256':geo.canonical_sha(candidate),
        'nonzero_screen_explicitly_allowed':candidate['score']!=0,'justification':justification,
        'screening_findings_preserved':True,'acceptance':'fresh full matrix and visual review still required'}
    survey.start(report['map'],run_root=run_root,round_index=int(report.get('round_index',0))+1,
        extra_seeds=[list(position)],max_full_attempts=1)
    job=survey._job();job['source_pins'] += [geo.pin(path),geo.pin(previous.__file__),geo.pin(__file__)]
    job['ground_candidates']=copy.deepcopy(report['ground_candidates'])
    job['screen_candidates']=copy.deepcopy(report['screen_candidates'])
    job['iterator']=previous._retry_work(job,candidate)
    return survey.status_snapshot(job)


def poll():return survey.poll()


def cancel():return survey.cancel()
