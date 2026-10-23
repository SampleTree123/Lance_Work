"""Compare annotation allocation on one frozen seven-axis strict family graph.

Uniform means uniform within a shared finite candidate pool and exact strata;
it does not mean uniform over every possible legal graph session.
"""
import sys
sys.dont_write_bytecode=True
from collections import Counter,defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import time
import experiments as ex

HERE=Path(__file__).resolve().parent
UNIT={(2,'linear'):5,(3,'linear'):5,(4,'linear'):5,(5,'linear'):5,
      (3,'root'):2,(4,'root'):1,(4,'intermediate'):3,(5,'root'):1,(5,'intermediate'):3}


def stratum(s):
    occ,par,axes=s
    fork=[t for t,p in enumerate(par) if t and p != t-1]
    return len(axes),('linear' if not fork else 'root' if par[fork[0]]==0 else 'intermediate')


def load_graph(split):
    stem=f'motif_a7_f5_n3000_s20261021_{split}_uq1_ab3'
    graph=ex.read(stem+'_graph.json')
    ex.kernel.AXES=tuple(graph['axes'])
    nodes=[tuple(n['state'][a] for a in graph['axes']) for n in graph['nodes']]
    edges={(e['source_index'],e['target_index']):graph['axes'].index(e['axis']) for e in graph['edges']}
    adj=[[] for _ in nodes]
    for (u,v),a in edges.items():adj[u].append((v,a))
    original=[]
    for line in (HERE/(stem+'_sessions.jsonl')).read_text().splitlines():
        s=json.loads(line)
        original.append((s['node_indices'],s['parent_occurrence_indices_gt'],[graph['axes'].index(a) for a in s['edge_axes']]))
    return stem,graph,nodes,adj,edges,original


def pool(split,nodes,adj,edges,original):
    sessions=list(original)
    seen={(tuple(o),tuple(p)) for o,p,a in sessions}
    attempts=[]
    for j,balanced in enumerate((False,True,False,True)):
        extra,metrics=ex.kernel.sample_sessions(nodes,adj,edges,len(original),random.Random(90101+j),balanced=balanced,
            quality=True,followup=True,fork_length_policy='20_40_40',source_balanced=True,unique_source_result=True,axis_balance=3.)
        added=0
        for o,p,a in extra:
            key=tuple(o),tuple(p)
            if key not in seen:
                sessions.append((o,p,a));seen.add(key);added+=1
        attempts.append({'seed':90101+j,'balanced_proposal':balanced,'generated':len(extra),'new_unique':added,
                         'generation_attempts':metrics['sampling_attempts']})
    path=HERE/f'sampling_{split}_candidate_pool.jsonl'
    with path.open('w',encoding='utf-8') as fp:
        for i,(o,p,a) in enumerate(sessions):
            fp.write(json.dumps({'pool_index':i,'node_indices':o,'parent_occurrence_indices_gt':p,
                'edge_axes':[ex.kernel.AXES[x] for x in a]},separators=(',',':'))+'\n')
    return sessions,attempts


def features(sessions,edges):
    edge_ids={e:i for i,e in enumerate(sorted(edges))}
    result=[]
    for o,p,a in sessions:
        ids=tuple(edge_ids[o[p[t]],o[t]] for t in range(1,len(o)))
        result.append({'edges':ids,'nodes':o,'pair':(o[0],o[-1]),'stratum':stratum((o,p,a)),
                       'order':(tuple(a),tuple(p)),'shortest':len(set(a))==len(a) and all(t==0 or src==t-1 for t,src in enumerate(p))})
    return result,edge_ids


def diagnose(selected,sessions,feat,nodes,edges,edge_ids):
    edge_counts=Counter();node_counts=Counter();pairs=Counter();orders=Counter();commuting=Counter();strata=Counter();axes=Counter()
    for i in selected:
        f=feat[i]
        edge_counts.update(f['edges']);node_counts.update(f['nodes']);pairs[f['pair']]+=1;orders[f['order']]+=1;strata[f['stratum']]+=1
        axes.update(ex.kernel.AXES[a] for a in sessions[i][2])
        if f['shortest']:commuting[f['pair']]+=1
    vals=[edge_counts[i] for i in range(len(edges))]
    sorted_counts=sorted(vals,reverse=True)
    total=sum(vals)
    return {'unique_sessions':len(selected),'unique_atomic_edges_used':len(edge_counts),'registered_atomic_edges':len(edges),
        'edge_coverage':len(edge_counts)/len(edges),'edge_exposure_including_zeros':ex.factor_stats(vals),
        'edge_exposure_used_only':ex.factor_stats(list(edge_counts.values())),
        'edge_top_1pct_exposure_share':sum(sorted_counts[:math.ceil(.01*len(vals))])/total,
        'edge_exposure_histogram':dict(sorted(Counter(vals).items())),
        'unique_nodes_used':len(node_counts),'node_reuse':ex.factor_stats([node_counts[i] for i in range(len(nodes))]),
        'unique_root_final_pairs':len(pairs),'root_final_pair_max_exposure':max(pairs.values()),'root_final_pair_duplicate_sessions':len(selected)-len(pairs),
        'unique_axis_parent_orders':len(orders),'shortest_straight_sessions':sum(commuting.values()),
        'commuting_root_final_classes':len(commuting),'commuting_order_excess':sum(commuting.values())-len(commuting),
        'commuting_max_class':max(commuting.values()),'axis_exposure':dict(axes),
        'strata':{str(k):v for k,v in sorted(strata.items())},
        'actual_edit_occurrences':total}


