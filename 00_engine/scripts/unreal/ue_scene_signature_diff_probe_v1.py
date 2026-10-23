"""Root-executed read-only diagnosis of runtime8 scene-signature instability.

Uses the exact runtime8 payload fields. Compare immediate repeated reads and a
later editor tick; never adjusts the active checker or accepts a stale report.
"""
from pathlib import Path
import json
import time
import unreal as u
import ue_scene_site_review_v1 as worker
import scene_site_review_geometry_v1 as geo
import scene_site_survey_v1 as inputs

LIVE='_dm_scene_signature_diff_probe_v1'


def payload():
    rows=[]
    for actor in worker.actors().get_all_level_actors():
        if actor.get_actor_label().startswith(worker.PREFIX):continue
        try:components=sorted((worker._component_state(c) for c in actor.get_components_by_class(u.PrimitiveComponent)),key=lambda r:str(r['path']))
        except Exception:components=[{'unavailable':True}]
        rows.append({'path':worker._safe(actor.get_path_name),'location':worker._safe(actor.get_actor_location),
            'rotation':worker._safe(actor.get_actor_rotation),'scale':worker._safe(actor.get_actor_scale3d),
            'hidden':worker._safe(lambda:actor.get_editor_property('hidden')),'components':components})
    dirty=worker._safe(lambda:[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
        +[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()])
    return {'actors':sorted(rows,key=lambda r:str(r['path'])),'dirty_packages':sorted(dirty) if isinstance(dirty,list) else dirty}


def differences(before,after):
    result=[]
    def compare(a,b,path):
        if a==b:return
        if isinstance(a,dict) and isinstance(b,dict):
            for key in sorted(set(a)|set(b)):compare(a.get(key),b.get(key),path+'/'+str(key))
        elif isinstance(a,list) and isinstance(b,list) and len(a)==len(b):
            for index,(x,y) in enumerate(zip(a,b)):compare(x,y,path+'/'+str(index))
        else:
            item={'field':path,'before':a,'after':b}
            if isinstance(a,(int,float)) and isinstance(b,(int,float)):item['absolute_delta']=abs(a-b)
            result.append(item)
    old={a['path']:a for a in before['actors']};new={a['path']:a for a in after['actors']}
    for path in sorted(set(old)|set(new)):
        a=old.get(path);b=new.get(path)
        if a is None or b is None:
            result.append({'actor':path,'field':'actor_presence','before_present':a is not None,'after_present':b is not None});continue
        a=dict(a);b=dict(b)
        ac={c.get('path','unavailable_'+str(i)):c for i,c in enumerate(a.pop('components'))}
        bc={c.get('path','unavailable_'+str(i)):c for i,c in enumerate(b.pop('components'))}
        start=len(result);compare(a,b,'actor')
        for key in sorted(set(ac)|set(bc)):compare(ac.get(key),bc.get(key),'component/'+str(key))
        for row in result[start:]:row['actor']=path
    compare(before['dirty_packages'],after['dirty_packages'],'dirty_packages')
    return result


def finish(job):
    if job.get('handle'):u.unregister_slate_post_tick_callback(job['handle']);job['handle']=None
    same_map=worker.current_map()==job['map']
    later=payload() if same_map else None
    immediate=differences(job['first'],job['immediate'])
    delayed=differences(job['immediate'],later) if later else []
    report={'schema':'scene_signature_diff_probe_v1','map':job['map'],'status':'complete' if same_map else 'map_changed',
        'runtime_signature_fields_exact':True,'source_pins':[geo.pin(worker.__file__),geo.pin(__file__)],
        'first_signature':geo.canonical_sha(job['first']),'immediate_signature':geo.canonical_sha(job['immediate']),
        'delayed_signature':geo.canonical_sha(later) if later else None,
        'immediate_difference_count':len(immediate),'delayed_difference_count':len(delayed),
        'immediate_differences':immediate,'delayed_differences':delayed,
        'snapshots':{'first':job['first'],'immediate':job['immediate'],'delayed':later},
        'elapsed_seconds':time.monotonic()-job['started'],
        'scope':'Exact field diagnosis only. Does not authorize weakening signatures or accepting stale matrix reports.'}
    path=Path(job['run'])/'signature_diagnostics'/(job['id']+'.json')
    inputs.write(path,report);job['status']=report['status'];job['report_path']=str(path)


def tick(delta):
    job=getattr(u,LIVE,None)
    if job and job['status']=='running' and time.monotonic()>=job['deadline']:finish(job)


def start(delay_seconds=2.,*,run_root=inputs.RUN):
    previous=getattr(u,LIVE,None)
    if previous and previous['status']=='running':raise ValueError('A signature probe is already running')
    now=time.monotonic();first=payload();immediate=payload()
    job={'id':'signature_diff_'+time.strftime('%Y%m%d_%H%M%S'),'run':str(Path(run_root).resolve()),
        'status':'running','map':worker.current_map(),'started':now,
        'first':first,'immediate':immediate,'deadline':time.monotonic()+max(.1,float(delay_seconds))}
    setattr(u,LIVE,job);job['handle']=u.register_slate_post_tick_callback(tick)
    return poll()


def poll():
    job=getattr(u,LIVE,None)
    return {'status':job['status'],'map':job['map'],'report_path':job.get('report_path')} if job else {'status':'idle'}
