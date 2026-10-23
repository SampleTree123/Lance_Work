"""Small legal action/camera support expansion and actual .4 sampling, no UE."""
from pathlib import Path
from collections import defaultdict,Counter
import argparse,copy,hashlib,importlib.util,json,sys,time
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent
V6=OUT/'dataset_compact_graph_20261022_v6'
sys.path.insert(0,str(V6))
from build_compact import Domain,Graph,load_saved_graph,legal_add,save_empty_graph,read,write,token
sys.path.insert(0,str(OUT/'dataset_local_support_20261021_v3'))
from resample_local import save_graph
sys.path.insert(0,str(OUT/'dataset_balanced_graph_20261022_v5'))
from audit_candidate import Rules

def pin(p):return {'path':str(Path(p).resolve()),'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()}
def support(g,used=None):
    out=defaultdict(set)
    for u,s in enumerate(g.nodes):
        if used is None or u in used:out[s['action']].add(s['camera'])
    return {a:sorted(cs) for a,cs in sorted(out.items())}
def build():
    domain=Domain();rules=Rules();forbidden=set();meta={}
    for split in ('train','test'):
        source=V6/'selected_seed1'/split;target=ROOT/'graph'/split
        if target.exists():raise FileExistsError(target)
        g=load_saved_graph(source,domain,forbidden);old=len(g.nodes)
        actions=list(domain.actions) if split=='train' else sorted({s['action'] for s in g.nodes})
        before=support(g);contexts=defaultdict(list)
        for u,s in enumerate(g.nodes):
            signature=token({k:v for k,v in s.items() if k not in ('action','camera')})
            contexts[signature].append(u)
        # Use one of the already broad camera contexts: each new state joins
        # an existing action line and its same-action camera line.
        contexts=[ids for ids in contexts.values() if len({g.nodes[u]['camera'] for u in ids})>=2]
        records=[]
        for action in sorted(actions,key=lambda a:len(before.get(a,[]))):
            missing=max(0,10-len(support(g).get(action,[])))
            if not missing:continue
            existing=set(support(g).get(action,[]));options=[]
            for ids in contexts:
                anchors=[u for u in ids if g.nodes[u]['camera']!='front_head' and not rules.valid_state(dict(g.nodes[u],action=action))]
                if not anchors:continue
                u=anchors[0];viable=[]
                for camera in domain.cameras:
                    if camera=='front_head':continue
                    s=dict(g.nodes[u],action=action,camera=camera)
                    if camera not in existing and not rules.valid_state(s) and domain.canonical(s) not in forbidden:
                        viable.append((camera,u))
                if len(viable)>=missing:
                    options.append((len({g.nodes[v]['camera'] for v in ids}),ids,viable,u))
            if not options:raise RuntimeError(('cannot complete action camera minimum',split,action,missing))
            _,ids,viable,anchor=max(options,key=lambda row:row[0])
            anchorstate=copy.deepcopy(g.nodes[anchor]);anchorstate['action']=action
            action_anchor=legal_add(g,anchor,anchorstate,'action') if g.nodes[anchor]['action']!=action else anchor
            if action_anchor is None:raise RuntimeError(('action anchor rejected',split,action))
            # Spread static/dynamic/front/nonfront cameras, avoid head-only action context.
            priority=['front_full','side_full','back_full','front_three_quarter_full','rear_three_quarter_full','front_upper','dolly_in_front','dolly_out_front','orbit_120','orbit_360','high_full','low_full','dolly_in_side','dolly_out_side']
            viable.sort(key=lambda row:(priority.index(row[0]) if row[0] in priority else 99,row[0]))
            for camera,u in viable[:missing]:
                t=copy.deepcopy(g.nodes[action_anchor]);t['camera']=camera
                v=action_anchor if t==g.nodes[action_anchor] else legal_add(g,action_anchor,t,'camera')
                if v is None:raise RuntimeError(('legal support expansion rejected',split,action,camera))
                records.append({'action':action,'camera':camera,'source':g.provenance[v]['parent'],'axis':g.provenance[v]['axis'],'target':v})
        after=support(g)
        assert all(len(after[a])>=10 for a in actions)
        target.parent.mkdir(parents=True,exist_ok=True)
        construction={'strategy':'retain original verified graph; add missing action-camera combinations on existing broad legal camera contexts','source':str(source),'original_nodes':old,'added_nodes':len(g.nodes)-old,'minimum_cameras_per_represented_action':10,'actions_required':actions,'coverage_before':before,'coverage_after':after,'legal_additions':records,'test_full_catalog_coverage_required':False,'all_new_nodes_are_true_atomic_action_or_camera_targets':True,'inputs':[pin(source/f) for f in ('nodes.json','edges.json','metrics.json')]}
        save_empty_graph(target,g,construction);meta[split]={'nodes':len(g.nodes),'added':len(g.nodes)-old,'action_camera_pairs':sum(map(len,after.values())),'minimum_cameras':min(map(len,after.values())),'axis_edges':dict(Counter(e['axis'] for e in g.edges.values()))}
        forbidden.update(g.keys)
        print('GRAPH',split,json.dumps(meta[split]),flush=True)
    write(ROOT/'GRAPH_SUMMARY.json',meta)
    # Freeze a clear, reviewable sampler change. All other v68 logic is retained.
    code=(V6/'sample_compact_v68_snapshot.py').read_text(encoding='utf-8')
    needle="    return tuple(out)"
    assert code.count(needle)==1
    code=code.replace(needle,"    out.append(('action_camera', (state['action'], state['camera'])))\n"+needle)
    needle="if field == axis or (axis == 'wardrobe' and field.startswith('wardrobe_')):"
    assert code.count(needle)==1
    code=code.replace(needle,"if field == axis or (axis in ('action','camera') and field == 'action_camera') or (axis == 'wardrobe' and field.startswith('wardrobe_')):")
    needle="weight = (1.0, 1.2, .045, .0008)[count]"
    assert code.count(needle)==1
    code=code.replace(needle,"weight = (.30, 1.0, 3.0, .0008)[count]")
    code=code.replace("'reuse_note': 'Reuse below two can result from coverage, zero/one-use preference, fixed fork jobs, and local graph support; no missing edge is invented to raise reuse.'", "'reuse_note': 'V9 desired mean used-edge reuse about 2.5; target weights count0=.30/count1=1/count2=3/count3=.0008; cap3 available from attempt0, cap4 final rare fallback. Actual mean is reported, not forced.'")
    (ROOT/'sampler_v9.py').write_text(code,encoding='utf-8')
    write(ROOT/'SAMPLER_CHANGES.json',{'baseline':pin(V6/'sample_compact_v68_snapshot.py'),'snapshot':pin(ROOT/'sampler_v9.py'),'history_decay':.4,'new_coverage':'explicit warmup for every action-camera pair represented in graph, by real action or camera target; fixed original kind/length/fork/start-camera quota retained','reuse_desired_mean':2.5,'cap2_attempts':0,'count0_1_2_3_edge_weights':[.30,1.0,3.0,.0008],'cap4_policy':'unchanged final 3% retry tail only; coverage override may request fourth if necessary','max_attempts':240,'tail_fallback_after':120,'nonidentity_upper_slack':.025,'source_builder':pin(__file__)})

def sample():
    import sampler_v9
    d=Domain();forbidden=set();summary={};start=time.time()
    (ROOT/'structural_candidate').mkdir(parents=True,exist_ok=True)
    write(ROOT/'structural_candidate/SAMPLER_CODE.json',{'source':pin(ROOT/'sampler_v9.py'),'changes':str(ROOT/'SAMPLER_CHANGES.json'),'seed':{'train':2026102261,'test':2026102262},'parameter_overrides':{'history_decay':.4,'nonidentity_upper_slack':.025,'cap2_attempts':0,'max_attempts':240,'tail_fallback_after':120}})
    for i,(split,total) in enumerate([('train',12000),('test',2400)]):
        source=ROOT/'graph'/split;dest=ROOT/'structural_candidate'/split
        if dest.exists():raise FileExistsError(dest)
        g=load_saved_graph(source,d,forbidden)
        sessions,sampling=sampler_v9.sample(g,total,2026102261+i,history_decay=.4,nonidentity_upper_slack=.025,cap2_attempts=0,max_attempts=240,tail_fallback_after=120,progress_every=1000)
        dest.mkdir(parents=True);write(dest/'sampling.json',sampling)
        construction=read(source/'metrics.json')['construction'];construction.update(sampling=sampling,sample_seed=2026102261+i,sampler_source_sha256=pin(ROOT/'sampler_v9.py')['sha256'])
        metrics=save_graph(dest,g,sessions,construction)
        used={n for c in sessions for n in c['history']};coverage=support(g,used)
        targets=defaultdict(set)
        for c in sessions:
            for st in c['steps']:
                s=g.nodes[st['target']]
                if st['axis'] in ('action','camera'):targets[s['action']].add(s['camera'])
        result={'complete':sampling['complete'],'nodes':len(g.nodes),'used_nodes':len(used),'sessions':len(sessions),'actual_main_action_camera':coverage,'target_action_camera':{a:sorted(cs) for a,cs in targets.items()},'minimum_actual_cameras':min(map(len,coverage.values())),'axis_reuse':sampling.get('axis_reuse'),'edge_reuse_histogram':sampling.get('edge_reuse_histogram'),'four_use_edge_fraction':sampling.get('four_use_edge_fraction'),'nonidentity_relative_deviation':sampling.get('nonidentity_relative_deviation'),'edited_attribute_target_coverage':sampling.get('edited_attribute_target_coverage'),'start_camera_quota_met':sampling.get('start_camera_quota_met')}
        summary[split]=result;write(ROOT/'STRUCTURAL_SUMMARY.json',summary)
        forbidden.update(g.keys);print('SAMPLED',split,json.dumps({k:v for k,v in result.items() if k not in ('actual_main_action_camera','target_action_camera','edited_attribute_target_coverage')}),flush=True)
    write(ROOT/'structural_candidate/SUMMARY.json',{'splits':summary,'elapsed_seconds':time.time()-start,'sampler':pin(ROOT/'sampler_v9.py')})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['build','sample'],required=True);a=p.parse_args()
    build() if a.mode=='build' else sample()
