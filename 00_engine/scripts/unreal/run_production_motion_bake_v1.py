"""Serial root-owned remote bake driver; durable per-task receipts allow resume."""
from pathlib import Path
import json, subprocess, sys, time
import production_motion_contract_v1 as c

def main():
    tasks=c.read(c.RUN/'ue_tasks_v1.json')['tasks'];started=time.time()
    for task in tasks:
        if '--skip-failed' in sys.argv and Path(task['report_path']).exists() and not c.read(task['report_path']).get('success'):
            print('failed_pending',task['motion_id'],task['sex'],flush=True);continue
        if Path(task['report_path']).exists() and c.read(task['report_path']).get('success'):
            print('existing',task['motion_id'],task['sex'],flush=True);continue
        code=("import sys; sys.path.insert(0,'D:/UE/Lance_Work/00_engine/scripts/unreal'); "
              "import ue_production_motion_library_v1 as p; import production_motion_contract_v1 as c; "
              f"task=next(t for t in c.read(c.RUN/'ue_tasks_v1.json')['tasks'] if t['motion_id']=={task['motion_id']!r} and t['sex']=={task['sex']!r}); "
              "result=p.run(task); print({'success':result['success'],'motion':task['motion_id'],'sex':task['sex']})")
        r=subprocess.run([sys.executable,'-X','utf8',str(Path(__file__).with_name('ue_remote_exec.py')),
                          '--project','datatry_02','--command',code],capture_output=True,text=True,encoding='utf-8',timeout=180)
        log=c.RUN/'driver'/f"{task['motion_id']}_{task['sex']}.log";log.parent.mkdir(exist_ok=True)
        log.write_text(r.stdout+r.stderr,encoding='utf-8')
        if not Path(task['report_path']).exists() or not c.read(task['report_path']).get('success'):
            raise RuntimeError('Bake failed; inspect '+str(log))
        print('baked',task['motion_id'],task['sex'],round(time.time()-started,1),flush=True)
    c.publish_runtime_manifest(require_complete='--skip-failed' not in sys.argv)
    print('complete52',round(time.time()-started,1),flush=True)

if __name__=='__main__':main()
