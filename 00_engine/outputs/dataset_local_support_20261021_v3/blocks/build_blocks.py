"""Offline finite-support overlapping edit blocks, revision 3.

API: grow_blocks(domain, budget, seed, forbidden=None) -> (Graph, metadata).
load_graph(path, domain=None) reconstructs saved Graph for independent sampling.
Every non-root state is introduced through an already-existing legal atomic edge.
"""
from __future__ import annotations
import argparse, copy, itertools, json, random, sys, time
from collections import Counter, defaultdict, deque
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
V1=HERE.parents[1]/'dataset_trial_build_20261021_v1'
sys.path.insert(0,str(V1))
from build_trial import Domain,Graph,AXES,ID_CAMERAS,UPPER,COLORS,save_graph,sample,write,read,token,digest

def pools(d,sex):
    return {'identity':d.ids[sex],'hair':d.hairs[sex],'hair_color':COLORS,
            'wardrobe':[r['family_id'] for r in d.cat['sexes'][sex]['families']],
            'action':d.actions,'camera':d.cameras,'site':d.sites}

def represented(g,axis,sex=None):
    return {s['wardrobe']['family_id'] if axis=='wardrobe' else s[axis]
            for s in g.nodes if sex is None or s['sex']==sex}

def legal_add(g,parent,t,axis):
    s=g.nodes[parent]
    if not g.d.valid(t) or g.d.edge(s,t,axis) is None:return None
    # Reject accidental multi-attribute changes before invoking Graph's buckets.
    sk,tk=g.d.canonical(s),g.d.canonical(t)
    if [AXES[k] for k in range(len(AXES)) if sk[k]!=tk[k]]!=[axis]:return None
    return g.add(t,parent,axis)

def forced_target(d,s,axis,value,rng):
    t=copy.deepcopy(s)
    if axis=='wardrobe':
        t[axis]=d.nc.sample_choice(s['sex'],rng,family_id=value)
    else:t[axis]=value
    return t

def cover_domains(g,rng,budget):
    """Greedy catalog coverage through actual edges, never unrelated full states."""
    records=[]
    # Identity needs a front source, so cover it before broadening cameras.
    for axis in ('identity','wardrobe','hair','action','camera','site','hair_color'):
        for sex in ('female','male'):
            values=pools(g.d,sex)[axis]
            missing=[v for v in values if v not in represented(g,axis,sex if axis in ('identity','hair','wardrobe') else None)]
            rng.shuffle(missing)
            for value in missing:
                candidates=[i for i,s in enumerate(g.nodes) if s['sex']==sex and axis in g.d.allowed_axes(s)]
                rng.shuffle(candidates)
                # Spread support rather than placing every new category at one root.
                candidates.sort(key=lambda i:sum(map(len,g.adj[i].values())))
                for u in candidates:
                    t=forced_target(g.d,g.nodes[u],axis,value,rng)
                    if len(g.nodes)>=budget:break
                    v=legal_add(g,u,t,axis)
                    if v is not None:
                        records.append({'axis':axis,'value':value,'source':u,'target':v});break
    return records

def wardrobe_palette(d,s,rng,width=3):
    """Several families, each with a real same-group single target if available."""
    base=copy.deepcopy(s['wardrobe']);rows=[base]
    candidates=[v for v in pools(d,s['sex'])['wardrobe'] if v!=base['family_id']]
    rng.shuffle(candidates)
    for family in candidates:
        t=forced_target(d,s,'wardrobe',family,rng)
        if d.edge(s,t,'wardrobe'):
            rows.append(t['wardrobe'])
            if len(rows)>=width:break
    # One single per represented family; locked/no-single sources stay whole-only.
    for choice in list(rows):
        ss={**s,'wardrobe':choice};single=d.singles(ss)
        if single:
            slots=sorted({r['slot'] for r in single});slot=rng.choice(slots)
            rows.append(copy.deepcopy(rng.choice([r for r in single if r['slot']==slot])['choice']))
    unique={d.wkey({**s,'wardrobe':w}):w for w in rows}
    return list(unique.values())

