"""Offline compact Hamming-face graphs. Existing v1 legality remains authoritative."""
from __future__ import annotations
import argparse, copy, hashlib, itertools, random, sys
from collections import Counter
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'dataset_balanced_graph_20261022_v5'))
from build_balanced import (Domain,Graph,AXES,ID_CAMERAS,COLORS,legal_add,pools,
    support_diagnostics,save_empty_graph,read,write,token,groups,wardrobe_candidates,
    cover_train,used_core,catalog_core,core_assets)
LOCAL=('hair','hair_color','wardrobe','action','site')
TEST_LAYOUT='closed_full_shared_lineworld'
TRAIN_LAYOUT='wardrobe8'

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

def closed_wardrobes(d,sex,block_id,rng):
    specs=[[("female.pretty_dresses","skirts",('shirts','skirts')),("female.streetwear_collection","skirt_with_shirt",('shirts','skirts'))],
           [("male.jiving","default",('shirts','pants')),("male.summer","default",('shirts','pants'))],
           [("female.off_shoulder_dresses","default",('full_body',)),("female.shirts_pants_a_i","default",('shirts','pants'))],
           [("male.pop_style","default",('shirts','coats')),("male.jiving","default",('shirts','pants'))],
           [("female.summer_girl_four_colors","default",('shirts','pants')),("female.african_casual","pants_with_shirt",('shirts','pants'))],
           [("male.1920s_collection","full_body",('full_body',)),("male.mesh_it_up","default",('shirts','pants'))]]
    out=[]
    for family,group,slots in specs[block_id]:
        base=d.nc.sample_choice(sex,rng,family_id=family,group_id=group)
        singles=d.nc.single_piece_neighbors(sex,base)
        if len(slots)==1:
            choices=[r['choice'] for r in singles if r['slot']==slots[0]]
            rng.shuffle(choices)
            if len(choices)<3:raise RuntimeError(('not enough fullbody values',family))
            out.extend([base,*choices[:3]])
        else:
            a=rng.choice([r for r in singles if r['slot']==slots[0]])['choice']
            b=rng.choice([r for r in singles if r['slot']==slots[1]])['choice']
            both=copy.deepcopy(a);both['slot_choices'][slots[1]]=b['slot_choices'][slots[1]]
            both=d.nc.validate_choice(sex,both)['normalized_choice']
            out.extend([base,a,b,both])
    assert len(out)==8
    return out

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

def ensure_incoming_targets(g,rng):
    """Used values are insufficient: each catalog value needs a true edit in."""
    repairs=[];d=g.d
    for axis in ('identity','hair','hair_color','action','site','camera'):
        for sex in ('female','male'):
            for value in pools(d,sex)[axis]:
                if any(e['axis']==axis and g.nodes[v][axis]==value and
                       (axis not in ('identity','hair') or g.nodes[v]['sex']==sex)
                       for (u,v),e in g.edges.items()):continue
                anchors=[u for u,s in enumerate(g.nodes) if s['sex']==sex and axis in d.allowed_axes(s) and s[axis]!=value]
                rng.shuffle(anchors)
                anchors.sort(key=lambda u:-len(g.adj[u]))
                for u in anchors:
                    t=copy.deepcopy(g.nodes[u]);t[axis]=value
                    before=len(g.nodes);v=legal_add(g,u,t,axis)
                    if v is None:continue
                    added=list(range(before,len(g.nodes)))
                    # Pair the new value across an adjacent context so its
                    # edit-target node has a non-identity way to leave.
                    for other in ('hair','site','action','wardrobe','hair_color'):
                        if other==axis:continue
                        for w in g.adj[u].get(other,[]):
                            z=copy.deepcopy(g.nodes[w]);z[axis]=copy.deepcopy(value)
                            old=len(g.nodes);q=legal_add(g,v,z,other)
                            if q is not None:
                                added.extend(range(old,len(g.nodes)));break
                        else:continue
                        break
                    repairs.append({'axis':axis,'value':value,'source':u,'nodes':added});break
                else:raise RuntimeError(('incoming target impossible',axis,value))
    return repairs

