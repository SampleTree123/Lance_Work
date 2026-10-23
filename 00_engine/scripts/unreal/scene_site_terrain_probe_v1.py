"""Offline Landscape-directed bounded probe plan; no geometry/motion edits."""
from pathlib import Path
import json
import scene_site_survey_v1 as survey


def grid(report,side=15,near_side=9,near_step_cm=200.):
    landscapes=[a for a in report['actor_inventory'] if 'landscape' in a['class'].lower()
        and isinstance(a.get('bounds_origin'),list) and isinstance(a.get('bounds_extent'),list)]
    if not landscapes:raise ValueError('No observed Landscape bounds in source survey')
    points=[];seen=set()
    def add(x,y,a,kind):
        c=a['bounds_origin'];e=a['bounds_extent']
        if not all(abs(p-center)<extent-100 for p,center,extent in zip((x,y),c[:2],e[:2])):return
        key=(round(x,1),round(y,1))
        if key in seen:return
        seen.add(key);points.append({'xy':[x,y],'landscape_actor':a['label'],'source':kind,
            'trace_top_z_cm':c[2]+e[2]+500.,'trace_bottom_z_cm':c[2]-e[2]-500.})
    for a in landscapes:
        c=a['bounds_origin'];e=a['bounds_extent']
        for row in range(side):
            for col in range(side):
                add(c[0]+(2*col/(side-1)-1)*max(0,e[0]-500),
                    c[1]+(2*row/(side-1)-1)*max(0,e[1]-500),a,'landscape_interior_grid')
        for actor in report['actor_inventory']:
            if 'playerstart' not in actor['class'].lower():continue
            p=actor['location']
            for row in range(near_side):
                for col in range(near_side):add(p[0]+(col-near_side//2)*near_step_cm,
                    p[1]+(row-near_side//2)*near_step_cm,a,'player_start_neighborhood')
    if len(points)>640:raise ValueError('Terrain plan exceeded bounded640seed budget')
    return points


def prepare(report_path):
    path=Path(report_path).resolve();report=survey.read(path)
    survey.geo.verify_sources(report['source_pins'])
    plan={'schema':'primary_scene_terrain_probe_plan_v1','map':report['map'],
        'source_report':survey.geo.pin(path),'source_pins':[survey.geo.pin(__file__),survey.geo.pin(path),*report['source_pins']],
        'seeds':grid(report),'policy':{'ground_probe_radius_cm':80.,'flat_tolerance_cm':3.,
            'min_normal_z':.94,'standing_capsule_radius_cm':25.,'max_refinement_seeds':128,
            'refinement_step_cm':200.,'best_candidates_limit':12},
        'scope':'Actual Landscape bounds only; coarse terrain grid plus start neighborhood; original ground tolerance retained',
        'automatic_scene_rejection':False}
    target=survey.RUN/'terrain_probe_plans'/(report['attempt_id']+'_terrain_plan_v1.json')
    survey.write(target,plan)
    return {'success':True,'plan':str(target),'seed_count':len(plan['seeds'])}


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('report',type=Path);args=parser.parse_args()
    print(json.dumps(prepare(args.report),ensure_ascii=True))
