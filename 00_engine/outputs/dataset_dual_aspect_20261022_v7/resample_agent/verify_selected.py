"""Targeted provenance checks for the economical resampling candidate."""
import sys,json,hashlib
from pathlib import Path
from collections import Counter
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
V6=HERE.parent.parent/'dataset_compact_graph_20261022_v6'
report={}
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
for split,name,graph in [('train','train_4200_component_split','graph_n'),('test','test_1100','graph_t')]:
    p=HERE/name; src=V6/graph/split
    nodes=read(p/'nodes.json'); origins=read(p/'ORIGIN.json'); sn=read(src/'nodes.json'); se=read(src/'edges.json')
    edge_map={(e['source'],e['target']):{k:v for k,v in e.items() if k not in ('source','target')} for e in se}
    issues=[]
    for row,o in zip(nodes,origins):
        state=dict(row['state']); state['aspect']='landscape'
        if state!=sn[o['source_id']]['state']: issues.append(['state_origin',row['id']])
    for e in read(p/'edges.json'):
        u,v=e['source'],e['target']; meta={k:v for k,v in e.items() if k not in ('source','target')}
        if nodes[u]['state']['aspect']!=nodes[v]['state']['aspect']: issues.append(['cross_aspect_edge',u,v])
        if edge_map.get((origins[u]['source_id'],origins[v]['source_id']))!=meta: issues.append(['non_original_edge',u,v])
    sampling=read(p/'sampling.json')
    report[split]={'path':str(p),'source_graph':str(src),'issues':issues,'issue_count':len(issues),
        'complete':sampling['complete'],'core_target_coverage':sampling['edited_attribute_target_coverage']['wardrobe_core'],
        'source_hashes':{x:sha(src/x) for x in ['nodes.json','edges.json']},
        'output_hashes':{x:sha(p/x) for x in ['nodes.json','edges.json','sessions.jsonl','ORIGIN.json','sampling.json']}}
report['sampler']={'path':str(V6/'sample_compact_v68_snapshot.py'),'sha256':sha(V6/'sample_compact_v68_snapshot.py'),
    'parameters':{'history_decay':.2,'nonidentity_upper_slack':.025,'max_attempts':240,'seed_train':2026102261,'seed_test':2026102262}}
report['scope']='Targeted original node/edge provenance and sampling checks only; full formal audit belongs to parent audit agent.'
(HERE/'SELECTED_PROVENANCE_CHECK.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({s:{'issues':report[s]['issue_count'],'complete':report[s]['complete'],'core':report[s]['core_target_coverage']} for s in ['train','test']}))