def load_saved_graph(path,d,forbidden=None):
    g=Graph(d,forbidden)
    for row in read(path/'nodes.json'):
        p=row.get('created_by',{})
        v=g.add(row['state'],p.get('parent'),p.get('axis'))
        if v!=row['id']:raise RuntimeError('saved graph canonical mismatch')
    return g

def head_camera_escape(g,meta):
    """Trade ordinary whole-only leaves for complete head identity exits."""
    contexts={}
    for u,s in enumerate(g.nodes):
        if s['camera']!='front_head':continue
        sig=g.keys[u][1:]
        contexts.setdefault(sig,[]).append(u)
    lines=sorted(contexts.values(),key=lambda ids:(-len(ids),ids[0]))[:2]
    if any(len(line)<7 for line in lines):raise RuntimeError('expected two dense head identity lines')
    sources=[u for line in lines for u in line]
    children=Counter(p['parent'] for p in g.provenance if p.get('parent') is not None)
    candidates=[u for u,s in enumerate(g.nodes) if s['camera'] not in ID_CAMERAS and
                not g.d.singles(s) and not children[u] and
                s['wardrobe']['family_id'] in ('female.elise','male.dawkins')]
    candidates.sort(key=lambda u:(sum(map(len,g.adj[u].values())),u))
    if len(candidates)<len(sources):raise RuntimeError('not enough safe ordinary leaves')
    removed=set(candidates[:len(sources)]);new=Graph(g.d,g.forbidden);mapping={}
    for u,s in enumerate(g.nodes):
        if u in removed:continue
        p=g.provenance[u];parent=p.get('parent');axis=p.get('axis')
        if parent is None:v=new.add(copy.deepcopy(s))
        else:
            if parent not in mapping:raise RuntimeError('removed a provenance parent')
            v=legal_add(new,mapping[parent],copy.deepcopy(s),axis)
        if v is None:raise RuntimeError('retained graph introduction failed')
        mapping[u]=v
    copied=[]
    for u in sources:
        t=copy.deepcopy(g.nodes[u]);t['camera']='front_upper'
        v=legal_add(new,mapping[u],t,'camera')
        if v is None:raise RuntimeError('head camera escape failed')
        copied.append({'old_source':u,'source':mapping[u],'target':v})
    for block in meta.get('blocks',[]):
        block['roots']=[mapping[u] for u in block.get('roots',[]) if u in mapping]
        if 'slot_closure_nodes' in block:block['slot_closure_nodes']=[mapping[u] for u in block['slot_closure_nodes'] if u in mapping]
    meta['roots']=[mapping[u] for u in meta.get('roots',[]) if u in mapping]
    meta['head_camera_escape']={'removed_original_nodes':sorted(removed),'copied':copied,
        'removed_nodes_were_ordinary_camera_whole_only_provenance_leaves':True}
    if len(new.nodes)!=len(g.nodes):raise RuntimeError('escape changed node budget')
    return new,meta

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
    incoming_repairs=ensure_incoming_targets(g,rng) if train else []
    diag=graph_diagnostics(g)
    meta={'strategy':'shared_camera_two_axis_faces_with_dense_front_identity_faces', 'split':split,'seed':seed,
        'roots':[u for b in blocks for u in b['roots']],'blocks':blocks,'coverage_repairs':repairs,'incoming_target_repairs':incoming_repairs,
        'each_non_root_from_legal_single_axis_edge':True,'diagnostics':support_diagnostics(g),
        'compact_diagnostics':diag,'registered_edge_counts':diag['directed_axis_edges'],
        'core_assets_expected':len(catalog_core(d)),'core_assets_covered':len(used_core(g)), 'node_cap':5000 if train else 800}
    if len(g.nodes)>meta['node_cap']:raise RuntimeError(('node cap exceeded',split,len(g.nodes)))
    return g,meta

