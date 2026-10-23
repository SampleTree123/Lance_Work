"""Recoverable bounded comparison queue; root is sole UE executor."""
from pathlib import Path
import argparse,sys,subprocess,json
import run_all_motion_camera_review_v1 as base
S=Path(__file__).resolve().parent
RUN=S.parents[1]/'outputs/camera_follow_compact_scene_20261015_v1'

def remote(code,label,run=RUN):
 folder=RUN/'commands';folder.mkdir(parents=True,exist_ok=True)
 script=folder/(label+'.py')
 script.write_text('import sys,unreal as u,json,importlib\nfrom pathlib import Path\nsys.path.insert(0,'+repr(str(S))+')\nimport ue_follow_compact_review_v1 as review\nimportlib.reload(review)\nreview.RUN=Path('+repr(str(RUN))+')\nreview.ASSETS='+repr(ASSETS)+'\nreview.PLAN_NAME='+repr(PLAN_NAME)+'\n'+code,encoding='utf-8')
 with script.with_suffix('.log').open('w',encoding='utf-8') as out:
  result=subprocess.run([sys.executable,'-X','utf8',str(S/'ue_remote_exec.py'),'--project','datatry_02','--script',str(script)],stdout=out,stderr=subprocess.STDOUT)
 if result.returncode:raise RuntimeError('UE command failed: '+str(script.with_suffix('.log')))

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--plan',default='camera_compact_comparison_plan_v1.json');parser.add_argument('--ids',nargs='*');parser.add_argument('--prefix',default='compact');parser.add_argument('--run-root',type=Path,default=RUN);parser.add_argument('--assets',default='/Game/DataMake/Validation/CameraFollowCompact20261015');args=parser.parse_args()
 RUN=args.run_root.resolve();ASSETS=args.assets
 if not RUN.is_relative_to(S.parents[1]/'outputs') or not ASSETS.startswith('/Game/DataMake/Validation/'):raise ValueError('Comparison output must remain in owned validation scope')
 PLAN_NAME=args.plan;path=RUN/PLAN_NAME;plan=base.read(path);digest=base.sha(path)
 rows=[s for s in plan['shots'] if not args.ids or s['shot_id'] in args.ids]
 base.remote=remote;base.RUN=RUN;base.PLAN_NAME=PLAN_NAME
 with base.run_lock(RUN):
  shots={s['shot_id']:s for s in rows};done=base.verified_rows(shots,RUN)
  for orientation in ('landscape','portrait'):
   selected=[s for s in rows if s['orientation']==orientation]
   for index,start in enumerate(range(0,len(selected),4)):
    group=selected[start:start+4];attempt=f'{args.prefix}_{orientation}_{index:02d}_{digest[:8]}'
    report=base.complete_batch(attempt,group,done,path,digest,RUN)
    if report:
     for row in report['videos']:done[row['shot_id']]=row
     base.retire_verified_raw(attempt,report,shots,RUN,fresh_process=True)
    base.atomic_json(RUN/(args.prefix+'_progress.json'),{'verified':len(done),'target':len(rows),'last_attempt':attempt})
    print(f'{args.prefix}: {len(done)}/{len(rows)} verified',flush=True)
