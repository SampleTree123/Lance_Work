"""One offline broad-axis, low-value product graph trial; old trials are inputs only."""
from __future__ import annotations
import copy, random, sys, time
from collections import Counter
from pathlib import Path
sys.dont_write_bytecode = True
HERE=Path(__file__).resolve().parent
V3=HERE.parent/'dataset_local_support_20261021_v3'
sys.path.insert(0,str(V3/'blocks'))
from build_blocks import *
HERE=Path(__file__).resolve().parent


def values(g,a,sex=None):
    return represented(g,a,sex)


def pick(d,g,a,sex,rng,exclude=()):
    rows=[v for v in pools(d,sex)[a] if v not in exclude]
    seen=values(g,a,sex if a in ('identity','hair','wardrobe') else None)
    fresh=[v for v in rows if v not in seen]
    return rng.choice(fresh or rows)


def groups(d,sex):
    return [(f['family_id'],r['group_id']) for f in d.cat['sexes'][sex]['families'] for r in f['groups']]


def have_groups(g,sex):
    return {(s['wardrobe']['family_id'],s['wardrobe']['group_id']) for s in g.nodes if s['sex']==sex}


def wardrobe_values(d,g,s,rng):
    """Four choices: base, a real single if possible, two other family groups."""
    out=[copy.deepcopy(s['wardrobe'])]
    singles=d.singles(s)
    if singles:out.append(copy.deepcopy(rng.choice(singles)['choice']))
    seen=have_groups(g,s['sex']);available=groups(d,s['sex']);rng.shuffle(available)
    available.sort(key=lambda p:p in seen)
    for fam,grp in available:
        if fam in {w['family_id'] for w in out}:continue
        w=d.nc.sample_choice(s['sex'],rng,family_id=fam,group_id=grp)
        if d.edge(s,{**s,'wardrobe':w},'wardrobe'):
            out.append(w)
        if len(out)>=4:break
    return out


def root(d,g,sex,rng,j):
    # Seed independent valid contexts with useful unseen catalogue values.
    candidates=groups(d,sex);rng.shuffle(candidates)
    candidates.sort(key=lambda p:(p[0] in values(g,'wardrobe',sex),p in have_groups(g,sex)))
    for fam,grp in candidates:
        for k in range(30):
            s=d.initial(rng)
            s.update(sex=sex,identity=pick(d,g,'identity',sex,rng),hair=pick(d,g,'hair',sex,rng),
                     hair_color=pick(d,g,'hair_color',sex,rng),action=pick(d,g,'action',sex,rng),
                     site=pick(d,g,'site',sex,rng),camera='dolly_in_front' if j%2 else 'front_upper',
                     wardrobe=d.nc.sample_choice(sex,rng,family_id=fam,group_id=grp))
            if d.valid(s) and d.singles(s):
                u=g.add(s)
                if u is not None:return u
    # Locked families need not supply a single; coverage patches handle them.
    for k in range(100):
        s=d.initial(rng)
        if s['sex']!=sex:continue
        s['camera']='dolly_out_front'
        if d.valid(s):
            u=g.add(s)
            if u is not None:return u
    raise RuntimeError('root allocation exhausted')


def twin_patch(g,u,t,a,budget,records,width=2):
    """Add a requested value and clone its context neighbors, giving an exit axis."""
    if len(g.nodes)>=budget:return False
    old=len(g.nodes);v=legal_add(g,u,t,a)
    if v is None:return False
    paired=[]
    neighbors=[(axis,w) for axis,vs in g.adj[u].items() if axis!=a for w in vs]
    neighbors.sort(key=lambda aw:(aw[0]=='identity',aw[0]=='wardrobe'))
    for b,w in neighbors:
        need=sum(len(set(pools(g.d,sex)[aa])-values(g,aa,sex if aa in ('identity','hair') else None))
                 for aa in ('identity','hair','camera','site','action','hair_color') for sex in ('female','male'))
        need+=sum(len(set(groups(g.d,sex))-have_groups(g,sex)) for sex in ('female','male'))
        if len(g.nodes)+need>=budget or len(paired)>=width-1:break
        tt=copy.deepcopy(g.nodes[w]);tt[a]=copy.deepcopy(t[a])
        z=legal_add(g,v,tt,b)
        if z is not None:paired.append(z)
    if len(g.nodes)>old:records.append({'axis':a,'source':u,'target':v,'context_clones':paired})
    return len(g.nodes)>old


