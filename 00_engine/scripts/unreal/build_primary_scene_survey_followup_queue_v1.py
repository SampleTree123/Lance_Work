"""Offline triage of completed primary-map surveys; never executes Unreal.

This is a mutable queue over immutable reports, not an exclusion authority. The
existing primary inventory remains authoritative. A bounded watch is optional.
"""
from pathlib import Path
from collections import Counter
import argparse
import json
import math
import time
import scene_site_survey_v1 as inputs

RUN=inputs.RUN


def point_distance(a,b):return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))


def _summary(report):
    index=report.get('selected_full_attempt_index')
    full=report.get('full_attempts',[])
    return full[index] if isinstance(index,int) and 0<=index<len(full) else None


def measured_site_context(report):
    site=report.get('site')
    if not site:return None
    p=[site['position'][k] for k in ('x','y','z')]
    ground=next((g for g in report.get('ground_candidates',[]) if g.get('position')
        and point_distance(p,g['position'])<.01),None)
    words=('house','building','temple','castle','station','church','apartment','shop','tower')
    actors=[a for a in report.get('actor_inventory',[]) if a.get('bounds_origin')
        and any(w in (a.get('label','')+' '+a.get('class','')).lower() for w in words)]
    nearest=sorted(actors,key=lambda a:point_distance(p,a['bounds_origin']))[:3]
    return {'support_actor':(ground.get('support_hit') or {}).get('actor') if ground else None,
        'seed':ground.get('seed') if ground else None,
        'nearest_named_architecture_centers':[{'actor':a['label'],'position':a['bounds_origin'],
            'distance_cm':point_distance(p,a['bounds_origin'])} for a in nearest],
        'method':'Observed label/class hints and center distances only; not rendered visibility or automatic map classification.'}


def alternative(report,blocked_actors):
    best=report.get('site')
    if not best:return None
    start=[best['position'][k] for k in ('x','y','z')]
    centers=[r['bounds_origin'] for r in report.get('actor_inventory',[])
        if r['label'] in blocked_actors and r.get('bounds_origin')]
    candidates=[]
    for c in report.get('screen_candidates',[]):
        if point_distance(c['position'],start)<250:continue
        support=next((g.get('support_hit',{}).get('actor') for g in report.get('ground_candidates',[])
            if g.get('position') and point_distance(g['position'],c['position'])<.1),None)
        separation=min((point_distance(c['position'],p) for p in centers),default=point_distance(c['position'],start))
        candidates.append((c['score'],separation,c,support))
    if not candidates:return None
    ground=[r for r in candidates if not any(word in (r[3] or '').lower() for word in ('roof','ceiling'))]
    # Roof hits are valid physics candidates but need an explicit visual choice;
    # do not silently rank a rooftop above an equally clear ground-level point.
    pool=ground or candidates
    _,_,value,support=max(pool,key=lambda row:(row[0],row[1],-row[2]['yaw']))
    return {'position':value['position'],'yaw':value['yaw'],'screen_score':value['score'],
        'support_actor':support,
        'authority':'persisted screening candidate only; requires fresh full matrix and visual review',
        'selection':'prefer non-rooftop candidates, highest screening score then separation from blocking actors; background legibility still needs visual review'}


