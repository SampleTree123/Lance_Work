"""Recompute analysis from saved round-two graph/session artifacts, no growth."""
import sys
sys.dont_write_bytecode=True
import json
from pathlib import Path
import experiments as ex

here=Path(__file__).resolve().parent
for name in sys.argv[1:]:
    document=ex.read(name)
    for r in document['records']:
        graph=ex.read(r['key']+'_graph.json')
        ex.kernel.AXES=tuple(graph['axes'])
        nodes=[tuple(n['state'][a] for a in graph['axes']) for n in graph['nodes']]
        family=[n['family'] for n in graph['nodes']]
        edges={(e['source_index'],e['target_index']):graph['axes'].index(e['axis']) for e in graph['edges']}
        adj=[[] for _ in nodes]
        for (u,v),a in edges.items():adj[u].append((v,a))
        sessions=[]
        for line in (here/(r['key']+'_sessions.jsonl')).read_text().splitlines():
            s=json.loads(line)
            sessions.append((s['node_indices'],s['parent_occurrence_indices_gt'],[graph['axes'].index(a) for a in s['edge_axes']]))
        cat=ex.kernel.Catalog(ex.read('inventory_landscape.json'),ex.read('site_checkpoint.json'),
            ex.read('appearance_catalog.json') if r['editable_axes']==7 else None,split_policy='scene')
        r.update(ex.analyze(cat,r['split'],nodes,adj,edges,family,sessions,r['sampling']))
    ex.write(here/name,document)
    print(name)
