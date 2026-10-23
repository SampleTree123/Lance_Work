"""Budget-neutral repairs of missing outfit groups and saved sites in the trial."""
import copy
import random
from collections import Counter, deque
from resample_local import Domain, Graph, AXES, load_graph, sample_local, save_graph, write, ROOT


def labels(s):
    return [*[(a,s[a]) for a in AXES if a!='wardrobe'],('family',s['wardrobe']['family_id']),('group',(s['wardrobe']['family_id'],s['wardrobe']['group_id']))]


def replace_one(h, source, target, axis, forbidden):
    assert h.d.edge(h.nodes[source],target,axis) and h.d.valid(target)
    assert [a for i,a in enumerate(AXES) if h.d.canonical(h.nodes[source])[i] != h.d.canonical(target)[i]] == [axis]
    count=Counter(x for s in h.nodes for x in labels(s))
    neighbors={i:{v for vs in row.values() for v in vs} for i,row in enumerate(h.adj)}
    candidates=[]
    for i,s in enumerate(h.nodes):
        if i==source or any(count[x]<=1 for x in labels(s)):continue
        if not neighbors[i] or any(len(neighbors[v])<=1 for v in neighbors[i]):continue
        candidates.append((len(neighbors[i]),s['identity']!=target['identity'],i))
    if not candidates:raise RuntimeError('No value-preserving replacement candidate')
    _,_,victim=min(candidates)
    states=[s for i,s in enumerate(h.nodes) if i!=victim]+[target]
    result=Graph(h.d,forbidden)
    for s in states:
        assert result.add(s) is not None
    assert len(result.nodes)==len(h.nodes)
    return result,{'axis':axis,'source_canonical':list(h.keys[source]),'target_canonical':list(h.d.canonical(target)),
                   'replaced_canonical':list(h.keys[victim]),'replaced_node_degree':len(neighbors[victim])}


def repair(h,forbidden,seed):
    d=h.d;rng=random.Random(seed);repairs=[]
    all_groups=[(sex,f['family_id'],g['group_id']) for sex,p in d.cat['sexes'].items() for f in p['families'] for g in f['groups']]
    have={(s['sex'],s['wardrobe']['family_id'],s['wardrobe']['group_id']) for s in h.nodes}
    for sex,family,group in all_groups:
        if (sex,family,group) in have:continue
        candidates=[i for i,s in enumerate(h.nodes) if s['sex']==sex and s['wardrobe']['family_id']!=family and 'wardrobe' in d.allowed_axes(s)]
        rng.shuffle(candidates)
        for u in candidates:
            s=h.nodes[u];t=copy.deepcopy(s)
            t['wardrobe']=d.nc.sample_choice(sex,rng,family_id=family,group_id=group)
            if d.edge(s,t,'wardrobe') and d.canonical(t) not in h.known and d.canonical(t) not in forbidden:
                h,record=replace_one(h,u,t,'wardrobe',forbidden)
                record['missing_group']=[sex,family,group];repairs.append(record);have.add((sex,family,group));break
        else:raise RuntimeError(f'Cannot repair group {family}/{group}')
    for site in d.sites:
        if site in {s['site'] for s in h.nodes}:continue
        indices=list(range(len(h.nodes)));rng.shuffle(indices)
        for u in indices:
            s=h.nodes[u];t=copy.deepcopy(s);t['site']=site
            if d.valid(t) and d.canonical(t) not in h.known and d.canonical(t) not in forbidden:
                h,record=replace_one(h,u,t,'site',forbidden)
                record['missing_site']=site;repairs.append(record);break
        else:raise RuntimeError(f'Cannot repair site {site}')
    # Store a legal edit-first spanning construction without parents removed by pruning.
    result=Graph(d,forbidden);unseen=set(range(len(h.nodes)))
    while unseen:
        root=min(unseen);unseen.remove(root);mapping={root:result.add(h.nodes[root])};queue=deque([root])
        while queue:
            u=queue.popleft()
            for axis in AXES:
                for v in h.adj[u].get(axis,[]):
                    if v not in unseen:continue
                    unseen.remove(v);mapping[v]=result.add(h.nodes[v],mapping[u],axis);queue.append(v)
    assert len(result.nodes)==len(h.nodes)
    return result,repairs


def main():
    d=Domain();forbidden=set();summary={}
    for j,(split,total) in enumerate([('train',12000),('test',2400)]):
        original=load_graph(ROOT/'linked'/split,d,forbidden)
        g,repairs=repair(original,forbidden,20261103+j)
        ss,sm=sample_local(g,total,20261101+j)
        summary[split]=save_graph(ROOT/'linked_complete'/split,g,ss,{'source_graph':'linked','coverage_repairs':repairs,'sampling':sm})
        forbidden.update(g.keys)
        print(split,len(g.nodes),len(ss),'repairs',len(repairs),'unused',summary[split]['unused_nodes'],flush=True)
    write(ROOT/'linked_complete/SUMMARY.json',summary)


if __name__=='__main__':main()
