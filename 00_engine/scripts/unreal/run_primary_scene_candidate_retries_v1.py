"""Root-only serial rechecks of the six explicitly selected scene candidates."""
from pathlib import Path
import json,time,sys
import run_primary_scene_surveys_v1 as batch
RUN=batch.RUN

def matching_complete(change):
 match=batch.matching_dual_complete(change['map'],change['position'],change['yaw'])
 return str(match[0]) if match else None

def execute():
 changes=batch.read(RUN/'root_candidate_reselections_v1.json')['changes'];results=[]
 for i,c in enumerate(changes):
  if (RUN/'STOP').exists():return results
  ready=matching_complete(c)
  if ready:results.append({'site_id':c['site_id'],'report':ready,'reused':True,'reused_verified_dual':True});continue
  old=batch.read(RUN/'survey_progress.json')
  if old.get('status')=='running':raise RuntimeError('Another survey still running; root must wait before this driver')
  position=[c['position'][k] for k in ('x','y','z')]
  code="import sys,unreal as u\nsys.path.insert(0,"+repr(str(batch.S))+")\nimport ue_scene_site_review_v1 as worker\nimport ue_primary_scene_survey_dual_v3 as dual\nassert not u.get_editor_subsystem(u.MoviePipelineQueueSubsystem).is_rendering()\nassert not (dual.poll().get('status')=='running')\nworker.restore()\nassert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'Preserve unsaved maps before switching'\nassert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level("+repr(c['map'])+")\nworker.enable_live_view()\nprint(dual.start_candidate("+repr(c['source_report'])+","+repr(position)+","+repr(c['yaw'])+",allow_nonzero_screen=True,justification="+repr(c['reason'])+"))\n"
  batch.remote(code,'explicit_retry_'+c['site_id'])
  deadline=time.monotonic()+1800;last=0
  while True:
   if (RUN/'STOP').exists():return results
   state=batch.read(RUN/'survey_progress.json')
   if state.get('map')==c['map'] and state.get('status')!='running':break
   if time.monotonic()>deadline:raise RuntimeError('Observation deadline; inspect still-live UE job rather than restart')
   if time.monotonic()-last>60:
    last=time.monotonic();print(c['site_id'],state.get('full_check'),flush=True)
   time.sleep(3)
  results.append({'site_id':c['site_id'],'report':state.get('report_path'),'status':state['status']})
  batch.write(RUN/'candidate_retry_batch_progress_v1.json',{'completed':results,'next_index':i+1})
  print('Finished candidate',c['site_id'],state['status'],flush=True)
 return results
if __name__=='__main__':execute()
