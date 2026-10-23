"""Experimental offline edit-first graph builder. No UE calls, no media jobs."""
from __future__ import annotations
import argparse, copy, hashlib, json, math, random, sys, time
from collections import Counter, defaultdict
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
AXES = ('identity', 'hair', 'hair_color', 'wardrobe', 'action', 'camera', 'site')
ID_CAMERAS = {'front_head', 'front_upper', 'dolly_in_front', 'dolly_out_front'}
UPPER = {'front_upper','side_upper','back_upper','front_three_quarter_upper','rear_three_quarter_upper'}
COLORS = ['original','black','gold','silver_white','red','blue','pink']

def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write(path, obj): Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
def token(obj): return json.dumps(obj, sort_keys=True, separators=(',',':'),ensure_ascii=False)
def digest(obj): return hashlib.sha256(token(obj).encode()).hexdigest()[:24]
def weighted(rng, values, weights): return rng.choices(values, weights=weights, k=1)[0]
def dist(values):
    a=sorted(values); n=len(a); total=sum(a)
    return {'n':n,'sum':total,'mean':total/n if n else 0,'p95':a[math.ceil(.95*n)-1] if n else 0,'max':max(a,default=0),'zeros':a.count(0),
            'gini':2*sum((i+1)*v for i,v in enumerate(a))/(n*total)-(n+1)/n if total else 0}

class Domain:
    def __init__(self):
        import normalize_catalog as nc
        self.nc=nc; self.cat=nc.load_catalog()
        self.ids={s:[r['id'] for r in self.cat['sexes'][s]['identities']] for s in ('female','male')}
        self.hairs={s:[r.get('hair_id',r.get('id')) for r in self.cat['sexes'][s]['hairs']] for s in self.ids}
        self.actions=[r if isinstance(r,str) else r.get('id',r.get('motion_id')) for r in self.cat['actions']]
        self.cameras=[r if isinstance(r,str) else r.get('id',r.get('camera_id')) for r in self.cat['cameras']]
        self.sites=[r if isinstance(r,str) else r.get('id',r.get('site_id')) for r in self.cat['sites']]
        self.exclusions=set()
        for r in self.cat['exclusions']:
            self.exclusions.add((r.get('site_id',r.get('site')),r['action_id'],r['camera_id'],r.get('aspect','landscape')))
        self.wcache={}; self.scache={}; self.ucache={}
    def wkey(self,s):
        k=(s['sex'],token(s['wardrobe']))
        if k not in self.wcache:self.wcache[k]=token(self.nc.wardrobe_key(s['sex'],s['wardrobe']))
        return self.wcache[k]
    def upperkey(self,s):
        k=(s['sex'],token(s['wardrobe']))
        if k not in self.ucache:self.ucache[k]=token(self.nc.upper_asset_ids(s['sex'],s['wardrobe']))
        return self.ucache[k]
    def canonical(self,s):
        return tuple(self.wkey(s) if a=='wardrobe' else s[a] for a in AXES)
    def valid(self,s):
        return (s['site'],s['action'],s['camera'],s['aspect']) not in self.exclusions
    def singles(self,s):
        k=(s['sex'],token(s['wardrobe']))
        if k not in self.scache:self.scache[k]=self.nc.single_piece_neighbors(s['sex'],s['wardrobe'])
        rows=self.scache[k]
        if s['camera']=='front_head':return []
        if s['camera'] in UPPER:
            rows=[r for r in rows if self.upperkey({**s,'wardrobe':r['choice']}) != self.upperkey(s)]
        return rows
    def initial(self,rng):
        for _ in range(1000):
            sex=rng.choice(['female','male'])
            s={'sex':sex,'identity':rng.choice(self.ids[sex]),'hair':rng.choice(self.hairs[sex]),'hair_color':rng.choice(COLORS),
               'action':rng.choice(self.actions),'site':rng.choice(self.sites),'camera':weighted(rng,self.cameras,[1.5 if c in ID_CAMERAS else 1 for c in self.cameras]),
               'wardrobe':self.nc.sample_choice(sex,rng),'aspect':'landscape'}
            if self.valid(s):return s
        raise RuntimeError('initial state exhausted')
    def allowed_axes(self,s):
        return [a for a in AXES if (a!='identity' or s['camera'] in ID_CAMERAS) and (a not in ('action','wardrobe') or s['camera']!='front_head')]
    def mutate(self,s,rng,axis=None):
        axes=self.allowed_axes(s)
        if axis is None: axis=weighted(rng,axes,[2 if a=='identity' else 1 for a in axes])
        if axis not in axes:return None
        t=copy.deepcopy(s)
        if axis=='wardrobe':
            singles=self.singles(s)
            if singles and rng.random()<.5:
                slot=rng.choice(sorted(set(r['slot'] for r in singles)))
                t['wardrobe']=copy.deepcopy(rng.choice([r for r in singles if r['slot']==slot])['choice'])
            else:
                for _ in range(100):
                    w=self.nc.sample_whole_change(s['sex'],s['wardrobe'],rng)
                    t['wardrobe']=w
                    if self.wkey(t)!=self.wkey(s) and (s['camera'] not in UPPER or self.upperkey(t)!=self.upperkey(s)):break
                else:return None
        else:
            vals={'identity':self.ids[s['sex']], 'hair':self.hairs[s['sex']], 'hair_color':COLORS,
                  'action':self.actions,'camera':self.cameras,'site':self.sites}[axis]
            vals=[v for v in vals if v!=s[axis]]
            if axis in ('action','camera','site'):vals=[v for v in vals if self.valid({**s,axis:v})]
            if not vals:return None
            t[axis]=weighted(rng,vals,[1.5 if axis=='camera' and v in ID_CAMERAS else 1 for v in vals])
        if self.canonical(t)==self.canonical(s) or not self.valid(t):return None
        return t,axis
    def edge(self,s,t,axis):
        if s['sex']!=t['sex'] or axis not in self.allowed_axes(s) or not self.valid(t):return None
        if axis!='wardrobe':return {'axis':axis,'mode':'attribute'}
        sw,tw=s['wardrobe'],t['wardrobe']
        if s['camera'] in UPPER and self.upperkey(s)==self.upperkey(t):return None
        if sw['family_id']!=tw['family_id']:
            # Shoes alone, or same physical clothes via different family labels, are not an edit.
            if self.nc.core_asset_ids(s['sex'],sw)==self.nc.core_asset_ids(t['sex'],tw):return None
            return {'axis':axis,'mode':'whole_outfit'}
        if sw['group_id']!=tw['group_id']:return None
        for r in self.singles(s):
            if self.wkey({**s,'wardrobe':r['choice']})==self.wkey(t):return {'axis':axis,'mode':'single_piece','slot':r['slot']}
        return None

