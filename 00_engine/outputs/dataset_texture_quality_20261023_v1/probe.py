"""Run bounded sequential A/B jobs against saved pilot maps."""
import sys,time,json,argparse
from pathlib import Path
RUN=Path(__file__).resolve().parent
ROOT=RUN.parents[2]
sys.path.insert(0,str(ROOT/'00_engine/scripts/unreal'))
import run_dataset_render_v11 as driver
p=argparse.ArgumentParser();p.add_argument('--mode',choices=['inherit','fully_load','disabled'],required=True);p.add_argument('--job',default='ref_hair_train_node_000000_front');p.add_argument('--fresh',action='store_true');p.add_argument('--fixture',action='store_true');p.add_argument('--evict',action='store_true');opts=p.parse_args()
out=RUN/((opts.job+'_'+opts.mode)+('_fresh' if opts.fresh or opts.fixture else '')+('_evict' if opts.evict else ''))
args=driver.parse_args(['--run-root',str(out),'--command-only','status','--command-timeout','600'])
args.worker_module='ue_dataset_texture_probe_v1'
transport=driver.Transport(args)
request={'run_root':str(out),'source_run':str(RUN.parent/'dataset_render_pilot_20261023_v1'),'job_id':opts.job,'texture_mode':opts.mode}
if opts.fresh or opts.fixture:request['source_run']=str(RUN/'fresh_fixture')
with driver.queue_lock(RUN):
    if not driver.renderer_idle(transport(dict(request,action='status'))):raise RuntimeError('UE busy')
    if opts.fresh:
        import shutil
        old=RUN.parent/'dataset_render_pilot_20261023_v1'; fixture=RUN/'fresh_fixture'
        for rel in ['main_jobs.json','reference_pilot_jobs.json','jobs/train_node_000000/prepared.json']:
            dst=fixture/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(old/rel,dst)
        result=transport(dict(request,action='prepare_reference',fixture_run=str(fixture)));print('fresh prepared',result.get('reused'),flush=True)
    start=time.monotonic()
    if opts.evict:transport(dict(request,action='evict'))
    submitted=transport(dict(request,action='render'));print('Submitted',opts.mode,opts.job,flush=True)
    result=driver.wait_render(transport,request,time.monotonic(),600,1,submitted=submitted)
    driver.assert_accepted(result)
    driver.write(out/'RESULT.json',{'seconds':time.monotonic()-start,'result':result})
    print('Completed',time.monotonic()-start,flush=True)
