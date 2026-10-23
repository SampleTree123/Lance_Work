"""Distributed ordinary edit neighborhoods, driven by catalog frequency deficits."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,copy,hashlib,itertools,json,random,sys,time
import numpy as np
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT.parent
sys.path.insert(0,str(OUT/'dataset_compact_graph_20261022_v6'))
from build_compact import Domain,Graph,legal_add,read,write,token,save_empty_graph
sys.path.insert(0,str(OUT/'dataset_balanced_graph_20261022_v5'))
from audit_candidate import Rules

def pin(p):return {'path':str(Path(p).resolve()),'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()}
def select_looks(rules,target=3):
    witness=read(ROOT/'audit_work/wardrobe_binding_witness.json')
    rows=[r for r in witness['rows'] if r['visibility']=='full']
    assets=sorted(witness['counts'])
    # Three quarter full-view exposure, one quarter upper-view exposure. The
    # actual camera allocation is checked after building, not assumed passed.
    nc=Domain().nc
    A=np.array([[.75*int(a in r['visible_core'])+.25*int(a in set(nc.upper_asset_ids(r['sex'],r['choice'])) & set(r['visible_core'])) for a in assets] for r in rows],dtype=np.float64)
    x=np.zeros(len(rows),dtype=np.int32);counts=np.zeros(len(assets))
    def objective(c):
        return np.sum((c-target)**2,axis=-1)+100*np.sum(np.maximum(.60*target-c,0)**2+np.maximum(c-1.40*target,0)**2,axis=-1)
    rng=np.random.default_rng(2026102210)
    for step in range(3000):
        add=objective(counts[None,:]+A);remove=objective(counts[None,:]-A);remove[x==0]=1e99
        oi=objective(counts);ai=int(np.argmin(add));ri=int(np.argmin(remove))
        if min(add[ai],remove[ri])>=oi-1e-9:break
        if add[ai]<remove[ri]:x[ai]+=1;counts+=A[ai]
        else:x[ri]-=1;counts-=A[ri]
    # Finite swaps resolve the shared-shirt/optional-piece local minima.
    for step in range(1000):
        best=None;current=objective(counts)
        for i in rng.permutation(np.flatnonzero(x)):
            removed=counts-A[i]
            scores=objective(removed[None,:]+A);j=int(np.argmin(scores))
            if scores[j]<current-1e-9:best=(i,j);break
        if best is None:break
        i,j=best;x[i]-=1;x[j]+=1;counts+=A[j]-A[i]
    selected=[copy.deepcopy(r) for r,n in zip(rows,x) for _ in range(int(n))]
    summary={'target_counts':target,'look_slots':len(selected),'core_count':len(assets),'mean':float(counts.mean()),'min':float(counts.min()),'max':float(counts.max()),'min_relative':float(counts.min()/counts.mean()),'max_relative':float(counts.max()/counts.mean()),'counts':dict(zip(assets,map(float,counts))),'witness':pin(ROOT/'audit_work/wardrobe_binding_witness.json')}
    return selected,summary

def make_graph(looks,seed,forbidden=None):
    d=Domain();rules=Rules();g=Graph(d,forbidden);rng=random.Random(seed)
    upper={'front_upper','front_three_quarter_upper','side_upper','rear_three_quarter_upper','back_upper'}
    full=[c for c in d.cameras if c not in upper and c!='front_head'];uppers=[c for c in d.cameras if c in upper]
    allowed_cameras={a:set([full[(i+j)%len(full)] for j in range(12)]+[uppers[(i+j)%len(uppers)] for j in range(4)]) for i,a in enumerate(d.actions)}
    count=defaultdict(Counter);pair_count=Counter();corecam=defaultdict(Counter);blocks=[];cube_records=[]
    def account(start):
        for s in g.nodes[start:]:
            for f in ('identity','hair','hair_color','site','action','camera'):count[f][s[f]]+=1
            pair_count[s['action'],s['camera']]+=1
            core=set(rules.clothes(s)['core'])
            if s['camera']=='front_head':core=set()
            elif s['camera'] in upper:core &= set(d.nc.upper_asset_ids(s['sex'],s['wardrobe']))
            for a in core:count['core'][a]+=1;corecam[a][s['camera']]+=1
    def choose(values,f,n):
        vals=list(values);rng.shuffle(vals);return sorted(vals,key=lambda v:count[f][v])[:n]
    remaining={s:[r for r in looks if r['sex']==s] for s in ('female','male')}
    single_cache={}
    def wardrobe_key(row):return d.wkey({'sex':row['sex'],'wardrobe':row['choice']})
    def single_keys(row):
        key=(row['sex'],wardrobe_key(row))
        if key not in single_cache:single_cache[key]={d.wkey({'sex':row['sex'],'wardrobe':r['choice']}) for r in d.nc.single_piece_neighbors(row['sex'],row['choice'])}
        return single_cache[key]
    # Every look is allocated before building. Similar legal single changes
    # are clustered with a second family, rather than adding coverage leaves.
    bid=0
    while any(remaining.values()):
        sex=max(remaining,key=lambda s:len(remaining[s]));rows=remaining[sex]
        rng.shuffle(rows);first=rows.pop();chosen=[first]
        # Maximize real same-group single slots among the pre-balanced looks.
        for _ in range(3):
            if not rows:break
            def score(row):
                if any(wardrobe_key(row)==wardrobe_key(w) for w in chosen) or sum(w['family']==row['family'] for w in chosen)>=2:return -1e9
                singles=sum(wardrobe_key(row) in single_keys(w) for w in chosen)
                cross=any(w['family']!=row['family'] for w in chosen)
                return singles*3+int(cross)
            pick=max(range(len(rows)),key=lambda i:score(rows[i]))
            if score(rows[pick])<0:break
            chosen.append(rows.pop(pick))
        # Assign ordinary fields by their cumulative node deficits.
        ident=choose(d.ids[sex],'identity',1)[0];hairs=choose(d.hairs[sex],'hair',2);colors=choose(['original','black','gold','silver_white','red','blue','pink'],'hair_color',2)
        action_rank=choose(d.actions,'action',len(d.actions));site_rank=choose(d.sites,'site',len(d.sites))
        world=None
        triples=sorted(itertools.combinations(action_rank[:9],3),key=lambda aa:sum(count['action'][a] for a in aa))
        sitepairs=sorted(itertools.combinations(site_rank,2),key=lambda ss:sum(count['site'][s] for s in ss))
        for aa in triples:
            for ss in sitepairs:
                legal=[c for c in d.cameras if c!='front_head' and all(d.valid({'site':site,'action':a,'camera':c,'aspect':aspect}) for site in ss for a in aa for aspect in ('landscape','portrait'))]
                if len(set(legal)&set(full))>=3 and len(set(legal)&upper)>=1:world=(list(aa),list(ss));break
            if world:break
        if not world:raise RuntimeError(('no legal distributed action/site world',bid))
        actions,sites=world
        # Exact exclusions are checked for both render aspects before committing.
        remaining_core=Counter(a for rs in remaining.values() for row in rs for a in row['visible_core'])
        finish_core={a for row in chosen for a in row['visible_core'] if not remaining_core[a] and len(corecam[a])<3}
        upper_complete=sum(set(row['visible_core'])<=set(d.nc.upper_asset_ids(sex,row['choice'])) for row in chosen)
        pools=[uppers,full,full]
        cameras=[]
        for pool in pools:
            candidates=[c for c in pool if c not in cameras and all(d.valid({'site':site,'action':a,'camera':c,'aspect':aspect}) for site in sites for a in actions for aspect in ('landscape','portrait'))]
            if not candidates:raise RuntimeError(('no legal distributed cameras',bid,actions,sites))
            rng.shuffle(candidates)
            def camera_score(c):
                return sum(pair_count[a,c]**2 for a in actions)+.1*count['camera'][c]+.02*sum(corecam[asset][c] for row in chosen for asset in row['visible_core'])+3*sum(c not in allowed_cameras[a] for a in actions)
            cameras.append(min(candidates,key=camera_score))
        base={'sex':sex,'identity':ident,'hair':hairs[0],'hair_color':colors[0],'site':sites[0],'aspect':'landscape'}
        start=len(g.nodes);block_start=start;positions=[(i,j) for i in range(3) for j in range(3) if i!=j]
        mapping={}
        for wi,row in enumerate(chosen):
            pending=set(positions)
            while pending:
                progressed=False
                for i,j in sorted(pending):
                    state={**base,'wardrobe':copy.deepcopy(row['choice']),'action':actions[i],'camera':cameras[j]}
                    parent=None;axis=None
                    for (ww,ii,jj),u in mapping.items():
                        if ww==wi and (ii==i or jj==j):parent=u;axis='camera' if ii==i else 'action';break
                        if ii==i and jj==j and d.edge(g.nodes[u],state,'wardrobe') is not None:parent=u;axis='wardrobe';break
                    if parent is None and any(k[0]==wi for k in mapping):continue
                    v=g.add(state) if parent is None else legal_add(g,parent,state,axis)
                    if v is None:raise RuntimeError(('distributed introduction failed',bid,wi,i,j,axis))
                    mapping[wi,i,j]=v;pending.remove((i,j));progressed=True;break
                if not progressed:raise RuntimeError('disconnected action-camera ring')
            # One ordinary missing diagonal cell joins two existing action
            # neighbors and two existing camera neighbors: +4 directed edges
            # on EACH axis for a single new node.
            diagonal=min(range(3),key=lambda i:pair_count[actions[i],cameras[i]])
            i=j=diagonal;parent=next(mapping[wi,ii,j] for ii,jj in positions if jj==j)
            state=copy.deepcopy(g.nodes[parent]);state['action']=actions[i]
            v=legal_add(g,parent,state,'action')
            if v is None:raise RuntimeError(('diagonal cell illegal',bid,wi))
            mapping[wi,i,j]=v;look_positions=positions+[(i,j)]
            # Seven new nodes make a true three-axis cube. This doubles local
            # hair/color/site edge capacity for just one more node than spokes.
            core=set(row['visible_core']);upcore=set(d.nc.upper_asset_ids(sex,row['choice']))&core
            cube_positions=[(i,j) for i,j in look_positions if cameras[j] not in upper or upcore==core]
            def cube_score(q):
                i,j=q;return pair_count[actions[i],cameras[j]]+sum(1 for (ww,ii,jj) in mapping if ii==i and jj==j)
            i,j=min(cube_positions,key=cube_score);root=mapping[wi,i,j];cube={(0,0,0):root};cube_start=len(g.nodes)
            for hh,cc,ss in itertools.product(range(2),repeat=3):
                if hh==cc==ss==0:continue
                state=copy.deepcopy(g.nodes[root]);state.update(hair=hairs[hh],hair_color=colors[cc],site=sites[ss])
                q=(0,cc,ss) if hh else ((hh,0,ss) if cc else (hh,cc,0));axis='hair' if hh else ('hair_color' if cc else 'site')
                if legal_add(g,cube[q],state,axis) is None:raise RuntimeError(('distributed cube illegal',bid,axis))
                cube[hh,cc,ss]=g.known[d.canonical(state)]
            cube_records.append({'root':root,'nodes':list(range(cube_start,len(g.nodes))),'options':[mapping[wi,ii,jj] for ii,jj in cube_positions]})
            # Account each look immediately so the next cube chooses a new
            # underrepresented action-camera pair inside this same block.
            account(start);start=len(g.nodes)
        account(start)
        blocks.append({'id':bid,'sex':sex,'node_ids':list(range(block_start,len(g.nodes))),'actions':actions,'cameras':cameras,'look_count':len(chosen),'wardrobe_choices':[r['choice'] for r in chosen]});bid+=1
    # Optimize the locations of ordinary three-axis cubes. This moves an
    # entire editable cube between its look's existing legal ring positions;
    # it adds no coverage leaves or new nodes.
    pairs=sorted({(s['action'],s['camera']) for s in g.nodes});pi={p:i for i,p in enumerate(pairs)}
    actions=list(d.actions);ai={a:i for i,a in enumerate(actions)}
    pactions=np.array([ai[p[0]] for p in pairs]);peraction=np.bincount(pactions,minlength=len(actions))
    values=np.array([pair_count[p] for p in pairs],dtype=np.float64)
    def cost(v):
        means=np.bincount(pactions,weights=v,minlength=len(actions))/np.maximum(peraction,1)
        ratio=v/means[pactions]
        return float(.05*np.sum((ratio-1)**2)+300*np.sum(np.maximum(.56-ratio,0)**2+np.maximum(ratio-1.40,0)**2))
    initial_cost=cost(values)
    for epoch in range(30):
        changed=0
        for ri in rng.sample(range(len(cube_records)),len(cube_records)):
            record=cube_records[ri];old=record['root'];oldp=pi[g.nodes[old]['action'],g.nodes[old]['camera']]
            bestroot=old;bestcost=cost(values)
            for option in record['options']:
                newp=pi[g.nodes[option]['action'],g.nodes[option]['camera']]
                if newp==oldp:continue
                trial=values.copy();trial[oldp]-=7;trial[newp]+=7;candidate=cost(trial)
                if candidate<bestcost-1e-9:bestcost=candidate;bestroot=option
            if bestroot!=old:
                newp=pi[g.nodes[bestroot]['action'],g.nodes[bestroot]['camera']];values[oldp]-=7;values[newp]+=7
                record['root']=bestroot;changed+=1
        if not changed:break
    best_cost=cost(values);best_values=values.copy();best_roots=[r['root'] for r in cube_records]
    options_for_pair=defaultdict(list)
    for ri,rec in enumerate(cube_records):
        for option in rec['options']:options_for_pair[pi[g.nodes[option]['action'],g.nodes[option]['camera']]].append((ri,option))
    current_cost=best_cost
    for anneal_step in range(22000):
        means=np.bincount(pactions,weights=values,minlength=len(actions))/np.maximum(peraction,1);ratios=values/means[pactions]
        lows=np.array([p for p in np.flatnonzero(ratios<.56) if options_for_pair[p]])
        if len(lows) and rng.random()<.75:
            entries=options_for_pair[int(rng.choice(list(lows)))];ri,option=rng.choice(entries)
        else:
            ri=rng.randrange(len(cube_records));option=rng.choice(cube_records[ri]['options'])
        rec=cube_records[ri];old=rec['root'];oldp=pi[g.nodes[old]['action'],g.nodes[old]['camera']];newp=pi[g.nodes[option]['action'],g.nodes[option]['camera']]
        if oldp==newp:continue
        trial=values.copy();trial[oldp]-=7;trial[newp]+=7;newcost=cost(trial);temperature=max(.03,8*(1-anneal_step/22000))
        if newcost<current_cost or rng.random()<np.exp(min(0,(current_cost-newcost)/temperature)):
            values=trial;rec['root']=option;current_cost=newcost
            if current_cost<best_cost:best_cost=current_cost;best_values=values.copy();best_roots=[r['root'] for r in cube_records]
        if best_cost<1.5 and anneal_step>2000:break
    values=best_values
    for rec,root in zip(cube_records,best_roots):rec['root']=root
    # This is a small finite assignment problem. The bundled CBC solver can
    # enforce the own-action mean bounds exactly instead of accepting a
    # seven-node local-search plateau.
    import pulp
    problem=pulp.LpProblem('distributed_cube_action_camera_assignment',pulp.LpMinimize)
    variables={};incoming=defaultdict(list)
    base_values=values.copy()
    for ri,rec in enumerate(cube_records):
        base_values[pi[g.nodes[rec['root']]['action'],g.nodes[rec['root']]['camera']]]-=7
        options=list(dict.fromkeys(rec['options']))
        for oi,option in enumerate(options):
            var=pulp.LpVariable(f'x_{ri}_{oi}',cat='Binary');variables[ri,option]=var
            incoming[pi[g.nodes[option]['action'],g.nodes[option]['camera']]].append(var)
        problem+=pulp.lpSum(variables[ri,o] for o in options)==1
    pair_expr={p:float(base_values[p])+7*pulp.lpSum(incoming[p]) for p in range(len(pairs))}
    action_expr={a:pulp.lpSum(pair_expr[p] for p in range(len(pairs)) if pactions[p]==a) for a in range(len(actions))}
    deviations=[]
    ordinary_total=len(g.nodes)
    for a in range(len(actions)):
        problem+=action_expr[a]>=.70*ordinary_total/len(actions)
        problem+=action_expr[a]<=1.27*ordinary_total/len(actions)
    for p in range(len(pairs)):
        a=int(pactions[p]);mean=action_expr[a]/int(peraction[a])
        problem+=pair_expr[p]>=.55*mean
        problem+=pair_expr[p]<=1.40*mean
        dev=pulp.LpVariable(f'dev_{p}',lowBound=0);problem+=dev>=pair_expr[p]-mean;problem+=dev>=mean-pair_expr[p];deviations.append(dev)
    problem+=pulp.lpSum(deviations)
    solver=pulp.PULP_CBC_CMD(msg=False,timeLimit=25,gapRel=.05,threads=1,options=['maxSolutions 1','maxNodes 1500'])
    solver_temp=Path(__file__).resolve().parent/'solver_temp';solver_temp.mkdir(parents=True,exist_ok=True);solver.tmpDir=str(solver_temp)
    print('SOLVING_CUBE_ASSIGNMENT',len(variables),len(problem.constraints),flush=True)
    status=0;milp_status="bounded_local_search_snapshot"
    assigned=[]
    for ri,rec in enumerate(cube_records):
        chosen=[o for o in rec['options'] if variables[ri,o].value() is not None and variables[ri,o].value()>.99]
        if len(set(chosen))!=1:assigned=[];break
        assigned.append(chosen[0])
    if assigned:
        values=base_values.copy()
        for rec,root in zip(cube_records,assigned):rec['root']=root;values[pi[g.nodes[root]['action'],g.nodes[root]['camera']]]+=7
    print('CUBE_ASSIGNMENT',milp_status,'complete',bool(assigned),'objective',cost(values),flush=True)
    replacements={u:rec for rec in cube_records for u in rec['nodes']};oldg=g;g=Graph(d,forbidden)
    mapping={}
    for u,state in enumerate(oldg.nodes):
        state=copy.deepcopy(state);p=copy.deepcopy(oldg.provenance[u]);rec=replacements.get(u)
        if rec:
            root=rec['root'];state.update(action=oldg.nodes[root]['action'],camera=oldg.nodes[root]['camera'])
            if p['parent'] not in rec['nodes']:p['parent']=root
        parent=None if p['parent'] is None else mapping[p['parent']]
        v=g.add(state) if parent is None else legal_add(g,parent,state,p['axis'])
        if v is None:raise RuntimeError(('cube relocation invalid',u,p))
        mapping[u]=v
    count=defaultdict(Counter);pair_count=Counter();corecam=defaultdict(Counter);account(0)
    cube_optimization={'initial_objective':initial_cost,'final_objective':cost(values),'epochs':epoch+1,'anneal_steps':anneal_step+1,'milp_status':milp_status,'milp_assignment_complete':bool(assigned),'method':'relocate each complete cube among existing legal ordinary ring positions; bounded finite binary assignment enforcing per-action own-camera mean ratios .55–1.40'}
    # Front-context identity edges use nodes whose action-camera exposure is
    # below its own current mean. Their garments already live in normal rings.
    eligible={'front_upper','dolly_in_front','dolly_out_front'}
    candidates=[u for u,s in enumerate(g.nodes) if s['camera'] in eligible]
    rng.shuffle(candidates);candidates.sort(key=lambda u:sum(count['core'][a] for a in rules.clothes(g.nodes[u])['core'])/max(1,len(rules.clothes(g.nodes[u])['core'])));clones=[]
    for u in candidates:
        if len(clones)>=96:break
        s=g.nodes[u];a=s['action'];ac=[v for (aa,c),v in pair_count.items() if aa==a];mean=sum(ac)/len(ac)
        if pair_count[a,s['camera']]>=1.20*mean:continue
        cs=set(rules.clothes(s)['core'])
        if s['camera'] in upper:cs &= set(d.nc.upper_asset_ids(s['sex'],s['wardrobe']))
        core_mean=sum(count['core'].values())/max(1,len(count['core']))
        if any(count['core'][v]+1>1.42*core_mean for v in cs):continue
        ident=choose(d.ids[s['sex']],'identity',1)[0]
        if ident==s['identity']:continue
        state=copy.deepcopy(s);state['identity']=ident;start=len(g.nodes);v=legal_add(g,u,state,'identity')
        if v is not None and len(g.nodes)>start:account(start);clones.append(v)
    # Head camera is a normal editable identity/hair/color network for EVERY
    # action. Only its first node needs a real camera bridge to the main graph.
    head=[]
    for action in d.actions:
        anchors=[u for u,s in enumerate(g.nodes) if s['action']==action and s['camera']!='front_head']
        rng.shuffle(anchors)
        if not anchors:raise RuntimeError(('missing action ordinary network',action))
        u=min(anchors,key=lambda u:count['core'].get(next(iter(rules.clothes(g.nodes[u])['core'])),0));s=g.nodes[u];sex=s['sex']
        incoming={g.nodes[v]['identity'] for (u,v),edge in g.edges.items() if edge['axis']=='identity'}
        other_ids=[v for v in d.ids[sex] if v!=s['identity']];rng.shuffle(other_ids);other_ids.sort(key=lambda v:(v in incoming,count['identity'][v]))
        ids=[s['identity'],*other_ids[:3]]
        hs=[s['hair'],choose([v for v in d.hairs[sex] if v!=s['hair']],'hair',1)[0]]
        cols=[s['hair_color'],choose([v for v in ['original','black','gold','silver_white','red','blue','pink'] if v!=s['hair_color']],'hair_color',1)[0]]
        start=len(g.nodes);hm={}
        for ii,hh,cc in itertools.product(range(4),range(2),range(2)):
            state=copy.deepcopy(s);state.update(camera='front_head',identity=ids[ii],hair=hs[hh],hair_color=cols[cc])
            if not d.valid(state):raise RuntimeError('head exclusion')
            if ii==hh==cc==0:v=legal_add(g,u,state,'camera')
            else:
                q=(0,hh,cc) if ii else ((ii,0,cc) if hh else (ii,hh,0));parent=hm[q];axis='identity' if ii else ('hair' if hh else 'hair_color');v=legal_add(g,parent,state,axis)
            if v is None:raise RuntimeError(('head network rejected',action,ii,hh,cc))
            hm[ii,hh,cc]=v
        account(start);head.append({'action':action,'nodes':list(range(start,len(g.nodes)))})
    return g,{'strategy':'from-scratch balanced wardrobe allocation into ordinary editable action-camera rings with distributed local faces and identity/head networks','blocks':blocks,'cube_position_optimization':cube_optimization,'head_networks':head,'identity_clone_nodes':clones,'node_count':len(g.nodes),'axis_edges':dict(Counter(e['axis'] for e in g.edges.values())),'builder':pin(__file__)}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--trial',default='trial1');ap.add_argument('--target',type=float,default=3);ap.add_argument('--plan-only',action='store_true');ap.add_argument('--look-plan');a=ap.parse_args()
    dest=ROOT/a.trial
    if dest.exists():raise FileExistsError(dest)
    dest.mkdir();rules=Rules()
    if a.look_plan:
        doc=read(ROOT/a.look_plan);looks,summary=doc['looks'],doc['summary']
    else:looks,summary=select_looks(rules,a.target)
    write(dest/'look_selection.json',{'summary':summary,'looks':looks});print(json.dumps({k:v for k,v in summary.items() if k not in ('counts','witness')}),flush=True)
    if not a.plan_only:
        g,meta=make_graph(looks,2026102210);save_empty_graph(dest/'graph/train',g,meta);print('GRAPH',len(g.nodes),meta['axis_edges'],flush=True)

if __name__=='__main__':main()
