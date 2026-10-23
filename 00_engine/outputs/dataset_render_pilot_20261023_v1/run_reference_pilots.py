"""Bounded local reference-image prototype runner; main dataset remains unchanged."""
import sys,time,json
from pathlib import Path
RUN=Path(__file__).resolve().parent
S=RUN.parents[1]/'scripts/unreal'
sys.path.insert(0,str(S))
import run_dataset_render_v11 as driver
args=driver.parse_args(['--run-root',str(RUN),'--jobs',str(RUN/'reference_pilot_jobs.json'),'--worker-module','ue_dataset_reference_pilot_v11','--command-only','status','--command-timeout','600'])
transport=driver.Transport(args)
results=[]
with driver.queue_lock(RUN):
    for jid in ['ref_garment_train_node_000000_front','ref_identity_train_node_000000_front','ref_hair_train_node_000000_front','ref_hair_train_node_000000_back']:
        request={'run_root':str(RUN),'jobs_path':str(args.jobs),'job_id':jid,'workspace':str(args.workspace),'project_root':str(args.project_root),'pool_mb':10240}
        if not driver.renderer_idle(transport(dict(request,action='status'))):raise RuntimeError('UE busy')
        start=time.monotonic()
        prepared=transport(dict(request,action='prepare'));print(jid,'prepared',flush=True)
        rendering=transport(dict(request,action='render'))
        done=driver.wait_render(transport,request,time.monotonic(),600,2,submitted=rendering)
        driver.assert_accepted(done)
        results.append({'job_id':jid,'seconds':time.monotonic()-start,'receipt':done['receipt_path'],'image':str(RUN/'jobs'/jid/'frames/frame_0000.png')})
        driver.write(RUN/'REFERENCE_LOCAL_RESULTS.json',{'prototype_not_approved':True,'results':results})
        print(jid,'done',flush=True)
