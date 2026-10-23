"""Explore a smaller fixed-aspect graph using only immutable original edges."""
import sys, json, copy, random, time
from pathlib import Path
from collections import Counter, defaultdict
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
V6 = HERE.parent.parent / 'dataset_compact_graph_20261022_v6'
sys.path[:0] = [str(V6), str(V6.parent/'dataset_local_support_20261021_v3')]
from resample_local import Domain, Graph, save_graph, read, write
from sample_compact_v68_snapshot import sample
import networkx as nx

def construct(split, budget):
    src=V6/('graph_n' if split=='train' else 'graph_t')/split
    rows=read(src/'nodes.json'); states=[r['state'] for r in rows]; edges=read(src/'edges.json')
    counts=Counter(e['axis'] for e in edges)
    graph=nx.Graph(); graph.add_nodes_from(range(len(rows)))
    for e in edges:
        if e['source'] < e['target']:
            graph.add_edge(e['source'],e['target'],weight=10000/counts[e['axis']] * (10 if split=='train' and e['axis']=='camera' else 1))
    colors={}; component_sizes=[]
    for sex in ('female','male'):
        ids=[i for i,s in enumerate(states) if s['sex']==sex]
        sub=graph.subgraph(ids)
        cs=sorted(nx.connected_components(sub),key=len,reverse=True)
        component_sizes.append((sex,[len(c) for c in cs]))
        if split=='train':
            bins=[set(),set()]
            for c in cs:
                parts=nx.community.kernighan_lin_bisection(sub.subgraph(c),max_iter=20,seed=20261022)
                for j in (0,1): bins[j].update(parts[j])
        elif max(map(len,cs)) < len(ids)*.65:
            bins=[set(),set()]
            for c in cs:
                bins[min(range(2),key=lambda j:len(bins[j]))].update(c)
        else:
            bins=nx.community.kernighan_lin_bisection(sub, max_iter=15, seed=20261022)
        for c,vs in enumerate(bins):
            for u in vs: colors[u]=c
    allowed={u:{colors[u]} for u in colors}
    adjacency=defaultdict(list)
    for e in edges: adjacency[e['source']].append((e['target'],e['axis']))
    # Copy the nodes with the largest currently recoverable rare-axis support.
    # Recompute gains after each copy so newly recoverable edges count exactly.
    for iteration in range(budget-len(rows)):
        best=None
        for u,aspects in allowed.items():
            if len(aspects)==2: continue
            a=1-colors[u]
            gain=sum(10000/counts[axis] for v,axis in adjacency[u] if a in allowed[v])
            # A copied boundary node should serve both the common and rare axes.
            value=gain
            if best is None or value>best[0]: best=(value,u,a)
        if best is None or best[0]<=0: break
        allowed[best[1]].add(best[2])
    d=Domain(); g=Graph(d); mapping={}; origin=[]
    for u in range(len(rows)):
        for a in sorted(allowed[u]):
            idx=len(g.nodes); mapping[u,a]=idx
            s=copy.deepcopy(states[u]); s['aspect']=('landscape','portrait')[a]
            g.nodes.append(s); g.keys.append(d.canonical(s)+(s['aspect'],)); g.adj.append(defaultdict(list)); g.provenance.append({'parent':None,'axis':None}); origin.append({'id':idx,'source_id':u,'aspect':s['aspect']})
    for e in edges:
        u,v=e['source'],e['target']
        for a in allowed[u]&allowed[v]:
            x,y=mapping[u,a],mapping[v,a]; meta={k:v for k,v in e.items() if k not in ('source','target')}
            g.edges[x,y]=meta; g.adj[x][e['axis']].append(y)
    meta={'source':str(src),'original_nodes':len(rows),'nodes':len(g.nodes),'components':component_sizes,
          'axis_counts':dict(Counter(e['axis'] for e in g.edges.values())),
          'aspect_axis_counts':{asp:dict(Counter(e['axis'] for (u,v),e in g.edges.items() if g.nodes[u]['aspect']==asp)) for asp in ('landscape','portrait')},
          'aspect_sex_camera_nodes':dict(Counter(f"{s['aspect']}|{s['sex']}|{s['camera']}" for s in g.nodes))}
    return g,origin,meta

def main():
    split=sys.argv[1]; budget=int(sys.argv[2]); output=HERE/f'{split}_{budget}'
    if len(sys.argv)>3: output=HERE/f'{split}_{budget}_{sys.argv[3]}'
    output.mkdir(exist_ok=True)
    start=time.time(); g,origin,meta=construct(split,budget)
    write(output/'CONSTRUCTION.json',meta); write(output/'ORIGIN.json',origin)
    print('CONSTRUCTED',split,len(g.nodes),meta['axis_counts'],meta['aspect_axis_counts'],flush=True)
    sessions,sampling=sample(g,12000 if split=='train' else 2400,2026102261 if split=='train' else 2026102262,max_attempts=240,progress_every=1000,history_decay=.2,nonidentity_upper_slack=.025)
    meta['sampling']=sampling
    if sessions: save_graph(output,g,sessions,meta)
    write(output/'sampling.json',sampling)
    write(output/'RESULT.json',{'elapsed':time.time()-start,'complete':sampling['complete'],'sessions':len(sessions),'aspect_sessions':dict(Counter(g.nodes[s['history'][0]]['aspect'] for s in sessions)),'axis_counts':sampling['axis_counts'],'nonidentity_relative_deviation':sampling.get('nonidentity_relative_deviation'),'errors':sampling.get('errors_and_retries')})
    print('RESULT',json.dumps(read(output/'RESULT.json')),flush=True)
if __name__=='__main__': main()
