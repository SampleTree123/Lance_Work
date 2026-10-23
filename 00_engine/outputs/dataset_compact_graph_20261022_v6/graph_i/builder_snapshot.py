"""Offline compact Hamming-face graphs. Existing v1 legality remains authoritative."""
from __future__ import annotations
import argparse, copy, hashlib, itertools, random, sys
from collections import Counter
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE.parent/'dataset_balanced_graph_20261022_v5'))
from build_balanced import (Domain,Graph,AXES,ID_CAMERAS,COLORS,legal_add,pools,
    support_diagnostics,save_empty_graph,read,write,token,groups,wardrobe_candidates,
    cover_train,used_core,catalog_core,core_assets)
LOCAL=('hair','hair_color','wardrobe','action','site')
TEST_LAYOUT='four'

def select_rows(d,sex,slot,rng,exclude=()):
    candidates=[]
    for f,group in groups(d,sex):
        if f['family_id'] in exclude:continue
        for _ in range(3):
            w=d.nc.sample_choice(sex,rng,family_id=f['family_id'],group_id=group['group_id'])
            rows=[r for r in d.nc.single_piece_neighbors(sex,w) if r['slot']==slot]
            if rows:candidates.append((w,rows));break
    if not candidates:raise RuntimeError(('no legal single',sex,slot))
    base,rows=rng.choice(candidates)
    return copy.deepcopy(base),copy.deepcopy(rng.choice(rows)['choice'])

def wardrobes(d,sex,slots,rng,width):
    a,b=select_rows(d,sex,slots[0],rng)
    c,e=select_rows(d,sex,slots[-1],rng,(a['family_id'],))
    return [a,b,c,e][:width]

def palette_pick(d,g,sex,a,width,rng):
    rows=list(pools(d,sex)[a]);rng.shuffle(rows)
    counts=Counter(s[a] for s in g.nodes if a not in ('identity','hair') or s['sex']==sex)
    rows.sort(key=lambda v:counts[v])
    return rows[:width]

def patterns(widths,train):
    # All one-axis lines, then selected two-axis faces, with canonical parents.
    zero=(0,)*len(LOCAL);out=[zero]
    for k,n in enumerate(widths):
        for value in range(1,n):
            q=list(zero);q[k]=value;out.append(tuple(q))
    pairs=list(itertools.combinations(range(5),2)) if train else [(0,2),(1,3),(3,4),(1,4)]
    for i,j in pairs:
        for x in range(1,widths[i]):
            for y in range(1,widths[j]):
                q=list(zero);q[i]=x;q[j]=y;out.append(tuple(q))
    if not train:
        # One extra hair value crossed with the full color line; this balances
        # the three non-wardrobe axes without spending another complete face.
        for y in range(1,widths[1]):
            q=list(zero);q[0]=1;q[1]=y;out.append(tuple(q))
    return out