def analyze(path):
    report=inputs.read(path);full=_summary(report)
    bad=[]
    for pin in report.get('source_pins',[]):
        try:inputs.geo.verify_pin(pin)
        except (ValueError,OSError) as exc:bad.append({'path':pin['path'],'error':str(exc)})
    issues=full.get('issues',[]) if full else []
    kinds=Counter(i['kind'] for i in issues)
    actors=Counter((i.get('hit') or {}).get('actor') for i in issues)
    actors.pop(None,None)
    summary=full['summary'] if full else {}
    clean=summary.get('no_proxy_conflict_combinations',-1)
    usable=(report.get('status')=='complete' and report.get('site') is not None and full is not None
        and summary.get('full_matrix_sampled') is True and summary.get('matrix_combinations')==1260
        and summary.get('sample_items_completed')==summary.get('total_sample_items') and not bad)
    state='best_candidate_pending_visual_review' if usable else 'failed_search_not_scene_rejection' if report.get('status')=='complete' and not full else 'attempt_incomplete_or_stale_not_scene_rejection'
    suggestions=[];site_context=measured_site_context(report)
    if site_context:
        support=(site_context.get('support_actor') or '').lower()
        nearest=site_context['nearest_named_architecture_centers']
        if any(w in support for w in ('mountain','roof','ceiling')) or ('paddyfield' in support and nearest and nearest[0]['distance_cm']>10000):
            suggestions.append({'priority':0,'action':'select_authored_main_scene_ground_before_render_acceptance',
                'reason':'Measured support is distant terrain or a roof. Proxy clearance does not establish the requested main environment backdrop.',
                'site_context':site_context,'automatic_scene_rejection':False})
    if 'generator already executing' in (report.get('error') or ''):
        suggestions.append({'priority':0,'action':'retry_with_separate_guarded_v2_callback',
            'reason':'Nested Slate callbacks attempted to advance the same active generator. This is an execution failure, not a ground or scene rejection.',
            'entry':'ue_primary_scene_survey_guarded_v2.start(round_index=1,max_full_attempts=1)',
            'verification':'Original search, full matrix, source pins and scene signature remain unchanged.'})
    if bad:suggestions.append({'priority':0,'action':'rebuild_current_inputs_then_retry','reason':'Report input pins no longer verify; never treat this as a current clear result.'})
    if kinds.get('ground_missing') or kinds.get('ground_height') or kinds.get('ground_slope'):
        suggestions.append({'priority':0,'action':'retry_another_flat_surface_then_review_affected_routes',
            'reason':'Ground conflicts affect every camera/aspect of the corresponding action; check collision settings and actual floor continuity, retain map.'})
    if not full and report.get('status')=='complete':
        rejected=Counter(r.get('reason','standing-region findings') for r in report.get('ground_candidates',[]) if not r.get('eligible'))
        suggestions.append({'priority':0,'action':'expanded_anchor_or_explicit_ground_seed_retry',
            'reason':'No candidate reached the full matrix; this is a bounded search failure, not evidence that the scene is unusable.',
            'ground_rejection_reasons':dict(rejected)})
        narrow_floors=[a for a in report.get('actor_inventory',[]) if 'floor' in a.get('label','').lower()
            and isinstance(a.get('bounds_extent'),list) and a['bounds_extent'][2]<1
            and 60<=min(a['bounds_extent'][:2])<180 and max(a['bounds_extent'][:2])>=150]
        if not report.get('ground_candidates') and narrow_floors:
            suggestions.append({'priority':0,'action':'explicit_contiguous_narrow_floor_center_seeds',
                'reason':'Floor tiles exist but minXY extent <180cm removed them before ground sampling. Test joined floor centers with the unchanged standing/ground/camera checks; do not infer absence of usable ground.',
                'actor_count':len(report.get('actor_inventory',[])),
                'filtered_floor_evidence':[{'actor':a['label'],'center':a['bounds_origin'],'extent':a['bounds_extent']} for a in narrow_floors[:24]],
                'suggested_explicit_seeds':([[560.,-240.,0.],[880.,-240.,0.],[2280.,-460.,160.],[2920.,-460.,160.]]
                    if report['map']=='/Game/Scenes/Kowloon/Maps/Kowloon' else [a['bounds_origin'] for a in narrow_floors[:8]]),
                'seed_authority':'Bounds-derived, untraced suggestions. Adjacent tiles may form usable floor; scenery/background and complete camera envelopes still need measurement and visual review.'})
        landscapes=[a for a in report.get('actor_inventory',[]) if 'landscape' in a.get('class','').lower()
            and isinstance(a.get('bounds_origin'),list) and isinstance(a.get('bounds_extent'),list)]
        if landscapes:
            labels={a['label'] for a in landscapes};ground=report.get('ground_candidates',[])
            inside=lambda p:any(all(abs(p[k]-a['bounds_origin'][k])<=a['bounds_extent'][k] for k in (0,1)) for a in landscapes)
            attempts=sum(g['seed']['source_actor'] in labels for g in ground)
            outside=sum(not inside(g['seed']['position']) for g in ground)
            suggestions.append({'priority':0,'action':'dedicated_landscape_interior_grid_and_shallowest_surface_search',
                'reason':'General farthest-point seed coverage can be dominated by distant decorative terrain meshes; search actual Landscape bounds before rejecting the scene.',
                'landscape_bounds':[{'actor':a['label'],'origin':a['bounds_origin'],'extent':a['bounds_extent']} for a in landscapes],
                'landscape_actor_seed_count':attempts,'seed_count_outside_landscape_xy_bounds':outside,
                'total_seed_count':len(ground),
                'trace_note':'Use the actual Landscape top-to-bottom Z range; the generic5000cm down trace can miss low terrain. Retain original5cm action-ground tolerance.'})
    if full and not usable:suggestions.append({'priority':0,'action':'inspect_coverage_or_attempt_error_before_reuse','reason':report.get('error') or 'Full matrix or source freshness not proven.'})
    if issues:
        camera_kinds={'camera_collision','occlusion','visibility_unmeasured'}
        only_camera=all(i['kind'] in camera_kinds for i in issues)
        suggestion={'priority':1,'action':'translate_to_another_persisted_candidate_and_full_recheck' if only_camera else 'relocate_body_and_camera_envelope_and_full_recheck',
            'reason':'Findings remain suspected; try another location before confirming any combination exclusion.',
            'blocking_actors':dict(actors),'suggested_candidate':alternative(report,set(actors))}
        if all(i.get('camera_id')=='orbit_360' for i in issues):
            suggestion['yaw_note']='Changing yaw does not remove the complete circular camera envelope for a nearly stationary360degree orbit; location change is preferable.'
        if kinds.get('visibility_unmeasured'):
            suggestion['visibility_note']='No in-frustum landmark is a framing/measurement issue; it is not by itself an environment occluder.'
        suggestions.append(suggestion)
    collisionless=report.get('collision_visibility_limitations',{}).get('components_without_visibility_collision',0)
    if usable and clean==1260:
        suggestions.append({'priority':2,'action':'render_character_and_orbit_or_occlusion_sensitive_samples',
            'reason':'A clear sampled trace matrix is not a mesh, collisionless-geometry, clothing/hair or exposure visual certification.',
            'collisionless_or_visibility_ignored_component_count':collisionless})
    affected=sorted({(i['action_id'],i['camera_id'],i['aspect']) for i in issues})
    return {'report':inputs.geo.pin(path),'map':report['map'],'attempt_id':report['attempt_id'],
        'status':report['status'],'assessment':state,'current_full_candidate_valid':usable,
        'site':report.get('site'),'site_context':site_context,'summary':summary,'source_pin_errors':bad,
        'issue_count':len(issues),'issue_kinds':dict(kinds),'blocking_actors':dict(actors),
        'affected_issue_combinations':[dict(zip(('action_id','camera_id','aspect'),key)) for key in affected],
        'suggestions':suggestions,'lighting_visual_assessed':report.get('exposure_assessment',{}).get('rendered_luminance_assessed',False),
        'confirmed_exclusions':[],'human_acceptance':'pending'}


