import json
from pathlib import Path
from collections import Counter
HERE=Path(__file__).resolve().parent
V6=HERE.parent.parent/'dataset_compact_graph_20261022_v6'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
out={}
for split,name,graph in [('train','train_4200_component_split','graph_n'),('test','test_1100','graph_t')]:
    p=HERE/name
    old=read(V6/'selected_seed1'/split/'nodes.json'); graphrows=read(V6/graph/split/'nodes.json')
    nodes=read(p/'nodes.json'); origins=read(p/'ORIGIN.json')
    sessions=[json.loads(l) for l in (p/'sessions.jsonl').read_text().splitlines()]
    semantic=Counter((origins[e['source']]['source_id'],origins[e['target']]['source_id']) for s in sessions for e in s['steps'])
    unused=sorted(set(range(len(nodes)))-{u for s in sessions for u in s['history']})
    out[split]={
        'graph_id_equals_selected_seed1_id':len(old)==len(graphrows) and all(a['id']==b['id'] and a['state']==b['state'] and a['canonical_id']==b['canonical_id'] for a,b in zip(old,graphrows)),
        'unused_nodes':[{'new_id':u,'origin':origins[u],'node':nodes[u]} for u in unused],
        'same_content_directed_edge_aggregate_reuse':{'max':max(semantic.values()),'mean_among_used_semantic_edges':sum(semantic.values())/len(semantic),'used_unique':len(semantic),'edits':sum(semantic.values()),'histogram':dict(Counter(semantic.values()))},
        'edited_target_coverage':read(p/'sampling.json')['edited_attribute_target_coverage']}
(HERE/'FINAL_MAPPING_CHECK.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out,indent=2))