def add_template(g,sex,cameras,ws,rng,train,block_id):
    d=g.d;widths=[3,3,4,4,3] if train else [3,3,4,3,3]
    palettes={a:palette_pick(d,g,sex,a,n,rng) for a,n in zip(LOCAL,widths) if a!='wardrobe'}
    palettes['wardrobe']=ws
    # A valid entire face set avoids sparse camera exclusions breaking the template.
    first=next((c for c in cameras if c.endswith('full')),next(c for c in cameras if c!='front_head'))
    for _ in range(10000):
        s=d.initial(rng);s.update(sex=sex,identity=palette_pick(d,g,sex,'identity',1,rng)[0],camera=first,
            **{a:copy.deepcopy(palettes[a][0]) for a in LOCAL})
        if all(d.valid({**s,'camera':c,'action':ac,'site':site}) for c in cameras for ac in palettes['action'] for site in palettes['site']):break
        palettes['action']=rng.sample(d.actions,widths[3]);palettes['site']=rng.sample(d.sites,widths[4])
    else:raise RuntimeError('no exclusion-free local template')
    if d.canonical(s) in g.forbidden:raise RuntimeError('forbidden root; choose a new seed')
    root=g.add(s);states={(0,)*5:root};roots=[root]
    for q in patterns(widths,train)[1:]:
        k=max(i for i,v in enumerate(q) if v);parent=list(q);parent[k]=0
        u=states[tuple(parent)];t=copy.deepcopy(s)
        for j,a in enumerate(LOCAL):t[a]=copy.deepcopy(palettes[a][q[j]])
        v=legal_add(g,u,t,LOCAL[k])
        if v is None:raise RuntimeError(('template illegal',q,LOCAL[k]))
        states[q]=v
    mapping={(first,q):u for q,u in states.items()}
    for camera in cameras:
        if camera==first:continue
        for q,u in states.items():
            t=copy.deepcopy(g.nodes[u]);t['camera']=camera
            v=legal_add(g,u,t,'camera')
            if v is None:raise RuntimeError(('camera mirror illegal',camera,q))
            mapping[camera,q]=v
    # Dense identity lines on useful hair/color/site faces, not isolated head leaves.
    identity_values=palette_pick(d,g,sex,'identity',5 if train else 4,rng)
    if s['identity'] not in identity_values:identity_values[-1]=s['identity']
    clone_patterns=[q for q in states if q[2]==q[3]==0 and (train or sum(v!=0 for v in q)<=1)]
    for camera in cameras:
        if camera not in ID_CAMERAS:continue
        for q in clone_patterns:
            u=mapping[camera,q]
            for value in identity_values:
                if value==s['identity']:continue
                t=copy.deepcopy(g.nodes[u]);t['identity']=value
                if legal_add(g,u,t,'identity') is None:raise RuntimeError('identity clone rejected')
    return {'id':block_id,'sex':sex,'roots':roots,'cameras':cameras,'template_nodes':len(states),
        'palette_sizes':dict(zip(LOCAL,widths)),'wardrobe_slots':sorted({r['slot'] for w in ws for r in d.nc.single_piece_neighbors(sex,w)}),
        'identity_clone_patterns':len(clone_patterns),'identity_values':identity_values,'palettes':palettes}

def graph_diagnostics(g):
    cameras={}
    for c in g.d.cameras:
        ids=[u for u,s in enumerate(g.nodes) if s['camera']==c]
        cameras[c]={'nodes':len(ids),'nonisolated':sum(bool(g.adj[u]) for u in ids),
            'outgoing':sum(sum(map(len,g.adj[u].values())) for u in ids),
            'by_axis':dict(Counter(a for u in ids for a,vs in g.adj[u].items() for v in vs)),
            'max_distinct_outgoing':max((sum(map(len,g.adj[u].values())) for u in ids),default=0)}
    incoming=set()
    for (u,v),e in g.edges.items():
        if e['axis']=='wardrobe':incoming.update(core_assets(g.d,g.nodes[v]['sex'],g.nodes[v]['wardrobe'])-core_assets(g.d,g.nodes[u]['sex'],g.nodes[u]['wardrobe']))
    return {'by_camera':cameras,'directed_axis_edges':dict(Counter(e['axis'] for e in g.edges.values())),
        'single_slot_edges':dict(Counter(e['slot'] for e in g.edges.values() if e.get('mode')=='single_piece')),
        'core_changed_in':len(incoming),'missing_core_changed_in':sorted(set(catalog_core(g.d))-incoming)}

