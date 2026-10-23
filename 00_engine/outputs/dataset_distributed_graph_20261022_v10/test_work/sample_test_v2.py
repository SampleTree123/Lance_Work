"""Actual sampler with balanced history exposure feedback and frozen snapshots."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys,time
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent;OUT=ROOT.parent.parent
sys.path.insert(0,str(OUT/'dataset_local_support_20261021_v3'))
from resample_local import Domain,load_graph,save_graph,read,write
def pin(p):return {'path':str(Path(p).resolve()),'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--trial',required=True);ap.add_argument('--output',default='candidate1');ap.add_argument('--split',default='train',choices=['train','test']);ap.add_argument('--slack',type=float,default=.04);ap.add_argument('--attempts',type=int,default=360);a=ap.parse_args()
    folder=ROOT/a.trial/a.output;target=folder/a.split
    if target.exists():raise FileExistsError(target)
    folder.mkdir(parents=True,exist_ok=True)
    code=(OUT/'dataset_compact_graph_20261022_v6/sample_compact_v68_snapshot.py').read_text(encoding='utf-8')
    code=code.replace('weight = (1.0, 1.2, .045, .0008)[count]','weight = (.30, 1.0, 3.0, .0005)[count]')
    needle='    def source_support_weight(u):'
    assert code.count(needle)==1
    extra='''    history_counts = defaultdict(Counter)
    history_cache = {}
    visible_assets = []
    frequency_fields = ('identity','action','hair','hair_color','site')
    frequency_pools = {f: {s[f] for s in g.nodes} for f in frequency_fields}
    frequency_cameras = defaultdict(set)
    all_visible_core = set()
    for state in g.nodes:
        core = set(g.d.nc.core_asset_ids(state['sex'],state['wardrobe']))
        if state['camera']=='front_head': core=set()
        elif state['camera'] in {'front_upper','front_three_quarter_upper','side_upper','rear_three_quarter_upper','back_upper'}:
            core &= set(g.d.nc.upper_asset_ids(state['sex'],state['wardrobe']))
        visible_assets.append(core); all_visible_core.update(core)
        if state['camera']!='front_head': frequency_cameras[state['action']].add(state['camera'])

    def occurrence_weight(u):
        if u in history_cache:return history_cache[u]
        state=g.nodes[u];total=sum(node_use.values())
        weight=((total/max(1,len(g.nodes))+2)/(node_use[u]+2))**1.5
        for field in frequency_fields:
            expected=(total+20)/len(frequency_pools[field])
            ratio=(expected+5)/(history_counts[field][state[field]]+5)
            weight*=max(.20,min(5,ratio))**1.0
        core=visible_assets[u]
        if core:
            expected=(sum(history_counts['visible_core'].values())+20)/max(1,len(all_visible_core))
            weight*=math.exp(sum(math.log(max(.15,min(6,(expected+5)/(history_counts['visible_core'][v]+5)))) for v in core)/len(core)*4.0)
        if state['camera']!='front_head':
            expected=(sum(v for (act,cam),v in history_counts['action_camera'].items() if act==state['action'])+10)/max(1,len(frequency_cameras[state['action']]))
            weight*=max(.15,min(6,(expected+4)/(history_counts['action_camera'][state['action'],state['camera']]+4)))**8.0
        history_cache[u]=weight
        return weight

    def camera_frequency_ratio(u):
        state=g.nodes[u]
        if state['camera']=='front_head':return 1.0
        expected=(sum(v for (act,cam),v in history_counts['action_camera'].items() if act==state['action'])+10)/max(1,len(frequency_cameras[state['action']]))
        return (expected+4)/(history_counts['action_camera'][state['action'],state['camera']]+4)

    def camera_exit_start_weight(u):
        if g.nodes[u]['camera'] not in {'front_upper','front_three_quarter_upper','side_upper','rear_three_quarter_upper','back_upper'}:return 1.0
        if camera_frequency_ratio(u)>.90:return 1.0
        return 4.0 if explicit[u].get('camera') else .20

    def axis_frequency_weight(u,axis,options):
        if axis!='camera':return 1.0
        current=max(.1,camera_frequency_ratio(u))
        ratios=[camera_frequency_ratio(v)/current for v in options]
        weight=max(.15,min(8,sum(ratios)/len(ratios)))**3
        if g.nodes[u]['camera'] in {'front_upper','front_three_quarter_upper','side_upper','rear_three_quarter_upper','back_upper'} and current<.80:weight*=30
        return weight

'''
    code=code.replace(needle,extra+needle)
    code=code.replace('weights.append(weight * capacity_weight * source_support_weight(u) * support[u])','weights.append(weight * capacity_weight * source_support_weight(u) * support[u] * occurrence_weight(u) * camera_exit_start_weight(u))')
    needle='        weights = []\n        for u in candidates:'
    assert code.count(needle)==1
    code=code.replace(needle,'''        # A fixed upper-camera quota does not require every unseen cube state
        # to become a start. When that conditional camera is overexposed, use
        # any real same-camera source that still has a legal camera exit.
        if job_camera in {'front_upper','front_three_quarter_upper','side_upper','rear_three_quarter_upper','back_upper'}:
            exits=[u for rows in live_groups.values() for u in rows
                   if camera_frequency_ratio(u)<.80 and any(edge_use[u,v]<cap for v in explicit[u].get('camera',()))]
            if exits:candidates=sorted(set(exits))
'''+needle)
    code=code.replace('return weight * source_support_weight(v)','return weight * source_support_weight(v) * occurrence_weight(v)')
    code=code.replace('* ratio ** feedback_exponent)','* ratio ** feedback_exponent * axis_frequency_weight(u,axis,options[axis]))')
    needle='            node_use.update(history)'
    assert code.count(needle)==1
    code=code.replace(needle,needle+'''
            for history_node in history:
                history_state=g.nodes[history_node]
                for field in frequency_fields:history_counts[field][history_state[field]]+=1
                history_counts['visible_core'].update(visible_assets[history_node])
                if history_state['camera']!='front_head':history_counts['action_camera'][history_state['action'],history_state['camera']]+=1
            history_cache.clear()
''')
    snapshot=folder/'sampler_source.py';snapshot.write_text(code,encoding='utf-8')
    spec=importlib.util.spec_from_file_location('distributed_sample',snapshot);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    source=ROOT/a.trial/'graph'/a.split;g=load_graph(source,Domain())
    params={'history_decay':.4,'nonidentity_upper_slack':a.slack,'cap2_attempts':0,'max_attempts':a.attempts,'tail_fallback_after':120,'identity_target_fraction':.09}
    write(folder/'SAMPLER_CODE.json',{'source':pin(snapshot),'graph_source':str(source),'seed':2026102210+(a.split=='test'),'parameters':params,'frequency_feedback':'actual full history occurrences; per-node usage, identity/action/hair/color/site, visible formal core, per-action camera mean; source and target selection plus camera/action-axis expected exposure improvement; upper overrepresented starts prefer legal camera exits; no fabricated edges','builder':pin(__file__)})
    started=time.time();sessions,sampling=module.sample(g,12000 if a.split=='train' else 2400,2026102210+(a.split=='test'),progress_every=1000,**params)
    target.mkdir(parents=True);write(target/'sampling.json',sampling)
    construction=read(source/'metrics.json')['construction'];construction.update(sampling=sampling,sample_seed=2026102210+(a.split=='test'),sampler_source=pin(snapshot),sampling_parameters=params)
    metrics=save_graph(target,g,sessions,construction)
    summary={'complete':sampling['complete'],'sessions':len(sessions),'nodes':len(g.nodes),'used_nodes':len({u for c in sessions for u in c['history']}),'axis_counts':sampling['axis_counts'],'axis_reuse':sampling['axis_reuse'],'four_use_edge_fraction':sampling['four_use_edge_fraction'],'nonidentity_relative_deviation':sampling['nonidentity_relative_deviation'],'elapsed_seconds':time.time()-started}
    write(folder/f'SUMMARY_{a.split}.json',summary);print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