class Graph:
    def __init__(self,d,forbidden=None):
        self.d=d; self.nodes=[]; self.keys=[]; self.known={}; self.buckets=defaultdict(list)
        self.adj=[]; self.edges={}; self.provenance=[]; self.forbidden=forbidden or set()
    def add(self,s,parent=None,axis=None):
        key=self.d.canonical(s)
        if key in self.forbidden:return None
        if key in self.known:return self.known[key]
        i=len(self.nodes); self.nodes.append(s); self.keys.append(key);self.known[key]=i;self.adj.append(defaultdict(list));self.provenance.append({'parent':parent,'axis':axis})
        for k,a in enumerate(AXES):
            sig=(a,key[:k]+key[k+1:])
            for j in self.buckets[sig]:
                for u,v in ((i,j),(j,i)):
                    e=self.d.edge(self.nodes[u],self.nodes[v],a)
                    if e is not None:self.edges[u,v]=e;self.adj[u][a].append(v)
            self.buckets[sig].append(i)
        return i

def grow(d,budget,seed,policy,forbidden=None):
    rng=random.Random(seed);g=Graph(d,forbidden);roots=max(4,budget//25); proposals=Counter(); attempts=0
    for _ in range(roots):
        while g.add(d.initial(rng)) is None:pass
    while len(g.nodes)<budget and attempts<budget*40:
        attempts+=1;u=rng.randrange(len(g.nodes));s=g.nodes[u];m=d.mutate(s,rng)
        if not m:continue
        t,a=m;proposals[a]+=1;v=g.add(t,u,a)
        if v is None:continue
        if policy=='squares' and rng.random()<.75 and len(g.nodes)+2<=budget:
            axes=[x for x in d.allowed_axes(s) if x!=a]
            b=weighted(rng,axes,[2 if x=='identity' else 1 for x in axes]);m2=d.mutate(s,rng,b)
            if not m2:continue
            w=m2[0]; z=copy.deepcopy(t);z[b]=copy.deepcopy(w[b])
            if not d.valid(z) or b not in d.allowed_axes(t) or d.edge(t,z,b) is None:continue
            j=g.add(w,u,b)
            if j is not None:g.add(z,v,b)
    if len(g.nodes)!=budget:raise RuntimeError(f'growth {len(g.nodes)}/{budget}')
    return g,{'roots':roots,'attempts':attempts,'proposal_axes':dict(proposals)}

def quotas(total):
    fork=total//3;linear=total-fork; out=[]
    for typ,n,weights in [('linear',linear,[.25]*4),('fork',fork,[.1,.2,.35,.35])]:
        counts=[round(n*w) for w in weights];counts[-1]+=n-sum(counts)
        for L,c in zip(range(2,6),counts):out.extend([(typ,L)]*c)
    return out

def choose_existing_start(g,rng,policy='hierarchy'):
    # A hierarchy over represented states, not new random independent full configurations.
    ids=list(range(len(g.nodes)))
    if policy=='uniform_nodes': return rng.choice(ids)
    fields=('sex','camera','identity','site','action','hair','hair_color','family','group') if policy=='camera_first' else ('sex','identity','site','action','camera','hair','hair_color','family','group')
    for field in fields:
        groups=defaultdict(list)
        for i in ids:
            s=g.nodes[i];value=s['wardrobe'][field+'_id'] if field in ('family','group') else s[field]
            groups[value].append(i)
        vals=sorted(groups)
        v=weighted(rng,vals,[1.5 if field=='camera' and x in ID_CAMERAS else 1 for x in vals])
        ids=groups[v]
        if len(ids)==1:break
    return rng.choice(ids)

def sample(g,total,seed,start_policy='hierarchy'):
    rng=random.Random(seed); schedule=quotas(total);rng.shuffle(schedule);out=[];seen=set();reject=Counter()
    start_cache=[choose_existing_start(g,rng,start_policy) for _ in range(max(1000,total//2))]
    for typ,L in schedule:
        ft=rng.randrange(2,L+1) if typ=='fork' else None
        fp=rng.randrange(ft-1) if ft else None
        # Fix fork round/source before retries; uniqueness must not bias those choices.
        for attempt in range(3000):
            history=[rng.choice(start_cache)];steps=[]
            for t in range(1,L+1):
                p=fp if t==ft else t-1;u=history[p];opts=g.adj[u]
                axes=[a for a in AXES if opts.get(a)]
                if not axes:break
                a=weighted(rng,axes,[2 if a=='identity' else 1 for a in axes]);vs=opts[a]
                if a=='wardrobe':
                    modes=defaultdict(list)
                    for v in vs:modes[g.edges[u,v]['mode']].append(v)
                    mode=rng.choice(sorted(modes));vs=modes[mode]
                    if mode=='single_piece':
                        slots=sorted(set(g.edges[u,v]['slot'] for v in vs));sl=rng.choice(slots)
                        vs=[v for v in vs if g.edges[u,v]['slot']==sl]
                    else:
                        fams=sorted(set(g.nodes[v]['wardrobe']['family_id'] for v in vs));fam=rng.choice(fams)
                        vs=[v for v in vs if g.nodes[v]['wardrobe']['family_id']==fam]
                        groups=sorted(set(g.nodes[v]['wardrobe']['group_id'] for v in vs));group=rng.choice(groups)
                        vs=[v for v in vs if g.nodes[v]['wardrobe']['group_id']==group]
                v=weighted(rng,vs,[1.5 if a=='camera' and g.nodes[v]['camera'] in ID_CAMERAS else 1 for v in vs])
                steps.append({'source_position':p,'source':u,'target':v,**g.edges[u,v]});history.append(v)
            if len(steps)!=L:reject['dead_end']+=1;continue
            signature=(history[0],tuple((r['source_position'],r['target']) for r in steps))
            if signature in seen:reject['duplicate_structure']+=1;continue
            seen.add(signature);out.append({'id':f'session_{len(out):06d}','kind':typ,'length':L,'fork_round':ft,'history':history,'steps':steps});break
        else:reject[f'unfilled_{typ}_{L}']+=1
    return out,dict(reject)

def stats(g,sessions):
    nodeuse=Counter();edgeuse=Counter();axes=Counter();modes=Counter();starts=Counter(); forkround=Counter();forkparents=Counter();forkimpact=Counter();missing=Counter();caps=Counter();revisits=0;sameaxis=0;mono=0
    for s in sessions:
        nodeuse.update(s['history']);starts[g.nodes[s['history'][0]]['camera']]+=1
        revisits+=len(set(s['history']))<len(s['history']);seq=[r['axis'] for r in s['steps']];mono+=len(set(seq))==1;sameaxis+=any(a==b for a,b in zip(seq,seq[1:]))
        for t,r in enumerate(s['steps'],1):
            u,v=r['source'],r['target'];axes[r['axis']]+=1;edgeuse[u,v]+=1
            if r['axis']=='wardrobe':modes[r['mode']]+=1
            for a in g.d.allowed_axes(g.nodes[u]):
                caps[a]+=1
                if not g.adj[u].get(a):missing[a]+=1
            if s['fork_round']==t:
                forkround[f'L{s["length"]}_t{t}']+=1;forkparents['root' if r['source_position']==0 else 'intermediate']+=1
                latest=g.nodes[s['history'][t-1]];src=g.nodes[u];tar=g.nodes[v]
                preserve=[a for a in AXES if a!=r['axis']]
                differs=any(g.d.canonical(latest)[AXES.index(a)]!=g.d.canonical(src)[AXES.index(a)] for a in preserve)
                forkimpact['different_preserved_state' if differs else 'same_result_possible_from_latest']+=1
    coverage={}
    for a in ('sex',)+AXES:
        counts=Counter((s['wardrobe']['family_id'] if a=='wardrobe' else s[a]) for s in g.nodes)
        coverage[a]={'distinct':len(counts),'counts':dict(counts)}
    total=sum(axes.values())
    return {'nodes':len(g.nodes),'sessions':len(sessions),'registered_edges':len(g.edges),'used_edges':len(edgeuse),'unused_nodes':len(g.nodes)-len(nodeuse),
            'edit_steps':total,'axis_counts':dict(axes),'axis_percent':{a:round(100*axes[a]/total,4) for a in AXES},'wardrobe_modes':dict(modes),
            'node_use':dist([nodeuse[i] for i in range(len(g.nodes))]),'edge_use':dist(list(edgeuse.values())),
            'length_kind':dict(Counter(f'{s["kind"]}_{s["length"]}' for s in sessions)), 'fork_rounds':dict(forkround),'fork_parent':dict(forkparents),'fork_effect':dict(forkimpact),
            'sessions_with_revisited_node':revisits,'sessions_with_consecutive_same_axis':sameaxis,'single_axis_sessions':mono,
            'coverage':coverage,'start_camera_counts':dict(starts),'legal_axis_missing_from_graph_count':dict(missing),'legal_axis_opportunities':dict(caps)}

def save_graph(path,g,sessions,meta):
    path.mkdir(parents=True,exist_ok=True)
    nodes=[{'id':i,'canonical_id':'node_'+digest(g.keys[i]),'state':s,'created_by':g.provenance[i]} for i,s in enumerate(g.nodes)]
    write(path/'nodes.json',nodes);write(path/'edges.json',[{'source':u,'target':v,**e} for (u,v),e in sorted(g.edges.items())])
    with (path/'sessions.jsonl').open('w',encoding='utf-8') as f:
        for s in sessions:f.write(json.dumps(s,ensure_ascii=False,separators=(',',':'))+'\n')
    result=stats(g,sessions);result['construction']=meta;write(path/'metrics.json',result)
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--policy',choices=['walk','squares'],default='squares');ap.add_argument('--scale',choices=['smoke','full'],default='smoke');ap.add_argument('--seed',type=int,default=20261021);ap.add_argument('--start-policy',choices=['hierarchy','camera_first','uniform_nodes'],default='hierarchy');args=ap.parse_args()
    d=Domain(); target=HERE/(args.scale+'_'+args.policy+('' if args.start_policy=='hierarchy' else '_'+args.start_policy)); used=set(); report={};start=time.time()
    specs=[('train',2500,12000),('test',500,2400)] if args.scale=='full' else [('train',180,80),('test',80,20)]
    for j,(split,budget,total) in enumerate(specs):
        g,meta=grow(d,budget,args.seed+j,args.policy,used);ss,reject=sample(g,total,args.seed+100+j,args.start_policy);meta['sampling_rejections']=reject;meta['start_policy']=args.start_policy
        report[split]=save_graph(target/split,g,ss,meta);used.update(g.keys)
        print(split, len(g.nodes),len(ss),report[split]['axis_percent'],flush=True)
    report['elapsed_seconds']=time.time()-start;write(target/'SUMMARY.json',report)
    print('done',target,round(report['elapsed_seconds'],2),flush=True)
if __name__=='__main__':main()