def cover(g,budget,rng,records):
    d=g.d
    # Identity targets always enter a context which already has other edits.
    for sex in ('female','male'):
        for identity in d.ids[sex]:
            if identity in values(g,'identity',sex):continue
            candidates=[i for i,s in enumerate(g.nodes) if s['sex']==sex and s['camera'] in ID_CAMERAS]
            rng.shuffle(candidates)
            for u in candidates:
                t=copy.deepcopy(g.nodes[u]);t['identity']=identity
                if twin_patch(g,u,t,'identity',budget,records):break
    for sex in ('female','male'):
        for fam,grp in groups(d,sex):
            if (fam,grp) in have_groups(g,sex):continue
            candidates=[i for i,s in enumerate(g.nodes) if s['sex']==sex and s['wardrobe']['family_id']!=fam and 'wardrobe' in d.allowed_axes(s)]
            rng.shuffle(candidates)
            for u in candidates:
                t=copy.deepcopy(g.nodes[u]);t['wardrobe']=d.nc.sample_choice(sex,rng,family_id=fam,group_id=grp)
                if twin_patch(g,u,t,'wardrobe',budget,records):break
    for a in ('hair','camera','site','action','hair_color'):
        for sex in ('female','male'):
            for value in pools(d,sex)[a]:
                if value in values(g,a,sex if a=='hair' else None):continue
                candidates=[i for i,s in enumerate(g.nodes) if s['sex']==sex and a in d.allowed_axes(s)]
                rng.shuffle(candidates)
                for u in candidates:
                    t=copy.deepcopy(g.nodes[u]);t[a]=value
                    if twin_patch(g,u,t,a,budget,records):break


def grow_wide(d,budget,seed,forbidden=None):
    rng=random.Random(seed);g=Graph(d,forbidden);blocks=[];roots=[];repairs=[]
    train=budget>1000
    count=16 if train else 20
    # The test has the same 40 identities/45 groups, so 4-axis products are the
    # affordable core. Train can cross every formal axis in 7-axis products.
    schedule=['action','camera','site','hair_color','action','camera','site','action','camera','site','hair_color','action','camera','site','action','hair_color','camera','site','action','site']
    for j in range(count):
        sex=('female','male')[j%2];u=root(d,g,sex,rng,j);roots.append(u);s=g.nodes[u]
        axes=list(AXES) if train else ['identity','hair','wardrobe',schedule[j]]
        palettes={}
        for a in axes:
            if a=='wardrobe':
                ws=wardrobe_values(d,g,s,rng)
                # Spread products across identities before spending nodes on
                # wider local target palettes. Exact single/whole semantics
                # are retained; this alternates candidate support by block.
                palettes[a]=[ws[0],ws[1] if (j//2)%2==0 else ws[-1]]
            elif a=='camera':
                # With an identity dimension, only eligible front cameras let
                # the entire product preserve its identity edit axis.
                cams=sorted(ID_CAMERAS-{'front_head',s['camera']}) if train else [c for c in d.cameras if c!=s['camera']]
                fresh=[c for c in cams if c not in values(g,'camera')]
                palettes[a]=[s[a],rng.choice(fresh or cams)]
            else:palettes[a]=[s[a],pick(d,g,a,sex,rng,[s[a]])]
        b=add_block(g,u,axes,rng,budget,len(blocks),2,palettes)
        blocks.append(b)
        print('BLOCK',budget,j,len(g.nodes),len(b['new_nodes']),flush=True)
    cover(g,budget,rng,repairs)
    if len(g.nodes)>budget:raise RuntimeError('coverage exceeded budget')
    # Spend any remaining budget on overlapping products anchored at the
    # weakest contexts; identity has no artificial per-person cap.
    attempts=0
    while len(g.nodes)<budget and attempts<budget:
        attempts+=1
        candidates=list(range(len(g.nodes)));rng.shuffle(candidates)
        u=min(candidates[:150],key=lambda i:len(g.adj[i]))
        s=g.nodes[u];allowed=d.allowed_axes(s)
        allowed.sort(key=lambda a:(bool(g.adj[u].get(a)),rng.random()))
        axes=allowed[:min(5,len(allowed))]
        palettes={a:palette(d,s,a,rng,2) for a in axes}
        if 'wardrobe' in axes:palettes['wardrobe']=wardrobe_values(d,g,s,rng)[:3]
        b=add_block(g,u,axes,rng,budget,len(blocks),2,palettes)
        if b['new_nodes']:blocks.append(b)
    assert len(g.nodes)==budget,(len(g.nodes),budget)
    diag=support_diagnostics(g)
    diag['groups']={'expected':sum(len(groups(d,sex)) for sex in ('female','male')),'actual':sum(len(have_groups(g,sex)) for sex in ('female','male'))}
    diag['identity_node_counts']=dict(Counter(s['identity'] for s in g.nodes))
    return g,{'strategy':'wide_low_value_legal_products_no_per_identity_caps','seed':seed,'roots':roots,'blocks':blocks,
              'coverage_context_patches':repairs,'diagnostics':diag,'each_non_root_from_legal_single_axis_edge':True,
              'no_history_or_axis_repetition_ban':True,'latest_contract':'20261021 local finite support'}


def main():
    d=Domain();forbidden=set();out={};start=time.time()
    for j,(split,budget) in enumerate([('train',2500),('test',500)]):
        g,meta=grow_wide(d,budget,2026102140+j,forbidden)
        out[split]=save_empty_graph(HERE/'wide'/split,g,meta)
        forbidden.update(g.keys)
        print('GRAPH_READY',split,len(g.nodes),len(g.edges),meta['diagnostics']['axis_support_histogram'],meta['diagnostics']['coverage'],meta['diagnostics']['groups'],flush=True)
    out['elapsed_seconds']=time.time()-start
    write(HERE/'wide'/'SUMMARY.json',out)

if __name__=='__main__':main()
