"""One camera-balanced broad context variant; no old trial files are changed."""
import copy, random, sys, time
from collections import Counter
from pathlib import Path
sys.dont_write_bytecode=True
from build_wide import *
HERE=Path(__file__).resolve().parent


def initial_context(d,g,sex,camera,rng):
    choices=groups(d,sex);rng.shuffle(choices)
    choices.sort(key=lambda p:(p[0] in values(g,'wardrobe',sex),p in have_groups(g,sex)))
    for fam,grp in choices:
        for k in range(20):
            s=d.initial(rng)
            s.update(sex=sex,identity=pick(d,g,'identity',sex,rng),hair=pick(d,g,'hair',sex,rng),
                     hair_color=pick(d,g,'hair_color',sex,rng),action=pick(d,g,'action',sex,rng),
                     site=pick(d,g,'site',sex,rng),camera=camera,
                     wardrobe=d.nc.sample_choice(sex,rng,family_id=fam,group_id=grp))
            if d.valid(s) and d.singles({**s,'camera':'dolly_in_front'}):return s
    raise RuntimeError('balanced root exhausted')


def camera_values(d,g,s,width,rng,eligible=True):
    other=[c for c in d.cameras if c not in ID_CAMERAS]
    rng.shuffle(other);other.sort(key=lambda c:c in values(g,'camera'))
    return ([s['camera']]+other[:width-1]) if eligible else other[:width]


def grow_balanced(d,budget,seed,forbidden):
    rng=random.Random(seed);g=Graph(d,forbidden);blocks=[];roots=[];repairs=[]
    train=budget>1000
    for j in range(20):
        sex=('female','male')[j%2]
        front=sorted(ID_CAMERAS)[(j//2)%4]
        s=initial_context(d,g,sex,front,rng)
        u=g.add(s);roots.append(u)
        identity=pick(d,g,'identity',sex,rng,[s['identity']])
        axes=list(AXES) if train else ['identity','hair','wardrobe','camera']
        if train:
            # Rotate the omitted nonidentity dimension: six changing axes,
            # four camera values, and two values for every other dimension.
            omitted=['hair','hair_color','wardrobe','action','site'][j%5]
            axes.remove(omitted)
        width=4 if train else (3 if j<18 else 2)
        eligible=train or j<16
        cameras=camera_values(d,g,s,width,rng,eligible)
        palettes={}
        for a in axes:
            if a=='identity':palettes[a]=[s[a],identity]
            elif a=='camera':palettes[a]=cameras
            elif a=='wardrobe':
                ws=wardrobe_values(d,g,{**s,'camera':'dolly_in_front'},rng)
                palettes[a]=[s[a],ws[1] if (j//2)%2==0 else ws[-1]]
            else:palettes[a]=[s[a],pick(d,g,a,sex,rng,[s[a]])]
        if eligible:
            b=add_block(g,u,axes,rng,len(g.nodes)+(111 if train else 1000),len(blocks),2,palettes)
            blocks.append(b)
        else:
            # Both identities enter through a front identity edge; each then
            # reaches its shared nonfront palette through a legal camera edit.
            t=copy.deepcopy(s);t['identity']=identity
            v=legal_add(g,u,t,'identity')
            local_axes=[a for a in axes if a!='identity']
            local={a:vals for a,vals in palettes.items() if a!='identity'}
            for base in (u,v):
                t=copy.deepcopy(g.nodes[base]);t['camera']=cameras[0]
                anchor=legal_add(g,base,t,'camera')
                b=add_block(g,anchor,local_axes,rng,budget,len(blocks),2,local)
                blocks.append(b)
        print('BALANCED_BLOCK',budget,j,len(g.nodes),flush=True)
    cover(g,budget,rng,repairs)
    attempts=0
    while len(g.nodes)<budget and attempts<budget:
        attempts+=1
        # Fill existing weak contexts without concentrating on the front pool.
        candidates=list(range(len(g.nodes)));rng.shuffle(candidates)
        nonfront=[u for u in candidates if g.nodes[u]['camera'] not in ID_CAMERAS]
        u=min((nonfront or candidates)[:150],key=lambda i:len(g.adj[i]))
        s=g.nodes[u];axes=[a for a in d.allowed_axes(s) if a!='camera']
        rng.shuffle(axes);axes.sort(key=lambda a:bool(g.adj[u].get(a)));axes=axes[:4]
        vals={a:palette(d,s,a,rng,2) for a in axes}
        if 'wardrobe' in axes:vals['wardrobe']=wardrobe_values(d,g,s,rng)[:3]
        b=add_block(g,u,axes,rng,budget,len(blocks),2,vals)
        if b['new_nodes']:blocks.append(b)
    assert len(g.nodes)==budget,(len(g.nodes),budget)
    diag=support_diagnostics(g)
    diag['groups']={'expected':45,'actual':sum(len(have_groups(g,sex)) for sex in ('female','male'))}
    diag['identity_node_counts']=dict(Counter(s['identity'] for s in g.nodes))
    diag['identity_camera_node_fraction']=sum(s['camera'] in ID_CAMERAS for s in g.nodes)/budget
    return g,{'strategy':'camera_balanced_broad_context_products_all40_identity_base_pairs','roots':roots,'blocks':blocks,
              'coverage_context_patches':repairs,'diagnostics':diag,'seed':seed,
              'each_non_root_from_legal_single_axis_edge':True,'no_history_or_axis_repetition_ban':True,
              'camera_eligible_target_fraction':6/23,'latest_contract':'20261021 finite target support'}


def main():
    d=Domain();forbidden=set();summary={}
    for j,(split,budget) in enumerate([('train',2500),('test',500)]):
        g,meta=grow_balanced(d,budget,2026102150+j,forbidden)
        summary[split]=save_empty_graph(HERE/'wide_balanced'/split,g,meta)
        forbidden.update(g.keys)
        print('GRAPH_READY',split,len(g.nodes),len(g.edges),meta['diagnostics'],flush=True)
    write(HERE/'wide_balanced'/'SUMMARY.json',summary)

if __name__=='__main__':main()
