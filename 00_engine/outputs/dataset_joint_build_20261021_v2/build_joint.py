"""Joint demand completion with a full-domain historical-target mass.

Finite-support experimental compression. It does NOT claim exact full-catalog
target sampling. Missing axes/modes cause demand completion or a frozen-tape
retry, never renormalization over the axes/modes present in the graph.
"""
from __future__ import annotations
import copy,json,random,sys,time,argparse
from pathlib import Path
from collections import Counter,defaultdict
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
V1=HERE.parent/'dataset_trial_build_20261021_v1'
sys.path.insert(0,str(V1))
from build_trial import Domain,Graph,grow,quotas,stats,save_graph,AXES,ID_CAMERAS,UPPER,COLORS,token,write,digest

def pick_u(values,weights,u):
    total=sum(weights);x=u*total
    for value,w in zip(values,weights):
        x-=w
        if x<0:return value
    return values[-1]

class Joint:
    def __init__(self,d,g,budget,rng):
        self.d=d;self.g=g;self.budget=budget;self.rng=rng;self.counts=Counter();self.edgeuse=Counter();self.started=Counter();self.pool_cache={};self.choice_cache={}
    def pools(self,s,axis):
        key=token(s),axis
        if key in self.pool_cache:return self.pool_cache[key]
        values={'identity':self.d.ids[s['sex']],'hair':self.d.hairs[s['sex']],'hair_color':COLORS,'action':self.d.actions,'camera':self.d.cameras,'site':self.d.sites}[axis]
        values=[v for v in values if v!=s[axis] and (axis not in ('action','camera','site') or self.d.valid({**s,axis:v}))]
        weights=[1.5 if axis=='camera' and v in ID_CAMERAS else 1 for v in values];z=sum(weights)
        result={v:w/z for v,w in zip(values,weights)};self.pool_cache[key]=result
        return result
    def whole_probability(self,s,target):
        """Probability of this labeled wardrobe choice under the catalog hierarchy.

        Source family excluded; core/upper family collisions are separately
        rejected by formal legality. Current families use distinct asset IDs.
        """
        w=target['wardrobe']; sex=s['sex']; families=self.d.cat['sexes'][sex]['families']
        f=next(f for f in families if f['family_id']==w['family_id']);gr=next(g for g in f['groups'] if g['group_id']==w['group_id'])
        p=1/(len(families)-1)/len(f['groups'])
        for slot,options in gr['slot_options'].items():p/=len(options)+(slot in gr['optional_slots'])
        p/=2**len(gr['optional_assets'])
        shoes=self.d.nc._footwear_options(sex,f,gr,w);p/=len(shoes)
        return p
    def legal_targets(self,u,axis,mode,history):
        s=self.g.nodes[u]; rows={}; all_candidates={}
        if axis!='wardrobe':
            probs=self.pools(s,axis)
            for v in set(history):
                if v==u:continue
                t=self.g.nodes[v]; dif=[a for a,x,y in zip(AXES,self.g.keys[u],self.g.keys[v]) if x!=y]
                if dif==[axis] and t[axis] in probs:rows[v]=probs[t[axis]]
            for v in self.g.adj[u].get(axis,[]):all_candidates[v]=probs[self.g.nodes[v][axis]]
        elif mode=='single_piece':
            singles=self.d.singles(s);slots={r['slot'] for r in singles};counts=Counter(r['slot'] for r in singles)
            probs={self.d.wkey({**s,'wardrobe':r['choice']}):1/len(slots)/counts[r['slot']] for r in singles}
            for v in set(history):
                if v==u:continue
                t=self.g.nodes[v];dif=[a for a,x,y in zip(AXES,self.g.keys[u],self.g.keys[v]) if x!=y]
                if dif==[axis] and self.d.wkey(t) in probs:rows[v]=probs[self.d.wkey(t)]
            for v in self.g.adj[u].get(axis,[]):
                if self.g.edges[u,v]['mode']==mode:all_candidates[v]=probs[self.d.wkey(self.g.nodes[v])]
        else:
            for v in set(history)|set(self.g.adj[u].get(axis,[])):
                if v==u:continue
                t=self.g.nodes[v];dif=[a for a,x,y in zip(AXES,self.g.keys[u],self.g.keys[v]) if x!=y]
                if dif!=[axis]:continue
                e=self.d.edge(s,t,axis)
                if not e or e['mode']!=mode:continue
                p=self.whole_probability(s,t)
                if v in history:rows[v]=p
                if v in self.g.adj[u].get(axis,[]):all_candidates[v]=p
        return rows,all_candidates
    def propose(self,s,axis,mode):
        if axis!='wardrobe':return self.d.mutate(s,self.rng,axis)
        t=copy.deepcopy(s)
        if mode=='single_piece':
            singles=self.d.singles(s);slot=self.rng.choice(sorted({r['slot'] for r in singles}));t['wardrobe']=copy.deepcopy(self.rng.choice([r for r in singles if r['slot']==slot])['choice'])
        else:t['wardrobe']=self.d.nc.sample_whole_change(s['sex'],s['wardrobe'],self.rng,require_upper_change=s['camera'] in UPPER)
        return (t,axis) if self.d.edge(s,t,axis) else None
    def step(self,u,history,tape):
        s=self.g.nodes[u];axes=self.d.allowed_axes(s)
        axis=pick_u(axes,[2 if a=='identity' else 1 for a in axes],tape[0]);mode='attribute'
        if axis=='wardrobe':mode='single_piece' if self.d.singles(s) and tape[1]<.5 else 'whole_outfit'
        hist,all_opts=self.legal_targets(u,axis,mode,history);mass=min(1,sum(hist.values())); wants_history=tape[2]<mass
        if wants_history:
            values=sorted(hist); v=pick_u(values,[hist[v] for v in values],tape[3]);self.counts['history_target_selected']+=1
            return v,axis,mode,{'history_probability':mass,'history_selected':True}
        options={v:p for v,p in all_opts.items() if v not in history}
        if options:
            values=sorted(options);v=pick_u(values,[options[v] for v in values],tape[3]);self.counts['existing_nonhistory_target']+=1
            return v,axis,mode,{'history_probability':mass,'history_selected':False}
        if len(self.g.nodes)>=self.budget:
            self.counts['budget_missing_'+axis+('_'+mode if axis=='wardrobe' else '')]+=1;return None
        for _ in range(80):
            m=self.propose(s,axis,mode)
            if m is None:continue
            target,_=m;k=self.d.canonical(target)
            if k in {self.g.keys[v] for v in history}:continue
            v=self.g.add(target,u,axis)
            if v is None:continue
            self.counts['demand_completed_'+axis]+=1
            return v,axis,mode,{'history_probability':mass,'history_selected':False}
        self.counts['proposal_exhausted']+=1;return None
    def start(self,sex,camera):
        options=[i for i,s in enumerate(self.g.nodes) if s['sex']==sex and s['camera']==camera and self.g.adj[i]]
        if not options:return None
        # Within the chosen sex/camera, favor underused identity starts; no
        # claims that absent identity/camera cross-products are supplied.
        ids=sorted({self.g.nodes[i]['identity'] for i in options})
        identity=min(ids,key=lambda v:(self.started[v],self.rng.random()))
        return self.rng.choice([i for i in options if self.g.nodes[i]['identity']==identity])
    def run(self,total,max_attempts=120):
        jobs=quotas(total);self.rng.shuffle(jobs);out=[];seen=set();unfilled=[];start_clock=time.time()
        for index,(kind,L) in enumerate(jobs):
            fork=self.rng.randrange(2,L+1) if kind=='fork' else None;parent=self.rng.randrange(fork-1) if fork else None
            sex=self.rng.choice(['female','male']);camera=pick_u(self.d.cameras,[1.5 if c in ID_CAMERAS else 1 for c in self.d.cameras],self.rng.random())
            tapes=[[self.rng.random() for _ in range(4)] for _ in range(L)]
            for attempt in range(max_attempts):
                start=self.start(sex,camera)
                if start is None:break
                history=[start];steps=[]
                for turn in range(1,L+1):
                    p=parent if turn==fork else turn-1;u=history[p];r=self.step(u,history,tapes[turn-1])
                    if r is None:break
                    v,axis,mode,diag=r
                    e=self.g.edges.get((u,v))
                    if e is None:raise RuntimeError('missing legal demanded edge')
                    steps.append({'source_position':p,'source':u,'target':v,**e,'sampling_diagnostic':diag});history.append(v)
                if len(steps)!=L:continue
                signature=(history[0],tuple((r['source_position'],r['target']) for r in steps))
                if signature in seen:self.counts['duplicate_structure']+=1;continue
                seen.add(signature);self.started[self.g.nodes[start]['identity']]+=1
                out.append({'id':f'joint_{len(out):06d}','kind':kind,'length':L,'fork_round':fork,'history':history,'steps':steps,'proposal_id':index,'proposal_attempts':attempt+1});break
            else:attempt=max_attempts
            if not out or out[-1]['proposal_id']!=index:unfilled.append({'proposal_id':index,'kind':kind,'length':L,'fork_round':fork,'fork_parent':parent,'sex':sex,'camera':camera})
            if (index+1)%1000==0:print('proposals',index+1,'accepted',len(out),'nodes',len(self.g.nodes),round(time.time()-start_clock,1),flush=True)
        return out,{'events':dict(self.counts),'unfilled_count':len(unfilled),'unfilled_by_kind_length':dict(Counter(f'{r["kind"]}_{r["length"]}' for r in unfilled)),'unfilled':unfilled,'initial_identity_start_counts':dict(self.started)}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,default=20261025);ap.add_argument('--reserve',type=float,default=.35);ap.add_argument('--attempts',type=int,default=120);args=ap.parse_args()
    d=Domain(); root=HERE/f'joint_reserve{int(args.reserve*100)}';used=set();summary={}
    for j,(split,budget,total) in enumerate([('train',2500,12000),('test',500,2400)]):
        g,meta=grow(d,int(budget*(1-args.reserve)),args.seed+j,'squares',used)
        planner=Joint(d,g,budget,random.Random(args.seed+20+j));sessions,result=planner.run(total,args.attempts)
        metrics=save_graph(root/split,g,sessions,{'seed_growth':meta,'joint_sampling':{k:v for k,v in result.items() if k!='unfilled'},'finite_support_approximation':True})
        write(root/split/'unfilled_proposals.json',result['unfilled']);summary[split]=metrics;used.update(g.keys)
        print(split,len(sessions),metrics['axis_percent'],metrics['sessions_with_revisited_node'],flush=True)
    write(root/'SUMMARY.json',summary)
if __name__=='__main__':main()