def palette(d,s,axis,rng,width=3):
    if axis=='wardrobe':return wardrobe_palette(d,s,rng,width)
    vals=[v for v in pools(d,s['sex'])[axis] if v!=s[axis]]
    rng.shuffle(vals)
    if axis=='camera':
        # Weighted sampling without replacement of local camera candidates.
        chosen=[]
        while vals and len(chosen)<width-1:
            v=rng.choices(vals,weights=[1.5 if x in ID_CAMERAS else 1 for x in vals])[0]
            vals.remove(v);chosen.append(v)
        vals=chosen
    return [s[axis],*vals[:width-1]]

def add_block(g,anchor,axes,rng,budget,block_id,width=3,palettes=None):
    """BFS in a finite Cartesian palette; each state is reached along one axis."""
    d=g.d;base=g.nodes[anchor]
    values=palettes or {a:palette(d,base,a,rng,width) for a in axes}
    queue=deque([anchor]);seen={anchor};added=[]
    while queue and len(g.nodes)<budget:
        u=queue.popleft();s=g.nodes[u]
        for a in axes:
            if a not in d.allowed_axes(s):continue
            for value in values[a]:
                t=copy.deepcopy(s);t[a]=copy.deepcopy(value)
                if d.canonical(t)==g.keys[u]:continue
                old=len(g.nodes);v=legal_add(g,u,t,a)
                if v is None:continue
                if len(g.nodes)>old:added.append(v)
                if v not in seen:seen.add(v);queue.append(v)
                if len(g.nodes)>=budget:break
            if len(g.nodes)>=budget:break
    return {'id':block_id,'anchor':anchor,'axes':list(axes),'palette_sizes':{a:len(v) for a,v in values.items()},
            'palettes':values,'new_nodes':added,'reachable_nodes':sorted(seen)}

def support_diagnostics(g):
    eligible=Counter();missing=Counter();both=0;singlelegal=0;singlesmissing=0;wholemissing=0
    for i,s in enumerate(g.nodes):
        for a in g.d.allowed_axes(s):
            eligible[a]+=1
            if not g.adj[i].get(a):missing[a]+=1
        if 'wardrobe' in g.d.allowed_axes(s) and g.d.singles(s):
            singlelegal+=1;modes={g.edges[i,v]['mode'] for v in g.adj[i].get('wardrobe',[])}
            singlesmissing+='single_piece' not in modes;wholemissing+='whole_outfit' not in modes
            both+=modes=={'single_piece','whole_outfit'}
    coverage={}
    for a in AXES:
        expected=set().union(*(set(pools(g.d,sex)[a]) for sex in ('female','male')))
        actual=represented(g,a)
        coverage[a]={'expected':len(expected),'actual':len(actual),'missing':sorted(expected-actual)}
    return {'coverage':coverage,'formal_eligible_nodes':dict(eligible),'formal_axis_missing_graph_nodes':dict(missing),
            'formal_single_nodes':singlelegal,'of_those_with_both_modes':both,'of_those_missing_single':singlesmissing,
            'of_those_missing_whole':wholemissing,'isolated_nodes':[i for i,a in enumerate(g.adj) if not any(a.values())],
            'axis_support_histogram':dict(Counter(len([a for a in AXES if row.get(a)]) for row in g.adj)),
            'degree_histogram':dict(Counter(sum(map(len,row.values())) for row in g.adj))}

