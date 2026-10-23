"""Root-executed terrain flat-patch probes; read-only and bounded Slate ticks."""
from pathlib import Path
import math
import time
import unreal as u
import scene_site_survey_v1 as offline
import scene_site_review_geometry_v1 as geo
import ue_scene_site_review_v1 as worker

LIVE='_dm_scene_terrain_probe_v1'


def ray(a,b,job):
    return worker.hit_data(u.SystemLibrary.line_trace_single(worker.world(),u.Vector(*a),u.Vector(*b),
        u.TraceTypeQuery.ECC_VISIBILITY,True,job['ignored'],u.DrawDebugTrace.NONE))


def _probe(seed,job):
    x,y=seed['xy'];h=ray([x,y,seed['trace_top_z_cm']],[x,y,seed['trace_bottom_z_cm']],job);yield
    if not h:return {'seed':seed,'eligible':False,'reason':'no_ground_hit'}
    if h['actor']!=seed['landscape_actor']:
        return {'seed':seed,'eligible':False,'reason':'hit_other_actor_before_landscape','hit':h}
    p=h['point'];errors=[];hits=[]
    for dx,dy in ((-80,-80),(-80,0),(-80,80),(0,-80),(0,0),(0,80),(80,-80),(80,0),(80,80)):
        hit=ray([p[0]+dx,p[1]+dy,p[2]+80],[p[0]+dx,p[1]+dy,p[2]-150],job);yield
        hits.append(hit)
        if not hit or hit['actor']!=seed['landscape_actor']:errors.append(float('inf'))
        else:errors.append(abs(hit['point'][2]-p[2]))
    height=max(errors);normal=min((v['normal'][2] for v in hits if v),default=-1.)
    flat=height<=3. and normal>=.94
    standing=None
    if flat:
        standing=worker.hit_data(u.SystemLibrary.sphere_trace_single(worker.world(),u.Vector(p[0],p[1],p[2]+40),
            u.Vector(p[0],p[1],p[2]+145),25.,u.TraceTypeQuery.ECC_VISIBILITY,True,job['ignored'],u.DrawDebugTrace.NONE));yield
    return {'seed':seed,'position':p,'support_hit':h,'height_error_cm':height if math.isfinite(height) else None,
        'min_normal_z':normal,'ground_hits':hits,'eligible':flat and standing is None,
        'standing_hit':standing,'scope':'3cm flatness over160cm standing region; full motion-route and camera checks still required'}


def _work(job):
    for seed in job['plan']['seeds']:
        result=yield from _probe(seed,job);job['results'].append(result)
    # Refine the least-sloped measured locations, regardless of coarse success.
    best=sorted([r for r in job['results'] if r.get('position') and r.get('height_error_cm') is not None],
        key=lambda r:(r['height_error_cm'],-r.get('min_normal_z',0)))[:16]
    seen={tuple(round(v,1) for v in r['seed']['xy']) for r in job['results']}
    extra=[]
    for record in best:
        seed=record['seed'];p=record['position']
        for dx,dy in ((-400,0),(400,0),(0,-400),(0,400),(-200,-200),(-200,200),(200,-200),(200,200)):
            xy=[p[0]+dx,p[1]+dy];key=tuple(round(v,1) for v in xy)
            if key in seen:continue
            seen.add(key);extra.append(dict(seed,xy=xy,source='local_flatness_refinement'))
            if len(extra)>=128:break
        if len(extra)>=128:break
    for seed in extra:
        # Coarse seeds are inside observed Landscape bounds; refinement extends
        # only4m. The helper below still verifies against the actual bounds.
        if not _inside(seed,job):continue
        result=yield from _probe(seed,job);job['results'].append(result)


def _inside(seed,job):
    a=next(a for a in job['source']['actor_inventory'] if a['label']==seed['landscape_actor'])
    return all(abs(seed['xy'][k]-a['bounds_origin'][k])<a['bounds_extent'][k]-100 for k in (0,1))


def finish(job,status='complete',error=None):
    if job.get('handle'):u.unregister_slate_post_tick_callback(job['handle']);job['handle']=None
    if worker.current_map()!=job['plan']['map']:status='stale';error='Map changed'
    try:
        geo.verify_sources([*job['plan']['source_pins'],*job['runtime_pins']])
        if worker.scene_signature()!=job['scene_signature_start']:status='stale';error='Scene changed during terrain probe'
    except Exception as exc:status='stale';error=str(exc)
    good=[r for r in job['results'] if r['eligible']]
    good.sort(key=lambda r:(r['height_error_cm'],-r['min_normal_z']))
    # Retain spatially separated patches, with a best-first fallback.
    selected=[]
    for row in good:
        if any(sum((a-b)**2 for a,b in zip(row['position'][:2],p['position'][:2]))<200**2 for p in selected):continue
        selected.append(row)
        if len(selected)>=12:break
    report={'schema':'primary_scene_terrain_probe_result_v1','status':status,'error':error,
        'map':job['plan']['map'],'plan':job['plan_pin'],'policy':job['plan']['policy'],
        'runtime_pins':job['runtime_pins'],'scene_signature':job['scene_signature_start'],
        'results':job['results'],'flat_candidates':selected,'extra_seeds':[r['position'] for r in selected],
        'search_result':'flat_candidates_require_full_matrix' if selected else 'bounded_search_unresolved_not_scene_rejection',
        'full1260_matrix_checked':False,'confirmed_exclusions':[],
        'limitations':['Standing-region flatness only; original5cm full action-route tolerance remains unchanged.',
            'No collisionless-mesh, body/camera envelope, rendered visibility or exposure certification.']}
    path=Path(job['run'])/'terrain_probes'/(job['id']+'.json');offline.write(path,report)
    job['status']=status;job['report_path']=str(path)


def tick(delta):
    job=getattr(u,LIVE,None)
    if not job or job['status']!='running':return
    if worker.current_map()!=job['plan']['map']:finish(job,'stale','Map changed');return
    try:
        start=time.monotonic();count=0
        while time.monotonic()-start<.016 and count<48:next(job['iterator']);count+=1
    except StopIteration:finish(job)
    except Exception as exc:finish(job,'failed',str(exc))


def start(plan_path,*,run_root=offline.RUN):
    old=getattr(u,LIVE,None)
    if old and old['status']=='running':raise ValueError('Terrain probe already running')
    plan=offline.read(plan_path);geo.verify_sources(plan['source_pins'])
    if worker.current_map()!=plan['map']:raise ValueError('Coordinator must load target map first')
    source=offline.read(plan['source_report']['path'])
    job={'id':'terrain_probe_'+time.strftime('%Y%m%d_%H%M%S'),'status':'running','plan':plan,
        'plan_pin':geo.pin(plan_path),'source':source,'run':str(run_root),'results':[],
        'runtime_pins':[geo.pin(__file__),geo.pin(worker.__file__)],
        'scene_signature_start':worker.scene_signature(),
        'ignored':worker.owned()}
    setattr(u,LIVE,job);job['iterator']=_work(job);job['handle']=u.register_slate_post_tick_callback(tick)
    return poll()


def poll():
    job=getattr(u,LIVE,None)
    return {'status':job['status'],'completed_probes':len(job['results']),'report_path':job.get('report_path')} if job else {'status':'idle'}