def compact_cover(g,rng,candidates):
    """Cover each catalog target with one genuine atomic introduction."""
    d=g.d;records=[]
    while True:
        missing=set(catalog_core(d))-used_core(g)
        have={(s['sex'],s['wardrobe']['family_id'],s['wardrobe']['group_id']) for s in g.nodes}
        options=[]
        for sex in ('female','male'):
            for w in candidates[sex]:
                gain=len(core_assets(d,sex,w)&missing)
                group_gain=(sex,w['family_id'],w['group_id']) not in have
                if gain or group_gain:options.append((gain+group_gain,sex,w))
        if not options:break
        _,sex,w=max(options,key=lambda r:r[0])
        anchors=[u for u,s in enumerate(g.nodes) if s['sex']==sex and s['camera'].endswith('full') and s['wardrobe']['family_id']!=w['family_id']]
        rng.shuffle(anchors)
        for u in anchors:
            t=copy.deepcopy(g.nodes[u]);t['wardrobe']=copy.deepcopy(w)
            v=legal_add(g,u,t,'wardrobe')
            if v is not None:records.append({'axis':'wardrobe','source':u,'nodes':[v]});break
        else:raise RuntimeError('cannot cover core')
    for axis in ('identity','hair','hair_color','action','site','camera'):
        for sex in ('female','male'):
            for value in pools(d,sex)[axis]:
                if any(s[axis]==value and (axis not in ('identity','hair') or s['sex']==sex) for s in g.nodes):continue
                anchors=[u for u,s in enumerate(g.nodes) if s['sex']==sex and axis in d.allowed_axes(s)]
                rng.shuffle(anchors)
                for u in anchors:
                    t=copy.deepcopy(g.nodes[u]);t[axis]=value
                    v=legal_add(g,u,t,axis)
                    if v is not None:records.append({'axis':axis,'source':u,'nodes':[v]});break
                else:raise RuntimeError(('cannot cover value',axis,value))
    return records

def grow_faces(d,split,seed,forbidden=None):
    rng=random.Random(seed);g=Graph(d,forbidden);train=split=='train';blocks=[]
    # Every camera has both sexes in train. Test partitions cameras across four
    # templates to spend its 800-node budget on useful edit choices.
    cams=list(d.cameras)
    assignments=[]
    slot_pairs={'female':[('skirts','full_body'),('coats','shirts')], 'male':[('pants','shirts'),('coats','full_body')]}
    if train:
        for sex in ('female','male'):
            for j in range(2):assignments.append((sex,cams[j::2],slot_pairs[sex][j]))
    else:
        # Front identities split evenly between genders; each quarter gets a front.
        fronts=['front_head','front_upper','dolly_in_front','dolly_out_front']
        rest=[c for c in cams if c not in fronts]
        for j,(sex,pair) in enumerate([('female',('skirts','full_body')),('male',('pants','shirts')),('female',('coats','shirts')),('male',('coats','full_body'))]):
            assignments.append((sex,[fronts[j],*rest[j::4]],pair))
    for j,(sex,cs,slots) in enumerate(assignments):
        ws=wardrobes(d,sex,slots,rng,4)
        blocks.append(add_template(g,sex,cs,ws,rng,train,j))
        print('BLOCK',split,j,len(g.nodes),flush=True)
    candidates={s:wardrobe_candidates(d,s,rng) for s in ('female','male')}
    repairs=compact_cover(g,rng,candidates) if train else []
    diag=graph_diagnostics(g)
    meta={'strategy':'shared_camera_two_axis_faces_with_dense_front_identity_faces', 'split':split,'seed':seed,
        'roots':[u for b in blocks for u in b['roots']],'blocks':blocks,'coverage_repairs':repairs,
        'each_non_root_from_legal_single_axis_edge':True,'diagnostics':support_diagnostics(g),
        'compact_diagnostics':diag,'registered_edge_counts':diag['directed_axis_edges'],
        'core_assets_expected':len(catalog_core(d)),'core_assets_covered':len(used_core(g)), 'node_cap':5000 if train else 800}
    if len(g.nodes)>meta['node_cap']:raise RuntimeError(('node cap exceeded',split,len(g.nodes)))
    return g,meta

