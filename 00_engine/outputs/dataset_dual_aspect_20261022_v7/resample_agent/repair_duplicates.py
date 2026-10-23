"""Replace aspect-agnostic duplicates with an eligible immutable v6 session."""
import sys,copy,json,hashlib,shutil
from pathlib import Path
from collections import Counter,defaultdict
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent; V6=HERE.parent.parent/'dataset_compact_graph_20261022_v6'
sys.path[:0]=[str(V6.parent/'dataset_local_support_20261021_v3')]
from resample_local import Domain,Graph,save_graph
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
def sessions(p): return [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines()]
def sig(s,origin=None):
    hist=[origin[u]['source_id'] for u in s['history']] if origin else s['history']
    return (hist[0],tuple((e['source_position'],hist[j]) for j,e in enumerate(s['steps'],1)))
def pattern(s): return(s['kind'],s['length'],s['fork_round'],tuple(e['source_position'] for e in s['steps']))
report={}
for split,name in [('train','train_4200_component_split'),('test','test_1100')]:
    source=HERE/name; target=HERE/f'repair_{split}'
    if target.exists(): raise FileExistsError(target)
    nodes=read(source/'nodes.json'); origins=read(source/'ORIGIN.json'); edges=read(source/'edges.json')
    ss=sessions(source/'sessions.jsonl'); originals=sessions(V6/'selected_seed1'/split/'sessions.jsonl')
    mapping={(o['source_id'],o['aspect']):o['id'] for o in origins}
    known=set(); duplicates=[]
    for j,s in enumerate(ss):
        key=sig(s,origins)
        if key in known: duplicates.append(j)
        known.add(key)
    history_keys={tuple(origins[u]['source_id'] for u in s['history']) for s in ss}
    edgeuse=Counter((e['source'],e['target']) for s in ss for e in s['steps'])
    allowed={(e['source'],e['target']):{k:v for k,v in e.items() if k not in ('source','target')} for e in edges}
    records=[]
    for idx in duplicates:
        old=ss[idx]; aspect=nodes[old['history'][0]]['state']['aspect']; camera=nodes[old['history'][0]]['state']['camera']
        old_edges=Counter((e['source'],e['target']) for e in old['steps'])
        options=[]
        for original in originals:
            if pattern(original)!=pattern(old) or sig(original) in known: continue
            if tuple(reversed(original['history'])) in history_keys: continue
            if any((u,aspect) not in mapping for u in original['history']): continue
            new=copy.deepcopy(original); new['id']=old['id']; new['aspect']=aspect
            new['history']=[mapping[u,aspect] for u in original['history']]
            valid=True
            for e in new['steps']:
                e['source']=mapping[e['source'],aspect]; e['target']=mapping[e['target'],aspect]
                if allowed.get((e['source'],e['target']))!={k:v for k,v in e.items() if k not in ('source','target','source_position')}:valid=False
            if not valid: continue
            extra=Counter((e['source'],e['target']) for e in new['steps'])
            maximum=max(edgeuse[k]-old_edges[k]+c for k,c in extra.items())
            if maximum>4: continue
            samecamera=nodes[new['history'][0]]['state']['camera']==camera
            axisdelta=sum(abs(Counter(e['axis'] for e in old['steps'])[a]-Counter(e['axis'] for e in new['steps'])[a]) for a in ('identity','hair','hair_color','wardrobe','action','camera','site'))
            options.append(((not samecamera,maximum>3,axisdelta,maximum),original['id'],new))
        if not options: raise RuntimeError(f'No replacement {split} {old["id"]}')
        score,originalid,new=min(options,key=lambda r:r[0])
        for k,c in old_edges.items(): edgeuse[k]-=c
        edgeuse.update((e['source'],e['target']) for e in new['steps'])
        ss[idx]=new; known.add(sig(new,origins));history_keys.add(tuple(origins[u]['source_id'] for u in new['history']))
        records.append({'session_id':old['id'],'original_v6_session_id':originalid,'aspect':aspect,'selection_score':score,'old_session':old,'new_session':new})
    d=Domain();g=Graph(d)
    for row in nodes:
        s=row['state'];g.nodes.append(s);g.keys.append(d.canonical(s)+(s['aspect'],));g.provenance.append(row['created_by']);g.adj.append(defaultdict(list))
    for e in edges:
        u,v=e['source'],e['target'];meta={k:v for k,v in e.items() if k not in ('source','target')};g.edges[u,v]=meta;g.adj[u][e['axis']].append(v)
    metrics=save_graph(target,g,ss,{'source_before_repair':str(source),'repair_method':'immutable v6 session transplant with identical kind/length/fork_round/source_position sequence','repair_records':'REPAIR.json','original_sampler_metadata':'sampling_pre_repair.json'})
    shutil.copyfile(source/'ORIGIN.json',target/'ORIGIN.json');shutil.copyfile(source/'sampling.json',target/'sampling_pre_repair.json')
    summary={'source':str(source),'source_sessions_sha256':hashlib.sha256((source/'sessions.jsonl').read_bytes()).hexdigest(),'records':records,'unique_semantic_chains':len({sig(s,origins) for s in ss}),'sessions':len(ss),'max_edge_reuse':max(edgeuse.values()),'start_camera_quota_preserved':all(not r['selection_score'][0] for r in records),'kind_length_fork_parent_patterns_preserved':all(pattern(r['old_session'])==pattern(r['new_session']) for r in records),'slot_support_limitation_unchanged':'The independent audit found substantial formal single-piece slot support loss in train. Duplicate repair does not resolve it.'}
    (target/'REPAIR.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');report[split]=summary
(HERE/'REPAIR_SUMMARY.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({split:{k:v for k,v in r.items() if k not in ('records',)} for split,r in report.items()},indent=2))
