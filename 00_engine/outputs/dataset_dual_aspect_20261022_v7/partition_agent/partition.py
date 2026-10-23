"""Reproducible chain-level dual-aspect hypergraph partition experiment.

Run: python partition.py --quick (baseline); python partition.py (all candidates).
Input files are immutable. Aspect 0=landscape; 1=portrait. Each original session
is assigned exactly once and retains its original history/steps elsewhere.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, time, warnings
from pathlib import Path
import numpy as np
warnings.filterwarnings('ignore',message='A NumPy version')

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parents[1]/'dataset_compact_graph_20261022_v6'/'selected_seed1'
ASPECTS=('landscape','portrait')

def dump(path, obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def load(split):
    nodes=json.loads((SOURCE/split/'nodes.json').read_text(encoding='utf-8'))
    chains=[json.loads(x) for x in (SOURCE/split/'sessions.jsonl').read_text(encoding='utf-8').splitlines()]
    byid={n['id']:n for n in nodes}
    assert list(byid)==list(range(len(nodes))), 'Requires compact zero-based node ids'
    sets=[np.array(sorted(set(c['history'])),dtype=np.int32) for c in chains]
    # Chains with identical node sets are moved together. This removes the
    # energy barrier caused by duplicate and reversed histories.
    bundles={}
    for i,ids in enumerate(sets): bundles.setdefault(tuple(ids),[]).append(i)
    groups=[np.array(v,dtype=np.int32) for v in bundles.values()]
    gn=[sets[g[0]] for g in groups]
    mask=json.loads((HERE/'portrait_eligibility_mask.json').read_text(encoding='utf-8'))['splits'][split]
    forbidden=set(mask['portrait_forbidden_chain_ids'])
    forced=np.array([any(chains[i]['id'] in forbidden for i in g) for g in groups])
    assert mask['node_count']==len(nodes) and mask['session_count']==len(chains)
    keys=[('total','all')]
    for c in chains:
        st=byid[c['history'][0]]['state']
        keys += [('sex',st['sex']),('camera',st['camera']),('sex_camera',st['sex']+'|'+st['camera'])]
        keys += [('axis',s['axis']) for s in c['steps']]
        keys += [('edit',s['axis']+'|'+s.get('mode','')) for s in c['steps']]
    keys=sorted(set(keys)); ki={k:i for i,k in enumerate(keys)}
    features=np.zeros((len(groups),len(keys)),dtype=np.float64)
    for gi,g in enumerate(groups):
        for i in g:
            c=chains[i]; st=byid[c['history'][0]]['state']
            for key in [('total','all'),('sex',st['sex']),('camera',st['camera']),('sex_camera',st['sex']+'|'+st['camera'])]: features[gi,ki[key]]+=1
            for s in c['steps']:
                features[gi,ki[('axis',s['axis'])]]+=1
                features[gi,ki[('edit',s['axis']+'|'+s.get('mode',''))]]+=1
    totals=features.sum(axis=0)
    return dict(nodes=nodes,chains=chains,sets=sets,groups=groups,gn=gn,features=features,keys=keys,totals=totals,forced=forced,forbidden=forbidden)

def spectral(d,seed):
    n=len(d['nodes']); rows=[]; cols=[]; weights=[]
    # Normalized clique expansion supplies only a warm start; optimization
    # below directly charges each shared node once, regardless of degree.
    for ids,g in zip(d['gn'],d['groups']):
        for a in ids:
            for b in ids:
                if a!=b:
                    rows.append(a); cols.append(b); weights.append(len(g)/(len(ids)-1))
    parent=list(range(n))
    def find(i):
        while parent[i]!=i: parent[i]=parent[parent[i]]; i=parent[i]
        return i
    for aa,bb in zip(rows,cols): parent[find(aa)]=find(bb)
    _,labels=np.unique([find(i) for i in range(n)],return_inverse=True)
    nc=int(labels.max())+1
    rows=np.array(rows); cols=np.array(cols); weights=np.array(weights)
    degree=np.bincount(rows,weights=weights,minlength=n)
    roots=np.sqrt(np.maximum(degree,1)); inv=1/roots
    weights=weights*inv[rows]*inv[cols]
    comp_degree=np.bincount(labels,weights=roots**2,minlength=nc)
    rng=np.random.default_rng(seed); score=rng.normal(size=n)
    # Lazy normalized-adjacency power iteration, projecting away each
    # connected component's constant eigenvector. NumPy only.
    for iteration in range(600):
        score=.5*score+.5*np.bincount(rows,weights=weights*score[cols],minlength=n)
        means=np.bincount(labels,weights=score*roots,minlength=nc)/comp_degree
        score-=roots*means[labels]
        norms=np.sqrt(np.bincount(labels,weights=score**2,minlength=nc))
        score/=np.maximum(norms[labels],1e-20)
    values=np.array([score[x].mean() for x in d['gn']])
    # Start each source camera near half while preserving spatial ordering.
    assign=np.zeros(len(values),dtype=np.int8)
    cameras=[i for i,k in enumerate(d['keys']) if k[0]=='camera']
    chosen=np.argmax(d['features'][:,cameras],axis=1)
    for ci in range(len(cameras)):
        ids=np.where(chosen==ci)[0]; ids=ids[np.argsort(values[ids],kind='stable')]
        sizes=d['features'][ids,d['keys'].index(('total','all'))]
        assign[ids[np.cumsum(sizes)>=sizes.sum()/2]]=1
    assign[d['forced']]=0
    return assign

def optimize(d,initial,seed,profile,passes=24):
    rng=np.random.default_rng(seed); x=initial.copy(); f=d['features']; totals=d['totals']; keys=d['keys']
    coeff=np.array([profile['weight'].get(k[0],0)/max(t,1) for k,t in zip(keys,totals)])
    lo=np.array([profile['bounds'].get(k[0],(0.05,0.95))[0]*t for k,t in zip(keys,totals)])
    hi=np.array([profile['bounds'].get(k[0],(0.05,0.95))[1]*t for k,t in zip(keys,totals)])
    bound_coeff=np.array([profile.get('bound_weight_by_feature',{}).get(k[0],profile['bound_weight'])/max(t,1) for k,t in zip(keys,totals)])
    portrait=x@f
    incidence=np.zeros((len(d['nodes']),2),dtype=np.int32)
    for ids,s in zip(d['gn'],x): incidence[ids,s]+=1
    incident=[[] for _ in d['nodes']]
    for gi,ids in enumerate(d['gn']):
        for node in ids: incident[node].append(gi)
    incident=[np.array(v,dtype=np.int32) for v in incident]
    def penalty(v):
        over=np.maximum(lo-v,0)+np.maximum(v-hi,0)
        return np.sum(coeff*(v-totals*.5)**2)+np.sum(over**2*bound_coeff)
    initial_duplicate=int(np.count_nonzero(np.all(incidence>0,axis=1)))
    best=x.copy(); best_cost=initial_duplicate+penalty(portrait)
    trace=[dict(pass_index=-1,duplicates=initial_duplicate,objective=float(best_cost),accepted=0,star_accepted=0)]
    for p in range(passes):
        temp=max(0,profile.get('temperature',1.2)*(1-p/max(1,passes-5))) if p<passes-5 else 0
        accepted=0
        for gi in rng.permutation(len(x)):
            if d['forced'][gi]: continue
            ids=d['gn'][gi]; old=int(x[gi]); new=1-old
            before=(incidence[ids,0]>0)&(incidence[ids,1]>0)
            after_old=incidence[ids,old]-1; after_new=incidence[ids,new]+1
            delta=int(np.count_nonzero((after_old>0)&(after_new>0))-np.count_nonzero(before))
            changed=portrait+(1-2*old)*f[gi]
            change=delta+penalty(changed)-penalty(portrait)
            if change < -1e-10 or (temp>0 and rng.random()<np.exp(-max(change,0)/temp)):
                x[gi]=new; incidence[ids,old]-=1; incidence[ids,new]+=1; portrait=changed; accepted+=1
        # Node-star moves flip many chains together, escaping the barrier
        # where an individual chain cannot eliminate a highly shared node.
        star_accepted=0
        if p>=1:
            for node in rng.permutation(len(incident)):
                group=incident[node]
                for new in rng.permutation(2):
                    moving=group[x[group]!=new]
                    if new==1 and np.any(d['forced'][moving]): continue
                    if not len(moving): continue
                    old=1-new
                    ids,multiplicity=np.unique(np.concatenate([d['gn'][gi] for gi in moving]),return_counts=True)
                    before=(incidence[ids,0]>0)&(incidence[ids,1]>0)
                    after_old=incidence[ids,old]-multiplicity
                    after_new=incidence[ids,new]+multiplicity
                    delta=int(np.count_nonzero((after_old>0)&(after_new>0))-np.count_nonzero(before))
                    changed=portrait+(1-2*old)*f[moving].sum(axis=0)
                    change=delta+penalty(changed)-penalty(portrait)
                    if change < -1e-10:
                        x[moving]=new; incidence[ids,old]-=multiplicity; incidence[ids,new]+=multiplicity; portrait=changed; star_accepted+=1
        duplicate=int(np.count_nonzero(np.all(incidence>0,axis=1)))
        score=duplicate+penalty(portrait)
        if score<best_cost: best_cost=score; best=x.copy()
        trace_row=dict(pass_index=p,duplicates=duplicate,objective=float(score),accepted=accepted,star_accepted=star_accepted)
        if profile.get('record_distribution',False):
            six_indices=[i for i,k in enumerate(keys) if k[0]=='axis' and k[1]!='identity']
            ax_indices=[i for i,k in enumerate(keys) if k[0]=='axis']
            cam_indices=[i for i,k in enumerate(keys) if k[0]=='camera']
            p6=portrait[six_indices]; l6=totals[six_indices]-p6
            trace_row.update(render_jobs=len(d['nodes'])+duplicate,portrait_chain_fraction=float(portrait[keys.index(('total','all'))]/len(d['chains'])),six_axis_max_relative_deviation_landscape_pct=float(np.max(np.abs(l6*6/l6.sum()-1))*100),six_axis_max_relative_deviation_portrait_pct=float(np.max(np.abs(p6*6/p6.sum()-1))*100),axis_portrait_fraction_min=float(np.min(portrait[ax_indices]/totals[ax_indices])),axis_portrait_fraction_max=float(np.max(portrait[ax_indices]/totals[ax_indices])),camera_portrait_fraction_min=float(np.min(portrait[cam_indices]/totals[cam_indices])),camera_portrait_fraction_max=float(np.max(portrait[cam_indices]/totals[cam_indices])))
        trace.append(trace_row)
        if p>=passes-5 and accepted==0 and star_accepted==0: break
    return best,trace

def chain_labels(d,x):
    out=np.zeros(len(d['chains']),dtype=np.int8)
    for group,label in zip(d['groups'],x): out[group]=label
    return out

def stats(d,labels):
    needs=[set(),set()]; report={}
    for aspect in range(2):
        chosen=[c for c,l in zip(d['chains'],labels) if l==aspect]
        used=set(n for c in chosen for n in c['history']); needs[aspect]=used
        starts=[d['nodes'][c['history'][0]]['state'] for c in chosen]
        report[ASPECTS[aspect]]={
            'chains':len(chosen),'chain_fraction':len(chosen)/len(labels),'unique_nodes':len(used),
            'chain_start_sex':dict(collections.Counter(s['sex'] for s in starts)),
            'chain_start_camera':dict(sorted(collections.Counter(s['camera'] for s in starts).items())),
            'chain_start_sex_camera':dict(sorted(collections.Counter(s['sex']+'|'+s['camera'] for s in starts).items())),
            'axis_steps':dict(sorted(collections.Counter(s['axis'] for c in chosen for s in c['steps']).items())),
            'edit_axis_mode_steps':dict(sorted(collections.Counter(s['axis']+'|'+s.get('mode','') for c in chosen for s in c['steps']).items())),
            'rendered_node_sex':dict(collections.Counter(d['nodes'][i]['state']['sex'] for i in used)),
            'rendered_node_camera':dict(sorted(collections.Counter(d['nodes'][i]['state']['camera'] for i in used).items())),
            'kind':dict(collections.Counter(c['kind'] for c in chosen)),
            'length':dict(sorted(collections.Counter(c['length'] for c in chosen).items())),
        }
    union=needs[0]|needs[1]; shared=needs[0]&needs[1]
    assert union==set(n for c in d['chains'] for n in c['history'])
    report.update(original_nodes=len(d['nodes']),used_union_nodes=len(union),shared_nodes=len(shared),render_jobs=len(needs[0])+len(needs[1]),render_increase_fraction=len(shared)/len(union),chain_count=len(labels))
    cameras=set(d['nodes'][c['history'][0]]['state']['camera'] for c in d['chains'])
    report['all_start_cameras_covered_both']=all(set(report[a]['chain_start_camera'])==cameras for a in ASPECTS)
    report['all_7_axes_covered_both']=all(len(report[a]['axis_steps'])==7 for a in ASPECTS)
    report['all_sexes_covered_both']=all(len(report[a]['chain_start_sex'])==2 for a in ASPECTS)
    report['start_camera_portrait_fraction']={c:report['portrait']['chain_start_camera'].get(c,0)/sum(report[a]['chain_start_camera'].get(c,0) for a in ASPECTS) for c in sorted(cameras)}
    return report,needs

def save(d,split,name,labels,metadata):
    assert all(int(label)==0 for c,label in zip(d['chains'],labels) if c['id'] in d['forbidden'])
    report,needs=stats(d,labels)
    out=HERE/name/split; out.mkdir(parents=True,exist_ok=True)
    with (out/'assignment.jsonl').open('w',encoding='utf-8') as stream:
        for c,aspect in zip(d['chains'],labels): stream.write(json.dumps({'id':c['id'],'aspect':ASPECTS[int(aspect)]},separators=(',',':'))+'\n')
    dump(out/'stats.json',report); dump(out/'node_requirements.json',{a:sorted(needs[i]) for i,a in enumerate(ASPECTS)})
    dump(out/'method.json',metadata)
    print(split,name,'renders',report['render_jobs'],'shared',report['shared_nodes'],'portrait',round(report['portrait']['chain_fraction'],4),'camera range',tuple(round(v,3) for v in (min(report['start_camera_portrait_fraction'].values()),max(report['start_camera_portrait_fraction'].values()))),flush=True)
    return report

PROFILES={
 'balanced':dict(weight={'total':3,'sex':1,'camera':.3,'sex_camera':.1,'axis':.1,'edit':.03},bounds={'total':(.45,.55),'sex':(.40,.60),'camera':(.35,.65),'sex_camera':(.30,.70),'axis':(.35,.65),'edit':(.30,.70)},bound_weight=200,temperature=.15),
 'economy':dict(weight={'total':2,'sex':.3,'camera':.03,'sex_camera':.01,'axis':.01,'edit':.003},bounds={'total':(.45,.55),'sex':(.35,.65),'camera':(.20,.80),'sex_camera':(.15,.85),'axis':(.25,.75),'edit':(.15,.85)},bound_weight=150,temperature=.25),
 'tight':dict(weight={'total':5,'sex':2,'camera':1,'sex_camera':.5,'axis':.3,'edit':.1},bounds={'total':(.45,.55),'sex':(.45,.55),'camera':(.40,.60),'sex_camera':(.35,.65),'axis':(.40,.60),'edit':(.35,.65)},bound_weight=300,temperature=.1),
}

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--quick',action='store_true'); parser.add_argument('--passes',type=int,default=24); args=parser.parse_args()
    summary={}; started=time.time()
    for split in ('train','test'):
        d=load(split); print(split,'bundles',len(d['groups']),'features',len(d['keys']),flush=True)
        rng=np.random.default_rng(6101); random=rng.integers(0,2,len(d['chains']),dtype=np.int8)
        for i,c in enumerate(d['chains']):
            if c['id'] in d['forbidden']: random[i]=0
        summary.setdefault('random_baseline',{})[split]=save(d,split,'random_baseline',random,{'seed':6101,'method':'independent chain Bernoulli baseline'})
        initial=spectral(d,6101)
        summary.setdefault('spectral_baseline',{})[split]=save(d,split,'spectral_baseline',chain_labels(d,initial),{'seed':6101,'method':'normalized node clique spectral score; camera-stratified bundle median'})
        if not args.quick:
            for name,profile in PROFILES.items():
                best=None; best_objective=float('inf'); best_meta=None
                for seed in [6101,6102]:
                    x,trace=optimize(d,initial,seed,profile,args.passes)
                    objective=min(t['objective'] for t in trace)
                    if objective<best_objective: best=x; best_objective=objective; best_meta={'seed':seed,'method':'spectral warm start + bundled hypergraph simulated annealing and greedy refinement','profile':profile,'trace':trace}
                summary.setdefault(name,{})[split]=save(d,split,name,chain_labels(d,best),best_meta)
                dump(HERE/'summary.json',summary)
    hashes={split:{f:hashlib.sha256((SOURCE/split/f).read_bytes()).hexdigest() for f in ['nodes.json','sessions.jsonl']} for split in ['train','test']}
    dump(HERE/'input_hashes.json',hashes); dump(HERE/'summary.json',summary)
    print('finished_seconds',round(time.time()-started,2),flush=True)

if __name__=='__main__': main()
