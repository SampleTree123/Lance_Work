"""Independent actual-node/history frequency audit for the v10 experiment.

Uses formal Rules.clothes, not builder counts. Writes only the requested audit.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
OUT=HERE.parents[1]
sys.path.insert(0,str(OUT/'dataset_balanced_graph_20261022_v5'))
from audit_candidate import Rules, UPPER, quota_counts

FIELDS=('identity','action','hair','hair_color','site')

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def pin(path):return {'path':str(Path(path).resolve()),'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()}
def token(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def content_key(rules,state):return rules.canonical(dict(state,aspect='landscape'))
def visible_core(rules,state):
    clothes=rules.clothes(state)
    if state['camera']=='front_head':return ()
    return tuple(sorted(set(clothes['upper'])&set(clothes['core']))) if state['camera'] in UPPER else clothes['core']

def frequency(counts,pool):
    keys=sorted(pool); values={k:counts[k] for k in keys};total=sum(values.values());mean=total/len(keys) if keys else 0
    # Exact integer cross-products avoid a false failure on range boundaries.
    below=[k for k,v in values.items() if 2*len(keys)*v<total or v==0]
    above=[k for k,v in values.items() if 2*len(keys)*v>3*total]
    return {'denominator_values':len(keys),'total':sum(values.values()),'mean':mean,
        'counts':values,'ratios_to_own_mean':{k:v/mean if mean else None for k,v in values.items()},
        'zero_values':[k for k,v in values.items() if not v], 'below_half_mean':below,'above_one_and_half_mean':above,
        'passed':bool(keys) and not below and not above,
        'minimum':min(values.values(),default=0),'maximum':max(values.values(),default=0)}

def exposure(rules,weighted_states,train):
    counts={field:collections.Counter() for field in (*FIELDS,'core_asset')}
    action_cameras=collections.defaultdict(collections.Counter)
    camera_actions=collections.defaultdict(collections.Counter)
    core_actions=collections.defaultdict(set);core_cameras=collections.defaultdict(set)
    head_count=0;head_by_action=collections.Counter()
    for state,weight in weighted_states:
        for field in FIELDS:counts[field][state[field]]+=weight
        if state['camera']=='front_head':head_count+=weight;head_by_action[state['action']]+=weight
        else:
            action_cameras[state['action']][state['camera']]+=weight
            camera_actions[state['camera']][state['action']]+=weight
        for asset in visible_core(rules,state):
            counts['core_asset'][asset]+=weight
            core_actions[asset].add(state['action']);core_cameras[asset].add(state['camera'])
    pools={field:rules.pools[field] if train else set(counts[field]) for field in counts}
    distributions={field:frequency(counts[field],pool) for field,pool in pools.items()}
    within_action={action:frequency(cs,set(cs)) for action,cs in sorted(action_cameras.items())}
    opposite={camera:frequency(cs,set(cs)) for camera,cs in sorted(camera_actions.items())}
    garment={asset:{'visible_count':counts['core_asset'][asset], 'actions':sorted(core_actions[asset]),
        'effective_cameras':sorted(core_cameras[asset]),'action_count':len(core_actions[asset]),'effective_camera_count':len(core_cameras[asset]),
        'passed_min3_actions_and_cameras':len(core_actions[asset])>=3 and len(core_cameras[asset])>=3} for asset in sorted(pools['core_asset'])}
    return {'frequency_unit':'caller-defined weighted actual states','distributions':distributions,
        'action_within_camera_counts':{a:dict(cs) for a,cs in sorted(action_cameras.items())},
        'each_action_internal_camera_frequency':within_action,
        'opposite_camera_internal_action_frequency_diagnostic_only':opposite,
        'visible_garment_context_coverage':garment,'front_head_occurrences_excluded_from_effective_action_camera_and_all_core':head_count,
        'front_head_action_concentration_diagnostic':{action:{'all_camera_count':counts['action'][action],'front_head_count':head_by_action[action],
            'front_head_fraction':head_by_action[action]/counts['action'][action] if counts['action'][action] else 0} for action in sorted(pools['action'])},
        'all_requested_global_frequencies_in_range':all(d['passed'] for d in distributions.values()),
        'all_action_internal_camera_frequencies_in_range':all(d['passed'] for d in within_action.values()),
        'all_represented_garments_min3_actions_and_cameras':bool(garment) and all(g['passed_min3_actions_and_cameras'] for g in garment.values())}

def audit_split(rules,root,split):
    path=root/split;nodes=read(path/'nodes.json');state_by_id={n['id']:n['state'] for n in nodes}
    saved_edges={(e['source'],e['target']):e for e in read(path/'edges.json')}
    errors=collections.Counter();examples=[]
    def error(kind,detail):
        errors[kind]+=1
        if len(examples)<30:examples.append({'kind':kind,'detail':detail})
    if len(state_by_id)!=len(nodes):error('duplicate_node_ids',len(nodes)-len(state_by_id))
    sessions=[json.loads(line) for line in (path/'sessions.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    history=collections.Counter();semantic_edges=collections.Counter();axis_edges=collections.defaultdict(collections.Counter)
    quotas=collections.Counter();session_signatures=set();length5=collections.Counter()
    exact_nodes={};keys={}
    for node,state in state_by_id.items():
        try:
            invalid=rules.valid_state(state)
            if invalid:error('invalid_state',{'node':node,'reasons':invalid})
            key=content_key(rules,state);keys[node]=key
            exact=rules.canonical(state)
            if exact in exact_nodes:error('duplicate_render_state',[exact_nodes[exact],node])
            exact_nodes[exact]=node
        except Exception as exc:error('formal_state_resolution',{'node':node,'error':str(exc)})
    for chain in sessions:
        h=chain['history'];steps=chain['steps'];length=chain['length'];kind=chain['kind']
        quotas[f'{kind}_{length}']+=1
        history.update(h)
        if len(h)!=length+1 or len(steps)!=length:error('history_length',chain['id'])
        if length not in (2,3,4,5) or kind not in ('linear','fork'):error('invalid_kind_length',chain['id'])
        forks=[];aspects=set()
        for node in h:
            if node not in state_by_id:error('unknown_history_node',{'chain':chain['id'],'node':node})
            else:aspects.add(state_by_id[node]['aspect'])
        if len(aspects)!=1:error('mixed_aspect_chain',chain['id'])
        for turn,step in enumerate(steps,1):
            pos=step['source_position'];s=step['source'];t=step['target']
            if not (0<=pos<turn and pos<len(h) and turn<len(h) and h[pos]==s and h[turn]==t):
                error('parent_history_binding',{'chain':chain['id'],'turn':turn});continue
            if pos!=turn-1:forks.append(turn)
            if s not in keys or t not in keys:continue
            registered=saved_edges.get((s,t))
            if registered is None:error('unregistered_chain_edge',{'chain':chain['id'],'turn':turn})
            elif registered['axis']!=step['axis']:error('registered_edge_axis',{'chain':chain['id'],'turn':turn})
            try:
                actual=rules.edge(state_by_id[s],state_by_id[t])
                if actual['axis']!=step['axis'] or actual['mode']!=step['mode']:error('edge_metadata',{'chain':chain['id'],'turn':turn})
            except Exception as exc:error('illegal_atomic_edge',{'chain':chain['id'],'turn':turn,'error':str(exc)})
            pair=(keys[s],keys[t]);semantic_edges[pair]+=1;axis_edges[step['axis']][pair]+=1
        if kind=='linear' and forks:error('linear_nonlatest_parent',chain['id'])
        if kind=='fork' and forks!=[chain.get('fork_round')]:error('fork_count_or_round',chain['id'])
        sig=(tuple(keys.get(n,('missing',n)) for n in h),tuple(st['source_position'] for st in steps))
        if sig in session_signatures:error('duplicate_structural_chain',chain['id'])
        session_signatures.add(sig)
        if length==5:length5[len(set(st['axis'] for st in steps))]+=1
    expected_sessions=12000 if split=='train' else 2400
    expected_quota=quota_counts(expected_sessions)
    if dict(quotas)!=expected_quota:error('fixed_chain_quotas',{'actual':dict(quotas),'expected':expected_quota})
    used=set(history);unused=set(state_by_id)-used
    if unused:error('unused_registered_nodes',len(unused))
    content={keys[n]:state_by_id[n] for n in used if n in keys}
    unique=exposure(rules,[(s,1) for s in content.values()],split=='train')
    occurrence=exposure(rules,[(state_by_id[n],c) for n,c in history.items() if n in state_by_id],split=='train')
    unique['frequency_unit']='one per actual chain-used complete content state; aspect deduplicated'
    occurrence['frequency_unit']='every saved chain history position including initial, abandoned fork branches and revisits; no aspect dedup across occurrences'
    # Formal attainable effective cameras are conditional on the represented
    # sites/aspects, never fabricated from nonexistent extra sites.
    camera_limits={}
    actions=rules.pools['action'] if split=='train' else {s['action'] for s in content.values()}
    sites={s['site'] for s in content.values()};aspects={s['aspect'] for s in state_by_id.values()}
    for action in sorted(actions):
        possible={camera for camera in rules.pools['camera'] if camera!='front_head' and any((site,action,camera,aspect) not in rules.exclusions for site in sites for aspect in aspects)}
        required=10 if split=='train' else min(10,len(possible))
        cameras=set(unique['action_within_camera_counts'].get(action,{}))
        camera_limits[action]={'actual':len(cameras),'cameras':sorted(cameras),'formally_attainable_at_represented_sites':len(possible),'required':required,'passed':len(cameras)>=required}
    edge_hist=collections.Counter(semantic_edges.values());used_edges=len(semantic_edges)
    max_reuse=max(semantic_edges.values(),default=0)
    if max_reuse>4:error('semantic_edge_cap4',max_reuse)
    frequency_pass=all(e[k] for e in (unique,occurrence) for k in ('all_requested_global_frequencies_in_range','all_action_internal_camera_frequencies_in_range'))
    core_context_pass=unique['all_represented_garments_min3_actions_and_cameras'] if split=='train' else True
    axis_counts={axis:sum(cs.values()) for axis,cs in axis_edges.items()}
    nonidentity_axes=('hair','hair_color','wardrobe','action','camera','site')
    six_mean=sum(axis_counts.get(a,0) for a in nonidentity_axes)/6
    six_deviation={a:abs(axis_counts.get(a,0)-six_mean)/six_mean if six_mean else 1 for a in nonidentity_axes}
    if max(six_deviation.values())>.10:error('six_nonidentity_axis_balance',six_deviation)
    result={'split':split,'inputs':[pin(path/f) for f in ('nodes.json','edges.json','sessions.jsonl')],
        'counts':{'registered_render_nodes':len(nodes),'used_render_nodes':len(used),'unique_used_content_states':len(content),'unused_registered_nodes':len(unused),'sessions':len(sessions),'history_occurrences':sum(history.values()),'edit_occurrences':sum(len(c['steps']) for c in sessions)},
        'semantic_error_counts':dict(errors),'semantic_error_examples':examples,'passed_hard_semantics':not errors,
        'unique_content_node_frequency':unique,'chain_history_occurrence_frequency':occurrence,
        'action_effective_camera_minimum':camera_limits,
        'semantic_directed_edge_reuse':{'ignores_aspect':True,'unique_used_edges':used_edges,'edit_occurrences':sum(semantic_edges.values()),'mean':sum(semantic_edges.values())/used_edges if used_edges else 0,'maximum':max_reuse,'histogram':dict(sorted(edge_hist.items())),'four_use_edge_fraction':edge_hist[4]/used_edges if used_edges else 0,'mean_target_2_5_is_soft':True,'four_use_fraction_soft_target':.005,'per_axis_mean':{axis:sum(cs.values())/len(cs) for axis,cs in axis_edges.items()}},
        'length5_distinct_axis_histogram':dict(sorted(length5.items())),
        'edit_axis_counts':axis_counts,'six_nonidentity_max_relative_deviation':max(six_deviation.values()),
        'all_node_and_chain_frequency_ranges_passed':frequency_pass,
        'all_action_camera_minima_passed':bool(camera_limits) and all(v['passed'] for v in camera_limits.values()),
        'action_camera_minimum_is_training_requirement':split=='train',
        'all_visible_core_context_minima_passed':core_context_pass,
        'garment_context_minimum_is_training_requirement':split=='train',
        'passed_all_requested_distribution_checks':frequency_pass and core_context_pass and (bool(camera_limits) and all(v['passed'] for v in camera_limits.values()) if split=='train' else True)}
    return result,set(content),session_signatures

def audit(candidate,output):
    candidate=Path(candidate);output=Path(output);rules=Rules();results={};content_keys={};sessions={}
    for split in ('train','test'):
        results[split],content_keys[split],sessions[split]=audit_split(rules,candidate,split)
    overlap=len(content_keys['train']&content_keys['test']);chain_overlap=len(sessions['train']&sessions['test'])
    result={'schema':'independent_distributed_graph_frequency_audit_v10','candidate':str(candidate.resolve()),
        'scope':'saved actual main content and full chain histories, formal clothes visibility, no UE/media acceptance',
        'range_policy':{'minimum_ratio':.5,'maximum_ratio':1.5,'own_mean_for_each_attribute_and_frequency_unit':True,'train_full_catalog_includes_zero_counts':True,'test_only_represented_values':True,'exceptions_preapproved':[]},
        'visibility_policy':{'front_head':'no garments and no effective action camera','upper_cameras':sorted(UPPER),'upper':'formal upper assets intersect actual resolved core','other_cameras':'all actual resolved core','occlusion':'not inferred; symbolic camera-class visibility only'},
        'inputs':[pin(Path(__file__)),pin(OUT/'dataset_balanced_graph_20261022_v5/audit_candidate.py'),pin(OUT/'dataset_trial_build_20261021_v1/normalize_catalog.py'),pin(OUT/'dataset_trial_build_20261021_v1/catalog.json')],
        'splits':results,'canonical_content_train_test_overlap':overlap,'structural_chain_train_test_overlap':chain_overlap,
        'passed_hard_semantics':not overlap and not chain_overlap and all(s['passed_hard_semantics'] for s in results.values()),
        'passed_all_requested_distribution_checks':all(s['passed_all_requested_distribution_checks'] for s in results.values()),
        'claims_three_seed_stability':False,'claims_media_or_training_acceptance':False}
    result['passed']=result['passed_hard_semantics'] and result['passed_all_requested_distribution_checks']
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':result['passed'],'hard_semantics':result['passed_hard_semantics'],'distribution_checks':result['passed_all_requested_distribution_checks'],'counts':{s:r['counts'] for s,r in results.items()}},ensure_ascii=False))
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,default=HERE/'distributed_frequency_audit.json');a=p.parse_args();audit(a.candidate,a.output)
