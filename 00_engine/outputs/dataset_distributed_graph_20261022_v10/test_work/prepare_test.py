from pathlib import Path
from collections import Counter,defaultdict,deque
import argparse,copy,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;OUT=ROOT.parent
sys.path.insert(0,str(OUT/'dataset_compact_graph_20261022_v6'));from build_compact import Domain,Graph,legal_add,read,write,save_empty_graph
sys.path.insert(0,str(ROOT/'audit_work'));from audit_distributed import Rules,exposure
def main():
    p=argparse.ArgumentParser();p.add_argument('--source',default='trial5');p.add_argument('--output',default='trial6');a=p.parse_args()
    src=HERE/a.source/'graph/test';dst=HERE/a.output/'graph/test'
    if dst.exists():raise FileExistsError(dst)
    rows=read(src/'nodes.json');byid={r['id']:r['state'] for r in rows};edges=read(src/'edges.json');rules=Rules();keep=set(byid);decisions=[]
    for iteration in range(50):
        pairs=Counter((byid[u]['action'],byid[u]['camera']) for u in keep if byid[u]['camera']!='front_head');acs=defaultdict(dict)
        for (act,cam),n in pairs.items():acs[act][cam]=n
        bad=sorted((n/(sum(acs[act].values())/len(acs[act])),act,cam) for (act,cam),n in pairs.items() if n<.5*sum(acs[act].values())/len(acs[act]))
        if not bad:break
        for ratio,act,cam in bad:
            remove={u for u in keep if (byid[u]['action'],byid[u]['camera'])==(act,cam)};trial=keep-remove
            if len({byid[u]['camera'] for u in trial})!=21:continue
            e=exposure(rules,[(byid[u],1) for u in trial],False)
            if not e['all_requested_global_frequencies_in_range']:continue
            keep=trial;decisions.append({'action':act,'camera':cam,'old_ratio':ratio,'removed':sorted(remove)});break
        else:break
    d=Domain();g=Graph(d);mapping={};adj=defaultdict(list)
    for edge in edges:
        u,v=edge['source'],edge['target']
        if u in keep and v in keep:adj[u].append((v,edge['axis']))
    while len(mapping)<len(keep):
        root=min(keep-set(mapping));mapping[root]=g.add(copy.deepcopy(byid[root]));q=deque([root])
        while q:
            u=q.popleft()
            for v,axis in adj[u]:
                if v in mapping:continue
                mapping[v]=legal_add(g,mapping[u],copy.deepcopy(byid[v]),axis)
                if mapping[v] is None:raise RuntimeError((u,v,axis))
                q.append(v)
    meta=read(src/'metrics.json')['construction'];meta.update(test_optional_pair_pruning=decisions,parent_source=str(src))
    save_empty_graph(dst,g,meta);e=exposure(rules,[(s,1) for s in g.nodes],False);write(HERE/a.output/'node_frequency_test.json',e)
    print(json.dumps({'nodes':len(g.nodes),'edges':dict(Counter(e['axis'] for e in g.edges.values())),'global':e['all_requested_global_frequencies_in_range'],'camera':e['all_action_internal_camera_frequencies_in_range'],'removed_pairs':len(decisions),'failed_camera':{k:v['ratios_to_own_mean'] for k,v in e['each_action_internal_camera_frequency'].items() if not v['passed']}}),flush=True)
if __name__=='__main__':main()