def select(policy,split,sessions,nodes,edges):
    base=12000 if split=='train' else 3000
    base_units=base//30
    marks={base_units//2:.5,base_units:1.,base_units*2:2.}
    feat,edge_ids=features(sessions,edges)
    by=defaultdict(list)
    for i,f in enumerate(feat):by[f['stratum']].append(i)
    available_units=min(len(by[k])//n for k,n in UNIT.items())
    units=min(base_units*2,available_units)
    rng=random.Random(76021)
    for rows in by.values():rng.shuffle(rows)
    edge_count=Counter();pair_count=Counter();order_count=Counter()
    selected=[];snapshots=[]
    selected_set=set()
    swaps=defaultdict(list)
    for i,f in enumerate(feat):
        if f['shortest'] and f['stratum'][0]==2:swaps[f['pair']].append(i)
    swap_groups=[v for v in swaps.values() if len(v)>=2]
    rng.shuffle(swap_groups)
    reserved_pairs=0
    def accept(i):
        selected.append(i);selected_set.add(i)
        f=feat[i]
        edge_count.update(f['edges']);pair_count[f['pair']]+=1;order_count[f['order']]+=1
    for unit in range(1,units+1):
        tasks=[k for k,n in UNIT.items() for _ in range(n)]
        rng.shuffle(tasks)
        if policy=='joint_reserved_swap' and unit%4==0:
            available=next((group for group in swap_groups if all(i not in selected_set for i in group[:2])),None)
            if available:
                for i in available[:2]:
                    rows=by[(2,'linear')]
                    j=rows.index(i);rows[j]=rows[-1];rows.pop()
                    tasks.remove((2,'linear'))
                    accept(i)
                reserved_pairs+=1
        for key in tasks:
            candidates=by[key]
            if policy=='uniform_candidate_session':
                chosen=len(candidates)-1
            else:
                candidates_idx=rng.sample(range(len(candidates)),min(48,len(candidates)))
                def score(j):
                    f=feat[candidates[j]]
                    edge_utility=sum(1/(1+edge_count[e]) for e in f['edges'])/len(f['edges'])
                    if policy in ('edge_content_joint','joint_reserved_swap'):
                        edge_utility+=.5/(1+pair_count[f['pair']])+.2/(1+order_count[f['order']])
                    return edge_utility,rng.random()
                chosen=max(candidates_idx,key=score)
            i=candidates[chosen]
            candidates[chosen]=candidates[-1];candidates.pop()
            accept(i)
        if unit in marks:
            d=diagnose(selected,sessions,feat,nodes,edges,edge_ids)
            d['explicit_reserved_commuting_pairs']=reserved_pairs
            snapshots.append({'session_budget_multiplier':marks[unit],**d})
            ex.write(HERE/f'sampling_{policy}_{split}_{marks[unit]:g}x_indices.json',selected)
    return {'policy':policy,'split':split,'base_session_budget':base,'pool_sessions':len(sessions),
        'pool_strata':{str(k):sum(f['stratum']==k for f in feat) for k in UNIT},
        'available_complete_30session_blocks':available_units,'requested_max_blocks':base_units*2,
        'filled_requested_max_budget':units==base_units*2,'snapshots':snapshots}


def main():
    output={'kind':'finite_shared_candidate_pool_annotation_sampling_study_not_model_training','records':[],'inputs':{},'pools':{}}
    for split in ('train','test'):
        tick=__import__('time').perf_counter()
        stem,graph,nodes,adj,edges,original=load_graph(split)
        sessions,attempts=pool(split,nodes,adj,edges,original)
        counts=Counter(stratum(s) for s in sessions)
        output['inputs'][split]={'graph':stem+'_graph.json','graph_sha256':hashlib.sha256((HERE/(stem+'_graph.json')).read_bytes()).hexdigest()}
        output['pools'][split]={'unique_sessions':len(sessions),'stratum_counts':{str(k):n for k,n in counts.items()},'proposals':attempts}
        print(json.dumps({'split':split,'pool':len(sessions),'strata':{str(k):n for k,n in counts.items()}},ensure_ascii=False),flush=True)
        for policy in ('uniform_candidate_session','edge_uniform','edge_content_joint'):
            result=select(policy,split,sessions,nodes,edges)
            output['records'].append(result)
            print(json.dumps({'split':split,'policy':policy,'results':[(r['session_budget_multiplier'],r['unique_atomic_edges_used'],r['unique_root_final_pairs']) for r in result['snapshots']]},ensure_ascii=False),flush=True)
        output['pools'][split]['elapsed_seconds']=round(__import__('time').perf_counter()-tick,3)
        ex.write(HERE/'sampling_study_metrics.json',output)


def reserved_only():
    output=ex.read('sampling_study_metrics.json')
    output['records']=[r for r in output['records'] if r['policy']!='joint_reserved_swap']
    for split in ('train','test'):
        stem,graph,nodes,adj,edges,original=load_graph(split)
        sessions=[]
        for line in (HERE/f'sampling_{split}_candidate_pool.jsonl').read_text().splitlines():
            s=json.loads(line)
            sessions.append((s['node_indices'],s['parent_occurrence_indices_gt'],[ex.kernel.AXES.index(a) for a in s['edge_axes']]))
        result=select('joint_reserved_swap',split,sessions,nodes,edges)
        output['records'].append(result)
        print(json.dumps({'split':split,'policy':result['policy'],'results':[(r['session_budget_multiplier'],r['unique_atomic_edges_used'],r['unique_root_final_pairs'],r['explicit_reserved_commuting_pairs']) for r in result['snapshots']]}),flush=True)
    ex.write(HERE/'sampling_study_metrics.json',output)


if __name__=='__main__':
    if '--add-reserved' in sys.argv:reserved_only()
    else:main()
