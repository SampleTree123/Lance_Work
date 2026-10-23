"""Root-only serial primary-map screening. Keeps every attempted map and report."""
from pathlib import Path
import json,sys,subprocess,time,argparse
S=Path(__file__).resolve().parent
RUN=S.parents[1]/'outputs/all_primary_scene_sites_20261015_v1'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,d):
 p=Path(p);p.parent.mkdir(exist_ok=True,parents=True);q=p.with_suffix('.tmp');q.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8');q.replace(p)
def remote(code,name):
 p=RUN/'commands'/(name+'.py');p.parent.mkdir(exist_ok=True,parents=True);p.write_text(code,encoding='utf-8')
 result=subprocess.run([sys.executable,'-X','utf8',str(S/'ue_remote_exec.py'),'--project','datatry_02','--script',str(p)],capture_output=True,text=True,encoding='utf-8',timeout=240)
 p.with_suffix('.log').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
 if result.returncode:raise RuntimeError('UE command failed: '+str(p.with_suffix('.log')))
 envelope=json.loads(result.stdout)
 if not isinstance(envelope,dict) or envelope.get('command_result',{}).get('success') is not True:
  raise RuntimeError('UE command envelope reported failure: '+str(p.with_suffix('.log')))
 return envelope

def matching_dual_complete(map_name,position=None,yaw=None):
 """Reuse only a fully verified fresh v3 report and its matching dual receipt."""
 from merge_primary_scene_surveys_v1 import _validate_dual, _same_point
 cache={};matches=[]
 for path in sorted((RUN/'dual_signature_reports').glob('*.json')):
  try:
   if read(path).get('map')!=map_name:continue
   report,index,evidence=_validate_dual(path,RUN.resolve(),cache)
   candidate=report['full_attempts'][index]['candidate']
   if not _same_point(report.get('site') or {},candidate):continue
   if position is not None and not _same_point({'position':position,'yaw':yaw},candidate):continue
   matches.append((Path(evidence['base_report']['path']),report,path))
  except (ValueError,OSError,KeyError,TypeError,IndexError):continue
 return max(matches,key=lambda row:(row[1]['full_attempts'][row[1]['selected_full_attempt_index']]['summary']['no_proxy_conflict_combinations'],row[1]['attempt_id']),default=None)
def execute(start=0,end=26):
 inventory=read(RUN/'survey_inventory_v1.json');results=[]
 for index,scene in enumerate(inventory['scenes']):
  if not start<=index<end:continue
  existing=matching_dual_complete(scene['map_path'])
  if existing:
   p,d,dual=existing;results.append({'index':index,'map':scene['map_path'],'report':str(p),'dual_evidence':str(dual),'status':d['status'],'reused_verified_dual':True});continue
  state=read(RUN/'survey_progress.json') if (RUN/'survey_progress.json').exists() else {}
  if state.get('status')=='running' and state.get('map')!=scene['map_path']:
   raise RuntimeError('Another map survey is running; wait before changing levels')
  if state.get('map')!=scene['map_path'] or state.get('status')!='running':
   code="import sys,unreal as u,importlib\nsys.path.insert(0,"+repr(str(S))+")\nimport ue_primary_scene_survey_dual_v3 as survey\nassert survey.poll().get('status')!='running', 'Another survey is still active'\nimportlib.reload(survey)\nassert not u.get_editor_subsystem(u.MoviePipelineQueueSubsystem).is_rendering()\nimport ue_scene_site_review_v1 as worker\nworker.restore()\nassert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'Unsaved map changes remain after restoring owned preview; inspect before loading another level'\nassert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level("+repr(scene['map_path'])+")\nworker.enable_live_view()\nprint(survey.start(max_full_attempts=1))\n"
   remote(code,f'survey_start_{index:02d}')
  deadline=time.monotonic()+1800;last=0
  while True:
   if (RUN/'STOP').exists():return
   state=read(RUN/'survey_progress.json')
   if state.get('map')==scene['map_path'] and state.get('status')!='running':break
   if time.monotonic()>deadline:raise RuntimeError('Survey exceeded30min; leavecurrentUEstate forinspection')
   if time.monotonic()-last>60:
    last=time.monotonic();print(index,scene['label'],state.get('phase'),state.get('full_check'),flush=True)
   time.sleep(3)
  results.append({'index':index,'map':scene['map_path'],'report':state.get('report_path'),'status':state['status']})
  write(RUN/'survey_batch_progress.json',{'completed':results,'next_index':index+1})
  print('Finished',index,scene['label'],state['status'],flush=True)
 return results
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--start',type=int,default=0);p.add_argument('--end',type=int,default=26);a=p.parse_args();execute(a.start,a.end)