def add_cube(g,sex,cameras,slots,rng,train,block_id):
    d=g.d;widths=[2,3,4,3,2] if train else [2,2,3,2,2]
    closed=train and TRAIN_LAYOUT=='wardrobe8'
    if closed:widths=[2,2,8,2,2]
    four=not train and TEST_LAYOUT.startswith('four')
    if four:widths=[3,1,3,2,2] if block_id%2==0 else [1,3,3,2,2]
    palettes={a:palette_pick(d,g,sex,a,n,rng) for a,n in zip(LOCAL,widths) if a!='wardrobe'}
    palettes['wardrobe']=closed_wardrobes(d,sex,block_id,rng) if closed else wardrobes(d,sex,slots,rng,4 if train else 3)
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
    rank={v:i for i,v in enumerate([0,4,1,2,3,5,6,7])}
    rows.sort(key=lambda q:(sum(v!=0 for v in q),q[:2],rank[q[2]] if closed else q[2],q[3:]))
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
            for value in range(widths[k]) if k==2 else [0]:
                parent=list(q);parent[k]=value
                if tuple(parent) not in states:continue
                u=states[tuple(parent)];v=legal_add(g,u,t,LOCAL[k])
                if v is not None:states[q]=v;found=True;break
            if found:break
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
    ids=palette_pick(d,g,sex,'identity',3 if closed else (5 if train else (7 if four else 4)),rng)
    if s['identity'] not in ids:ids[-1]=s['identity']
    clones=[q for q in states if q[1]<2 and q[2]<2 and q[3]<2] if train else [q for q in states if q[2]==q[3]==0]
    if closed:clones=list(states)
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
    closure=[]
    if four and TEST_LAYOUT=='four_closure' and block_id in (0,1,3):
        count={0:2,1:2,3:1}[block_id]
        for camera in [c for c in cameras if c!='front_head'][:count]:
            zero=(0,)*5;one=(0,0,1,0,0)
            u=mapping[camera,zero];v=mapping[camera,one]
            base=g.nodes[u];other=g.nodes[v]
            options=[r for r in d.singles(base) if r['slot']=='shirts']
            if not options:raise RuntimeError(('closure has no shirt',sex,block_id))
            target=rng.choice(options)['choice'];shirt=target['slot_choices']['shirts']
            target2=copy.deepcopy(other['wardrobe']);target2['slot_choices']['shirts']=shirt
            target2=d.nc.validate_choice(sex,target2)['normalized_choice']
            for source,w in ((u,target),(v,target2)):
                t=copy.deepcopy(g.nodes[source]);t['wardrobe']=w
                z=legal_add(g,source,t,'wardrobe')
                if z is None:raise RuntimeError('closure rejected')
                closure.append(z)
    return {'id':block_id,'sex':sex,'roots':[root],'cameras':cameras,'template_nodes':len(states),'slot_closure_nodes':closure,
        'palette_sizes':dict(zip(LOCAL,widths)),'palettes':palettes,'identity_values':ids,'identity_clone_patterns':len(clones)}

