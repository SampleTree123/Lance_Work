"""Select whole .4-sampled chains by sparse, exact same-bucket exchanges.

No graph changes. Kind, length and starting camera remain fixed on each swap.
All nodes and actual target values remain represented; semantic edge cap is 4.
"""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,copy,hashlib,json,random,shutil,sys,time
import numpy as np
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'audit_work'))
from audit_distributed import Rules,visible_core,exposure
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def lines(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines()]
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def pin(p):return {'path':str(p.resolve()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def signature(c):return (c['history'][0],tuple((s['source_position'],s['target']) for s in c['steps']))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--trial',default='trial12');ap.add_argument('--base',default='candidate2');ap.add_argument('--pools',nargs='+',default=['candidate1','candidate3']);ap.add_argument('--output',default='candidate4');ap.add_argument('--seconds',type=int,default=110);ap.add_argument('--split',default='train');a=ap.parse_args()
    root=ROOT/a.trial;base=root/a.base;out=root/a.output;split=a.split
    if out.exists():raise FileExistsError(out)
    rules=Rules();nodes=read(base/split/'nodes.json');states={n['id']:n['state'] for n in nodes};edges=read(base/split/'edges.json');edgekeys={(e['source'],e['target']):i for i,e in enumerate(edges)}
    fields=('identity','action','hair','hair_color','site');keys=[];groups=[]
    for f in fields:
        inds=[]
        for v in sorted({s[f] for s in states.values()}):inds.append(len(keys));keys.append((f,v))
        groups.append(np.array(inds))
    corepool=sorted({v for s in states.values() for v in visible_core(rules,s)});coreinds=[]
    for v in corepool:coreinds.append(len(keys));keys.append(('core',v))
    groups.append(np.array(coreinds));pairs=sorted({(s['action'],s['camera']) for s in states.values() if s['camera']!='front_head'});pairgroups=[]
    for act in sorted({s['action'] for s in states.values()}):
        inds=[]
        for ac in pairs:
            if ac[0]==act:inds.append(len(keys));keys.append(('pair',ac))
        pairgroups.append(np.array(inds))
    ki={k:i for i,k in enumerate(keys)};D=len(keys);nodefeat={}
    for u,s in states.items():
        cs=Counter(ki[f,s[f]] for f in fields);cs.update(ki['core',v] for v in visible_core(rules,s))
        if s['camera']!='front_head':cs[ki['pair',(s['action'],s['camera'])]]+=1
        nodefeat[u]=cs
    axislist=['identity','hair','hair_color','wardrobe','action','camera','site'];axisi={v:i for i,v in enumerate(axislist)}
    edgecoverage={}
    for e,i in edgekeys.items():
        st,tt=states[e[0]],states[e[1]];axis=edges[i]['axis']
        if axis!='wardrobe':tokens={(axis,tt[axis])}
        else:
            tokens={('family',tt['wardrobe']['family_id']),('group',tt['wardrobe']['family_id']+'/'+tt['wardrobe']['group_id'])}
            tokens|={('core',v) for v in set(rules.clothes(tt)['core'])-set(rules.clothes(st)['core'])}
        edgecoverage[i]=tokens
    records=[];sigindex={};poolinputs=[];baseids=[]
    for name in [a.base,*a.pools]:
        folder=root/name
        provenance={'sessions':pin(folder/split/'sessions.jsonl')}
        if (folder/'SAMPLER_CODE.json').exists():provenance['sampler_manifest']=pin(folder/'SAMPLER_CODE.json')
        if (folder/'sampler_source.py').exists():provenance['sampler_source']=pin(folder/'sampler_source.py')
        poolinputs.append(provenance)
        assert read(folder/split/'nodes.json')==nodes
        for c in lines(folder/split/'sessions.jsonl'):
            sig=signature(c)
            if sig not in sigindex:
                feat=Counter();n=Counter(c['history']);es=Counter(edgekeys[s['source'],s['target']] for s in c['steps']);tc=Counter();axes=np.zeros(7,dtype=np.int32)
                for u,weight in n.items():
                    for f,v in nodefeat[u].items():feat[f]+=v*weight
                for eid,weight in es.items():tc.update({v:weight for v in edgecoverage[eid]})
                for s in c['steps']:axes[axisi[s['axis']]]+=1
                vec=np.zeros(D,dtype=np.int16)
                for f,v in feat.items():vec[f]=v
                sigindex[sig]=len(records);records.append({'chain':c,'origin':name,'nodes':n,'edges':es,'coverage':tc,'axes':axes,'vec':vec,'bucket':(c['kind'],c['length'],states[c['history'][0]]['camera'])})
            if name==a.base:baseids.append(sigindex[sig])
    X=np.stack([r['vec'] for r in records]);selected=np.array(baseids,dtype=np.int32);selected_set=set(baseids);current=X[selected].sum(axis=0,dtype=np.int64)
    nodeuse=Counter();edgeuse=Counter();targetuse=Counter();axes=np.zeros(7,dtype=np.int64)
    buckets=defaultdict(list);selected_buckets=defaultdict(list)
    for i,r in enumerate(records):buckets[r['bucket']].append(i)
    for position,i in enumerate(selected):
        r=records[i];nodeuse.update(r['nodes']);edgeuse.update(r['edges']);targetuse.update(r['coverage']);axes+=r['axes'];selected_buckets[r['bucket']].append(position)
    four=sum(v==4 for v in edgeuse.values());used=len(edgeuse);initial_four=four;allgroups=groups+pairgroups
    def ratios_batch(vals):
        vals=np.atleast_2d(vals);rr=[]
        for inds in allgroups:
            sub=vals[:,inds];rr.append(sub/np.maximum(sub.mean(axis=1,keepdims=True),1e-8))
        return np.concatenate(rr,axis=1)
    def cost_batch(vals):
        rr=ratios_batch(vals);return 10000*np.sum(np.maximum(.50-rr,0)**2+np.maximum(rr-1.50,0)**2,axis=1)+1e-7*np.sum((rr-1)**2,axis=1)
    def violations(vals):
        rr=ratios_batch(vals)[0];return int(np.count_nonzero((rr<.50-1e-10)|(rr>1.50+1e-10)))
    flatorder=np.concatenate(allgroups);rng=random.Random(2026102212);started=time.time();trace=[];swaps=[];attempt=0;accepted=0;best_cost=float(cost_batch(current)[0]);next_progress=0
    while time.time()-started<a.seconds:
        attempt+=1;rr=ratios_batch(current)[0];bad=np.flatnonzero((rr<.50)|(rr>1.50));candidates=[]
        if len(bad):
            b=int(rng.choice(list(bad)));feature=int(flatorder[b]);high=rr[b]>1.5
            if high:
                positions=np.flatnonzero(X[selected,feature]>0);chosen_positions=rng.sample(list(positions),min(10,len(positions)))
                for pos in chosen_positions:
                    rec=records[int(selected[pos])];pool=buckets[rec['bucket']];candidates.extend((int(pos),j) for j in rng.sample(pool,min(45,len(pool))) if j not in selected_set)
            else:
                poolids=np.flatnonzero(X[:,feature]>0)
                for j in rng.sample(list(poolids),min(35,len(poolids))):
                    if j in selected_set:continue
                    positions=selected_buckets[records[j]['bucket']];candidates.extend((int(pos),int(j)) for pos in rng.sample(positions,min(4,len(positions))))
        else:
            if four/max(used,1)<=.005:break
            four_edges=[e for e,n in edgeuse.items() if n==4]
            e=rng.choice(four_edges);positions=[p for p,i in enumerate(selected) if e in records[int(i)]['edges']]
            for pos in positions:
                pool=buckets[records[int(selected[pos])]['bucket']];candidates.extend((pos,j) for j in rng.sample(pool,min(70,len(pool))) if j not in selected_set)
        if not candidates:continue
        pp=np.array([p for p,j in candidates]);jj=np.array([j for p,j in candidates]);proposed=current[None,:]+X[jj]-X[selected[pp]];scores=cost_batch(proposed)
        order=np.argsort(scores);chosen=None;objective=best_cost+.002*four
        for ci in order[:min(80,len(order))]:
            pos,j=candidates[int(ci)];oldid=int(selected[pos]);old,new=records[oldid],records[j];featcost=float(scores[ci])
            if not len(bad) and violations(proposed[ci]):continue
            newaxes=axes-old['axes']+new['axes'];six=newaxes[1:];mean=float(six.mean())
            if max(abs(six/mean-1))>.10:continue
            if any(nodeuse[u]-old['nodes'][u]+new['nodes'][u]<1 for u in old['nodes']):continue
            if any(targetuse[t]-old['coverage'][t]+new['coverage'][t]<1 for t in old['coverage']):continue
            affected=set(old['edges'])|set(new['edges']);nf=four;nu=used;valid=True
            for e in affected:
                v=edgeuse[e]-old['edges'][e]+new['edges'][e]
                if v>4 or v<0:valid=False;break
                nf+=int(v==4)-int(edgeuse[e]==4);nu+=int(v>0)-int(edgeuse[e]>0)
            if not valid:continue
            candidate_objective=featcost+.002*nf
            if candidate_objective<objective-1e-10:chosen=(pos,j,oldid,int(ci),nf,nu,newaxes,featcost);objective=candidate_objective
        if chosen:
            pos,j,oldid,ci,four,used,axes,best_cost=chosen;old,new=records[oldid],records[j]
            current=proposed[ci].copy();selected_set.remove(oldid);selected_set.add(j);selected[pos]=j
            nodeuse.subtract(old['nodes']);nodeuse.update(new['nodes']);edgeuse.subtract(old['edges']);edgeuse.update(new['edges']);targetuse.subtract(old['coverage']);targetuse.update(new['coverage']);accepted+=1
            swaps.append({'position':pos,'old_pool_index':oldid,'new_pool_index':j,'new_origin':new['origin'],'bucket':new['bucket']})
        if time.time()-started>next_progress:
            row={'elapsed':round(time.time()-started,2),'accepted':accepted,'attempts':attempt,'violating_frequency_values':violations(current),'frequency_cost':best_cost,'four_use_edges':four,'four_use_fraction':four/max(used,1)};trace.append(row);print('REPAIR',json.dumps(row),flush=True);next_progress+=15
    out.mkdir();dest=out/split;dest.mkdir()
    for f in ('nodes.json','edges.json'):shutil.copyfile(base/split/f,dest/f)
    final=[]
    for pos,i in enumerate(selected):
        c=copy.deepcopy(records[int(i)]['chain']);c['id']=f'session_{pos:06d}';c['selection_origin']={'pool':records[int(i)]['origin'],'original_session_id':records[int(i)]['chain']['id'],'method':'whole-chain same-kind-length-start-camera exchange'};final.append(c)
    (dest/'sessions.jsonl').write_text(''.join(json.dumps(c,ensure_ascii=False,separators=(',',':'))+'\n' for c in final),encoding='utf-8')
    summary={'source_candidate':str(base),'pools':poolinputs,'pool_unique_chains':len(records),'selected_chains':len(final),'actual_swaps':len(swaps),'swaps':swaps,'trace':trace,'frequency_violations':violations(current),'four_use_edges':four,'initial_four_use_edges':initial_four,'four_use_fraction':four/max(used,1),'all_nodes_used':all(nodeuse[u]>0 for u in states),'all_actual_target_tokens_preserved':all(v>0 for v in targetuse.values()),'edge_cap':max(edgeuse.values()),'elapsed_seconds':time.time()-started,'local_axis_kernel_base':'.4 per whole-history prior occurrence, plus globally balanced source/axis/target sampling and this explicit post-selection','inputs':[pin(Path(__file__)),pin(base/split/'nodes.json'),pin(base/split/'edges.json')]}
    write(out/'SELECTION.json',summary);print('FINISHED_REPAIR',json.dumps({k:v for k,v in summary.items() if k not in ('swaps','trace','pools','inputs')}),flush=True)
if __name__=='__main__':main()
