"""Reduce optional thin camera support while protecting real value/context gates."""
from pathlib import Path
from collections import Counter,defaultdict,deque
import argparse,copy,json,sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'audit_work'))
from distributed_builder import Domain,Graph,read,write,save_empty_graph,legal_add,pin
from audit_distributed import Rules,exposure
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',default='trial11');ap.add_argument('--output',default='trial12');a=ap.parse_args()
    src=ROOT/a.source/'graph/train';dest=ROOT/a.output/'graph/train'
    if dest.exists():raise FileExistsError(dest)
    nodes=read(src/'nodes.json');edges=read(src/'edges.json');byid={n['id']:n for n in nodes};keep=set(byid);rules=Rules();decisions=[]
    for iteration in range(30):
        pairs=Counter((byid[u]['state']['action'],byid[u]['state']['camera']) for u in keep if byid[u]['state']['camera']!='front_head')
        actions=defaultdict(dict)
        for (act,cam),v in pairs.items():actions[act][cam]=v
        candidates=sorted(((v/(sum(actions[act].values())/len(actions[act])),act,cam) for (act,cam),v in pairs.items() if len(actions[act])>10 and v < .5*sum(actions[act].values())/len(actions[act])))
        if not candidates:break
        accepted=False
        for ratio,act,cam in candidates:
            removing={u for u in keep if (byid[u]['state']['action'],byid[u]['state']['camera'])==(act,cam)}
            trial=keep-removing;check=exposure(rules,[(byid[u]['state'],1) for u in trial],True)
            if check['all_requested_global_frequencies_in_range'] and check['all_represented_garments_min3_actions_and_cameras']:
                keep=trial;decisions.append({'action':act,'camera':cam,'ratio_before':ratio,'removed_original_node_ids':sorted(removing),'reason':'optional camera under half own-action mean; retained all global value bounds and garment context minima'});accepted=True;break
        if not accepted:break
    # Rebuild each remaining connected component from its true retained atomic
    # edges. New roots are saved original states; no invented provenance edge.
    adjacent=defaultdict(list)
    for e in edges:
        if e['source'] in keep and e['target'] in keep:adjacent[e['source']].append((e['target'],e['axis']))
    d=Domain();g=Graph(d);mapping={};roots=[]
    while len(mapping)<len(keep):
        root=min(keep-set(mapping));v=g.add(copy.deepcopy(byid[root]['state']));mapping[root]=v;roots.append(v);queue=deque([root])
        while queue:
            u=queue.popleft()
            for target,axis in adjacent[u]:
                if target in mapping:continue
                v=legal_add(g,mapping[u],copy.deepcopy(byid[target]['state']),axis)
                if v is None:raise RuntimeError(('retained edge introduction rejected',u,target,axis))
                mapping[target]=v;queue.append(target)
    construction={'strategy':'distributed ordinary graph, with optional underexposed action-camera combinations omitted after joint value/context checks','source_graph':str(src),'source_inputs':[pin(src/f) for f in ('nodes.json','edges.json','metrics.json')],'source_construction':read(src/'metrics.json')['construction'],'selection_decisions':decisions,'old_to_new_id':mapping,'roots':roots,'registered_nodes_before':len(nodes),'registered_nodes_after':len(g.nodes),'removed_nodes':len(nodes)-len(g.nodes),'builder':pin(__file__),'axis_edges':dict(Counter(e['axis'] for e in g.edges.values()))}
    save_empty_graph(dest,g,construction)
    check=exposure(rules,[(s,1) for s in g.nodes],True);write(dest.parent.parent/'node_frequency_train.json',check)
    print(json.dumps({'nodes':len(g.nodes),'removed_nodes':len(nodes)-len(g.nodes),'removed_pairs':len(decisions),'all_global_frequency':check['all_requested_global_frequencies_in_range'],'all_action_camera_frequency':check['all_action_internal_camera_frequencies_in_range'],'all_core_contexts':check['all_represented_garments_min3_actions_and_cameras'],'min_cameras':min(len(c) for c in check['action_within_camera_counts'].values()),'axis_edges':construction['axis_edges']},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
