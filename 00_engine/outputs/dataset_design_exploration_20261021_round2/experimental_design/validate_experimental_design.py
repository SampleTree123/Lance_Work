"""Verify only generated symbolic experimental manifests; no visual/model claims."""
from collections import Counter
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROUND1=HERE.parents[1]/'dataset_design_exploration_20261021_v1'
groups=json.loads((HERE/'scene_group_candidates.json').read_text(encoding='utf-8'))
plan=json.loads((HERE/'minimal_scene_exposure_2x2.json').read_text(encoding='utf-8'))
graphs={}
for split in ['train','test']:
    path=ROUND1/f'graph/main_scene_holdout_hybrid_{split}_graph.json'
    raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==plan['source_graph_sha256'][split]
    graphs[split]=json.loads(raw)
assert len(groups['scenes'])==len({x['site'] for x in groups['scenes']})==21
assert sum(groups['all_20349_random5_partitions_under_this_provisional_taxonomy'].values())==20349
for name,split in [('training_exposure_module','train'),('matched_test_module','test')]:
    m=plan[name];states=[n['state'] for n in graphs[split]['nodes']]
    for edge in m['edge_pairs']:
        l0,l1=map(states.__getitem__,edge['left_source_target'])
        r0,r1=map(states.__getitem__,edge['right_source_target'])
        assert {k:v for k,v in l0.items() if k!='site'}=={k:v for k,v in r0.items() if k!='site'}
        assert {k:v for k,v in l1.items() if k!='site'}=={k:v for k,v in r1.items() if k!='site'}
        assert [k for k in l0 if l0[k]!=l1[k]]==[edge['axis']]
        assert l0['site']!=r0['site']
    assert m['left_node_count']==m['right_node_count']

m=plan['matched_test_module']['matched_multiround_capacity']
g=graphs['test'];states=[n['state'] for n in g['nodes']]
edge_lookup={(e['source_index'],e['target_index']):e['axis'] for e in g['edges']}
counts=Counter();signatures=set()
for s in m['selected_matched_sessions']:
    occ=s['left_node_indices'];right=s['right_node_indices'];parents=s['parents'];axes=s['axes']
    assert len(occ)==len(set(occ)) and len(set(axes))>=2
    forks=[t for t in range(1,len(occ)) if parents[t]!=t-1]
    assert len(forks)<=1
    sig=(tuple(occ),tuple(parents));assert sig not in signatures;signatures.add(sig)
    for t in range(1,len(occ)):
        assert 0<=parents[t]<t
        assert edge_lookup[occ[parents[t]],occ[t]]==edge_lookup[right[parents[t]],right[t]]==axes[t-1]
    if forks:
        t=forks[0];axis=axes[t-1];target=states[occ[t]]
        assert t<len(axes)
        assert [i for i in range(t) if {**states[occ[i]],axis:target[axis]}==target]==[parents[t]]
        counts['fork']+=1;counts['fork_L'+str(len(axes))]+=1;counts['root' if parents[t]==0 else 'nonroot']+=1
    else:
        counts['linear']+=1;counts['linear_L'+str(len(axes))]+=1
    counts['edits_per_cohort']+=len(axes)
assert counts['linear']==40 and counts['fork']==20 and counts['root']==8 and counts['nonroot']==12
assert [counts['fork_L'+str(k)] for k in [3,4,5]]==[4,8,8]
assert counts['edits_per_cohort']==224
report={'status':'pass','scope':'symbolic_matching_and_budget_only; not rendered or trained',
        'scene_count':21,'random5_splits_enumerated':20349,
        'training_module_edge_pairs':78,'test_module_edge_pairs':26,
        'matched_sessions_per_cohort':60,'counts':dict(counts),
        'single_turn_calls_two_models_two_cohorts':26*4,
        'multiround_calls_two_models_two_cohorts':224*4}
(HERE/'SELF_CHECK.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