def build(run=RUN):
    run=Path(run);inventory=inputs.read(run/'survey_inventory_v1.json')
    paths=sorted((run/'surveys').glob('*.json'))
    records=[];parse_errors=[]
    for path in paths:
        try:records.append(analyze(path))
        except (ValueError,OSError,KeyError,TypeError) as exc:parse_errors.append({'path':str(path),'error':str(exc)})
    notes_path=run/'scene_survey_site_context_notes_v1.json'
    notes=inputs.read(notes_path) if notes_path.exists() else {'notes':[]}
    scenes=[]
    for scene in inventory['scenes']:
        attempts=[r for r in records if r['map']==scene['map_path']]
        eligible=[r for r in attempts if r['current_full_candidate_valid']]
        best=max(eligible,key=lambda r:(r['summary']['no_proxy_conflict_combinations'],r['attempt_id']),default=None)
        if best:state='full_proxy_clear_pending_visual' if best['summary']['no_proxy_conflict_combinations']==1260 else 'candidate_conflicts_need_retry_or_visual_review'
        elif attempts:state='failed_search_or_attempt_not_scene_rejection'
        else:state='not_yet_surveyed'
        contextual=[r for r in notes.get('notes',[]) if r['map']==scene['map_path']]
        scenes.append({'map':scene['map_path'],'scene_label':scene['label'],'primary':True,
            'state':state,'best_report':best,'attempts':attempts,
            'site_context_review':contextual,
            'scene_rejected':False,'confirmed_exclusions':[]})
    queue={'schema':'all_primary_scene_survey_followup_queue_v1','success':not parse_errors,
        'inventory':inputs.geo.pin(run/'survey_inventory_v1.json'),'map_scope':'exact existing26primary entries; no map-purpose rescreen',
        'scenes':scenes,'counts':{'required_primary_maps':26,'maps_with_reports':sum(bool(s['attempts']) for s in scenes),
            'maps_with_full_candidate':sum(s['best_report'] is not None for s in scenes),
            'full_proxy_clear_maps':sum(s['state']=='full_proxy_clear_pending_visual' for s in scenes),
            'maps_with_conflicts':sum(s['state']=='candidate_conflicts_need_retry_or_visual_review' for s in scenes),
            'failed_or_unresolved_maps':sum(s['state']=='failed_search_or_attempt_not_scene_rejection' for s in scenes)},
        'parse_errors':parse_errors,'review_method':'offline report and input-pin triage; no Unreal operations',
        'site_context_notes':inputs.geo.pin(notes_path) if notes_path.exists() else None,
        'limitations':['Queue is mutable; pinned original survey reports remain immutable.',
            'No suspected trace conflict is automatically promoted to a confirmed exclusion.',
            'Offline triage cannot revalidate the current live scene signature; a report covers its saved snapshot only.',
            'Completed sampling and absent collision hits do not certify actual rendered visibility or exposure.']}
    path=run/'scene_survey_followup_queue_v1.json';temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(queue,ensure_ascii=False,separators=(',',':'),allow_nan=False),encoding='utf-8');temporary.replace(path)
    return queue


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-root',type=Path,default=RUN)
    parser.add_argument('--watch-seconds',type=int,default=0);args=parser.parse_args()
    seen=set();deadline=time.monotonic()+min(1200,max(0,args.watch_seconds))
    while True:
        queue=build(args.run_root)
        for scene in queue['scenes']:
            for record in scene['attempts']:
                if record['attempt_id'] in seen:continue
                seen.add(record['attempt_id'])
                print(json.dumps({'event':'new_report','map':record['map'],'attempt':record['attempt_id'],
                    'assessment':record['assessment'],'summary':record['summary'],'issue_kinds':record['issue_kinds'],
                    'actors':record['blocking_actors'],'suggestions':record['suggestions']},ensure_ascii=True),flush=True)
        if time.monotonic()>=deadline:break
        time.sleep(min(30,max(0,deadline-time.monotonic())))
    print(json.dumps({'event':'watch_complete','counts':queue['counts']}),flush=True)


if __name__=='__main__':main()
