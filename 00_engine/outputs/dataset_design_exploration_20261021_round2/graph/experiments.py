"""Round-two graph research: legal edge growth, balanced factors, small families.

Catalog-constrained synthetic topology only. No UE, rendering, or asset access.
"""
from __future__ import annotations
import sys
sys.dont_write_bytecode=True
import argparse
from collections import Counter,defaultdict
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
import random
import time

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('local_quality_kernel',HERE/'quality_kernel_round1.py')
kernel=importlib.util.module_from_spec(spec)
spec.loader.exec_module(kernel)
read=lambda name:json.loads((HERE/name).read_text(encoding='utf-8-sig'))
write=lambda path,obj:Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')


def factor_stats(values):
    d=kernel.distribution(values)
    n=len(values)
    mean=sum(values)/n if n else 0
    d['min']=min(values) if values else 0
    d['cv']=(sum((x-mean)**2 for x in values)/n)**.5/mean if mean else 0
    d['max_over_mean']=max(values)/mean if mean else 0
    return d


def induce(cat,nodes,families,restrict_families=True):
    buckets=defaultdict(list)
    for i,state in enumerate(nodes):
        for a in range(len(state)):
            buckets[(a,state[:a]+state[a+1:])].append(i)
    adj=[[] for _ in nodes]
    edges={}
    omitted=Counter()
    for (a,_),ids in buckets.items():
        for u in ids:
            for v in ids:
                if u == v or cat.sex[nodes[u][0]] != cat.sex[nodes[v][0]]: continue
                if restrict_families and families[u] != families[v]:
                    omitted[kernel.AXES[a]]+=1
                    continue
                edges[u,v]=a
                adj[u].append((v,a))
    for r in adj:r.sort()
    return adj,edges,dict(omitted)


