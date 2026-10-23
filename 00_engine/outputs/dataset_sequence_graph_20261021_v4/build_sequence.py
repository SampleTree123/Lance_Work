"""Offline sequence-first shared-state experiment, not a production sampler.

Construction favors previously missing edit directions and short order coverage.
Delivered sessions use the unchanged v3 sampler, with no no-repeat rule.
"""
from __future__ import annotations
import argparse, copy, itertools, random, sys, time
from collections import Counter
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
V3 = ROOT.parent / 'dataset_local_support_20261021_v3'
sys.path[:0] = [str(V3), str(V3/'blocks')]
from build_blocks import (Domain, Graph, AXES, ID_CAMERAS, COLORS, pools, legal_add,
                          cover_domains, support_diagnostics, save_empty_graph)
from resample_local import sample_local, save_graph, write


def cover_groups(g, rng, limit):
    records=[]
    for sex,p in g.d.cat['sexes'].items():
        for fam in p['families']:
            for group in fam['groups']:
                if any(s['sex']==sex and s['wardrobe']['family_id']==fam['family_id'] and s['wardrobe']['group_id']==group['group_id'] for s in g.nodes): continue
                candidates=[i for i,s in enumerate(g.nodes) if s['sex']==sex and s['wardrobe']['family_id']!=fam['family_id'] and 'wardrobe' in g.d.allowed_axes(s)]
                rng.shuffle(candidates)
                candidates.sort(key=lambda i:len(g.adj[i]))
                for u in candidates:
                    t=copy.deepcopy(g.nodes[u]);t['wardrobe']=g.d.nc.sample_choice(sex,rng,family_id=fam['family_id'],group_id=group['group_id'])
                    if len(g.nodes)>=limit: raise RuntimeError('Coverage exceeds budget')
                    v=legal_add(g,u,t,'wardrobe')
                    if v is not None:records.append({'source':u,'target':v,'axis':'wardrobe'});break
                else: raise RuntimeError('Unreachable group '+group['group_id'])
    return records


def candidate_trace(g,u,rng,pair_counts,axis_counts):
    """Plan five actual legal edits, including repeats. Bias is construction-only."""
    d=g.d;s=copy.deepcopy(g.nodes[u]);trace=[];local=[]
    for turn in range(5):
        axes=d.allowed_axes(s)
        weights=[]
        for a in axes:
            # An absent outgoing axis is a construction need, not an illegal edit.
            root_deficit=2 if not g.adj[u].get(a) else 1
            pair_deficit=1/(1+pair_counts[(local[-1],a)])**.35 if local else 1
            used_discount=.45 if a in local else 1
            weights.append((2 if a=='identity' else 1)*root_deficit*pair_deficit*used_discount/(1+axis_counts[a])**.15)
        a=rng.choices(axes,weights=weights,k=1)[0]
        m=d.mutate(s,rng,a)
        if not m: continue
        t=m[0];trace.append((a,copy.deepcopy(t[a])));local.append(a);s=t
    return trace


def replay_states(d,base,operations):
    s=copy.deepcopy(base);path=[]
    for a,value in operations:
        t=copy.deepcopy(s);t[a]=copy.deepcopy(value)
        if not d.valid(t) or d.edge(s,t,a) is None: return None
        if [x for j,x in enumerate(AXES) if d.canonical(s)[j]!=d.canonical(t)[j]]!=[a]: return None
        path.append((a,t));s=t
    return path


