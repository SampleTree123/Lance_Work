"""Read catalog names and exact symbolic cross-scene support; no UE access."""
from collections import Counter, defaultdict
import hashlib
import itertools
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUTPUTS=HERE.parents[1]
ROUND1=OUTPUTS/'dataset_design_exploration_20261021_v1'
GROUPS={
    'futuristic_stylized_city':['Cyberpunk_City','FuturisticMetaCity','Synthwave_city'],
    'east_asian_traditional_built':['AsianArchitecture','CHERRY_TREE','Japanese_Village','KyotoAlley'],
    'east_asian_modern_street':['Hong_Kong_Street','Kowloon','UrbanJapan'],
    'european_historical_built':['Medieval_Environment','VictorianStreet'],
    'arid_natural':['Brushify','RedDesertPack'],
    'transport_infrastructure':['DesertGasStation','Evening_Highway','QA_ModularParking','TheMetro'],
    'coastal_town':['Seaside_Town'],
    'theme_park':['AmusementPark'],
    'post_apocalyptic_city':['PostCity']}


def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def dump(name,value): (HERE/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def paired_module(graph, scene_left, scene_right):
    states=[n['state'] for n in graph['nodes']]
    axes=[a for a in graph['axes'] if a!='site']
    lookup={}
    for scene in [scene_left,scene_right]:
        lookup[scene]={}
        for e in graph['edges']:
            u,v=e['source_index'],e['target_index']
            if states[u]['site']==states[v]['site']==scene and e['axis']!='site':
                key=(e['axis'],tuple(states[u][a] for a in axes),tuple(states[v][a] for a in axes))
                lookup[scene][key]=(u,v)
    keys=sorted(lookup[scene_left].keys()&lookup[scene_right].keys())
    pairs=[{'axis':key[0],'left_source_target':list(lookup[scene_left][key]),
            'right_source_target':list(lookup[scene_right][key])} for key in keys]
    used={side:{n for p in pairs for n in p[side+'_source_target']} for side in ['left','right']}
    return {'left_scene':scene_left,'right_scene':scene_right,'directed_edge_pairs':len(pairs),
            'unordered_inverse_edge_pairs':len({tuple(sorted(p['left_source_target'])) for p in pairs}),
            'left_node_count':len(used['left']),'right_node_count':len(used['right']),
            'edge_axes':dict(Counter(p['axis'] for p in pairs)),
            'left_node_indices':sorted(used['left']),'right_node_indices':sorted(used['right']),
            'node_value_coverage':{a:len({states[n][a] for n in used['left']}) for a in axes},'edge_pairs':pairs}


def common_session_capacity(graph,module):
    states=[n['state'] for n in graph['nodes']]
    nodes=module['left_node_indices'];adj=defaultdict(list)
    for pair in module['edge_pairs']:
        u,v=pair['left_source_target'];adj[u].append((v,pair['axis']))
    counts=Counter();strict_counts=Counter();strict_source_counts=Counter();selected=defaultdict(list)
    wanted={**{'linear_L'+str(i):10 for i in [2,3,4,5]},
            'fork_L3_root':4,'fork_L4_root':2,'fork_L4_nonroot':6,'fork_L5_root':2,'fork_L5_nonroot':6}
    node_map={}
    for pair in module['edge_pairs']:
        for left,right in zip(pair['left_source_target'],pair['right_source_target']):
            assert node_map.get(left,right)==right
            node_map[left]=right
    unseen=set(nodes);components=[]
    while unseen:
        root=unseen.pop();seen={root};stack=[root]
        while stack:
            for v,_ in adj[stack.pop()]:
                if v in unseen: unseen.remove(v);seen.add(v);stack.append(v)
        components.append({'nodes':len(seen),'identities':len({states[n]['identity'] for n in seen}),
                           'edge_axes':sorted({a for n in seen for _,a in adj[n]})})
    def visit(occ,parents,axes,fork_turn):
        length=len(axes)
        if length>=2 and len(set(axes))>=2 and (fork_turn is None or fork_turn<length):
            key=('linear' if fork_turn is None else 'fork')+'_L'+str(length)
            counts[key]+=1
            strict=fork_turn is None
            if fork_turn is not None:
                target=states[occ[fork_turn]];axis=axes[fork_turn-1]
                valid=[i for i in range(fork_turn) if {**states[occ[i]],axis:target[axis]}==target]
                strict=len(valid)==1
            strict_counts[key]+=strict
            bucket=key if fork_turn is None else key+('_root' if parents[fork_turn]==0 else '_nonroot')
            if strict:
                strict_source_counts[bucket]+=1
                if len(selected[bucket])<wanted.get(bucket,0):
                    selected[bucket].append({'left_node_indices':occ,'right_node_indices':[node_map[n] for n in occ],
                                             'parents':parents,'axes':axes})
        if length==5: return
        t=length+1
        sources=[t-1]+(list(range(t-1)) if fork_turn is None and t>=2 else [])
        for p in sources:
            for v,axis in adj[occ[p]]:
                if v in occ: continue
                isfork=p!=t-1
                if isfork and {**states[occ[-1]],axis:states[v][axis]}==states[v]: continue
                visit(occ+[v],parents+[p],axes+[axis],t if isfork else fork_turn)
    for root in nodes: visit([root],[None],[],None)
    samples=[s for key in sorted(wanted) for s in selected[key]]
    assert all(len(selected[k])==v for k,v in wanted.items())
    selected_left={n for s in samples for n in s['left_node_indices']}
    return {'scope':'exhaustive_on_exact_common_subgraph_L2_to5_no_repeated_state_min2axes_fork_followup',
            'common_graph_components':components,
            'counts':dict(counts),'strict_all_history_source_unique_counts':dict(strict_counts),
            'strict_counts_by_length_and_root':dict(strict_source_counts),
            'selected_matched_sessions_per_cohort':len(samples),'selected_quotas':wanted,
            'selected_fork_root_nonroot_counts':[8,12],
            'selected_actual_left_node_union':len(selected_left),
            'selected_actual_right_node_union':len({n for s in samples for n in s['right_node_indices']}),
            'selected_actual_non_scene_value_coverage':{a:len({states[n][a] for n in selected_left}) for a in graph['axes'] if a!='site'},
            'selected_matched_sessions':samples,
            'not_number_of_independent_scenes_or_guarantee_of_full_benchmark_sampling':True}


def main():
    catalog_path=ROUND1/'inventory/scene_catalog.json'
    checkpoint_path=OUTPUTS/'review_progress_sync_20261021_v1/checkpoint.json'
    catalog=read(catalog_path);checkpoint=read(checkpoint_path)
    metadata={x['map_path']:x for x in catalog['scenes']}
    by_package={package:group for group,packages in GROUPS.items() for package in packages}
    graphs={s:read(ROUND1/f'graph/main_scene_holdout_hybrid_{s}_graph.json') for s in ['train','test']}
    node_site=defaultdict(Counter); state_context=defaultdict(set);edge_context=defaultdict(set)
    for split,g in graphs.items():
        states=[n['state'] for n in g['nodes']]
        axes=[a for a in g['axes'] if a!='site']
        for st in states:
            node_site[st['site']][split]+=1
            state_context[st['site']].add(tuple(st[a] for a in axes))
        for e in g['edges']:
            source,target=states[e['source_index']],states[e['target_index']]
            if source['site']==target['site'] and e['axis']!='site':
                edge_context[source['site']].add((e['axis'],tuple(source[a] for a in axes),tuple(target[a] for a in axes)))
    scenes=[]
    for site in checkpoint['sites']:
        r=metadata[site['map']];package=r['package']
        scenes.append({'site':site['id'],'name':r['name'],'package':package,'map':site['map'],
                       'catalog_role_category':r['category'],'provisional_semantic_group':by_package[package],
                       'graph_node_counts':dict(node_site[site['id']]),
                       'different_scene_same_other_fields_context_count':len(state_context[site['id']]),
                       'within_scene_non_scene_directed_edges':len(edge_context[site['id']])})
    group_counts={group:{split:sum(s['graph_node_counts'].get(split,0)>0 for s in scenes if s['provisional_semantic_group']==group)
                         for split in ['train','test']} for group in GROUPS}
    random_hist=Counter()
    for holdout in itertools.combinations(range(len(scenes)),5):
        test_groups=Counter(scenes[i]['provisional_semantic_group'] for i in holdout)
        new_type_scenes=sum(n for g,n in test_groups.items() if n==len(GROUPS[g]))
        random_hist[str(new_type_scenes)]+=1
    result={'status':'name_inferred_hypothesis_not_visual_or_asset_family_annotation',
            'source_hashes':{'catalog':hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
                             'checkpoint':hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()},
            'category_primary_is_role_not_scene_type':True,
            'current_split_is_catalog_first16_last5_not_randomized':True,
            'group_scene_counts':group_counts,'scenes':scenes,
            'all_20349_random5_partitions_under_this_provisional_taxonomy':dict(random_hist),
            'taxonomy_sensitivity':['TheMetro is transport at coarse level but underground indoor station at fine level.',
                'Medieval castle and Victorian street share a broad historical-European tag but differ in function/period.',
                'Kyoto alley versus Japanese village can be split by density/era; names do not verify pixels.',
                'Coastal, theme park and post-apocalyptic groups are singletons; type and instance cannot be separated there.']}
    pairs=[]
    for a,b in itertools.combinations(scenes,2):
        i,j=a['site'],b['site']
        common_edges=edge_context[i]&edge_context[j]
        pairs.append({'left_name':a['name'],'right_name':b['name'],'left_package':a['package'],'right_package':b['package'],
                      'left_split':next(iter(a['graph_node_counts'])),'right_split':next(iter(b['graph_node_counts'])),
                      'same_coarse_group':a['provisional_semantic_group']==b['provisional_semantic_group'],
                      'same_non_scene_state_contexts':len(state_context[i]&state_context[j]),
                      'matched_non_scene_directed_edges':len(common_edges),
                      'matched_edge_axes':dict(Counter(e[0] for e in common_edges))})
    dump('scene_group_candidates.json',result)
    dump('scene_matched_support.json',{'status':'exact_symbolic_support_not_visual_matching','pairs':pairs})
    package_site={s['package']:s['site'] for s in scenes}
    training=paired_module(graphs['train'],package_site['Cyberpunk_City'],package_site['CHERRY_TREE'])
    testing=paired_module(graphs['test'],package_site['Synthwave_city'],package_site['UrbanJapan'])
    testing['matched_multiround_capacity']=common_session_capacity(graphs['test'],testing)
    future_sites={s['site'] for s in scenes if s['provisional_semantic_group']=='futuristic_stylized_city'}
    train_states=[n['state'] for n in graphs['train']['nodes']]
    excluded_modules=set(training['left_node_indices'])|set(training['right_node_indices'])
    common_base={i for i,s in enumerate(train_states) if s['site'] not in future_sites and i not in excluded_modules}
    base_edges=[e for e in graphs['train']['edges'] if e['source_index'] in common_base and e['target_index'] in common_base]
    initial_base_count=len(common_base)
    common_base={n for e in base_edges for n in [e['source_index'],e['target_index']]}
    factorial={'status':'symbolic_2x2_design_not_training_run_or_visual_acceptance',
               'source_graph_sha256':{split:hashlib.sha256((ROUND1/f'graph/main_scene_holdout_hybrid_{split}_graph.json').read_bytes()).hexdigest() for split in ['train','test']},
               'factor_A':'train futuristic type exposure via paired module vs donor module',
               'factor_B':'test held-out Synthwave target cohort vs UrbanJapan control cohort',
               'all_test_scene_instances_unseen_in_both_training_regimes':True,
               'type_taxonomy_pending_pre_model_human_review':True,
               'common_base_nodes':len(common_base),'common_base_directed_edges':len(base_edges),
               'common_base_node_indices':sorted(common_base),
               'excluded_isolated_common_base_nodes':initial_base_count-len(common_base),
               'equal_synthetic_train_node_count_each_regime':len(common_base)+training['left_node_count'],
               'equal_selected_directed_edge_count_each_regime':len(base_edges)+training['directed_edge_pairs'],
               'training_exposure_module':training,'matched_test_module':testing,
               'new_GT_video_nodes_required_for_this_design':0,
               'existing_main_nodes_repurposed_does_not_create_new_independent_media':True}
    assert training['left_node_count']==training['right_node_count']
    dump('minimal_scene_exposure_2x2.json',factorial)
    testpairs=[p for p in pairs if p['left_split']==p['right_split']=='test']
    print(json.dumps({'group_counts':group_counts,'factorial_summary':{k:factorial[k] for k in [
        'common_base_nodes','common_base_directed_edges','equal_synthetic_train_node_count_each_regime',
        'equal_selected_directed_edge_count_each_regime','new_GT_video_nodes_required_for_this_design']},
        'training_module_summary':{k:training[k] for k in ['directed_edge_pairs','unordered_inverse_edge_pairs','left_node_count','node_value_coverage']},
        'test_module_summary':{k:testing[k] for k in ['directed_edge_pairs','unordered_inverse_edge_pairs','left_node_count','node_value_coverage']},
        'matched_multiround_summary':{k:testing['matched_multiround_capacity'][k] for k in [
            'strict_all_history_source_unique_counts','selected_matched_sessions_per_cohort',
            'selected_actual_left_node_union','selected_actual_right_node_union']}},ensure_ascii=True,indent=2))


if __name__=='__main__': main()
