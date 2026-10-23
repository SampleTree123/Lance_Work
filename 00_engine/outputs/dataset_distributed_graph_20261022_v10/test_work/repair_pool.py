"""Exchange real chains within identical kind/length/start-camera/fork jobs."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,copy,json,sys
import numpy as np
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;OUT=ROOT.parent
sys.path.insert(0,str(OUT/'dataset_local_support_20261021_v3'));from resample_local import Domain,load_graph,save_graph,read,write
sys.path.insert(0,str(ROOT/'audit_work'));from audit_distributed import Rules,visible_core,pin
def lines(p):return [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]
def main():
    p=argparse.ArgumentParser();p.add_argument('--trial',default='trial12');p.add_argument('--base',default='candidate1');p.add_argument('--pool',default='candidate2');p.add_argument('--output',default='candidate3');a=p.parse_args();trial=HERE/a.trial;base=trial/a.base;pool=trial/a.pool;dest=trial/a.output
    if dest.exists():raise FileExistsError(dest)
    g=load_graph(trial/'graph/test',Domain());rules=Rules();states=g.nodes
    for folder in (base,pool):
        assert [r['state'] for r in read(folder/'test/nodes.json')]==states
    sessions=lines(base/'test/sessions.jsonl');alternatives=lines(pool/'test/sessions.jsonl')
    dims=[('identity',s['identity']) for s in states]+[('action',s['action']) for s in states]+[('hair',s['hair']) for s in states]+[('hair_color',s['hair_color']) for s in states]+[('site',s['site']) for s in states]+[('core',v) for s in states for v in visible_core(rules,s)]+[('ac',(s['action'],s['camera'])) for s in states if s['camera']!='front_head']
    dims=list(dict.fromkeys(dims));di={v:i for i,v in enumerate(dims)};groups=defaultdict(list);actiongroups=defaultdict(list)
    for i,(field,v) in enumerate(dims):
        if field=='ac':actiongroups[v[0]].append(i)
        else:groups[field].append(i)
    freqgroups=list(groups.values())+list(actiongroups.values())
    def vector(c):
        v=np.zeros(len(dims),dtype=np.int32)
        for u in c['history']:
            s=states[u]
            for f in ('identity','action','hair','hair_color','site'):v[di[f,s[f]]]+=1
            for asset in visible_core(rules,s):v[di['core',asset]]+=1
            if s['camera']!='front_head':v[di['ac',(s['action'],s['camera'])]]+=1
        return v
    def key(c):return (c['kind'],c['length'],states[c['history'][0]]['camera'],c['fork_round'],next((st['source_position'] for t,st in enumerate(c['steps'],1) if st['source_position']!=t-1),None))
    def sig(c):return (tuple(c['history']),tuple(s['source_position'] for s in c['steps']))
    def edges(c):return Counter((st['source'],st['target']) for st in c['steps'])
    sv=[vector(c) for c in sessions];av=[vector(c) for c in alternatives];se=[edges(c) for c in sessions];ae=[edges(c) for c in alternatives];usedsignatures={sig(c) for c in sessions};index=defaultdict(list)
    for j,c in enumerate(alternatives):index[key(c)].append(j)
    counts=sum(sv);edgeuse=sum(se,Counter());nodeuse=Counter(u for c in sessions for u in c['history']);axes=Counter(st['axis'] for c in sessions for st in c['steps'])
    def objective(v):
        loss=0.
        for ids in freqgroups:
            vals=v[ids];mean=vals.mean();loss+=float(np.maximum(.505*mean-vals,0).sum()+np.maximum(vals-1.495*mean,0).sum())
        return loss
    current=objective(counts);trace=[]
    for epoch in range(100):
        best=None;bestscore=current
        for i,c in enumerate(sessions):
            for j in index[key(c)]:
                new=alternatives[j]
                if sig(new) in usedsignatures:continue
                trialcounts=counts-sv[i]+av[j];score=objective(trialcounts)
                if score>=bestscore-1e-9:continue
                nodechange=Counter(new['history']);nodechange.subtract(c['history'])
                if any(nodeuse[u]+n<=0 for u,n in nodechange.items()):continue
                change=ae[j].copy();change.subtract(se[i]);new4=sum(n==4 for n in edgeuse.values())
                valid=True
                for edge,n in change.items():
                    after=edgeuse[edge]+n
                    if after>4:valid=False;break
                    new4+=int(after==4)-int(edgeuse[edge]==4)
                if not valid or new4>18:continue
                axischange=Counter(st['axis'] for st in new['steps']);axischange.subtract(st['axis'] for st in c['steps']);newaxes=axes+axischange
                vals=[axes[x]+axischange[x] for x in ('hair','hair_color','wardrobe','action','camera','site')];mean=sum(vals)/6
                if max(abs(x/mean-1) for x in vals)>.1:continue
                bestscore=score;best=(i,j,nodechange,change,axischange,trialcounts)
        if best is None:break
        i,j,nc,ec,ac,counts=best;old=sessions[i];new=copy.deepcopy(alternatives[j]);new['id']=old['id'];usedsignatures.remove(sig(old));usedsignatures.add(sig(new));nodeuse.update(nc);edgeuse.update(ec);axes.update(ac);sessions[i]=new;sv[i]=av[j];se[i]=ae[j];trace.append({'session_index':i,'pool_session':alternatives[j]['id'],'loss_before':current,'loss_after':bestscore,'preserved_job':list(key(old))});current=bestscore
        print('SWAP',len(trace),current,flush=True)
        if current<1e-9:break
    dest.mkdir();meta=read(base/'test/metrics.json')['construction'];meta['test_real_chain_pool_repair']={'base':str(base),'pool':str(pool),'base_sessions':pin(base/'test/sessions.jsonl'),'pool_sessions':pin(pool/'test/sessions.jsonl'),'swaps':trace,'final_history_frequency_loss':current,'preserved':'kind length start camera fork round and parent; node set and all atomic edges unchanged; cap4 and all node use checked'}
    sampling=read(base/'test/sampling.json');sampling.update(complete=len(sessions)==2400,sampled_sessions=len(sessions),axis_counts=dict(axes),post_sampling_chain_pool_repair=meta['test_real_chain_pool_repair']);meta['sampling']=sampling
    save_graph(dest/'test',g,sessions,meta);write(dest/'test/sampling.json',sampling);write(dest/'repair_trace.json',meta['test_real_chain_pool_repair']);print('DONE',len(trace),current,flush=True)
if __name__=='__main__':main()
