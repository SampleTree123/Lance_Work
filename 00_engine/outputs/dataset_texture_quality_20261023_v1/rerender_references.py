"""Six reference prototypes, after the corrected main pilot is idle and complete."""
import sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parent
RUN=BASE/'corrected'
sys.path.insert(0,str(BASE.parents[2]/'00_engine/scripts/unreal'))
import run_dataset_render_v11 as d
args=d.parse_args(['--run-root',str(RUN),'--jobs',str(RUN/'reference_pilot_jobs.json'),'--worker-module','ue_dataset_reference_pilot_v11','--command-only','status','--command-timeout','600'])
t=d.Transport(args); results=[]
with d.queue_lock(RUN):
    for job in d.read(RUN/'reference_pilot_jobs.json')['jobs']:
        request={'run_root':str(RUN),'jobs_path':str(args.jobs),'job_id':job['job_id'],'pool_mb':10240}
        if not d.renderer_idle(t(dict(request,action='status'))):raise RuntimeError('UE busy')
        start=time.monotonic(); prepared=t(dict(request,action='prepare'));print(job['job_id'],'prepared',flush=True)
        submitted=t(dict(request,action='render'))
        done=d.wait_render(t,request,time.monotonic(),600,1,submitted=submitted);d.assert_accepted(done)
        results.append({'job_id':job['job_id'],'seconds':time.monotonic()-start,'receipt':done['receipt_path']})
        d.write(RUN/'REFERENCE_RESULTS.json',{'prototype_not_approved':True,'results':results})
        print(job['job_id'],'done',flush=True)
