"""Identity-balanced local blocks; independent contexts and equal node budgets."""
from __future__ import annotations
import copy,random,time
from collections import Counter
from pathlib import Path
from build_blocks import *

def balanced_root_cameras(d,n,rng):
    """Stratify the four-camera group, then balance cameras within each group."""
    front=sorted(ID_CAMERAS);other=[c for c in d.cameras if c not in ID_CAMERAS]
    nfront=round(n*(len(front)*1.5)/(len(other)+len(front)*1.5))
    rng.shuffle(front);rng.shuffle(other)
    rows=[front[i%len(front)] for i in range(nfront)]+[other[i%len(other)] for i in range(n-nfront)]
    rng.shuffle(rows)
    return rows

def grow_diverse(d,budget,seed,forbidden=None,dense=False,camera_balanced=False):
    rng=random.Random(seed);g=Graph(d,forbidden);identities=[(sex,i) for sex in ('female','male') for i in d.ids[sex]]
    caps={identity:budget//len(identities)+(j<budget%len(identities)) for j,(_,identity) in enumerate(identities)}
    roots={};blocks=[];repairs=[]
    context_offset=seed-202610217
    root_cameras=balanced_root_cameras(d,len(identities),rng) if camera_balanced else None
    for j,(sex,identity) in enumerate(identities):
        local=d.ids[sex].index(identity);family=pools(d,sex)['wardrobe'][local%len(pools(d,sex)['wardrobe'])]
        for _ in range(1000):
            s=d.initial(rng);s.update(sex=sex,identity=identity,hair=d.hairs[sex][local%len(d.hairs[sex])],
                  hair_color=COLORS[(j+3*context_offset)%7],action=d.actions[(j+5*context_offset+_)%len(d.actions)],site=d.sites[(j+11*context_offset+_//25)%len(d.sites)],
                  camera=root_cameras[j] if camera_balanced else sorted(ID_CAMERAS)[j%4],wardrobe=d.nc.sample_choice(sex,rng,family_id=family))
            if d.valid(s):
                u=g.add(s)
                if u is not None:roots[identity]=u;break
        else:raise RuntimeError('root exhausted')
    # Each identity gets one incoming clone and one outgoing identity edge. The
    # clone holds the complete context of its source, and is not an unrelated seed.
    for sex in ('female','male'):
        ids=d.ids[sex]
        for j,identity in enumerate(ids):
            u=roots[identity]
            if camera_balanced and g.nodes[u]['camera'] not in ID_CAMERAS:continue
            t=copy.deepcopy(g.nodes[u]);t['identity']=ids[(j+1)%len(ids)]
            v=legal_add(g,u,t,'identity');repairs.append({'source':u,'target':v,'axis':'identity'})
    # Allocate missing cameras across identities, preserving balanced per-ID caps.
    for j,camera in enumerate(c for c in d.cameras if c not in represented(g,'camera')):
        for offset in range(len(identities)):
            identity=identities[(j+offset)%len(identities)][1];u=roots[identity]
            t=copy.deepcopy(g.nodes[u]);t['camera']=camera
            v=legal_add(g,u,t,'camera')
            if v is not None:repairs.append({'source':u,'target':v,'axis':'camera'});break
    # Male has more families than registered identities; place remaining families
    # across separate contexts before consuming each identity's local node budget.
    for sex in ('female','male'):
        missing=[f for f in pools(d,sex)['wardrobe'] if f not in represented(g,'wardrobe',sex)]
        for j,family in enumerate(missing):
            for identity in d.ids[sex][j:]+d.ids[sex][:j]:
                u=roots[identity];s=g.nodes[u]
                if 'wardrobe' not in d.allowed_axes(s):continue
                t=forced_target(d,s,'wardrobe',family,rng);v=legal_add(g,u,t,'wardrobe')
                if v is not None:repairs.append({'source':u,'target':v,'axis':'wardrobe'});break
    for j,(sex,identity) in enumerate(identities):
        root=roots[identity]
        def count():return sum(s['identity']==identity for s in g.nodes)
        remaining=caps[identity]-count()
        axes=['hair','hair_color','wardrobe','action','camera','site']
        # Rotate dimensions independently of the identity edit sampling weight.
        rng.shuffle(axes);axes.sort(key=lambda a:sum(a in b['axes'] for b in blocks))
        allowed=[a for a in axes if a in d.allowed_axes(g.nodes[root])]
        if remaining>=26:
            chosen=allowed[:3]
            b=add_block(g,root,chosen,rng,len(g.nodes)+remaining,len(blocks),3)
            if b['new_nodes']:blocks.append(b)
        elif remaining>=8:
            chosen=allowed[:2]
            # For the small test blocks cap wardrobe to 3 states: base, an exact
            # single when possible, and another family. Single semantics unchanged.
            b=add_block(g,root,chosen,rng,len(g.nodes)+min(remaining,8),len(blocks),3)
            if b['new_nodes']:blocks.append(b)
        attempts=0
        while count()<caps[identity] and attempts<1000:
            attempts+=1
            ids=[i for i,s in enumerate(g.nodes) if s['identity']==identity]
            rng.shuffle(ids);u=min(ids[:80],key=lambda i:len(g.adj[i]))
            s=g.nodes[u];allowed=[a for a in d.allowed_axes(s) if a!='identity'];rng.shuffle(allowed)
            allowed.sort(key=lambda a:(bool(g.adj[u].get(a)),sum(a in g.adj[i] for i in ids)))
            if dense and caps[identity]-count()>=8:
                # Complete further crossing blocks replace one-dimensional
                # random tails. Anchor low-support states, including incoming
                # identity clones, so identity transitions can lead onwards.
                remaining=caps[identity]-count();chosen=allowed[:2]
                values={a:palette(d,s,a,rng,3) for a in chosen}
                needed=1
                for values_a in values.values():needed*=len(values_a)
                if needed-1>remaining and 'wardrobe' in chosen:
                    chosen=[a for a in allowed if a!='wardrobe'][:2]
                    values={a:palette(d,s,a,rng,3) for a in chosen};needed=9
                if len(chosen)==2 and needed-1<=remaining:
                    b=add_block(g,u,chosen,rng,len(g.nodes)+remaining,len(blocks),3,values)
                    if b['new_nodes']:
                        blocks.append(b);continue
            # Add whole additional triangle if room permits, else a single edge.
            a=allowed[0];m=d.mutate(s,rng,a)
            if dense and 'wardrobe' in allowed and d.singles(s):
                modes={g.edges[u,v]['mode'] for v in g.adj[u].get('wardrobe',[])}
                if 'single_piece' not in modes:
                    m=(copy.deepcopy(s),'wardrobe');m[0]['wardrobe']=copy.deepcopy(rng.choice(d.singles(s))['choice']);a='wardrobe'
                elif 'whole_outfit' not in modes:
                    m=(copy.deepcopy(s),'wardrobe');m[0]['wardrobe']=d.nc.sample_whole_change(s['sex'],s['wardrobe'],rng);a='wardrobe'
            if m:
                v=legal_add(g,u,m[0],a)
                if v is not None:repairs.append({'source':u,'target':v,'axis':a})
    if len(g.nodes)!=budget:raise RuntimeError(f'{len(g.nodes)}/{budget}')
    diagnostics=support_diagnostics(g)
    diagnostics['identity_node_counts']=dict(Counter(s['identity'] for s in g.nodes))
    diagnostics['root_camera_counts']=dict(Counter(g.nodes[u]['camera'] for u in roots.values()))
    diagnostics['all_node_camera_counts']=dict(Counter(s['camera'] for s in g.nodes))
    diagnostics['identity_camera_node_fraction']=sum(s['camera'] in ID_CAMERAS for s in g.nodes)/len(g.nodes)
    diagnostics['identity_supported_axes']={identity:dict(Counter(a for i,s in enumerate(g.nodes) if s['identity']==identity for a in AXES if g.adj[i].get(a))) for _,identity in identities}
    return g,{'strategy':'40_independent_context_roots_equal_per_identity_caps_nonidentity_local_blocks',
              'seed':seed,'dense_tail_blocks':dense,'camera_balanced_roots':camera_balanced,'roots':roots,'identity_caps':caps,'blocks':blocks,'repairs':repairs,'diagnostics':diagnostics,
              'identity_block_dimensions_not_weighted':True,'each_non_root_from_legal_single_axis_edge':True}

def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--dense',action='store_true');ap.add_argument('--camera-balanced',action='store_true');args=ap.parse_args()
    if args.camera_balanced:args.dense=True
    d=Domain();used=set();report={};target=HERE/('camera_balanced' if args.camera_balanced else 'dense_diverse' if args.dense else 'diverse');start=time.time()
    for j,(split,budget,total) in enumerate([('train',2500,12000),('test',500,2400)]):
        g,meta=grow_diverse(d,budget,202610217+j,used,args.dense,args.camera_balanced)
        report[split]=save_empty_graph(target/split,g,meta)
        print('GRAPH_READY',split,len(g.nodes),len(g.edges),str(target/split),flush=True)
        ss,reject=sample(g,total,202610317+j,'uniform_nodes');meta['preliminary_sampling']='v1 graph-neighbor diagnostic; final sampler owned by parent';meta['sampling_rejections']=reject
        report[split]=save_graph(target/split,g,ss,meta);used.update(g.keys)
        print('SAMPLED',split,len(ss),report[split]['axis_percent'],flush=True)
    report['elapsed_seconds']=time.time()-start;write(target/'SUMMARY.json',report)
if __name__=='__main__':main()
