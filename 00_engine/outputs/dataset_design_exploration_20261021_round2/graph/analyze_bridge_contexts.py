"""Separate identity transition registration, actual usage, and context breadth."""
import sys
sys.dont_write_bytecode=True
from collections import Counter,defaultdict
import json
import experiments as ex

HERE=ex.HERE
results=[]
for name in ('strict_family_a7_metrics.json','bridge_metrics.json'):
    for r in ex.read(name)['records']:
        g=ex.read(r['key']+'_graph.json');axes=g['axes'];nodes=g['nodes']
        registered=defaultdict(set);used=defaultdict(set)
        def identity_context(u,v,destination):
            a,b=nodes[u]['state'],nodes[v]['state']
            pair=a['identity'],b['identity']
            context=tuple((k,a[k]) for k in axes if k!='identity')
            destination[pair].add(context)
        for e in g['edges']:
            if e['axis']=='identity':identity_context(e['source_index'],e['target_index'],registered)
        for line in (HERE/(r['key']+'_sessions.jsonl')).read_text().splitlines():
            s=json.loads(line);o=s['node_indices'];p=s['parent_occurrence_indices_gt']
            for t,a in enumerate(s['edge_axes'],1):
                if a=='identity':identity_context(o[p[t]],o[t],used)
        rec={'key':r['key'],'split':r['split'],'bridge_fraction':r.get('bridge_fraction',0),
             'registered_identity_pairs':len(registered),'used_identity_pairs':len(used),
             'registered_contexts_per_identity_pair':ex.factor_stats([len(v) for v in registered.values()]),
             'used_contexts_per_identity_pair':ex.factor_stats([len(v) for v in used.values()]),
             'registered_pairs_in_only_one_context':sum(len(v)==1 for v in registered.values()),
             'used_pairs_in_only_one_context':sum(len(v)==1 for v in used.values()),
             'axis_transition_coverage':r['axis_value_transition_coverage'],'node_pair_coverage':r['pair_coverage']}
        if name=='bridge_metrics.json':
            new=nodes[r['growth']['base_node_budget']:]
            contexts=Counter(tuple((k,n['state'][k]) for k in axes if k!='identity') for n in new)
            rec['new_bridge_node_count']=len(new)
            rec['new_nonidentity_context_count']=len(contexts)
            rec['new_nodes_per_context_descending']=sorted(contexts.values(),reverse=True)
            rec['new_node_axis_value_counts']={a:dict(Counter(n['state'][a] for n in new)) for a in axes if a!='identity'}
            rec['top_contexts']=[{'state_except_identity':dict(k),'new_identity_nodes':n} for k,n in contexts.most_common(10)]
        results.append(rec)
ex.write(HERE/'bridge_context_analysis.json',{'interpretation':'same context copies broaden identity transitions but are not independent context evidence','results':results})
for r in results:
    print(json.dumps({k:r[k] for k in ('key','registered_identity_pairs','used_identity_pairs','registered_pairs_in_only_one_context','used_pairs_in_only_one_context')},ensure_ascii=False))