def add_closed_test(g,sex,cameras,rng,block_id):
    d=g.d;omit=[3,4,0,1,3,4][block_id]
    widths=[2,2,5,2,2];widths[omit]=1
    palettes={a:palette_pick(d,g,sex,a,n,rng) for a,n in zip(LOCAL,widths) if a!='wardrobe'}
    specs=[('female.pretty_dresses','skirts',('shirts','skirts')),
           ('male.jiving','default',('shirts','pants')),
           ('female.off_shoulder_dresses','default',('full_body',)),
           ('male.pop_style','default',('shirts','coats')),
           ('female.shirts_pants_a_i','default',('shirts','pants')),
           ('male.1920s_collection','full_body',('full_body',))]
    family,group,slots=specs[block_id]
    base=d.nc.sample_choice(sex,rng,family_id=family,group_id=group)
    single=d.nc.single_piece_neighbors(sex,base)
    if len(slots)==1:
        choices=[r['choice'] for r in single if r['slot']==slots[0]];rng.shuffle(choices)
        ws=[base,*choices[:3]]
    else:
        a=rng.choice([r for r in single if r['slot']==slots[0]])['choice']
        b=rng.choice([r for r in single if r['slot']==slots[1]])['choice']
        both=copy.deepcopy(a);both['slot_choices'][slots[1]]=b['slot_choices'][slots[1]]
        ws=[base,a,b,d.nc.validate_choice(sex,both)['normalized_choice']]
    locked='female.elise' if sex=='female' else 'male.dawkins'
    ws.append(d.nc.sample_choice(sex,rng,family_id=locked));palettes['wardrobe']=ws
    first=next((c for c in cameras if c.endswith('full')),next(c for c in cameras if 'upper' not in c and c!='front_head'))
    for _ in range(10000):
        s=d.initial(rng);s.update(sex=sex,identity=palette_pick(d,g,sex,'identity',1,rng)[0],camera=first,
            **{a:copy.deepcopy(palettes[a][0]) for a in LOCAL})
        if all(d.valid({**s,'camera':c,'action':ac,'site':site}) for c in cameras for ac in palettes['action'] for site in palettes['site']):break
        palettes['action']=rng.sample(d.actions,widths[3]);palettes['site']=rng.sample(d.sites,widths[4])
    else:raise RuntimeError('closed test exclusions')
    active=[k for k in (0,1,3,4) if widths[k]>1]
    fixed=next(k for k in active if k not in (3,4))
    rows=[q for q in itertools.product(*(range(n) for n in widths)) if q[2]<4 or q[fixed]==0]
    rank={v:i for i,v in enumerate([0,4,1,2,3])}
    rows.sort(key=lambda q:(sum(v!=0 for v in q),q[:2],rank[q[2]],q[3:]))
    states={};root=None
    for q in rows:
        t=copy.deepcopy(s)
        for k,a in enumerate(LOCAL):t[a]=copy.deepcopy(palettes[a][q[k]])
        if not any(q):root=g.add(t);states[q]=root;continue
        for k in range(5):
            if not q[k]:continue
            for value in range(widths[k]) if k==2 else [0]:
                parent=list(q);parent[k]=value
                if tuple(parent) not in states:continue
                v=legal_add(g,states[tuple(parent)],t,LOCAL[k])
                if v is not None:states[q]=v;break
            if q in states:break
        else:raise RuntimeError(('closed test no parent',q))
    mapping={(first,q):u for q,u in states.items()}
    for camera in cameras:
        if camera==first:continue
        for q,u in states.items():
            if camera=='front_head' and (q[2] or q[3]):continue
            t=copy.deepcopy(g.nodes[u]);t['camera']=camera
            v=legal_add(g,u,t,'camera')
            if v is None:raise RuntimeError('closed test mirror')
            mapping[camera,q]=v
    ids=palette_pick(d,g,sex,'identity',7,rng)
    if s['identity'] not in ids:ids[-1]=s['identity']
    core=[]
    for value in (0,1):
        q=[0]*5;q[active[0]]=value;core.append(tuple(q))
    broad=[q for q in states if q[2]==0]
    extra=next(v for v in ids if v!=s['identity'])
    for camera in cameras:
        if camera not in ID_CAMERAS:continue
        for q in core:
            u=mapping[camera,q]
            for ident in ids:
                if ident==s['identity']:continue
                t=copy.deepcopy(g.nodes[u]);t['identity']=ident
                if legal_add(g,u,t,'identity') is None:raise RuntimeError('closed test identity')
        for q in broad:
            if q in core:continue
            u=mapping[camera,q];t=copy.deepcopy(g.nodes[u]);t['identity']=extra
            if legal_add(g,u,t,'identity') is None:raise RuntimeError('closed test broad identity')
    return {'id':block_id,'sex':sex,'roots':[root],'cameras':cameras,'template_nodes':len(states),
        'omitted_axis':LOCAL[omit],'wardrobe_slots':list(slots),'palette_sizes':dict(zip(LOCAL,widths)),
        'palettes':palettes,'identity_values':ids,'identity_clone_patterns':len(core)}

