"""Run a separate, preserved v9 graph/reuse trial with exact quotas."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,sys,time
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from build_and_sample import Domain,load_saved_graph,save_graph,read,write,support,pin
def main():
    p=argparse.ArgumentParser();p.add_argument('--graph',default='graph');p.add_argument('--output',required=True);p.add_argument('--split',choices=['train','test'],required=True);p.add_argument('--cap2',type=int,default=0);p.add_argument('--third-weight',type=float,default=3);a=p.parse_args()
    source=ROOT/a.graph/a.split;dest=ROOT/a.output/a.split
    if dest.exists():raise FileExistsError(dest)
    code=(ROOT/'sampler_v9.py').read_text(encoding='utf-8')
    code=code.replace('weight = (.30, 1.0, 3.0, .0008)[count]',f'weight = (.30, 1.0, {a.third_weight}, .0008)[count]')
    snapshot=ROOT/a.output/'sampler_source.py';snapshot.parent.mkdir(parents=True,exist_ok=True);snapshot.write_text(code,encoding='utf-8')
    spec=importlib.util.spec_from_file_location('v9_trial_sampler',snapshot);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    params={'history_decay':.4,'nonidentity_upper_slack':.025,'cap2_attempts':a.cap2,'max_attempts':240,'tail_fallback_after':120,'third_weight':a.third_weight};write(snapshot.parent/'SAMPLER_CODE.json',{'source':pin(snapshot),'graph_source':str(source),'parameters':params,'seed':2026102261+(a.split=='test')})
    d=Domain();g=load_saved_graph(source,d);started=time.time()
    sessions,sampling=m.sample(g,12000 if a.split=='train' else 2400,2026102261+(a.split=='test'),history_decay=.4,nonidentity_upper_slack=.025,cap2_attempts=a.cap2,max_attempts=240,tail_fallback_after=120,progress_every=1000)
    dest.mkdir(parents=True);write(dest/'sampling.json',sampling)
    construction=read(source/'metrics.json')['construction'];construction.update(sampling=sampling,sample_seed=2026102261+(a.split=='test'),sampler_source_sha256=pin(snapshot)['sha256'],sampling_parameter_overrides=params)
    save_graph(dest,g,sessions,construction)
    used={n for c in sessions for n in c['history']};coverage=support(g,used)
    summary={'complete':sampling['complete'],'nodes':len(g.nodes),'used_nodes':len(used),'minimum_actual_cameras':min(map(len,coverage.values())),'four_use_edge_fraction':sampling['four_use_edge_fraction'],'axis_reuse':sampling['axis_reuse'],'nonidentity_relative_deviation':sampling['nonidentity_relative_deviation'],'elapsed_seconds':time.time()-started}
    write(snapshot.parent/'SUMMARY.json',summary);print('TRIAL',a.split,json.dumps(summary),flush=True)
if __name__=='__main__':main()
