"""Read-only analysis of round1 main; all writes stay beside this file.

These are exact metadata-policy/source statistics and state-oracle diagnostics,
not trained model or generated video performance.
"""
from collections import Counter, defaultdict
import hashlib
import itertools
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1] / 'dataset_design_exploration_20261021_v1'


def dump(name, obj):
    (HERE / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def load(split):
    prefix = SOURCE / 'graph' / ('main_scene_holdout_hybrid_' + split)
    return load_prefix(prefix)


def load_prefix(prefix):
    gb = Path(str(prefix) + '_graph.json').read_bytes()
    sb = Path(str(prefix) + '_sessions.jsonl').read_bytes()
    graph = json.loads(gb)
    return graph, [json.loads(x) for x in sb.decode().splitlines()], {
        'graph': hashlib.sha256(gb).hexdigest(), 'sessions': hashlib.sha256(sb).hexdigest()}


def summary(values):
    values = sorted(values)
    return {'count': len(values), 'min': min(values), 'median': values[len(values)//2],
            'max': max(values), 'sum': sum(values),
            'inverse_concentration': sum(values)**2/sum(x*x for x in values)}


def coverage(graph, indices):
    states = [graph['nodes'][i]['state'] for i in sorted(indices)]
    return {a: dict(sorted(Counter(s[a] for s in states).items())) for a in graph['axes']}


def turns(sessions):
    for s in sessions:
        for t in range(1, len(s['node_indices'])):
            yield s, t, s['parent_occurrence_indices_gt'][t]


def index_tables(sessions):
    tables = defaultdict(Counter)
    oracle_branch_tables = defaultdict(Counter)
    for s, t, parent in turns(sessions):
        tables[(len(s['edge_axes']), t)][parent] += 1
        tables[('turn_only',t)][parent] += 1
        if parent != t-1:
            oracle_branch_tables[(len(s['edge_axes']), t)][parent] += 1
            oracle_branch_tables[('turn_only',t)][parent] += 1
    pick = lambda c: min(c, key=lambda v: (-c[v], v))
    return {k: pick(c) for k,c in tables.items()}, {k: pick(c) for k,c in oracle_branch_tables.items()}


def policies(graph, sessions, index, branch_index):
    state = [n['state'] for n in graph['nodes']]
    names = ['always_latest', 'always_root', 'train_turn_index_majority',
             'oracle_session_length_turn_majority', 'oracle_fork_flag_then_train_turn_index',
             'oracle_fork_flag_and_session_length_then_train_index']
    out = {n: Counter() for n in names}
    for s in sessions:
        occ = s['node_indices']; parents = s['parent_occurrence_indices_gt']; length = len(occ)-1
        exact_session = {n: True for n in names}
        for t in range(1,len(occ)):
            parent=parents[t]; fork=parent != t-1
            key=(length,t)
            predictions = [t-1, 0, index.get(('turn_only',t),t-1),index.get(key,t-1),
                           branch_index.get(('turn_only',t),0) if fork else t-1,
                           branch_index.get(key,0) if fork else t-1]
            target=state[occ[t]]; axis=s['edge_axes'][t-1]
            for n,pred in zip(names,predictions):
                exact=pred==parent
                # Gold state + gold edited axis/value: a symbolic sanity oracle,
                # with teacher-forced history; never a pixel/video score.
                predicted_state={**state[occ[pred]],axis:target[axis]}
                out[n]['turn_total']+=1; out[n]['source_exact_turns']+=exact
                out[n]['state_oracle_exact_turns']+=predicted_state==target
                if fork:
                    out[n]['fork_total']+=1; out[n]['source_exact_forks']+=exact
                exact_session[n] &= exact
        for n in names:
            out[n]['session_total']+=1;out[n]['all_sources_correct_sessions']+=exact_session[n]
    for n,c in out.items():
        c['source_accuracy_all_turns']=c['source_exact_turns']/c['turn_total']
        c['source_accuracy_fork_only']=c['source_exact_forks']/c['fork_total']
        c['all_source_accuracy_session']=c['all_sources_correct_sessions']/c['session_total']
    return {n:dict(c) for n,c in out.items()}


def structural_statistics(graph, sessions):
    states=[n['state'] for n in graph['nodes']]
    node_count=Counter(); root_count=Counter(); edge_count=Counter(); fork=Counter(); scene_turn=Counter()
    pair_scenes=Counter(); root_scenes=Counter(); mixed=0
    parent=list(range(len(sessions)))
    conditional_sources=defaultdict(Counter)
    edit_conditional_aliases=Counter()
    def find(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]];i=parent[i]
        return i
    owner={}
    for j,s in enumerate(sessions):
        occ=s['node_indices']; ps=s['parent_occurrence_indices_gt']
        root_count[occ[0]]+=1;node_count.update(occ)
        root_scenes[states[occ[0]]['site']]+=1
        mixed += len({states[i]['site'] for i in occ})>1
        for node in set(occ):
            if node in owner:
                parent[find(j)] = find(owner[node])
            else: owner[node]=j
        for t in range(1,len(occ)):
            source,target=occ[ps[t]],occ[t]
            edge_count[source,target]+=1;scene_turn[states[target]['site']]+=1
            pair_scenes[states[source]['site'],states[target]['site']]+=1
            if ps[t]!=t-1:
                fork['parent_'+str(ps[t])]+=1;fork['lag_'+str(t-1-ps[t])]+=1
                fork['round_'+str(t)]+=1
                ds=[a for a in graph['axes'] if states[source][a]!=states[occ[t-1]][a]]
                fork['source_latest_hamming_'+str(len(ds))]+=1
                fork['edit_axis_'+s['edge_axes'][t-1]]+=1
                conditional_sources[str(t)][str(ps[t])]+=1
                axis=s['edge_axes'][t-1]; target_state=states[target]
                equivalents=[j for j in range(t) if {**states[occ[j]],axis:target_state[axis]}==target_state]
                edit_conditional_aliases[str(len(equivalents))]+=1
    # A node-disjoint packing is only a combinatorial lower bound, not ESS.
    chosen=[]; used=set()
    for j in sorted(range(len(sessions)),key=lambda j:(len(sessions[j]['node_indices']),sessions[j]['session_id'])):
        nodes=set(sessions[j]['node_indices'])
        if not nodes&used:
            chosen.append(j);used.update(nodes)
    return {'root_nodes_used':len(root_count),'root_session_reuse':summary(list(root_count.values())),
            'referenced_nodes':len(node_count),'node_occurrence_reuse':summary(list(node_count.values())),
            'unique_directed_edges_used':len(edge_count),'used_edge_reuse':summary(list(edge_count.values())),
            'session_shared_node_component_sizes':sorted(Counter(find(i) for i in range(len(sessions))).values(),reverse=True),
            'greedy_node_disjoint_session_pack':len(chosen),'pack_node_count':len(used),
            'pack_is_lower_bound_not_optimum_or_statistical_ess':True,
            'loose_node_disjoint_pack_upper_bound':len(states)//3,
            'mixed_scene_sessions':mixed,'root_scene_sessions':dict(root_scenes),'target_scene_turns':dict(scene_turn),
            'source_target_scene_turns':{'|'.join(k):v for k,v in pair_scenes.items()},'forks':dict(fork),
            'fork_source_parent_counts_by_round':{k:dict(v) for k,v in conditional_sources.items()},
            'fork_edit_conditional_equivalent_source_set_sizes':dict(edit_conditional_aliases)}


def contrastive_probes(graph):
    states=[n['state'] for n in graph['nodes']]
    adj=defaultdict(list)
    for e in graph['edges']: adj[e['source_index']].append((e['target_index'],e['axis']))
    groups=defaultdict(list)
    # Histories [source_A, same_latest] vs [source_B, same_latest],
    # same edit a=value, with different preserved fields d != a.
    for latest,neighbors in adj.items():
        for source,d in neighbors:
            for target,a in adj[source]:
                if a!=d and target!=latest:
                    groups[latest,d,a,states[target][a]].append((source,target))
    candidates=[]
    for (latest,d,a,value), choices in sorted(groups.items()):
        for x,y in itertools.combinations(sorted(set(choices)),2):
            if x[0]==y[0] or states[x[0]][d]==states[y[0]][d]: continue
            nodes={latest,*x,*y}
            # Histories contain 1 edit then a historical-root branch probe.
            for source,target in (x,y):
                assert {**states[source],a:value}==states[target]
                assert {**states[source],d:states[latest][d]}==states[latest]
            assert states[x[1]] != states[y[1]]
            candidates.append({'latest':latest,'history_difference_axis':d,'edit_axis':a,'edit_value':value,
                               'left_root_target':list(x),'right_root_target':list(y),'node_union':sorted(nodes)})
    # Deterministic diversity selection; no model or score-based filtering.
    chosen=[];covered=set();used=set();root_usage=Counter();remaining=list(candidates)
    for _ in range(min(100,len(candidates))):
        def score(c):
            tag=(c['history_difference_axis'],c['edit_axis'],states[c['latest']]['site'])
            roots=[c['left_root_target'][0],c['right_root_target'][0]]
            return (tag not in covered,-sum(root_usage[x] for x in roots),-len(set(c['node_union'])-used))
        best=max(range(len(remaining)),key=lambda i:score(remaining[i]))
        c=remaining.pop(best);chosen.append(c);used.update(c['node_union'])
        covered.add((c['history_difference_axis'],c['edit_axis'],states[c['latest']]['site']))
        root_usage.update([c['left_root_target'][0],c['right_root_target'][0]])
    return {'kind':'metadata_constructed_history_necessity_probes_not_rendered_or_human_validated',
            'history_shape':['root','one_edit_to_common_latest','branch_probe_from_root'],
            'same_current_instruction_and_latest_for_each_pair':True,
            'requires_history_value_not_encoded_in_shared_prior_text':True,
            'length2_probe_is_separate_from_main_min_length3_fork_sessions':True,
            'all_media_nodes_already_in_round1_test_graph':True,
            'candidate_pairs':len(candidates),'selected_pairs':len(chosen),'selected_node_union':len(used),
            'coverage_tags_selected':len(covered),'selected_node_coverage':coverage(graph,used) if used else {},
            'pairs':chosen}


def compare_variants():
    variants={
        'round1_main_root_heavy':SOURCE/'graph/main_scene_holdout_hybrid',
        'round1_sourcebalanced':SOURCE/'graph/sourcebalanced_scene_hybrid',
        'round2_stage1_balanced':HERE.parent/'graph/balanced_a5_f1_n3000_s20261021',
        'round2_stage1_hybrid':HERE.parent/'graph/hybrid_a5_f1_n3000_s20261021',
        'round2_strict_motif_a5':HERE.parent/'graph/motif_a5_f1_n3000_s20261021_{split}_uq1_ab3',
        'round2_strict_motif_a7':HERE.parent/'graph/motif_a7_f1_n3000_s20261021_{split}_uq1_ab3'}
    result={}
    for name,prefix in variants.items():
        resolve=lambda split:Path(str(prefix).format(split=split)) if '{split}' in str(prefix) else Path(str(prefix)+'_'+split)
        if not Path(str(resolve('test'))+'_sessions.jsonl').exists():
            result[name]={'status':'not_available_at_analysis_time'};continue
        train,ts,th=load_prefix(resolve('train'))
        test,es,eh=load_prefix(resolve('test'))
        index,branch_index=index_tables(ts)
        result[name]={'hashes':{'train':th,'test':eh},'test_policies':policies(test,es,index,branch_index),
                      'test_statistics':structural_statistics(test,es),
                      'test_coverage':coverage(test,range(len(test['nodes'])))}
    dump('source_balance_comparison.json',result)
    return {name:{'fork_root_accuracy':row.get('test_policies',{}).get('always_root',{}).get('source_accuracy_fork_only'),
                  'fork_flag_turn_only_accuracy':row.get('test_policies',{}).get('oracle_fork_flag_then_train_turn_index',{}).get('source_accuracy_fork_only'),
                  'fork_flag_and_length_index_accuracy':row.get('test_policies',{}).get('oracle_fork_flag_and_session_length_then_train_index',{}).get('source_accuracy_fork_only'),
                  'edit_conditional_aliases':row.get('test_statistics',{}).get('fork_edit_conditional_equivalent_source_set_sizes')}
            for name,row in result.items()}


def select_subset(graph,sessions,budget):
    states=[n['state'] for n in graph['nodes']]
    # Cover actual values first, then complete whole session node unions.
    remaining_values={(a,s[a]) for s in states for a in graph['axes']}
    selected=set()
    while remaining_values and len(selected)<budget:
        node=max((i for i in range(len(states)) if i not in selected),
                 key=lambda i:(sum((a,states[i][a]) in remaining_values for a in graph['axes']),-i))
        selected.add(node);remaining_values-={(a,states[node][a]) for a in graph['axes']}
    paths=[set(s['node_indices']) for s in sessions]
    while len(selected)<budget:
        candidates=[i for i,nodes in enumerate(paths) if 0<len(nodes-selected)<=budget-len(selected)]
        if not candidates: break
        # Completes an existing session at minimal media cost. Not an optimum.
        idx=min(candidates,key=lambda i:(len(paths[i]-selected),sessions[i]['session_id']))
        selected.update(paths[idx])
    if len(selected)<budget:
        selected.update(i for i in range(len(states)) if i not in selected and len(selected)<budget)
    kept=[i for i,nodes in enumerate(paths) if nodes<=selected]
    affected=[i for i,nodes in enumerate(paths) if nodes&selected]
    edge_count=sum(e['source_index'] in selected and e['target_index'] in selected for e in graph['edges'])
    return {'node_indices':sorted(selected),'node_count':len(selected),'retained_existing_sessions':len(kept),
            'affected_existing_sessions_if_removed_from_fit':len(affected),'induced_directed_edges':edge_count,
            'retained_session_indices':kept,'coverage':coverage(graph,selected),
            'selection_is_greedy_not_optimal_capacity':True}


def main():
    train,ts,th=load('train');test,es,eh=load('test')
    index,branch_index=index_tables(ts)
    stats={'kind':'exact_structural_analysis_no_model_training_or_video_scores',
           'source_hashes':{'train':th,'test':eh},'test_full_node_coverage':coverage(test,range(len(test['nodes']))),
           'policies_on_test':policies(test,es,index,branch_index),
           'train_fitted_turn_table':{'|'.join(map(str,k)):v for k,v in index.items()},
           'train_fitted_oracle_branch_table':{'|'.join(map(str,k)):v for k,v in branch_index.items()},
           'test':structural_statistics(test,es),'train':structural_statistics(train,ts)}
    probes=contrastive_probes(test)
    alternative={'status':'offline_layout_probe_not_frozen_or_complete_replacement_manifest',
                 'ood400_from_existing_test':select_subset(test,es,400),
                 'seen100_from_existing_train':select_subset(train,ts,100),
                 'requires_removing_seen100_and_all_affected_sessions_from_fit':True,
                 'requires_new_100_compatible_train_nodes_and_resampling_to_restore_2500_12000':True,
                 'no_3000_session_capacity_claim_from_retained_session_count':True}
    assert sum(len(s['edge_axes']) for s in es)==11200
    assert stats['policies_on_test']['always_latest']['source_exact_forks']==0
    assert stats['policies_on_test']['always_latest']['source_exact_turns']==10200
    assert probes['selected_pairs']<=100 and probes['selected_node_union']<=500
    dump('structural_analysis.json',stats);dump('history_necessity_probes.json',probes)
    dump('test_layout_probe.json',alternative)
    inv=json.loads((SOURCE/'inventory/normalized_inventory.json').read_text(encoding='utf-8'))
    sex={x['id']:x['sex'] for x in inv['identities']}
    nodes=test['nodes']; proxy_rows=[]
    for i,c in enumerate(probes['pairs']):
        for role,node in [('left_root',c['left_root_target'][0]),('left_target',c['left_root_target'][1]),
                          ('right_root',c['right_root_target'][0]),('right_target',c['right_root_target'][1]),('latest',c['latest'])]:
            s=nodes[node]['state']
            proxy_rows.append({'pair_index':i,'role':role,'node_index':node,'identity':s['identity'],'sex':sex[s['identity']],
                               'motion':s['action'],'camera':s['camera'],'aspect':s['aspect'],'site':s['site'],
                               'history_difference_axis':c['history_difference_axis'],'edit_axis':c['edit_axis']})
    dump('paired_probe_observability_keys.json',proxy_rows)
    comparison=compare_variants()
    print(json.dumps({'test_source_policies':stats['policies_on_test'],
                      'test_dependency_components':stats['test']['session_shared_node_component_sizes'],
                      'test_node_disjoint_pack':stats['test']['greedy_node_disjoint_session_pack'],
                      'contrastive_pairs_available_selected_nodes':[probes['candidate_pairs'],probes['selected_pairs'],probes['selected_node_union']],
                      'layout_retained_sessions':[alternative['ood400_from_existing_test']['retained_existing_sessions'],alternative['seen100_from_existing_train']['retained_existing_sessions']],
                      'source_balance_comparison':comparison},indent=2))


if __name__=='__main__': main()
