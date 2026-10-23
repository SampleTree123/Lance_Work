"""Coverage-first legal edit expansion; offline, no UE or render side effects."""
from __future__ import annotations
import argparse, copy, hashlib, json, random, sys, time
from collections import Counter
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
sys.path.insert(0,str(BASE/'dataset_local_support_20261021_v3'/'blocks'))
from build_blocks import Domain,Graph,AXES,ID_CAMERAS,COLORS,add_block,legal_add,pools,represented,support_diagnostics,save_empty_graph,read,write,token
CORE={'shirts','coats','pants','skirts','full_body'}
CORE_CACHE={}

def core_assets(d,sex,w):
    key=(sex,token(w))
    if key not in CORE_CACHE:CORE_CACHE[key]=set(d.nc.core_asset_ids(sex,w))
    return CORE_CACHE[key]

def groups(d,sex):
    return [(f,g) for f in d.cat['sexes'][sex]['families'] for g in f['groups']]

def used_core(g):
    return set().union(*(core_assets(g.d,s['sex'],s['wardrobe']) for s in g.nodes)) if g.nodes else set()

def catalog_core(d):
    out={}
    for sex in ('female','male'):
        for f,g in groups(d,sex):
            for a in g['required_assets']+g['optional_assets']+sum(g['slot_options'].values(),[]):
                if a['slot'] in CORE:out[a['asset_id']]={'sex':sex,'family':f['family_id'],'group':g['group_id'],'slot':a['slot'],'label':a['label']}
    return out

def pick(d,g,a,sex,rng,exclude=()):
    rows=[v for v in pools(d,sex)[a] if v not in exclude]
    counts=Counter(s[a] for s in g.nodes if a not in ('identity','hair') or s['sex']==sex)
    rng.shuffle(rows)
    return min(rows,key=lambda v:counts[v])

def wardrobe_candidates(d,sex,rng):
    """Every legal core value gets a realizable outfit, without full products."""
    rows=[];seen=set()
    def add(w):
        w=d.nc.validate_choice(sex,w)['normalized_choice'];key=token(w)
        if key not in seen:seen.add(key);rows.append(w)
    for f,g in groups(d,sex):
        base=d.nc.sample_choice(sex,rng,family_id=f['family_id'],group_id=g['group_id']);add(base)
        for slot,assets in g['slot_options'].items():
            if slot not in CORE:continue
            for a in assets:
                w=copy.deepcopy(base);w['slot_choices'][slot]=a['asset_id'];add(w)
        for a in g['optional_assets']:
            if a['slot'] in CORE:
                w=copy.deepcopy(base)
                if a['asset_id'] not in w['optional_asset_ids']:w['optional_asset_ids'].append(a['asset_id'])
                add(w)
    return rows

def choose_wardrobes(d,g,sex,rng,candidates,width):
    covered=used_core(g);seen_groups={(s['wardrobe']['family_id'],s['wardrobe']['group_id']) for s in g.nodes}
    rows=list(candidates);rng.shuffle(rows)
    rows.sort(key=lambda w:(-len(core_assets(d,sex,w)-covered),(w['family_id'],w['group_id']) in seen_groups))
    # A real single + another family, preferably with its own single, supports both modes.
    for base in rows:
        singles=d.nc.single_piece_neighbors(sex,base)
        if singles:break
    out=[copy.deepcopy(base)]
    if singles:out.append(copy.deepcopy(max(singles,key=lambda r:len(core_assets(d,sex,r['choice'])-covered))['choice']))
    others=[w for w in rows if w['family_id']!=base['family_id']]
    if width==3:
        fixed=[w for w in others if not d.nc.single_piece_neighbors(sex,w)]
        other=(fixed or others)[0]
    else:other=others[0]
    out.append(copy.deepcopy(other))
    if width==4:
        sing=d.nc.single_piece_neighbors(sex,other)
        if sing:out.append(copy.deepcopy(max(sing,key=lambda r:len(core_assets(d,sex,r['choice'])-covered))['choice']))
        else:
            for w in others:
                if w['family_id']!=other['family_id']:out.append(copy.deepcopy(w));break
    return out

def patch(g,u,value,axis,budget,rng,clones=2):
    if len(g.nodes)>=budget:return []
    t=copy.deepcopy(g.nodes[u]);t[axis]=copy.deepcopy(value)
    old=len(g.nodes);v=legal_add(g,u,t,axis)
    if v is None:return []
    added=list(range(old,len(g.nodes)))
    neighbors=[(a,w) for a,vs in g.adj[u].items() if a!=axis for w in vs]
    rng.shuffle(neighbors)
    for a,w in neighbors:
        if len(added)>=clones+1 or len(g.nodes)>=budget:break
        tt=copy.deepcopy(g.nodes[w]);tt[axis]=copy.deepcopy(value)
        before=len(g.nodes);z=legal_add(g,v,tt,a)
        if z is not None:added.extend(range(before,len(g.nodes)))
    return added

