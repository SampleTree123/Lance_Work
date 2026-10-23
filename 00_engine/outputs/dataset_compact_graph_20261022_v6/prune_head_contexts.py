"""Retain complete editable head subcubes while removing redundant contexts."""
import argparse, copy, hashlib, json, shutil, sys
from pathlib import Path
from collections import defaultdict
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'dataset_local_support_20261021_v3'))
from resample_local import Domain,load_graph
sys.path.insert(0,str(HERE.parent/'dataset_balanced_graph_20261022_v5'))
from build_balanced import Graph,read,write,save_empty_graph,token

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',default='graph_n');ap.add_argument('--per-family',type=int,default=2);ap.add_argument('--action-count',type=int,default=2);args=ap.parse_args()
    source=HERE/'graph_l_fixed/train';target=HERE/args.output/'train'
    if target.exists():raise RuntimeError('Never overwrite an existing graph')
    d=Domain();g=load_graph(source,d);meta=read(source/'metrics.json')['construction']
    coverage_start=min(v for row in meta['coverage_repairs'] for v in row['nodes'])
    wardrobes=defaultdict(set);actions=set()
    for u,s in enumerate(g.nodes):
        if u<coverage_start and s['camera']=='front_head':
            wardrobes[s['wardrobe']['family_id']].add(token(s['wardrobe']));actions.add(s['action'])
    selected_w={w for rows in wardrobes.values() for w in sorted(rows)[:args.per_family]}
    selected_a=set(sorted(actions)[:args.action_count])
    keep={u for u,s in enumerate(g.nodes) if u>=coverage_start or s['camera']!='front_head'
          or (token(s['wardrobe']) in selected_w and s['action'] in selected_a)}
    # Retain all ancestors of kept coverage/support nodes. No provenance rewiring
    # invents an edit; the original legal parent edges remain intact.
    todo=list(keep)
    while todo:
        u=todo.pop();p=g.provenance[u]['parent']
        if p is not None and p not in keep:keep.add(p);todo.append(p)
    reduced=Graph(d);mapping={}
    for u in sorted(keep):
        p=g.provenance[u];parent=None if p['parent'] is None else mapping[p['parent']]
        v=reduced.add(copy.deepcopy(g.nodes[u]),parent,p['axis']);mapping[u]=v
    counts={a:sum(e['axis']==a for e in reduced.edges.values()) for a in d.axes} if hasattr(d,'axes') else {}
    outmeta={'strategy':'retain_complete_head_editable_subcubes_and_protect_all_coverage_ancestors',
             'split':'train','source_graph':str(source),'source_nodes':len(g.nodes),
             'removed_nodes':sorted(set(range(len(g.nodes)))-keep),'old_to_new_id':mapping,
             'selected_head_wardrobe_contexts':sorted(selected_w),'selected_head_actions':sorted(selected_a),
             'coverage_nodes_start_in_source':coverage_start,'each_non_root_from_legal_single_axis_edge':True,
             'source_construction_metadata':str(source/'metrics.json'),'node_cap':5000,
             'registered_edge_counts':counts,'roots':[u for u,p in enumerate(reduced.provenance) if p['parent'] is None]}
    save_empty_graph(target,reduced,outmeta)
    dest=target.parent/'builder_snapshot.py';shutil.copyfile(__file__,dest)
    write(target.parent/'BUILD_CODE.json',{'path':str(dest),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
    print(json.dumps({'nodes':len(reduced.nodes),'removed':len(g.nodes)-len(reduced.nodes),
       'head_nodes':sum(s['camera']=='front_head' for s in reduced.nodes),
       'axis_edges':{a:sum(e['axis']==a for e in reduced.edges.values()) for a in ('identity','hair','hair_color','wardrobe','action','camera','site')}},ensure_ascii=False))

if __name__=='__main__':main()
