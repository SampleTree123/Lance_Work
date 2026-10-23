import json
from pathlib import Path
from collections import Counter

root=Path(__file__).resolve().parents[2]/'dataset_compact_graph_20261022_v6'/'selected_seed1'
for split in ['train','test']:
    nodes=json.loads((root/split/'nodes.json').read_text(encoding='utf-8'))
    chains=[json.loads(x) for x in (root/split/'sessions.jsonl').read_text(encoding='utf-8').splitlines()]
    parent=list(range(len(nodes)))
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]]
            x=parent[x]
        return x
    for chain in chains:
        for n in chain['history'][1:]:
            parent[find(n)]=find(chain['history'][0])
    comps=Counter(find(i) for i in range(len(nodes)))
    cc=Counter(find(c['history'][0]) for c in chains)
    print(split, 'nodes',len(nodes),'chains',len(chains),'components',len(comps),'largest',comps.most_common(20),'chain comps',cc.most_common(20),flush=True)
    for comp, count in cc.items():
        selected=[c for c in chains if find(c['history'][0])==comp]
        print(comp, 'sex',Counter(nodes[c['history'][0]]['state']['sex'] for c in selected),'camera',len(set(nodes[c['history'][0]]['state']['camera'] for c in selected)),'axes',Counter(s['axis'] for c in selected for s in c['steps']))