def cover_train(g,budget,rng,candidates):
    d=g.d;repairs=[]
    # Resolve missing complete core pieces and all legal family/group labels.
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
        options.sort(key=lambda x:-x[0]);score,sex,w=options[0]
        anchors=[i for i,s in enumerate(g.nodes) if s['sex']==sex and s['wardrobe']['family_id']!=w['family_id'] and s['camera']!='front_head']
        rng.shuffle(anchors)
        for u in anchors:
            added=patch(g,u,w,'wardrobe',budget,rng,2)
            if added:repairs.append({'axis':'wardrobe','source':u,'nodes':added});break
        else:raise RuntimeError(('core coverage cannot fit',len(g.nodes),len(missing)))
    for axis in ('identity','hair','hair_color','action','site','camera'):
        for sex in ('female','male'):
            for value in pools(d,sex)[axis]:
                have=represented(g,axis,sex if axis in ('identity','hair') else None)
                if value in have:continue
                anchors=[i for i,s in enumerate(g.nodes) if s['sex']==sex and axis in d.allowed_axes(s)]
                rng.shuffle(anchors)
                for u in anchors:
                    added=patch(g,u,value,axis,budget,rng,2)
                    if added:repairs.append({'axis':axis,'source':u,'nodes':added});break
                else:raise RuntimeError(('value coverage cannot fit',axis,value))
    return repairs

def repair_single_support(g,budget,rng):
    repairs=[]
    for u,s in enumerate(list(g.nodes)):
        singles=g.d.singles(s)
        if not singles or 'wardrobe' not in g.d.allowed_axes(s):continue
        if any(g.edges[u,v]['mode']=='single_piece' for v in g.adj[u].get('wardrobe',[])):continue
        if len(g.nodes)>=budget:break
        rng.shuffle(singles)
        # Prefer a target that shares the source's other-axis neighborhoods.
        for row in singles:
            t=copy.deepcopy(s);t['wardrobe']=row['choice']
            v=legal_add(g,u,t,'wardrobe')
            if v is not None:
                repairs.append({'source':u,'target':v,'slot':row['slot']});break
    return repairs

def grow(d,split,seed,forbidden=None):
    rng=random.Random(seed);g=Graph(d,forbidden);train=split=='train';budget=5000 if train else 800
    candidates={s:wardrobe_candidates(d,s,rng) for s in ('female','male')}
    blocks=[];roots=[]
    count=16 if train else 4
    for j in range(count):
        sex=('female','male')[j%2]
        ws=choose_wardrobes(d,g,sex,rng,candidates[sex],4 if train else 3)
        for _ in range(500):
            s=d.initial(rng)
            s.update(sex=sex,identity=pick(d,g,'identity',sex,rng),hair=pick(d,g,'hair',sex,rng),
                     hair_color=pick(d,g,'hair_color',sex,rng),action=pick(d,g,'action',sex,rng),site=pick(d,g,'site',sex,rng),
                     wardrobe=ws[0],camera=['front_upper','dolly_in_front','dolly_out_front'][j%3])
            if d.valid(s) and d.canonical(s) not in g.forbidden:break
        else:raise RuntimeError('root exhausted')
        u=g.add(s);roots.append(u)
        palettes={a:[s[a],pick(d,g,a,sex,rng,[s[a]])] for a in AXES if a not in ('wardrobe','camera')}
        others=[c for c in d.cameras if c not in ID_CAMERAS];rng.shuffle(others)
        counts=Counter(t['camera'] for t in g.nodes)
        other=min(others,key=lambda c:counts[c])
        palettes['camera']=[s['camera'],other];palettes['wardrobe']=ws
        block=add_block(g,u,list(AXES),rng,min(budget,len(g.nodes)+255 if train else len(g.nodes)+191),j,2,palettes)
        blocks.append(block)
        print('BLOCK',split,j,len(g.nodes),flush=True)
    repairs=cover_train(g,budget,rng,candidates) if train else []
    single_repairs=repair_single_support(g,budget,rng)
    # Small missing-target repairs must not remove broad edit choices from the core graph.
    diag=support_diagnostics(g)
    meta={'strategy':'seven_axis_legal_products_with_real_single_and_whole_wardrobe_targets_then_core_coverage',
          'split':split,'seed':seed,'roots':roots,'blocks':blocks,'coverage_repairs':repairs,'single_support_repairs':single_repairs,'diagnostics':diag,
          'core_assets_expected':len(catalog_core(d)),'core_assets_covered':len(used_core(g)),
          'registered_edge_counts':dict(Counter(e['axis'] for e in g.edges.values())),
          'node_cap':budget,'each_non_root_from_legal_single_axis_edge':True}
    return g,meta

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--variant',default='candidate_a');ap.add_argument('--seed',type=int,default=2026102201);args=ap.parse_args()
    d=Domain();fresh=d.nc.build_catalog()
    write(HERE/'catalog_current.json',fresh)
    # Compare domain IDs against the immutable input that existing helpers consume.
    assert {s:len(v['identities']) for s,v in fresh['sexes'].items()}=={s:len(v['identities']) for s,v in d.cat['sexes'].items()}
    for key in ('actions','cameras','sites'):
        assert {r['id'] for r in fresh[key]}=={r['id'] for r in d.cat[key]},('changed domain requires normalization',key)
    write(HERE/'catalog_snapshot.json',d.cat)
    forbidden=set();report={}
    for j,split in enumerate(('train','test')):
        g,meta=grow(d,split,args.seed+j,forbidden)
        report[split]=save_empty_graph(HERE/args.variant/split,g,meta)
        forbidden.update(g.keys)
        print('GRAPH_DONE',split,len(g.nodes),meta['registered_edge_counts'],meta['core_assets_covered'],flush=True)
    write(HERE/args.variant/'graph_summary.json',report)

if __name__=='__main__':main()
