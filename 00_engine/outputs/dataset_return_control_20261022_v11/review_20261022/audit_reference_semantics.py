"""Read-only independent reference/render-request semantic audit of v11."""
from pathlib import Path
import json, hashlib, collections, random

ROOT=Path(__file__).resolve().parents[4]
RUN=Path(__file__).resolve().parents[1]
CAND=RUN/'selected_candidate'
BASE=ROOT/'00_engine/outputs/dataset_trial_build_20261021_v1'
def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def stable(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
m=read(CAND/'reference_manifest.json'); summary=read(CAND/'reference_summary.json'); cat=read(BASE/'catalog.json')
errors=collections.Counter(); examples={}; checks=collections.Counter()
def check(ok,kind,evidence=None):
    checks[kind]+=1
    if not ok:
        errors[kind]+=1
        if len(examples.setdefault(kind,[]))<3: examples[kind].append(evidence)
refs={r['id']:r for r in m['requirements']}
check(len(refs)==len(m['requirements']),'unique_reference_ids')
check(len({stable([r['kind'],r['key']]) for r in refs.values()})==len(refs),'unique_reference_keys')
assets={}; groups={}; ids={}; hairs=collections.defaultdict(dict)
for sex,pool in cat['sexes'].items():
    ids.update({r['id']:r for r in pool['identities']})
    for r in pool['hairs']: hairs[r['hair_id']][sex]=r
    for r in pool['shared_shoes']: assets[r['asset_id']]={**r,'slot':'shoes'}
    for f in pool['families']:
        for g in f['groups']:
            groups[(sex,f['family_id'],g['group_id'])]=g
            for a in sum(g['slot_options'].values(),[])+g['required_assets']+g['optional_assets']: assets[a['asset_id']]=a
actions={r['id']:r for r in cat['actions']}; cameras={r['id']:r for r in cat['cameras']}; sites={r['id']:r for r in cat['sites']}
def pieces(s):
    w=s['wardrobe'];g=groups[(s['sex'],w['family_id'],w['group_id'])]
    return set([r['asset_id'] for r in g['required_assets']]+[v for v in w['slot_choices'].values() if v]+w['optional_asset_ids']+([w['shared_shoe_id']] if w['shared_shoe_id'] else []))
for r in refs.values():
    e=r['id'];check(r['media_path'] is None and r['status']=='planned_not_rendered','planned_not_rendered',e)
    check(r['id']=='ref_'+hashlib.sha256(stable({'kind':r['kind'],'key':r['key']}).encode()).hexdigest()[:24],'reference_id_hash',e)
    if r['kind']=='wardrobe_piece':
        a=assets[r['asset_id']]
        check(r['mesh_paths']==a['mesh_paths'] and r['slot']==a['slot'],'garment_exact_asset_meshes',e)
        check(r['body_present'] is False and r['background']=='neutral' and r['preserve_3d_shape'] is True,'garments_only_neutral_3d',e)
    if r['kind']=='identity': check(r['view']=='front_face' and r['character_meshes']==ids[r['identity']]['meshes'],'identity_front_exact_meshes',e)
    if r['kind']=='scene':
        check(r['site']==sites[r['site_id']] and r['person_present'] is False and r['clip_required'] is False and r['media_type']=='image','scene_empty_background_exact_site',e)
    if r['kind']=='motion':
        variants=[v for v in actions[r['action_id']]['variants'] if v['sex']==r['sex']]
        check(len(variants)==1 and variants[0]==r['available_target_sex_action_variant'],'motion_exact_target_sex_source',e)
        check(r['camera_rule']==cameras[r['camera_id']] and set(r['match_target'])=={'camera_rule','phase','speed','duration'},'motion_camera_clock_contract',e)
for pool in m['hair_reference_pools']:
    h=pool['hair_id']; sex=pool['fit_sex'];variants=pool['variants']
    check(len(variants)==2 and len({v['carrier_identity'] for v in variants})==2 and sex in hairs[h],'hair_two_distinct_legal_carriers',h)
    rng=random.Random(f'{m["seed"]}:hair_carriers:{h}'); expectedsex=rng.choice(sorted(hairs[h])); expected=rng.sample(sorted(r['id'] for r in cat['sexes'][expectedsex]['identities']),2)
    check(sex==expectedsex and [v['carrier_identity'] for v in variants]==expected,'hair_seed_reproducibility',h)
    for v in variants:
        rr=[refs[x] for x in v['reference_ids']]
        check(len(rr)==2 and {r['view'] for r in rr}=={'front','back'} and all(r['hair_color']=='black' and r['hair_id']==h and r['carrier_identity']==v['carrier_identity'] and r['carrier_sex']==sex and r['carrier_meshes']==ids[v['carrier_identity']]['meshes'] and r['hair_fit']==hairs[h][sex]['fit'] for r in rr),'hair_exact_pair_and_fit',h)

planpath=ROOT/'00_engine/outputs/production_workflow_20261017_v1/camera_library/production10/camera_plan.json'
plan=read(planpath);shots={s['shot_id']:s for s in plan['shots']}
links={(r['split'],r['session_id'],r['edit_round']):r for r in m['reference_links']}
check(len(links)==len(m['reference_links']),'unique_step_link_keys')
seen=set(); selected_refs=set(); pool_refs=set(); splitstats={}; renderstats={}
for split in ('train','test'):
    folder=CAND/split;nodes={n['id']:n for n in read(folder/'nodes.json')}; reqs=read(folder/'render_requests.json');stats=collections.Counter(); renders=collections.Counter()
    check(len(reqs)==len(nodes) and {r['node_id'] for r in reqs}==set(nodes),'render_exact_node_id_bijection',split)
    for r in reqs:
        n=nodes[r['node_id']];s=n['state'];cb=r['camera_binding']
        check(r['state']==s and r['content_id']==n['content_id'] and r['aspect']==s['aspect'],'render_matches_entire_node_state',[split,r['node_id']])
        check(cb['motion_id']==s['action'] and cb['camera_id']==s['camera'] and cb['orientation']==s['aspect'],'render_symbolic_camera_binding',[split,r['node_id']])
        shot=shots.get(cb['shot_id'])
        check(shot is not None and all(cb[k]==shot[k] for k in ('motion_id','camera_id','orientation','width','height','trajectory_sha256')) and Path(cb['plan_path'])==planpath,'render_current_source_camera_template',[split,r['node_id']])
        check(r['status']=='planned_not_rendered' and r['source_preset_is_final_render_spec'] is False and all(r[k] is None for k in ('final_resolution','final_fps','final_duration_seconds')),'render_explicit_unfrozen_media',[split,r['node_id']])
        renders[s['aspect']]+=1
    renderstats[split]={'nodes':len(nodes),'render_requests':len(reqs),'aspect':dict(renders)}
    edges={(e['source'],e['target']):e for e in read(folder/'edges.json')};usededges=set()
    for line in (folder/'sessions.jsonl').read_text(encoding='utf-8-sig').splitlines():
        sess=json.loads(line);stats['sessions']+=1
        for round,step in enumerate(sess['steps'],1):
            k=(split,sess['id'],round);seen.add(k);l=links.get(k);check(l is not None,'every_step_has_link',k)
            if l is None:continue
            source=nodes[step['source']];target=nodes[step['target']];s=source['state'];t=target['state'];axis=step['axis'];rr=[refs[x] for x in l['reference_ids']]
            check(l['source_history_occurrence']==step['source_position'] and step['source']==sess['history'][step['source_position']] and step['target']==sess['history'][round],'link_source_history_binding',k)
            check(l['source_node']==step['source'] and l['target_node']==step['target'] and l['source_canonical_id']==source['canonical_id'] and l['target_canonical_id']==target['canonical_id'] and l['axis']==axis and l['mode']==step['mode'] and l['used_edge_key']==f'{split}:{step["source"]}->{step["target"]}','link_exact_step_and_canonical_binding',k)
            usededges.add((step['source'],step['target']));selected_refs.update(l['reference_ids']);stats['edit_step_occurrences']+=1;stats['axis_'+axis]+=1
            if axis=='identity': check(len(rr)==1 and rr[0]['kind']=='identity' and rr[0]['identity']==t['identity'],'identity_link_target',k)
            elif axis=='hair':
                variants=l['hair_reference_variant_pool'];pool_refs.update(x for v in variants for x in v['reference_ids']);v=random.Random(f'{m["seed"]}:{split}:{sess["id"]}:{round}:hair_pair').choice(variants)
                check(l['hair_reference_pool_id']==t['hair'] and l['target_fit_sex']==t['sex'] and l['selected_hair_variant_id']==v['variant_id'] and l['reference_ids']==v['reference_ids'] and all(r['hair_id']==t['hair'] for r in rr),'hair_link_target_and_selected_pair',k)
            elif axis in ('site','action'):
                kind='scene' if axis=='site' else 'motion'; key=rr[0]['key'] if len(rr)==1 else {}
                expect={'action':t['action'],'camera':t['camera'],'sex':t['sex'],'symbolic_aspect':t['aspect']}
                if axis=='site':expect['site']=t['site']
                check(len(rr)==1 and rr[0]['kind']==kind and all(key.get(a)==b for a,b in expect.items()),'scene_motion_link_exact_symbolic_target',k)
            elif axis=='wardrobe':
                stats['wardrobe_'+step['mode']]+=1;targetpieces=pieces(t)
                if step['mode']=='whole_outfit': expected=targetpieces
                else:
                    changed=[slot for slot,val in t['wardrobe']['slot_choices'].items() if val!=s['wardrobe']['slot_choices'].get(slot)]
                    check(len(changed)==1 and l['single_piece_target_slot']==changed[0],'single_reference_changed_slot',k)
                    piece=t['wardrobe']['slot_choices'][changed[0]];expected={piece} if piece else set()
                    check(s['wardrobe']['shared_shoe_id']==t['wardrobe']['shared_shoe_id'],'single_preserves_shoe',k)
                    if piece is None: check(not rr and any(x['kind']=='remove_optional_piece' for x in l['text_constraints']),'optional_remove_explicit_no_media',k)
                check(set(l['target_piece_ids'])==expected and len(rr)==2*len(expected) and {(r['asset_id'],r['view']) for r in rr}=={(a,v) for a in expected for v in ('front','back')},'wardrobe_exact_target_items_and_views',k)
                barefoot=not any(assets[a]['slot']=='shoes' for a in targetpieces)
                check(l['target_barefoot']==barefoot and (not barefoot or any(x['kind']=='barefoot' for x in l['text_constraints'])),'barefoot_explicit_no_shoe_image',k)
                if barefoot:stats['wardrobe_barefoot']+=1
                if len(expected)>1:stats['wardrobe_multiple_items']+=1
            elif axis in ('camera','hair_color'):
                check(not rr and len(l['text_constraints'])==1 and l['text_constraints'][0]['target']==t[axis] and l['text_constraints'][0]['media_reference_required'] is False,'text_only_camera_color_exact_target',k)
    stats['unique_used_edges']=len(usededges);splitstats[split]=dict(stats)
check(set(links)==seen,'no_extraneous_links')
check(selected_refs|pool_refs==set(refs),'no_unrequired_reference_items')
check(summary['unique_reference_items']==len(refs) and summary['reference_link_occurrences']==len(seen) and summary['unique_reference_items_by_kind']==dict(collections.Counter(r['kind'] for r in refs.values())),'summary_recomputed_counts')
pins=[]
for origin,pp in [('manifest',m['inputs']),('catalog_sources',list(cat['sources'].values())),('catalog_source_pins',cat['source_pins'])]:
    for p in pp:
        actual=sha(p['path']) if Path(p['path']).is_file() else None
        pins.append({'origin':origin,**p,'actual_sha256':actual,'matches':actual==p['sha256']})
        check(actual==p['sha256'],'input_snapshot_hash_'+origin,p['path'])
out={'schema':'independent_v11_reference_semantic_review_20261022','candidate':str(CAND),'read_only_candidate':True,'passed':not errors,'checks':dict(checks),'errors':dict(errors),'examples':examples,'counts':{'requirements':len(refs),'links':len(seen),'selected_reference_items':len(selected_refs),'pool_only_reference_items':len(pool_refs-selected_refs),'kind':dict(collections.Counter(r['kind'] for r in refs.values()))},'splits':splitstats,'render_requests':renderstats,'input_pins':pins,'current_camera_plan_pin':{'path':str(planpath),'sha256':sha(planpath)},'pending_not_candidate_failures':['final_resolution_fps_duration','motion_carrier_and_main_clock','exact_scene_initial_world_transform_and_frame_signature','reference_generation_implementation_and_edit_text_templates','final_render_jobs_must_use_render_readiness_exposure_and_warmup_policy'], 'documentation_issue':'REFERENCES.md still lists aspect as unfrozen despite v11 dual-aspect policy; final numeric media dimensions remain unfrozen.'}
(Path(__file__).parent/'reference_findings.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in out.items() if k not in ('input_pins','examples','checks')},ensure_ascii=False,indent=2))