def add_closed_whole_test(g,sex,cameras,rng,block_id):
    d=g.d;single_only=block_id in (2,5)
    fifth=TEST_LAYOUT.endswith('_fifth');layout=TEST_LAYOUT.removesuffix('_fifth')
    shared_lines=layout.endswith('shared_lineworld')
    shared_base=layout.endswith('shared_baseworld') or shared_lines
    shared_world=layout.endswith('shared_world') or shared_base
    shared_ids=layout.endswith('shared_ids') or shared_world
    if shared_ids:
        cache=g.__dict__.setdefault('shared_test_identities',{})
        if sex not in cache:cache[sex]=palette_pick(d,g,sex,'identity',7,rng)
    ws=closed_wardrobes(d,sex,block_id,rng)[:4]
    if single_only:ws=ws[:2 if fifth else 3]
    locked='female.elise' if sex=='female' else 'male.dawkins'
    ws.append(d.nc.sample_choice(sex,rng,family_id=locked));nw=len(ws)
    palettes={a:palette_pick(d,g,sex,a,2,rng) for a in LOCAL if a!='wardrobe'};palettes['wardrobe']=ws
    worlds=g.__dict__.setdefault('shared_test_worlds',{})
    if shared_world and sex in worlds:
        for a in LOCAL:
            if a!='wardrobe':
                if shared_base:
                    base_value=worlds[sex][a][0]
                    alternate=next(v for v in palettes[a] if v!=base_value)
                    palettes[a]=[base_value,alternate]
                    if shared_lines and block_id in (0,1,2,3) and a==('hair_color' if sex=='female' else 'hair'):
                        palettes[a]=copy.deepcopy(worlds[sex][a])
                else:palettes[a]=copy.deepcopy(worlds[sex][a])
        ws[-1]=copy.deepcopy(worlds[sex]['locked_whole'])
    omit={c:[3,4,0,1,3,4][block_id] for c in cameras}
    if block_id==5:
        for c,k in zip(cameras,(0,1,4,4,0)):omit[c]=k
    original_omit=dict(omit);partial=None
    if fifth and single_only:
        for c in (cameras[:2] if block_id==2 else cameras[:1]):omit[c]=None
        if block_id==5:partial=cameras[-1]
    first=next((c for c in cameras if c.endswith('full')),next(c for c in cameras if 'upper' not in c and c!='front_head'))
    for _ in range(10000):
        s=d.initial(rng);s.update(sex=sex,identity=palette_pick(d,g,sex,'identity',1,rng)[0],camera=first,
            **{a:copy.deepcopy(palettes[a][0]) for a in LOCAL})
        if shared_ids:s['identity']=cache[sex][0]
        if all(d.valid({**s,'camera':c,'action':ac,'site':site}) for c in (d.cameras if shared_world else cameras) for ac in palettes['action'] for site in palettes['site']):break
        if shared_base and sex in worlds:
            for a,values in (('action',d.actions),('site',d.sites)):
                bv=worlds[sex][a][0];palettes[a]=[bv,rng.choice([v for v in values if v!=bv])]
        else:palettes['action']=rng.sample(d.actions,2);palettes['site']=rng.sample(d.sites,2)
    else:raise RuntimeError('complete whole test exclusions')
    if shared_world and sex not in worlds:
        worlds[sex]={a:copy.deepcopy(palettes[a]) for a in LOCAL if a!='wardrobe'}
        worlds[sex]['locked_whole']=copy.deepcopy(ws[-1])
    mapping={};root=None;rows_by_camera={};zero=(0,)*5
    wardrank={v:i for i,v in enumerate([0,nw-1,*range(1,nw-1)])}
    for camera in [first,*[c for c in cameras if c!=first]]:
        widths=[2,2,nw,2,2]
        if omit[camera] is not None:widths[omit[camera]]=1
        rows=list(itertools.product(*(range(n) for n in widths)))
        if camera==partial:
            axis=original_omit[camera];vary=next(k for k in (0,1,3,4) if k!=axis)
            for value in (0,1):
                for ward in range(nw):
                    q=[0]*5;q[axis]=1;q[vary]=value;q[2]=ward;rows.append(tuple(q))
        if camera=='front_head':rows=[q for q in rows if q[2]==(nw-1 if shared_world else 0) and q[3]==0]
        rows.sort(key=lambda q:(sum(v!=0 for v in q),q[:2],wardrank[q[2]],q[3:]))
        rows_by_camera[camera]=rows;states={}
        for q in rows:
            t=copy.deepcopy(s);t['camera']=camera
            for k,a in enumerate(LOCAL):t[a]=copy.deepcopy(palettes[a][q[k]])
            camera_zero=(0,0,nw-1,0,0) if camera=='front_head' and shared_world else zero
            if q==camera_zero:
                if root is None:root=g.add(t);v=root
                else:v=legal_add(g,mapping[first,q],t,'camera')
                if v is None:raise RuntimeError('complete whole camera root')
                states[q]=v;mapping[camera,q]=v;continue
            for k in range(5):
                if not q[k]:continue
                for value in range(widths[k]) if k==2 else [0]:
                    parent=list(q);parent[k]=value
                    if tuple(parent) not in states:continue
                    v=legal_add(g,states[tuple(parent)],t,LOCAL[k])
                    if v is not None:states[q]=v;mapping[camera,q]=v;break
                if q in states:break
            else:raise RuntimeError(('complete whole test no parent',camera,q))
    ids=list(cache[sex]) if shared_ids else palette_pick(d,g,sex,'identity',7,rng)
    if s['identity'] not in ids:ids[-1]=s['identity']
    extra=next(v for v in ids if v!=s['identity'])
    for camera in cameras:
        if camera not in ID_CAMERAS:continue
        active=(1 if sex=='female' else 0) if shared_world else next(k for k in (0,1,3,4) if k!=omit[camera])
        clone_ward=nw-1 if shared_world else 0
        core=[]
        for value in (0,1):q=[0]*5;q[active]=value;q[2]=clone_ward;core.append(tuple(q))
        for q in core:
            for ident in ids:
                if ident==s['identity']:continue
                u=mapping[camera,q];t=copy.deepcopy(g.nodes[u]);t['identity']=ident
                if legal_add(g,u,t,'identity') is None:raise RuntimeError('complete whole identity')
        for q in rows_by_camera[camera]:
            if q[2]!=clone_ward or q in core:continue
            if fifth and q[original_omit[camera]]:continue
            u=mapping[camera,q];t=copy.deepcopy(g.nodes[u]);t['identity']=extra
            if legal_add(g,u,t,'identity') is None:raise RuntimeError('complete whole broad identity')
    return {'id':block_id,'sex':sex,'roots':[root],'cameras':cameras,'omitted_axis_by_camera':{c:LOCAL[k] if k is not None else 'none_all_five_local_axes' for c,k in omit.items()},
        'palettes':palettes,'identity_values':ids,'formal_all_slots_and_both_modes_supported_in_base_cube':True}

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
    if not train and TEST_LAYOUT.startswith('closed_full'):
        camera_groups=[['front_head','front_full','side_full','rear_three_quarter_full'],
                       ['front_upper','front_three_quarter_full','back_full'],[],
                       ['dolly_out_front','side_upper'],['high_full','low_full'],[]]
        occupied={c for rows in camera_groups for c in rows}
        remaining=[c for c in d.cameras if c not in occupied and c!='dolly_in_front']
        camera_groups[2]=['dolly_in_front',*remaining[:4]];camera_groups[5]=remaining[4:]
    for j,((sex,slots),cs) in enumerate(zip(specs,camera_groups)):
        if not train and TEST_LAYOUT.startswith('closed_full'):block=add_closed_whole_test(g,sex,cs,rng,j)
        elif not train and TEST_LAYOUT=='closed_four':block=add_closed_test(g,sex,cs,rng,j)
        else:block=add_cube(g,sex,cs,slots,rng,train,j)
        blocks.append(block)
        print('CUBE',split,j,len(g.nodes),flush=True)
    candidates={s:wardrobe_candidates(d,s,rng) for s in ('female','male')}
    repairs=compact_cover(g,rng,candidates) if train else []
    incoming_repairs=ensure_incoming_targets(g,rng) if train else []
    diag=graph_diagnostics(g)
    meta={'strategy':'complete_five_axis_products_with_front_identity_subproducts', 'split':split,'seed':seed,
        'roots':[u for b in blocks for u in b['roots']],'blocks':blocks,'coverage_repairs':repairs,'incoming_target_repairs':incoming_repairs,
        'each_non_root_from_legal_single_axis_edge':True,'diagnostics':support_diagnostics(g),
        'compact_diagnostics':diag,'registered_edge_counts':diag['directed_axis_edges'],
        'core_assets_expected':len(catalog_core(d)),'core_assets_covered':len(used_core(g)), 'node_cap':5000 if train else 800}
    if len(g.nodes)>meta['node_cap']:raise RuntimeError(('node cap exceeded',split,len(g.nodes)))
    return g,meta

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--variant',default='graph_candidate');ap.add_argument('--seed',type=int,default=2026102207);ap.add_argument('--repair-source');ap.add_argument('--head-escape',action='store_true');args=ap.parse_args()
    if not args.variant.startswith('graph_'):raise ValueError('candidate must start with graph_')
    target=HERE/args.variant
    if any((target/split/'nodes.json').exists() for split in ('train','test')):
        raise FileExistsError('Saved graph candidates are immutable; choose a fresh --variant name.')
    target.mkdir(parents=True,exist_ok=True)
    source=Path(__file__).read_text(encoding='utf-8')
    snapshot=source.replace('HERE=Path(__file__).resolve().parent\n','HERE=Path(__file__).resolve().parents[1]\n')
    (target/'builder_snapshot.py').write_text(snapshot,encoding='utf-8')
    write(target/'builder_identity.json',{'original_builder_sha256':hashlib.sha256(source.encode()).hexdigest(),
        'seed':args.seed,'repair_source':args.repair_source,'head_escape':args.head_escape,
        'snapshot_note':'Only HERE adjusted for relocation; generation recipe exact.'})
    d=Domain();forbidden=set();report={}
    for j,split in enumerate(('train','test')):
        if args.repair_source:
            source=HERE/args.repair_source/split
            g=load_saved_graph(source,d,forbidden)
            meta=copy.deepcopy(read(source/'metrics.json')['construction'])
            meta['repaired_from']=args.repair_source
            meta['incoming_target_repairs']=ensure_incoming_targets(g,random.Random(args.seed+j)) if split=='train' else []
            if split=='test' and args.head_escape:g,meta=head_camera_escape(g,meta)
            meta['compact_diagnostics']=graph_diagnostics(g)
            meta['diagnostics']=support_diagnostics(g)
            meta['registered_edge_counts']=meta['compact_diagnostics']['directed_axis_edges']
        else:g,meta=grow(d,split,args.seed+j,forbidden)
        report[split]=save_empty_graph(HERE/args.variant/split,g,meta);forbidden.update(g.keys)
        write(HERE/args.variant/split/'capacity.json',meta['compact_diagnostics'])
        print('GRAPH_DONE',split,len(g.nodes),meta['registered_edge_counts'],flush=True)
    write(HERE/args.variant/'graph_summary.json',report)

if __name__=='__main__':main()
