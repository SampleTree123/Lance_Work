"""Bounded bridge check; identity-group tags are allowed to cross on real edges."""
import sys
sys.dont_write_bytecode=True
from collections import Counter
import json
import experiments as ex

HERE=ex.HERE
report=ex.read('bridge_metrics.json')
checks=[]
for r in report['records']:
    g=ex.read(r['key']+'_graph.json');ex.kernel.AXES=tuple(g['axes'])
    nodes=[tuple(row['state'][a] for a in g['axes']) for row in g['nodes']]
    cat=ex.kernel.Catalog(ex.read('inventory_landscape.json'),ex.read('site_checkpoint.json'),ex.read('appearance_catalog.json'),split_policy='scene')
    assert len(set(nodes))==len(nodes)==r['unique_nodes']
    assert all(cat.valid(n) for n in nodes)
    edges={(e['source_index'],e['target_index']):g['axes'].index(e['axis']) for e in g['edges']}
    adj=[[] for _ in nodes]
    registered_id_pairs=set()
    for (u,v),a in edges.items():
        assert [j for j,(x,y) in enumerate(zip(nodes[u],nodes[v])) if x!=y]==[a]
        assert cat.sex[nodes[u][0]]==cat.sex[nodes[v][0]]
        if a==0:registered_id_pairs.add((nodes[u][0],nodes[v][0]))
        adj[u].append((v,a))
    assert ex.kernel.components(adj)==r['graph_components']
    for i,row in enumerate(g['nodes']):
        assert row['node_id']==ex.kernel.digest(row['state'])
        p=row['generation_parent_index']
        if p is not None:assert p<i and edges[p,i]==g['axes'].index(row['generation_axis'])
    source_unique=0;root_sources=0;used=set();ids=set();quota=Counter();id_pairs=set()
    for line in (HERE/(r['key']+'_sessions.jsonl')).read_text().splitlines():
        s=json.loads(line);o=s['node_indices'];par=s['parent_occurrence_indices_gt'];axes=[g['axes'].index(a) for a in s['edge_axes']]
        assert s['session_id'] not in ids;ids.add(s['session_id'])
        assert len(o)==len(par)==len(axes)+1 and len(set(o))==len(o) and len(set(axes))>=2
        forks=[t for t,p in enumerate(par) if t and p!=t-1]
        assert len(forks)<=1
        for t in range(1,len(o)):
            assert 0<=par[t]<t and edges[o[par[t]],o[t]]==axes[t-1]
            if axes[t-1]==0:id_pairs.add((nodes[o[par[t]]][0],nodes[o[t]][0]))
        if forks:
            t=forks[0];a=axes[t-1]
            assert t<len(axes)
            eq=[p for p in range(t) if nodes[o[p]][:a]+nodes[o[p]][a+1:]==nodes[o[t]][:a]+nodes[o[t]][a+1:]]
            assert eq==[par[t]];source_unique+=1
            root_sources+=par[t]==0
        quota[len(axes),bool(forks)]+=1
        used.update(o)
    target=12000 if r['split']=='train' else 3000
    assert len(ids)==target and len(used)==len(nodes)
    assert [quota[k,False] for k in (2,3,4,5)]==[target//6]*4
    assert [quota[k,True] for k in (3,4,5)]==[target//15,target*2//15,target*2//15]
    assert len(id_pairs)==r['axis_value_transition_coverage']['identity']['used_value_pairs']
    assert len(registered_id_pairs)==r['axis_value_transition_coverage']['identity']['observed_value_pairs']
    assert root_sources==target*2//15
    assert len(nodes)-r['growth']['base_node_budget']==r['growth']['bridge_nodes']
    checks.append({'key':r['key'],'nodes':len(nodes),'sessions':target,'registered_identity_value_pairs':r['axis_value_transition_coverage']['identity']['observed_value_pairs'],
                   'used_identity_value_pairs':len(id_pairs),'components':len(r['graph_components'])})
out={'passed':True,'scope':'four_additional_bridge_candidates_only_not_main_snapshot_or_UE','checks':checks}
ex.write(HERE/'bridge_verification.json',out)
print(json.dumps({'passed':True,'graphs':len(checks),'sessions':sum(r['sessions'] for r in checks)}))