def add_cube(g,sex,cameras,slots,rng,train,block_id):
    d=g.d;widths=[2,3,4,3,2] if train else [2,2,3,2,2]
    four=not train and TEST_LAYOUT=='four'
    if four:widths=[3,1,3,2,2] if block_id%2==0 else [1,3,3,2,2]
    palettes={a:palette_pick(d,g,sex,a,n,rng) for a,n in zip(LOCAL,widths) if a!='wardrobe'}
    palettes['wardrobe']=wardrobes(d,sex,slots,rng,4 if train else 3)
    if not train:
        # A whole-outfit destination without legal single-piece alternatives
        # has no fictitious 50% single-mode opportunity in the audit.
        locked='female.elise' if sex=='female' else 'male.dawkins'
        palettes['wardrobe'][2]=d.nc.sample_choice(sex,rng,family_id=locked)
    first=next((c for c in cameras if c.endswith('full')),next(c for c in cameras if c!='front_head'))
    for _ in range(10000):
        s=d.initial(rng);s.update(sex=sex,identity=palette_pick(d,g,sex,'identity',1,rng)[0],camera=first,
            **{a:copy.deepcopy(palettes[a][0]) for a in LOCAL})
        if all(d.valid({**s,'camera':c,'action':ac,'site':site}) for c in cameras for ac in palettes['action'] for site in palettes['site']):break
        palettes['action']=rng.sample(d.actions,widths[3]);palettes['site']=rng.sample(d.sites,widths[4])
    else:raise RuntimeError('cube exclusions')
    rows=list(itertools.product(*(range(n) for n in widths)))
    if not train and not four:
        # A complete binary cube supplies all five axes. Six wardrobe/color
        # corners fund eight third-wardrobe states with real whole edits.
        rows=[q for q in rows if
            (q[2]<2 and not(q[2]==q[1]==1 and (q[0],q[3],q[4]) not in ((0,0,0),(1,1,1))))
            or (q[2]==2 and q[1]==0)]
    rows.sort(key=lambda q:(sum(v!=0 for v in q),q))
    states={};root=None
    for q in rows:
        t=copy.deepcopy(s)
        for k,a in enumerate(LOCAL):t[a]=copy.deepcopy(palettes[a][q[k]])
        if not any(q):
            root=g.add(t)
            if root is None:raise RuntimeError('forbidden cube root')
            states[q]=root;continue
        # Wardrobe-zero parents survive all selected-corner removals.
        found=False
        for k in sorted(range(5),key=lambda k:k!=2):
            if not q[k]:continue
            parent=list(q);parent[k]=0
            if tuple(parent) not in states:continue
            u=states[tuple(parent)];v=legal_add(g,u,t,LOCAL[k])
            if v is not None:states[q]=v;found=True;break
        if not found:raise RuntimeError(('no atomic cube parent',q))
    mapping={(first,q):u for q,u in states.items()}
    for camera in cameras:
        if camera==first:continue
        for q,u in states.items():
            if not train and camera=='front_head' and (q[2] or q[3]):continue
            t=copy.deepcopy(g.nodes[u]);t['camera']=camera
            v=legal_add(g,u,t,'camera')
            if v is None:raise RuntimeError('cube mirror rejected')
            mapping[camera,q]=v
    ids=palette_pick(d,g,sex,'identity',5 if train else (7 if four else 4),rng)
    if s['identity'] not in ids:ids[-1]=s['identity']
    clones=[q for q in states if q[1]<2 and q[2]<2 and q[3]<2] if train else [q for q in states if q[2]==q[3]==0]
    broad_clones=clones
    if four:
        active=0 if widths[0]>1 else 1
        clones=[q for q in clones if q[active]<2 and q[4]==0]
    for camera in cameras:
        if camera not in ID_CAMERAS:continue
        for q in clones:
            u=mapping[camera,q]
            for ident in ids:
                if ident==s['identity']:continue
                t=copy.deepcopy(g.nodes[u]);t['identity']=ident
                if legal_add(g,u,t,'identity') is None:raise RuntimeError('cube identity failed')
        if four:
            extra_id=next(v for v in ids if v!=s['identity'])
            for q in broad_clones:
                if q in clones:continue
                u=mapping[camera,q];t=copy.deepcopy(g.nodes[u]);t['identity']=extra_id
                if legal_add(g,u,t,'identity') is None:raise RuntimeError('four-axis identity failed')
        elif not train:
            # Extra color lines on two identities keep the small test color
            # domain from requiring pervasive cap-four reuse.
            third=next(c for c in COLORS if c not in palettes['hair_color'])
            for hair in range(2):
                q=(hair,0,0,0,0);u=mapping[camera,q]
                for ident in ids[:2]:
                    base=copy.deepcopy(g.nodes[u]);base['identity']=ident
                    source=g.known[d.canonical(base)]
                    t=copy.deepcopy(base);t['hair_color']=third
                    if legal_add(g,source,t,'hair_color') is None:raise RuntimeError('test color failed')
    return {'id':block_id,'sex':sex,'roots':[root],'cameras':cameras,'template_nodes':len(states),
        'palette_sizes':dict(zip(LOCAL,widths)),'palettes':palettes,'identity_values':ids,'identity_clone_patterns':len(clones)}

