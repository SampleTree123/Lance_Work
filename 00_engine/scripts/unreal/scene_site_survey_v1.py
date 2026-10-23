"""Offline, bounded shooting-point search preparation and evidence classification.

The existing primary flag is authoritative for the 26 maps. No UE import, map
purpose reclassification, asset modification, or automatic confirmed exclusion.
"""
from pathlib import Path
import argparse
import copy
import json
import math
import scene_site_review_geometry_v1 as geo
import scene_site_catalog_v1 as directory

RUN=geo.ROOT/'outputs/all_primary_scene_sites_20261015_v1'
POLICY={'max_anchor_seeds':96,'max_grounded_positions':12,'yaw_degrees':[0.,90.,180.,270.],
    'retry_yaw_degrees':[45.,135.,225.,315.],'ground_probe_radius_cm':80.,
    'ground_flat_tolerance_cm':3.,'ground_min_normal_z':.94,
    'max_ground_screen_probes':40,'max_body_screen_segments':40,'max_camera_screen_samples':60,
    'screen_trace_budget_per_candidate':200,'full_check_step_frames':15,
    'full_check_camera_radius_cm':8.,'full_check_body_radius_cm':3.,
    'default_max_full_attempts':2,'tick_budget_seconds':.016,
    'max_trace_calls_per_tick':48,'automatic_confirmed_exclusions':False}


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if read(path)!=value:raise ValueError('Refuse to replace frozen survey evidence: '+str(path))
        return
    path.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False),encoding='utf-8')


def norm2(point):return sum(float(v)**2 for v in point)


def farthest_indices(points,budget,mandatory=()):
    """Deterministic spatial coverage; mandatory indices retain camera families."""
    if not points:return []
    chosen=list(dict.fromkeys(int(i) for i in mandatory))[:budget]
    if not chosen:chosen=[max(range(len(points)),key=lambda i:(norm2(points[i]),-i))]
    distance=[min(norm2([a-b for a,b in zip(p,points[i])]) for i in chosen) for p in points]
    while len(chosen)<min(budget,len(points)):
        ix=max(range(len(points)),key=lambda i:(distance[i],-i))
        if distance[ix]<1e-8:break
        chosen.append(ix)
        distance=[min(old,norm2([a-b for a,b in zip(p,points[ix])])) for p,old in zip(points,distance)]
    return chosen


def prepare_proxies(local):
    ground=[];seen=set();body=[]
    for action in local['actions']:
        samples=action['samples']
        for row in samples:
            for probe in row['ground_probes']:
                p=probe['position'];key=(round(p[0]/15),round(p[1]/15))
                if key not in seen:
                    seen.add(key);ground.append({'position':[p[0],p[1],0.],
                        'motion_id':action['motion_id'],'frame_index':row['frame_index']})
        # Real skeletal segments at start/middle/end and largest horizontal head
        # excursion. This proxy is deliberately sparse; full checks follow.
        chosen=sorted(set([0,len(samples)//2,len(samples)-1,
            max(range(len(samples)),key=lambda i:norm2(samples[i]['bones'].get('head',[0,0,0])[:2]))]))
        for ix in chosen:
            row=samples[ix]
            for a,b in action['body_segments']:
                if a not in row['bones'] or b not in row['bones']:continue
                p,q=row['bones'][a],row['bones'][b]
                if min(p[2],q[2])<8:continue
                body.append({'a':p,'b':q,'motion_id':action['motion_id'],
                    'frame_index':row['frame_index'],'bones':[a,b]})
    ground=[ground[i] for i in farthest_indices([r['position'] for r in ground],POLICY['max_ground_screen_probes'])]
    body=[body[i] for i in farthest_indices([[.5*(a+b) for a,b in zip(r['a'],r['b'])] for r in body],POLICY['max_body_screen_segments'])]
    cameras=[];families={}
    for shot in local['shots']:
        rows=shot['samples']
        indices=sorted(set([0,len(rows)-1,max(range(len(rows)),key=lambda i:norm2(rows[i]['position']))]))
        for ix in indices:
            row=rows[ix]
            value={'position':row['position'],'look_at':row['look_at'],
                'shot_id':shot['shot_id'],'motion_id':shot['motion_id'],
                'camera_id':shot['camera_id'],'orientation':shot['orientation'],
                'frame_index':row['frame_index']}
            cameras.append(value)
            key=(shot['camera_id'],shot['orientation'])
            if key not in families or norm2(value['position'])>norm2(cameras[families[key]]['position']):families[key]=len(cameras)-1
    cameras=[cameras[i] for i in farthest_indices([r['position'] for r in cameras],POLICY['max_camera_screen_samples'],families.values())]
    return {'ground':ground,'body':body,'cameras':cameras,
        'coverage':{'camera_families':len({(r['camera_id'],r['orientation']) for r in cameras}),
            'all_camera_families':len(families),'ground_probes':len(ground),
            'body_segments':len(body),'camera_samples':len(cameras)},
        'scope':'screening extrema and camera-family representatives only; not the full matrix'}