def grow(d,budget,seed,forbidden):
    rng=random.Random(seed);g=Graph(d,forbidden);roots=[]
    for sex in ('female','male'):
        while True:
            s=d.initial(rng)
            if s['sex']!=sex: continue
            s['camera']=rng.choice(sorted(ID_CAMERAS-{'front_head'}))
            if not d.valid(s): continue
            u=g.add(s)
            if u is not None: roots.append(u);break
    # Cover labels by real edits before spending the remaining budget on crossings.
    coverage=cover_domains(g,rng,budget)
    coverage+=cover_groups(g,rng,budget)
    coverage_size=len(g.nodes)
    usage=Counter();axis_counts=Counter();pair_counts=Counter();bundles=[];attempts=0
    while len(g.nodes)<budget and attempts<budget*10:
        attempts+=1
        candidates=rng.sample(range(len(g.nodes)),min(100,len(g.nodes)))
        # Prefer low-direction nodes, including incoming identity clones, while
        # retaining overlap with already expanded states. No per-identity cap.
        u=min(candidates,key=lambda i:(len(g.adj[i])+.8*usage[i], rng.random()))
        trace=candidate_trace(g,u,rng,pair_counts,axis_counts)
        if not trace: continue
        orders=[trace]
        # Reorder only independent attribute operations, checking formal legality
        # at every intermediate source. Repeated-attribute traces stay ordered.
        if len({a for a,_ in trace})==len(trace):
            perms=list(itertools.permutations(trace));rng.shuffle(perms)
            perms.sort(key=lambda p:sum(pair_counts[(a[0],b[0])] for a,b in zip(p,p[1:])))
            orders.extend(perms[:24])
        start=len(g.nodes);accepted=[]
        allowance=min(budget-len(g.nodes),48 if budget>1000 else 20)
        for ops in orders:
            path=replay_states(d,g.nodes[u],ops)
            if path is None:continue
            keys=[d.canonical(s) for _,s in path]
            if any(k in forbidden for k in keys):continue
            missing=len(set(keys)-set(g.known))
            if len(g.nodes)-start+missing>allowance:continue
            p=u;nodepath=[u]
            for a,t in path:
                v=legal_add(g,p,t,a)
                assert v is not None
                nodepath.append(v);p=v
            seq=[a for a,_ in ops]
            axis_counts.update(seq);pair_counts.update(zip(seq,seq[1:]));accepted.append({'axes':seq,'nodes':nodepath})
        if len(g.nodes)>start:
            usage[u]+=1;bundles.append({'anchor':u,'new_nodes':len(g.nodes)-start,'paths':accepted})
        elif budget-len(g.nodes)<5:
            for _ in range(50):
                m=d.mutate(g.nodes[u],rng)
                if m and d.canonical(m[0]) not in g.known:
                    if legal_add(g,u,m[0],m[1]) is not None:break
        if attempts%25==0:print('growth',budget,len(g.nodes),attempts,flush=True)
    if len(g.nodes)!=budget:raise RuntimeError(f'Unfilled graph {len(g.nodes)}/{budget}')
    return g,{'strategy':'legal_five_edit_trace_order_union_with_shared_intermediates',
              'seed':seed,'roots':roots,'coverage_nodes':coverage_size,'coverage_edits':coverage,
              'construction_axis_repeat_discount':.45,'construction_only_not_session_rule':True,
              'max_bundle_new_nodes':48 if budget>1000 else 20,
              'attempts':attempts,'bundles':bundles,'diagnostics':support_diagnostics(g)}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--no-sample',action='store_true');args=ap.parse_args()
    d=Domain();forbidden=set();summary={};t=time.time()
    for j,(split,budget,total) in enumerate([('train',2500,12000),('test',500,2400)]):
        g,meta=grow(d,budget,20261112+j,forbidden)
        target=ROOT/'sequence'/split
        save_empty_graph(target,g,meta)
        print('GRAPH_READY',split,len(g.nodes),len(g.edges),flush=True)
        if not args.no_sample:
            ss,sm=sample_local(g,total,20261122+j)
            meta['sampling']=sm;summary[split]=save_graph(target,g,ss,meta)
            print('SAMPLED',split,len(ss),summary[split]['unused_nodes'],flush=True)
        forbidden.update(g.keys)
    summary['elapsed_seconds']=time.time()-t;write(ROOT/'sequence/SUMMARY.json',summary)

if __name__=='__main__':main()