def grow(d,split,seed,forbidden=None):
    rng=random.Random(seed);g=Graph(d,forbidden);train=split=='train';blocks=[]
    # One gender per camera, alternating six separate wardrobe networks. There
    # is no requirement to render both genders in every individual camera.
    specs=[('female',('skirts','shirts')),('male',('pants','shirts')),
           ('female',('full_body','coats')),('male',('coats','shirts')),
           ('female',('shirts','pants')),('male',('full_body','pants'))]
    fronts=['front_head','front_upper','dolly_in_front','dolly_out_front']
    rest=[c for c in d.cameras if c not in fronts]
    camera_groups=[[] for _ in specs]
    for j,c in enumerate(fronts):camera_groups[j].append(c)
    for j,c in enumerate(rest):camera_groups[j%6].append(c)
    for j,((sex,slots),cs) in enumerate(zip(specs,camera_groups)):
        blocks.append(add_cube(g,sex,cs,slots,rng,train,j))
        print('CUBE',split,j,len(g.nodes),flush=True)
    candidates={s:wardrobe_candidates(d,s,rng) for s in ('female','male')}
    repairs=compact_cover(g,rng,candidates) if train else []
    diag=graph_diagnostics(g)
    meta={'strategy':'complete_five_axis_products_with_front_identity_subproducts', 'split':split,'seed':seed,
        'roots':[u for b in blocks for u in b['roots']],'blocks':blocks,'coverage_repairs':repairs,
        'each_non_root_from_legal_single_axis_edge':True,'diagnostics':support_diagnostics(g),
        'compact_diagnostics':diag,'registered_edge_counts':diag['directed_axis_edges'],
        'core_assets_expected':len(catalog_core(d)),'core_assets_covered':len(used_core(g)), 'node_cap':5000 if train else 800}
    if len(g.nodes)>meta['node_cap']:raise RuntimeError(('node cap exceeded',split,len(g.nodes)))
    return g,meta

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--variant',default='graph_a');ap.add_argument('--seed',type=int,default=2026102207);args=ap.parse_args()
    if not args.variant.startswith('graph_'):raise ValueError('candidate must start with graph_')
    target=HERE/args.variant
    target.mkdir(parents=True,exist_ok=True)
    source=Path(__file__).read_text(encoding='utf-8')
    snapshot=source.replace('HERE=Path(__file__).resolve().parent\n','HERE=Path(__file__).resolve().parents[1]\n')
    (target/'builder_snapshot.py').write_text(snapshot,encoding='utf-8')
    write(target/'builder_identity.json',{'original_builder_sha256':hashlib.sha256(source.encode()).hexdigest(),
        'seed':args.seed,'snapshot_note':'Only HERE adjusted for relocation; generation recipe exact.'})
    d=Domain();forbidden=set();report={}
    for j,split in enumerate(('train','test')):
        g,meta=grow(d,split,args.seed+j,forbidden)
        report[split]=save_empty_graph(HERE/args.variant/split,g,meta);forbidden.update(g.keys)
        write(HERE/args.variant/split/'capacity.json',meta['compact_diagnostics'])
        print('GRAPH_DONE',split,len(g.nodes),meta['registered_edge_counts'],flush=True)
    write(HERE/args.variant/'graph_summary.json',report)

if __name__=='__main__':main()
