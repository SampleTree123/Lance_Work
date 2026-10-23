"""History-aware path resampling on immutable v10 nodes and legal edges.

Experimental offline optimizer: proposal probabilities are not final marginal
probabilities. Whole-chain acceptance retains existing frequency/coverage gates.
"""
from pathlib import Path
from collections import Counter, defaultdict
import argparse, copy, hashlib, json, math, random, shutil, sys, time
import numpy as np
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent
sys.path.insert(0, str(OUT/'dataset_distributed_graph_20261022_v10/audit_work'))
from audit_distributed import Rules, visible_core
AXES = ('identity','hair','hair_color','wardrobe','action','camera','site')

def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p, v):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(v, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def pin(p): return {'path':str(Path(p).resolve()), 'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()}
def sig(c): return (c['history'][0], tuple((s['source_position'],s['target']) for s in c['steps']))

class Optimizer:
    def __init__(self, source, split, seed):
        self.source=source; self.split=split; self.rng=random.Random(seed); self.rules=Rules()
        self.nodes=read(source/split/'nodes.json'); self.states={n['id']:n['state'] for n in self.nodes}
        self.edges=read(source/split/'edges.json'); self.edgeids={(e['source'],e['target']):i for i,e in enumerate(self.edges)}
        self.chains=[json.loads(x) for x in (source/split/'sessions.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
        self.adj=defaultdict(lambda:defaultdict(list)); self.tokens={}; self.eligible={}
        self.values={u:{a:json.dumps(self.rules.clothes(s)['key'],sort_keys=True) if a=='wardrobe' else s[a] for a in AXES} for u,s in self.states.items()}
        for i,e in enumerate(self.edges):
            u,v,a=e['source'],e['target'],e['axis']; self.adj[u][a].append((v,i))
            assert self.states[u]['aspect']==self.states[v]['aspect']
            if a!='wardrobe': self.tokens[i]={(a,self.values[v][a])}
            else:
                w=self.states[v]['wardrobe']; self.tokens[i]={('family',w['family_id']),('group',w['family_id']+'/'+w['group_id'])}
                self.tokens[i]|={('core',x) for x in set(self.rules.clothes(self.states[v])['core'])-set(self.rules.clothes(self.states[u])['core'])}
                self.eligible[i]=bool(self.rules.singles(self.states[u]))
        fields=('identity','action','hair','hair_color','site'); keys=[]; self.groups=[]
        for f in fields:
            inds=[]
            for value in sorted({s[f] for s in self.states.values()}): inds.append(len(keys)); keys.append((f,value))
            self.groups.append(np.array(inds))
        core=sorted({x for s in self.states.values() for x in visible_core(self.rules,s)})
        inds=[]
        for x in core: inds.append(len(keys)); keys.append(('core',x))
        self.groups.append(np.array(inds))
        for act in sorted({s['action'] for s in self.states.values()}):
            cams=sorted({s['camera'] for s in self.states.values() if s['action']==act and s['camera']!='front_head'}); inds=[]
            for cam in cams: inds.append(len(keys)); keys.append(('pair',(act,cam)))
            self.groups.append(np.array(inds))
        ki={k:i for i,k in enumerate(keys)}; self.D=len(keys); self.features={}
        for u,s in self.states.items():
            inds=[ki[f,s[f]] for f in fields]+[ki['core',x] for x in visible_core(self.rules,s)]
            if s['camera']!='front_head': inds.append(ki['pair',(s['action'],s['camera'])])
            self.features[u]=np.array(inds)
        self.group_index=np.empty(self.D,dtype=int)
        for i,inds in enumerate(self.groups):self.group_index[inds]=i
        self.group_sizes=np.array([len(x) for x in self.groups])
        self.records=[self.record(c) for c in self.chains]; self.signatures={sig(c) for c in self.chains}
        self.nodeuse=Counter();self.edgeuse=Counter();self.targetuse=Counter();self.axes=np.zeros(7,dtype=int);self.freq=np.zeros(self.D,dtype=int)
        self.single=0;self.opportunities=0
        for rec in self.records:
            self.nodeuse.update(rec['nodes']);self.edgeuse.update(rec['edges']);self.targetuse.update(rec['tokens']);self.axes+=rec['axes'];self.freq+=rec['freq'];self.single+=rec['single'];self.opportunities+=rec['opportunities']
        self.original_identity=int(self.axes[0]);self.four=sum(v==4 for v in self.edgeuse.values());self.used=sum(v>0 for v in self.edgeuse.values())
        self.baseline=self.summary(); self.accepted=0; self.attempts=0; self.rejects=Counter(); self.trace=[]

    def ancestors(self,c,position):
        result=[]
        while True:
            result.append(c['history'][position])
            if position==0:return result
            position=c['steps'][position-1]['source_position']

    def novelty(self,c,source_position,axis,target):
        value=self.values[target][axis]; ancestry=self.ancestors(c,source_position); current=self.values[ancestry[0]][axis]
        previous=next((self.values[u][axis] for u in ancestry if self.values[u][axis]!=current),None)
        if value==previous:return .05
        if any(self.values[u][axis]==value for u in ancestry):return .20
        if any(self.values[u][axis]==value for u in c['history']):return .35
        return 1.0

    def record(self,c):
        nodes=Counter(c['history']); edges=Counter(self.edgeids[s['source'],s['target']] for s in c['steps']); tokens=Counter();freq=np.zeros(self.D,dtype=np.int16);axes=np.zeros(7,dtype=int)
        for u,n in nodes.items():freq[self.features[u]]+=n
        for eid,n in edges.items():tokens.update({k:n for k in self.tokens[eid]})
        returns=others=single=opportunities=0
        for i,st in enumerate(c['steps']):
            a=st['axis'];axes[AXES.index(a)]+=1;tv=self.values[st['target']][a]
            if any(self.values[u][a]==tv for u in self.ancestors(c,st['source_position'])):returns+=1
            elif any(self.values[u][a]==tv for u in c['history'][:i+1]):others+=1
            eid=self.edgeids[st['source'],st['target']]
            if a=='wardrobe' and self.eligible[eid]:opportunities+=1;single+=st['mode']=='single_piece'
        return dict(nodes=nodes,edges=edges,tokens=tokens,freq=freq,axes=axes,returns=returns,others=others,distinct=int(np.count_nonzero(axes)),revisits=len(c['history'])-len(nodes),single=single,opportunities=opportunities)

    def ratios(self,freq):
        sums=np.bincount(self.group_index,weights=freq,minlength=len(self.groups))
        return freq/(sums/self.group_sizes)[self.group_index]

    def propose(self,c,old):
        # Preserve the initial node AND every historical-source position.
        pivot=self.rng.randrange(c['length'])
        new=dict(c);new['history']=c['history'][:pivot+1];new['steps']=[dict(s) for s in c['steps'][:pivot]]
        local=Counter(self.edgeids[s['source'],s['target']] for s in new['steps']);counts=Counter(s['axis'] for s in new['steps'])
        for i in range(pivot,c['length']):
            pos=c['steps'][i]['source_position'];u=new['history'][pos];options={};weights={}
            for a,adj in self.adj[u].items():
                vs=[];ws=[]
                for v,eid in adj:
                    used=self.edgeuse[eid]-old['edges'][eid]+local[eid]
                    if used>=4:continue
                    capacity=(1.5,1.4,.9,.008)[used]
                    novelty=self.novelty(new,pos,a,v)
                    exposure=float(np.exp(np.mean(np.log(np.maximum(.25,np.minimum(4,1/self.ratio[self.features[v]]))))))
                    vs.append((v,eid));ws.append(capacity*novelty*exposure)
                if vs:options[a]=vs;weights[a]=ws
            if not options:return None
            axes=list(options);aw=[]
            for a in axes:
                j=AXES.index(a);mean=float(self.axes[1:].mean()) if a!='identity' else self.original_identity
                global_weight=(mean/max(1,self.axes[j]))**3
                # Marginalize the history preference over available target values;
                # do not force a binary A/B attribute to reverse after selecting it.
                novelty_mass=sum(self.novelty(new,pos,a,v) for v,e in options[a])/len(options[a])
                aw.append((2 if a=='identity' else 1)*.4**counts[a]*global_weight*novelty_mass)
            a=self.rng.choices(axes,weights=aw,k=1)[0];vs=options[a];ws=weights[a]
            if a=='wardrobe':
                modes={self.edges[eid]['mode'] for v,eid in vs}
                if len(modes)>1:
                    desired=self.rng.choice(['single_piece','whole_outfit']);take=[j for j,(v,eid) in enumerate(vs) if self.edges[eid]['mode']==desired]
                    if take:vs=[vs[j] for j in take];ws=[ws[j] for j in take]
            v,eid=self.rng.choices(vs,weights=ws,k=1)[0];e=self.edges[eid]
            st={k:e[k] for k in ('axis','mode','slot') if k in e};st.update(source_position=pos,source=u,target=v)
            new['steps'].append(st);new['history'].append(v);local[eid]+=1;counts[a]+=1
        return new

    def consider(self,pos,new):
        old=self.records[pos];ns=sig(new)
        if ns in self.signatures:return False
        rec=self.record(new)
        if rec['distinct']<old['distinct']:self.rejects['axis_diversity']+=1;return False
        freq=self.freq-old['freq']+rec['freq'];rr=self.ratios(freq)
        if np.any(rr<.5-1e-10) or np.any(rr>1.5+1e-10):self.rejects['frequency']+=1;return False
        axes=self.axes-old['axes']+rec['axes'];six=axes[1:]
        if np.max(abs(six/six.mean()-1))>.10 or abs(axes[0]/self.original_identity-1)>.05:self.rejects['axis_counts']+=1;return False
        single=self.single-old['single']+rec['single'];opp=self.opportunities-old['opportunities']+rec['opportunities']
        if not .45<=single/max(1,opp)<=.55:self.rejects['single_balance']+=1;return False
        if any(self.nodeuse[u]-old['nodes'][u]+rec['nodes'][u]<1 for u in old['nodes']):self.rejects['node_coverage']+=1;return False
        if any(self.targetuse[t]-old['tokens'][t]+rec['tokens'][t]<1 for t in old['tokens']):self.rejects['target_coverage']+=1;return False
        four=self.four;used=self.used
        for e in set(old['edges'])|set(rec['edges']):
            before=self.edgeuse[e];after=before-old['edges'][e]+rec['edges'][e]
            if after>4 or after<0:return False
            four+=int(after==4)-int(before==4);used+=int(after>0)-int(before>0)
        if four/max(1,used)>.005:self.rejects['four_use']+=1;return False
        gain=old['returns']-rec['returns']+.30*(old['others']-rec['others'])+.30*(old['revisits']-rec['revisits'])+.10*(rec['distinct']-old['distinct'])
        # Equal-quality rearrangements may move exposure away from boundaries.
        smooth=float(np.sum((self.ratio-1)**4)-np.sum((rr-1)**4))
        if gain+.03*smooth<=1e-9:self.rejects['objective']+=1;return False
        self.signatures.remove(sig(self.chains[pos]));self.signatures.add(ns)
        self.chains[pos]=new;self.records[pos]=rec;self.freq=freq;self.ratio=rr;self.axes=axes;self.four=four;self.used=used;self.single=single;self.opportunities=opp
        for target,field in [(self.nodeuse,'nodes'),(self.edgeuse,'edges'),(self.targetuse,'tokens')]:target.subtract(old[field]);target.update(rec[field])
        self.accepted+=1;return True

    def summary(self):
        rs=self.records;bylength={}
        for length in range(2,6):
            rows=[r for c,r in zip(self.chains,rs) if c['length']==length]
            bylength[length]={'chains':len(rows),'return_events':sum(r['returns'] for r in rows),'return_chains':sum(r['returns']>0 for r in rows),'mean_distinct_axes':sum(r['distinct'] for r in rows)/len(rows)}
        return {'chains':len(rs),'return_events':sum(r['returns'] for r in rs),'return_chains':sum(r['returns']>0 for r in rs),'other_branch_repeat_events':sum(r['others'] for r in rs),'full_node_repeats':sum(r['revisits'] for r in rs),'by_length':bylength,'axis_counts':dict(zip(AXES,map(int,self.axes))),'used_edges':self.used,'four_use_edges':self.four,'conditional_single_fraction':self.single/max(1,self.opportunities)}

    def run(self,seconds):
        start=time.time();self.ratio=self.ratios(self.freq);next_log=0
        while time.time()-start<seconds:
            order=list(range(len(self.chains)));self.rng.shuffle(order)
            for pos in order:
                if time.time()-start>=seconds:break
                old=self.records[pos]
                if old['returns']==0 and old['others']==0 and self.rng.random()>.15:continue
                for _ in range(8 if old['returns'] else 2):
                    self.attempts+=1;new=self.propose(self.chains[pos],self.records[pos])
                    if new and self.consider(pos,new):break
                if time.time()-start>=next_log:
                    row={'elapsed':round(time.time()-start,1),'accepted':self.accepted,'attempts':self.attempts,**self.summary()};self.trace.append(row);print(json.dumps(row),flush=True);next_log+=30
        return self.summary()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--split',choices=['train','test'],required=True);ap.add_argument('--seconds',type=int,default=180);ap.add_argument('--seed',type=int,default=2026102211);args=ap.parse_args()
    dest=args.output/args.split
    if dest.exists():raise FileExistsError(dest)
    opt=Optimizer(args.source,args.split,args.seed);final=opt.run(args.seconds);dest.mkdir(parents=True)
    for name in ('nodes.json','edges.json'):shutil.copyfile(args.source/args.split/name,dest/name)
    for c in opt.chains:c['return_control']={'method':'history_weighted_suffix_resampling_with_whole_chain_constraints','baseline_session_id':c['id']}
    (dest/'sessions.jsonl').write_text(''.join(json.dumps(c,ensure_ascii=False,separators=(',',':'))+'\n' for c in opt.chains),encoding='utf-8')
    write(args.output/(args.split+'_optimization.json'),{'source':str(args.source),'seed':args.seed,'seconds':args.seconds,'sampler':pin(__file__),'proposal_weights':{'axis_decay':.4,'immediate_old_value':.05,'older_ancestor_value':.20,'other_branch_seen_value':.35,'new_value':1},'acceptance':'existing coverage and frequency gates; lower return/revisit objective; nondecreasing per-chain distinct axes; initial node and parent-position topology fixed','baseline':opt.baseline,'final':final,'accepted':opt.accepted,'attempts':opt.attempts,'rejects':dict(opt.rejects),'trace':opt.trace,'inputs':[pin(args.source/args.split/f) for f in ('nodes.json','edges.json','sessions.jsonl')]})
    print('FINISHED',json.dumps(final),flush=True)
if __name__=='__main__':main()
