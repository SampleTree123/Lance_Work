"""Spend 5/10 percent of the SAME 3000-node budget on real identity bridges."""
import sys
sys.dont_write_bytecode=True
from collections import Counter,defaultdict
import hashlib
import json
import random
import time
import experiments as ex

HERE=ex.HERE


def bridge(cat,split,budget,fraction,rng):
    base_budget=round(budget*(1-fraction))
    nodes,adj,edges,family,generation,growth=ex.grow_balanced(cat,split,base_budget,rng,5,parents=16,motifs=True)
    base_registered_edges=len(edges)
    base_node_count=len(nodes)
    domains=cat.domains(split)
    owner={identity:sex+'_'+str(j%5) for sex,opts in domains.items() for j,identity in enumerate(opts[0])}
    known={n:i for i,n in enumerate(nodes)}
    buckets=defaultdict(list)
    freq={sex:[Counter() for _ in opts] for sex,opts in domains.items()}
    bysex=defaultdict(list)
    for i,n in enumerate(nodes):
        sex=cat.sex[n[0]];bysex[sex].append(i)
        for a,v in enumerate(n):
            freq[sex][a][v]+=1;buckets[a,n[:a]+n[a+1:]].append(i)
    _,unrestricted,omitted=ex.induce(cat,nodes,family,False)
    identity_pairs={(nodes[u][0],nodes[v][0]) for (u,v),a in unrestricted.items() if a==0}
    base_identity_pairs=len(identity_pairs)
    base_components=ex.kernel.components(adj)
    final_sex={'female':budget//2,'male':budget-budget//2}
    steps=[];fallback=0
    def add(st,parent,axis):
        if st in known:return known[st]
        assert cat.valid(st)
        i=len(nodes);sex=cat.sex[st[0]]
        for u in buckets[0,st[1:]]:
            if cat.sex[nodes[u][0]]==sex:
                identity_pairs.add((nodes[u][0],st[0]));identity_pairs.add((st[0],nodes[u][0]))
        known[st]=i;nodes.append(st);family.append(owner[st[0]]);generation.append((parent,axis));bysex[sex].append(i)
        for a,v in enumerate(st):
            freq[sex][a][v]+=1;buckets[a,st[:a]+st[a+1:]].append(i)
        return i
    while len(nodes)<budget:
        sex=min((s for s in final_sex if len(bysex[s])<final_sex[s]),key=lambda s:len(bysex[s])/final_sex[s])
        remaining=final_sex[sex]-len(bysex[sex])
        opts=domains[sex]
        norm=[max(1,len(bysex[sex])/len(v)) for v in opts]
        sources=rng.sample(bysex[sex],min(80,len(bysex[sex])))
        best=None
        for u in sources:
            anchor=nodes[u]
            neighbors=[]
            for a in range(1,len(anchor)):
                if len(opts[a])==1:continue
                rows=[v for v in buckets[a,anchor[:a]+anchor[a+1:]] if v!=u and cat.sex[nodes[v][0]]==sex]
                if rows:neighbors.extend((w,a) for w in rng.sample(rows,min(2,len(rows))))
            targets=[v for v in opts[0] if owner[v]!=owner[anchor[0]]]
            for target in targets:
                v=(target,)+anchor[1:]
                for w,a in neighbors:
                    x=(target,)+nodes[w][1:]
                    new=[(st,pa,ax) for st,pa,ax in ((v,anchor,0),(x,v,a)) if st not in known]
                    if not new or len(new)>remaining:continue
                    if any(not cat.valid(st) for st,_,_ in new):continue
                    proposed=set()
                    for st,_,_ in new:
                        for q in buckets[0,st[1:]]:
                            if cat.sex[nodes[q][0]]==sex and nodes[q][0]!=target:
                                proposed.add((nodes[q][0],target));proposed.add((target,nodes[q][0]))
                    novel=len(proposed-identity_pairs)
                    inc=[Counter(st[j] for st,_,_ in new) for j in range(len(anchor))]
                    loss=sum((freq[sex][j][value]*n+n*(n-1)/2)/norm[j] for j,c in enumerate(inc)
                        if len(opts[j])>1 for value,n in c.items())/len(new)
                    score=loss-2.5*novel/len(new)
                    key=(score,rng.random())
                    if best is None or key<best[0]:best=(key,new,novel)
        if best is None:
            # Exact odd budgets may need one single-edge endpoint; counted honestly.
            fallback+=1
            for u in sources:
                target=min((v for v in opts[0] if owner[v]!=owner[nodes[u][0]]),key=lambda v:freq[sex][0][v])
                v=(target,)+nodes[u][1:]
                if v not in known:
                    best=((0,0),[(v,nodes[u],0)],0);break
            if best is None:raise RuntimeError('No bridge endpoint within remaining budget')
        before=len(identity_pairs)
        for st,pa,ax in best[1]:add(st,known[pa],ax)
        steps.append({'nodes_added':len(best[1]),'new_identity_value_pairs':len(identity_pairs)-before,'total_identity_value_pairs':len(identity_pairs)})
    adj,edges,_=ex.induce(cat,nodes,family,False)
    return nodes,adj,edges,family,generation,{'base_node_budget':base_budget,'base_components':base_components,
        'bridge_nodes':len(nodes)-base_node_count,'base_identity_value_pairs':base_identity_pairs,
        'base_within_family_directed_edges':base_registered_edges,'base_potential_cross_family_edges':len(unrestricted)-base_registered_edges,
        'fallback_single_endpoint_batches':fallback,'steps':steps,'base_growth':growth}


def main():
    ex.kernel.AXES=('identity','action','camera','aspect','site','hair_color','garment_slot','hair')
    records=[]
    for fraction in (.05,.10):
        for split,budget,target in (('train',2500,12000),('test',500,3000)):
            tick=time.perf_counter()
            cat=ex.kernel.Catalog(ex.read('inventory_landscape.json'),ex.read('site_checkpoint.json'),ex.read('appearance_catalog.json'),split_policy='scene')
            rng=random.Random(20261021+(10000 if split=='test' else 0))
            nodes,adj,edges,family,generation,growth=bridge(cat,split,budget,fraction,rng)
            sessions,metrics=ex.kernel.sample_sessions(nodes,adj,edges,target,random.Random(20269021),balanced=True,
                quality=True,followup=True,fork_length_policy='20_40_40',source_balanced=True,unique_source_result=True,axis_balance=3.)
            analysis=ex.analyze(cat,split,nodes,adj,edges,family,sessions,metrics)
            assert not analysis['structural_errors']
            assert analysis['history_source_result_equivalence']['ambiguous_forks']==0
            key=f'bridge_p{round(fraction*100)}_a7_n3000_s20261021_{split}'
            r={'key':key,'route':'motif_identity_bridge','bridge_fraction':fraction,'editable_axes':7,'family_count_per_sex':5,
               'total_node_budget':3000,'seed':20261021,'split':split,'unique_nodes':len(nodes),'registered_directed_edges':len(edges),
               'growth':growth,**analysis,'elapsed_seconds':round(time.perf_counter()-tick,3)}
            r['fulfilled_all_requirements']=metrics['sampled_unique_sessions']==target and analysis['all_nodes_referenced']
            records.append(r)
            ex.save_artifacts(key,cat,nodes,edges,family,generation,sessions)
            ex.write(HERE/'bridge_metrics.json',{'kind':'real_cross_family_identity_bridges_same_3000_budget_not_UE',
                'settings':{'fractions':[.05,.10],'seed':20261021,'final_budget':3000,'strict_source_result':True},'records':records})
            print(json.dumps({'key':key,'nodes':len(nodes),'bridge_nodes':growth['bridge_nodes'],'sessions':len(sessions),
                'identity_transition':analysis['axis_value_transition_coverage']['identity'],
                'identity_cv':analysis['node_factor_balance']['identity']['distribution_including_missing']['cv'],
                'cross_family_sessions':analysis['cross_family_sessions'],'components':analysis['graph_components'],
                'all_nodes_referenced':analysis['all_nodes_referenced'],'seconds':r['elapsed_seconds']},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
