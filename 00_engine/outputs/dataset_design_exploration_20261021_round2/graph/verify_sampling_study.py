"""Bounded validation of frozen strict graph and the finite candidate pools."""
import sys
sys.dont_write_bytecode=True
from collections import Counter
import json
from pathlib import Path
import experiments as ex
import sampling_study as study

HERE=Path(__file__).resolve().parent
results=[]
split_states={}
for split in ('train','test'):
    stem,g,nodes,adj,edges,original=study.load_graph(split)
    cat=ex.kernel.Catalog(ex.read('inventory_landscape.json'),ex.read('site_checkpoint.json'),ex.read('appearance_catalog.json'),split_policy='scene')
    assert len(nodes)==(2500 if split=='train' else 500)
    assert len(set(nodes))==len(nodes)
    assert all(cat.valid(n) for n in nodes)
    for i,row in enumerate(g['nodes']):
        assert row['node_id']==ex.kernel.digest(row['state'])
        p=row['generation_parent_index']
        if p is not None:
            assert p<i and edges[p,i]==g['axes'].index(row['generation_axis'])
    for (u,v),a in edges.items():
        assert [i for i,(x,y) in enumerate(zip(nodes[u],nodes[v])) if x!=y]==[a]
        assert cat.sex[nodes[u][0]]==cat.sex[nodes[v][0]]
        assert g['nodes'][u]['family']==g['nodes'][v]['family']
    sessions=[];seen=set();equivalence=Counter()
    for line in (HERE/f'sampling_{split}_candidate_pool.jsonl').read_text().splitlines():
        s=json.loads(line);o=s['node_indices'];p=s['parent_occurrence_indices_gt'];a=[g['axes'].index(x) for x in s['edge_axes']]
        assert len(set(o))==len(o) and len(set(a))>=2
        assert 2<=len(a)<=5 and len(o)==len(a)+1==len(p) and p[0] is None
        signature=tuple(o),tuple(p)
        assert signature not in seen;seen.add(signature)
        forks=[]
        for t in range(1,len(o)):
            assert 0<=p[t]<t and edges[o[p[t]],o[t]]==a[t-1]
            if p[t]!=t-1:
                forks.append(t)
                assert t<len(a)
                ax=a[t-1]
                eq=[q for q in range(t) if nodes[o[q]][:ax]+nodes[o[q]][ax+1:]==nodes[o[t]][:ax]+nodes[o[t]][ax+1:]]
                assert eq==[p[t]],eq
                equivalence[len(eq)]+=1
        assert len(forks)<=1
        sessions.append((o,p,a))
    feat,edge_ids=study.features(sessions,edges)
    checked=[]
    for record in ex.read('sampling_study_metrics.json')['records']:
        if record['split']!=split:continue
        for snap in record['snapshots']:
            selected=ex.read(f"sampling_{record['policy']}_{split}_{snap['session_budget_multiplier']:g}x_indices.json")
            assert len(set(selected))==len(selected)==snap['unique_sessions']
            counts=Counter(study.stratum(sessions[i]) for i in selected)
            units=len(selected)//30
            assert counts==Counter({k:n*units for k,n in study.UNIT.items()})
            fresh=study.diagnose(selected,sessions,feat,nodes,edges,edge_ids)
            for field in ('unique_atomic_edges_used','unique_root_final_pairs','commuting_order_excess','actual_edit_occurrences','unique_nodes_used'):
                assert fresh[field]==snap[field],(record['policy'],field)
            if snap['session_budget_multiplier']>=1:assert fresh['unique_nodes_used']==len(nodes)
            checked.append({'policy':record['policy'],'multiplier':snap['session_budget_multiplier'],'sessions':len(selected)})
    split_states[split]=set(nodes)
    results.append({'split':split,'nodes':len(nodes),'directed_edges':len(edges),'candidate_pool_sessions':len(sessions),
                    'fork_source_equivalence_histogram':dict(equivalence),'checked_selections':checked})
assert not split_states['train']&split_states['test']
out={'passed':True,'scope':'strong_7axis_5family_graph_pools_and_selected_policy_indices_only_not_UE_or_repository_audit',
     'checked_candidate_sessions':sum(r['candidate_pool_sessions'] for r in results),'results':results}
ex.write(HERE/'sampling_study_verification.json',out)
print(json.dumps({k:v for k,v in out.items() if k!='results'}))