def grow_balanced(cat,split,budget,rng,family_count=1,closure=.35,parents=40,motifs=False):
    domains=cat.domains(split)
    nodes=[]
    known={}
    family=[]
    generation=[]
    byfam=defaultdict(list)
    freq={sex:[Counter() for _ in opts] for sex,opts in domains.items()}
    axis_count={sex:Counter() for sex in domains}
    buckets=defaultdict(list)
    goals={}
    family_options={}
    rejected=Counter()
    motif_sizes=Counter()
    pair_indices=[(0,4),(1,2),(4,1)]
    pair_seen={p:set() for p in pair_indices}
    def add(state,fid,parent=None,axis=None):
        if state in known or not cat.valid(state):return False
        i=len(nodes)
        known[state]=i
        nodes.append(state)
        family.append(fid)
        generation.append((parent,axis))
        byfam[fid].append(i)
        sex=cat.sex[state[0]]
        for a,v in enumerate(state):
            freq[sex][a][v]+=1
            buckets[a,state[:a]+state[a+1:]].append(i)
        if axis is not None:axis_count[sex][axis]+=1
        for a,b in pair_indices:pair_seen[a,b].add((state[a],state[b]))
        return True
    sex_budgets={'female':budget//2,'male':budget-budget//2}
    for sex,opts in domains.items():
        assert len(opts[0]) >= family_count
        for f in range(family_count):
            fid=sex+f'_{f}'
            local=[list(x) for x in opts]
            local[0]=opts[0][f::family_count]
            family_options[fid]=local
            q,r=divmod(sex_budgets[sex],family_count)
            goals[fid]=q+(f<r)
            # A deterministic, counted root per family; never random full configs.
            state=[values[f%len(values)] if a != 0 else values[0] for a,values in enumerate(local)]
            if len(state)>6 and state[7] == 'none':state[5]='original'
            found=False
            for site in local[4]:
                state[4]=site
                if add(tuple(state),fid):found=True;break
            if not found:raise ValueError('No root for '+fid)
    attempts=0
    while len(nodes)<budget:
        fid=min((f for f in goals if len(byfam[f])<goals[f]),key=lambda f:(len(byfam[f])/goals[f],f))
        opts=family_options[fid]
        sex=fid.split('_')[0]
        active=[a for a,v in enumerate(opts) if len(v)>1]
        nsex=sum(len(v) for f,v in byfam.items() if f.startswith(sex+'_'))
        norms=[max(1,nsex/len(v)) for v in domains[sex]]
        # Target underallocated factor values; random ties preserve seed diversity.
        lows={a:sorted(opts[a],key=lambda v:(freq[sex][a][v],rng.random()))[:3] for a in active}
        sources=rng.sample(byfam[fid],min(parents,len(byfam[fid])))
        best=None
        if motifs:
            pairs=list(itertools.combinations(active,2))
            pairs=rng.sample(pairs,min(8,len(pairs)))
            for u in sources:
                anchor=nodes[u]
                for a,b in pairs:
                    for va in lows[a][:2]:
                        if va == anchor[a]:continue
                        for vb in lows[b][:2]:
                            if vb == anchor[b]:continue
                            v=anchor[:a]+(va,)+anchor[a+1:]
                            w=anchor[:b]+(vb,)+anchor[b+1:]
                            x=v[:b]+(vb,)+v[b+1:]
                            block=[(v,anchor,a),(w,anchor,b),(x,v,b)]
                            new=[(st,pa,ax) for st,pa,ax in block if st not in known]
                            attempts+=1
                            if not new or len(new)>goals[fid]-len(byfam[fid]):continue
                            if any(not cat.valid(st) for st,_,_ in block):continue
                            inc=[Counter(st[j] for st,_,_ in new) for j in range(len(anchor))]
                            loss=sum((freq[sex][j][value]*n+n*(n-1)/2)/norms[j] for j,c in enumerate(inc)
                                     if len(domains[sex][j])>1 for value,n in c.items())/len(new)
                            axis_loss=sum(axis_count[sex][ax]/max(1,nsex/len(active)) for _,_,ax in new)/len(new)
                            novelty=sum(len({(st[aa],st[bb]) for st,_,_ in new}-pair_seen[aa,bb]) for aa,bb in pair_indices)
                            score=loss+.35*axis_loss-.3*novelty/len(new)
                            key=(score,rng.random())
                            if best is None or key<best[0]:best=(key,new)
            if best is not None:
                motif_sizes[len(best[1])]+=1
                for st,pa,ax in best[1]:
                    assert add(st,fid,known[pa],ax)
                continue
            # At an exact final budget, completing a sampled square may fail.
            # A single-edge fallback is recorded, not mislabeled as a motif.
            rejected['motif_candidate_fallback']+=1
        for u in sources:
            for a in active:
                for value in lows[a]:
                    attempts+=1
                    if nodes[u][a] == value:continue
                    candidate=nodes[u][:a]+(value,)+nodes[u][a+1:]
                    if candidate in known:continue
                    if not cat.valid(candidate):rejected['constraint']+=1;continue
                    factor_loss=sum(freq[sex][j][v]/norms[j] for j,v in enumerate(candidate) if len(domains[sex][j])>1)
                    neighbors=sum(len(buckets[j,candidate[:j]+candidate[j+1:]]) for j in active)
                    axis_loss=axis_count[sex][a]/max(1,nsex/len(active))
                    score=factor_loss+.35*axis_loss-closure*math.log1p(neighbors)
                    key=(score,rng.random())
                    if best is None or key<best[0]:best=(key,candidate,u,a)
        if best is None:
            # Candidate-list incompleteness is a search failure, not capacity proof.
            raise RuntimeError(f'No candidate found at {len(nodes)}/{budget} family {fid}')
        _,state,u,a=best
        assert add(state,fid,u,a)
    adj,edges,omitted=induce(cat,nodes,family)
    assert all(adj)
    return nodes,adj,edges,family,generation,{'candidate_attempts':attempts,'rejected':dict(rejected),'omitted_cross_family_atomic_edges':omitted,
        'motif_new_node_batch_sizes':dict(motif_sizes),
        'generation_axis_counts':{sex:{kernel.AXES[a]:n for a,n in counts.items()} for sex,counts in axis_count.items()}}


def analyze(cat,split,nodes,adj,edges,families,sessions,metrics):
    domains=cat.domains(split)
    out={}
    axis_options=[]
    for a,axis in enumerate(kernel.AXES):
        vals=set(v for opts in domains.values() for v in opts[a])
        axis_options.append(vals)
        counts=Counter(n[a] for n in nodes)
        out[axis]={'counts':dict(sorted(counts.items())),'distribution_including_missing':factor_stats([counts[v] for v in vals])}
    conditional={}
    legal_expected={}
    for sex,opts in domains.items():
        sex_nodes=[n for n in nodes if cat.sex[n[0]]==sex]
        conditional[sex]={}
        for a,axis in enumerate(kernel.AXES):
            counts=Counter(n[a] for n in sex_nodes)
            conditional[sex][axis]=factor_stats([counts[v] for v in opts[a]])
    for a,axis in enumerate(kernel.AXES):
        actual=Counter(n[a] for n in nodes)
        expected=Counter()
        for sex,opts in domains.items():
            population=sum(cat.sex[n[0]]==sex for n in nodes)
            for v in opts[a]:expected[v]+=population/len(opts[a])
        legal_expected[axis]={'weighted_relative_cv':(sum((actual[v]-e)**2/e for v,e in expected.items())/len(nodes))**.5,
                             'expected_counts':dict(expected)}
    exposure=[Counter() for _ in kernel.AXES]
    edge_axes=Counter()
    family_sessions=Counter()
    wrong=Counter()
    source_equivalence=Counter()
    source_equivalence_examples=[]
    root_final=Counter()
    commuting=Counter()
    axis_sequences=Counter()
    parent_patterns=Counter()
    seen=set()
    node_sessions=Counter()
    cross_family_sessions=0
    used_value_pairs=defaultdict(set)
    for occ,par,axes in sessions:
        node_sessions.update(occ)
        seen.update(occ)
        family_sessions[families[occ[0]]]+=1
        if len(set(families[i] for i in occ)) != 1:cross_family_sessions+=1
        if len(set(occ)) != len(occ):wrong['state_repeat']+=1
        if len(set(axes))<2:wrong['single_axis']+=1
        forks=[t for t,p in enumerate(par) if t and p!=t-1]
        root_final[occ[0],occ[-1]]+=1
        axis_sequences[tuple(axes)]+=1
        parent_patterns[tuple(par)]+=1
        if not forks and len(set(axes)) == len(axes):commuting[occ[0],occ[-1]]+=1
        if len(forks)>1:wrong['multiple_forks']+=1
        if forks:
            t=forks[0]
            if t>=len(axes):wrong['fork_without_followup']+=1
            alt=list(nodes[occ[t-1]])
            alt[axes[t-1]]=nodes[occ[t]][axes[t-1]]
            if tuple(alt)==nodes[occ[t]]:wrong['counterfactual_source_unnecessary']+=1
            ax=axes[t-1]
            eq=[q for q in range(t) if nodes[occ[q]][:ax]+nodes[occ[q]][ax+1:] == nodes[occ[t]][:ax]+nodes[occ[t]][ax+1:]]
            source_equivalence[len(eq)]+=1
            if len(eq)>1 and len(source_equivalence_examples)<3:
                source_equivalence_examples.append({'occurrences':occ,'parents':par,'axes':[kernel.AXES[x] for x in axes],
                    'fork_turn':t,'equivalent_source_occurrences':eq})
        for t in range(1,len(occ)):
            u,v=occ[par[t]],occ[t]
            if edges.get((u,v)) != axes[t-1]:wrong['invalid_edge']+=1
            if cat.sex[nodes[u][0]] != cat.sex[nodes[v][0]]:wrong['cross_sex']+=1
            used_value_pairs[axes[t-1]].add((nodes[u][axes[t-1]],nodes[v][axes[t-1]]))
        for n in occ:
            for a,v in enumerate(nodes[n]):exposure[a][v]+=1
        edge_axes.update(kernel.AXES[a] for a in axes)
    edge_count=Counter(kernel.AXES[a] for a in edges.values())
    transition_coverage={}
    for a,axis in enumerate(kernel.AXES):
        possible={(u,v) for opts in domains.values() for u in opts[a] for v in opts[a] if u!=v}
        if not possible:continue
        observed={(nodes[u][a],nodes[v][a]) for (u,v),ax in edges.items() if ax==a}
        transition_coverage[axis]={'observed_value_pairs':len(observed),'domain_possible_value_pairs':len(possible),
                                   'coverage':len(observed)/len(possible),'used_value_pairs':len(used_value_pairs[a]),
                                   'used_coverage':len(used_value_pairs[a])/len(possible)}
    overlap={}
    family_values={f:[set() for _ in kernel.AXES] for f in set(families)}
    for n,f in zip(nodes,families):
        for a,v in enumerate(n):family_values[f][a].add(v)
    if len(family_values)>2:
        for a,axis in enumerate(kernel.AXES):
            jaccards=[len(family_values[f][a]&family_values[g][a])/len(family_values[f][a]|family_values[g][a])
                      for f,g in itertools.combinations(sorted(family_values),2) if f.split('_')[0] == g.split('_')[0]]
            overlap[axis]=sum(jaccards)/len(jaccards)
    active=[a for a,v in enumerate(axis_options) if len(v)>1]
    pairs={}
    for ax,bx in (('identity','site'),('action','camera'),('site','action'),('identity','garment_slot'),('garment_slot','hair')):
        if ax not in kernel.AXES or bx not in kernel.AXES:continue
        a,b=kernel.AXES.index(ax),kernel.AXES.index(bx)
        observed=set((n[a],n[b]) for n in nodes)
        # Identity/wardrobe denominator respects sex domains; other pairs share domains.
        possible=set((u,v) for opts in domains.values() for u in opts[a] for v in opts[b])
        cartesian=len(possible)
        if (ax,bx)==('site','action'):
            possible={(site,act) for opts in domains.values() for site in opts[4] for act in opts[1]
                      if any((site,act,cam,'landscape') not in cat.excluded for cam in opts[2])}
        if (ax,bx)==('action','camera'):
            possible={(act,cam) for opts in domains.values() for act in opts[1] for cam in opts[2]
                      if any((site,act,cam,'landscape') not in cat.excluded for site in opts[4])}
        pairs[ax+'__'+bx]={'observed':len(observed),'possible':len(possible),'cartesian_possible':cartesian,'coverage':len(observed)/len(possible)}
    return {'node_factor_balance':out,'node_factor_balance_conditional':conditional,'node_factor_balance_legal_expected':legal_expected,
        'session_factor_exposure':{kernel.AXES[a]:factor_stats([c[v] for v in axis_options[a]]) for a,c in enumerate(exposure)},
        'pair_coverage':pairs,'registered_edge_axis_counts':dict(edge_count),'sampled_edge_axis_counts':dict(edge_axes),
        'axis_value_transition_coverage':transition_coverage,
        'sampled_axis_balance':factor_stats([edge_axes[kernel.AXES[a]] for a in active]),
        'registered_axis_balance':factor_stats([edge_count[kernel.AXES[a]] for a in active]),
        'family_session_counts':dict(family_sessions),'family_node_counts':dict(Counter(families)),
        'structural_errors':dict(wrong),'all_nodes_referenced':len(seen)==len(nodes),
        'cross_family_sessions':cross_family_sessions,
        'graph_components':kernel.components(adj),'degree':factor_stats([len(v) for v in adj]),
        'nodes_with_only_one_edit_axis':sum(len({a for v,a in row})<2 for row in adj),
        'node_reuse':factor_stats([node_sessions[i] for i in range(len(nodes))]),
        'history_source_result_equivalence':{'fork_count':sum(source_equivalence.values()),'equivalence_set_size_histogram':dict(source_equivalence),
            'ambiguous_forks':sum(n for size,n in source_equivalence.items() if size>1),'examples':source_equivalence_examples},
        'order_diversity':{'unique_root_final_pairs':len(root_final),'root_final_pair_max_sessions':max(root_final.values()) if root_final else 0,
            'unique_axis_sequences':len(axis_sequences),'unique_parent_patterns':len(parent_patterns),
            'shortest_straight_sessions':sum(commuting.values()),'shortest_straight_root_final_classes':len(commuting),
            'commuting_order_excess_sessions':sum(commuting.values())-len(commuting),'max_commuting_class':max(commuting.values()) if commuting else 0},
        'within_sex_family_asset_jaccard_mean':overlap,
        'sampling':metrics}


def save_artifacts(prefix,cat,nodes,edges,families,generation,sessions):
    hashes=[kernel.digest(dict(zip(kernel.AXES,n))) for n in nodes]
    write(HERE/(prefix+'_graph.json'),{'kind':'catalog_constrained_synthetic_topology_not_UE_validation','axes':kernel.AXES,
        'nodes':[{'node_id':h,'state':dict(zip(kernel.AXES,n)),'family':f,'generation_parent_index':g[0],
                  'generation_axis':None if g[1] is None else kernel.AXES[g[1]]} for h,n,f,g in zip(hashes,nodes,families,generation)],
        'edges':[{'source_index':u,'target_index':v,'axis':kernel.AXES[a]} for (u,v),a in edges.items()]})
    with (HERE/(prefix+'_sessions.jsonl')).open('w',encoding='utf-8') as fp:
        for occ,parents,axes in sessions:
            fp.write(json.dumps({'session_id':kernel.digest(([hashes[i] for i in occ],parents),'sims'),
                'node_indices':occ,'parent_occurrence_indices_gt':parents,'edge_axes':[kernel.AXES[a] for a in axes]},separators=(',',':'))+'\n')
    examples=[]
    wanted={'straight','fork_root','fork_intermediate','garment_slot','hair','site'}
    for i,s in enumerate(sessions):
        o,p,a=s
        forks=[t for t,src in enumerate(p) if t and src != t-1]
        labels={'straight'} if not forks else {'fork_root' if p[forks[0]]==0 else 'fork_intermediate'}
        labels|=set(kernel.AXES[ax] for ax in a)
        if wanted & labels:
            examples.append({'labels':sorted(labels),**kernel.serial_session(s,nodes,i)})
            wanted-=labels
        if not wanted:break
    write(HERE/(prefix+'_examples.json'),examples)


def run(args):
    inventory=read('inventory_landscape.json')
    checkpoint=read('site_checkpoint.json')
    appearance=read('appearance_catalog.json') if args.axes==7 else None
    kernel.AXES=('identity','action','camera','aspect','site','hair_color')+(('garment_slot','hair') if appearance else ())
    records=[]
    for seed,route,total,fams in itertools.product(args.seeds,args.routes,args.budgets,args.families):
        split_hashes={}
        for split,budget,target in (('train',round(total*5/6),12000),('test',total-round(total*5/6),3000)):
            tick=time.perf_counter()
            cat=kernel.Catalog(inventory,checkpoint,appearance,split_policy='scene')
            rng=random.Random(seed+(0 if split=='train' else 10000))
            if route in ('balanced','motif'):
                nodes,adj,edges,family,generation,extra=grow_balanced(cat,split,budget,rng,fams,args.closure,args.parents,motifs=route=='motif')
            else:
                assert fams==1
                nodes,adj,edges,g,attempts=kernel.build_graph(cat,'hybrid',split,budget,rng,cover_values=True)
                family=[cat.sex[n[0]]+'_0' for n in nodes]
                generation=[(r['parent'],r['axis']) for r in g]
                extra={'candidate_attempts':attempts,'baseline':'round1_hybrid_growth'}
            sessions,metrics=kernel.sample_sessions(nodes,adj,edges,target,rng,balanced=True,followup=True,
                quality=True,fork_length_policy='20_40_40',source_balanced=True,unique_source_result=args.unique_source_result,axis_balance=args.axis_balance)
            analysis=analyze(cat,split,nodes,adj,edges,family,sessions,metrics)
            assert not analysis['structural_errors'],analysis['structural_errors']
            if args.unique_source_result:assert analysis['history_source_result_equivalence']['ambiguous_forks']==0
            key=f'{route}_a{args.axes}_f{fams}_n{total}_s{seed}_{split}'
            if args.unique_source_result or args.axis_balance:
                key+=f'_uq{int(args.unique_source_result)}_ab{args.axis_balance:g}'
            row={'key':key,'route':route,'editable_axes':args.axes,'family_count_per_sex':fams,
                 'total_node_budget':total,'seed':seed,'split':split,'unique_nodes':len(nodes),'registered_directed_edges':len(edges),
                 'catalog_rejections':dict(cat.rejects),'growth':extra,**analysis,'elapsed_seconds':round(time.perf_counter()-tick,3)}
            row['fulfilled_all_requirements']=(metrics['sampled_unique_sessions']==target and analysis['all_nodes_referenced'])
            if appearance:row['garment_manifest']=cat.garment_manifest
            records.append(row)
            split_hashes[split]={kernel.digest(dict(zip(kernel.AXES,n))) for n in nodes}
            if args.save:save_artifacts(key,cat,nodes,edges,family,generation,sessions)
            print(json.dumps({'key':key,'nodes':len(nodes),'edges':len(edges),'sessions':metrics['sampled_unique_sessions'],
                'node_coverage':analysis['all_nodes_referenced'],'factor_cv':{a:round(v['distribution_including_missing']['cv'],3) for a,v in analysis['node_factor_balance'].items()},
                'seconds':row['elapsed_seconds']},ensure_ascii=False),flush=True)
        assert not split_hashes['train'] & split_hashes['test']
        write(HERE/args.output,{'kind':'catalog_constrained_synthetic_topology_not_UE_validation','axes':kernel.AXES,
            'settings':vars(args),'records':records,'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.glob('*.json') if p.name in ('inventory_landscape.json','site_checkpoint.json','appearance_catalog.json')},
            'kernel_sha256':hashlib.sha256((HERE/'quality_kernel_round1.py').read_bytes()).hexdigest()})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--routes',nargs='+',choices=['balanced','motif','hybrid'],default=['balanced'])
    p.add_argument('--axes',type=int,choices=[5,7],default=5)
    p.add_argument('--families',type=int,nargs='+',default=[1])
    p.add_argument('--budgets',type=int,nargs='+',default=[3000])
    p.add_argument('--seeds',type=int,nargs='+',default=[20261021])
    p.add_argument('--closure',type=float,default=.35)
    p.add_argument('--parents',type=int,default=40)
    p.add_argument('--output',default='stage1_metrics.json')
    p.add_argument('--save',action='store_true')
    p.add_argument('--unique-source-result',action='store_true')
    p.add_argument('--axis-balance',type=float,default=0.)
    run(p.parse_args())