def anchor_seeds(actors,saved_sites=(),extra_seeds=(),limit=None,round_index=0):
    """Use actual actor bounds; map names never change primary inclusion."""
    limit=limit or POLICY['max_anchor_seeds'];seeds=[]
    def add(p,kind,label,priority):
        if len(p)==3 and all(math.isfinite(float(x)) for x in p):
            seeds.append({'position':[float(x) for x in p],'kind':kind,'source_actor':label,'priority':priority})
    for site in saved_sites:
        p=site['position'];add([p[k] for k in ('x','y','z')],'saved_site',site.get('site_id','saved'),0)
    for p in extra_seeds:add(p,'coordinator_anchor','explicit',0)
    for a in actors:
        label=a.get('label','');name=(label+' '+a.get('class','')).lower()
        if 'playerstart' in name:add(a['location'],'player_start',label,1)
        if any(s in name for s in ('sky','atmosphere','fog','light','reflection','postprocess','camera','volume')):continue
        c=a.get('bounds_origin');e=a.get('bounds_extent')
        if not c or not e or min(e[:2])<180 or max(e[:2])>250000:continue
        floor=any(word in name for word in ('floor','road','street','ground','landscape','terrain','pavement','plaza'))
        planar=e[2]<max(40.,.15*min(e[:2]))
        if not floor and not planar:continue
        priority=2 if floor else 3
        sx=min(e[0]*.65,3000.);sy=min(e[1]*.65,3000.)
        offsets=[(0,0),(-.65,0),(.65,0),(0,-.65),(0,.65),(-.5,-.5),(.5,.5)]
        if round_index:offsets+=[(-1,-1),(-1,1),(1,-1),(1,1)]
        for x,y in offsets:add([c[0]+x*sx,c[1]+y*sy,c[2]+e[2]+30],
            'surface_bounds',label,priority)
    seeds.sort(key=lambda s:(s['priority'],s['source_actor'],s['position']))
    unique=[];cells=set()
    for s in seeds:
        key=tuple(round(v/100) for v in s['position'])
        if key in cells:continue
        cells.add(key);unique.append(s)
    # Preserve high-quality starts then spread surface anchors over the map.
    mandatory=[i for i,s in enumerate(unique) if s['priority']<=1][:min(16,limit)]
    selected=farthest_indices([s['position'] for s in unique],limit,mandatory)
    return [unique[i] for i in selected]


def score_screen(record):
    c=record['counts']
    # Rank compatible ground/body coverage ahead of camera convenience. This
    # score is never interpreted as a confirmed compatible-combination count.
    penalty=100*c.get('ground_missing',0)+30*c.get('ground_height',0)+30*c.get('ground_slope',0)
    penalty+=50*c.get('body_collision',0)+4*c.get('camera_collision',0)+2*c.get('occlusion',0)
    return -float(penalty)


def combination_assessment(local,issues):
    action_kinds={'ground_missing','ground_height','ground_slope','body_collision'}
    affected_actions={i['action_id'] for i in issues if i['kind'] in action_kinds}
    affected={(i['action_id'],i['camera_id'],i['aspect']) for i in issues if i['kind'] not in action_kinds}
    rows=[]
    for s in local['shots']:
        key=(s['motion_id'],s['camera_id'],s['orientation'])
        flagged=key[0] in affected_actions or key in affected
        rows.append({'shot_id':s['shot_id'],'action_id':key[0],'camera_id':key[1],'aspect':key[2],
            'assessment':'suspected_conflict' if flagged else 'no_conflict_detected_at_sampled_proxies',
            'confirmed_excluded':False})
    return rows


def confirmed_exclusions(assessments,confirmations):
    """Only explicit externally reviewed findings can become exclusions."""
    by_id={s['shot_id']:s for s in assessments};result=[]
    for c in confirmations:
        if c.get('shot_id') not in by_id or c.get('decision')!='exclude' or not c.get('evidence') or not c.get('reviewer'):
            raise ValueError('Require exact shot, explicit reviewed decision and evidence')
        result.append(dict(by_id[c['shot_id']],confirmed_excluded=True,confirmation=copy.deepcopy(c)))
    return result


def prepare(run=RUN):
    run=Path(run).resolve();catalog=directory.build_catalog()
    scenes=[s for s in catalog['scenes'] if s['primary'] is True]
    if len(scenes)!=26:raise ValueError('Expected exactly the existing 26 primary entries')
    library=geo.load_library();local=geo.prepare_geometry(library,sample_step_frames=15)
    if len(local['shots'])!=1260 or len(local['actions'])!=30:raise ValueError('Expected complete accepted matrix')
    write(run/'survey_local_geometry_v1.json',local)
    proxies=prepare_proxies(local)
    write(run/'survey_screen_proxies_v1.json',proxies)
    inventory={'schema':'all_primary_scene_survey_inventory_v1','scenes':scenes,
        'counts':{'primary_maps':26,'all_catalog_maps':77,'nonprimary_maps_out_of_scope':51},
        'map_scope':'exact existing primary=True entries; no asset-purpose rescreen',
        'policy':POLICY,'geometry':geo.pin(run/'survey_local_geometry_v1.json'),
        'proxies':geo.pin(run/'survey_screen_proxies_v1.json'),
        'sources':[geo.pin(__file__),geo.pin(directory.__file__),*library['sources']],
        'human_acceptance':'pending'}
    write(run/'survey_inventory_v1.json',inventory)
    return {'success':True,'inventory':str(run/'survey_inventory_v1.json'),
        'primary_maps':26,'shots_per_map':1260,'proxy_counts':proxies['coverage']}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run-root',type=Path,default=RUN)
    args=parser.parse_args();print(json.dumps(prepare(args.run_root),ensure_ascii=True))