def grow_blocks(d,budget,seed,forbidden=None,wardrobe_spine=False):
    rng=random.Random(seed);g=Graph(d,forbidden);roots=[]
    for sex in ('female','male'):
        for _ in range(1000):
            s=d.initial(rng)
            if s['sex']!=sex:continue
            s['camera']=rng.choice(sorted(ID_CAMERAS-{'front_head'}))
            if not d.valid(s):continue
            u=g.add(s)
            if u is not None:roots.append(u);break
    coverage=cover_domains(g,rng,budget)
    blocks=[];axisuse=Counter();anchoruse=Counter();attempts=0
    while len(g.nodes)<budget and attempts<budget*3:
        attempts+=1
        # Prefer catalog-coverage leaves and under-used block anchors.
        candidates=list(range(len(g.nodes)));rng.shuffle(candidates)
        u=min(candidates[:min(150,len(candidates))],key=lambda i:(anchoruse[i],len(g.adj[i]),sum(map(len,g.adj[i].values()))))
        allowed=d.allowed_axes(g.nodes[u]);rng.shuffle(allowed)
        allowed.sort(key=lambda a:axisuse[a]/(2 if a=='identity' else 1))
        axes=allowed[:3]
        if wardrobe_spine and 'wardrobe' in allowed:
            axes=['wardrobe']+[a for a in allowed if a!='wardrobe'][:2]
        # Four-value support for cheap hair-color blocks gives three edit targets.
        width=4 if len(g.nodes)+64<budget and attempts%4==0 and 'wardrobe' not in axes else 3
        block=add_block(g,u,axes,rng,budget,len(blocks),width)
        if block['new_nodes']:
            blocks.append(block);axisuse.update(axes);anchoruse[u]+=1
    if len(g.nodes)!=budget:raise RuntimeError(f'graph filled {len(g.nodes)}/{budget}')
    meta={'strategy':'overlapping_3_axis_3_or_4_value_blocks_with_multifamily_single_piece_wardrobe',
          'wardrobe_spine':wardrobe_spine,
          'seed':seed,'roots':roots,'coverage_edits':coverage,'blocks':blocks,'block_axis_counts':dict(axisuse),
          'each_non_root_from_legal_single_axis_edge':True,'latest_contract':'20261021 finite target support accepted',
          'diagnostics':support_diagnostics(g)}
    return g,meta

def load_graph(path,domain=None):
    """Load saved node states; Graph.add deterministically rebuilds formal edges."""
    d=domain or Domain();g=Graph(d)
    for row in read(Path(path)/'nodes.json'):
        p=row.get('created_by',{});g.add(row['state'],p.get('parent'),p.get('axis'))
    return g

def save_empty_graph(path,g,meta):
    path.mkdir(parents=True,exist_ok=True)
    write(path/'nodes.json',[{'id':i,'canonical_id':'node_'+digest(g.keys[i]),'state':s,'created_by':g.provenance[i]} for i,s in enumerate(g.nodes)])
    write(path/'edges.json',[{'source':u,'target':v,**e} for (u,v),e in sorted(g.edges.items())])
    (path/'sessions.jsonl').write_text('',encoding='utf-8')
    result={'nodes':len(g.nodes),'registered_edges':len(g.edges),'sessions':0,'construction':meta}
    write(path/'metrics.json',result)
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,default=202610213);ap.add_argument('--no-sessions',action='store_true');ap.add_argument('--wardrobe-spine',action='store_true');args=ap.parse_args()
    d=Domain();used=set();report={};begin=time.time();target=HERE/('wardrobe_spines' if args.wardrobe_spine else 'candidate')
    for j,(split,budget,total) in enumerate([('train',2500,12000),('test',500,2400)]):
        g,meta=grow_blocks(d,budget,args.seed+j,used,args.wardrobe_spine)
        # Persist graphs immediately so a separate sampler can use them.
        report[split]=save_empty_graph(target/split,g,meta)
        write(target/split/'blocks.json',meta['blocks'])
        print('GRAPH_READY',split,len(g.nodes),len(g.edges),str(target/split),flush=True)
        if not args.no_sessions:
            ss,reject=sample(g,total,args.seed+100+j,'uniform_nodes')
            meta['preliminary_sampling']='v1 graph-neighbor diagnostic only; parent sampler will balance global axes/modes'
            meta['sampling_rejections']=reject
            report[split]=save_graph(target/split,g,ss,meta)
            print('SAMPLED',split,len(ss),'revisits',report[split]['sessions_with_revisited_node'],flush=True)
        used.update(g.keys)
    report['elapsed_seconds']=time.time()-begin;write(target/'SUMMARY.json',report)
    print('DONE',round(report['elapsed_seconds'],2),flush=True)
if __name__=='__main__':main()
