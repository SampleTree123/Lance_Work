"""Coordinator-only four-shot site pilot; explicit saved plans, recoverable attempts."""
from pathlib import Path
import sys,json,subprocess,time
import scene_site_review_pilot_v1 as pilot
RUN=pilot.RUN;S=pilot.S

def remote(code,label):
 folder=RUN/'pilot_commands';folder.mkdir(exist_ok=True)
 script=folder/(label+'.py');script.write_text("import sys,unreal as u\nsys.path.insert(0,"+repr(str(S))+")\nimport scene_site_review_pilot_v1 as p\n"+code,encoding='utf-8')
 result=subprocess.run([sys.executable,'-X','utf8',str(S/'ue_remote_exec.py'),'--project','datatry_02','--script',str(script)],capture_output=True,text=True,encoding='utf-8')
 (folder/(label+'.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
 if result.returncode:raise RuntimeError('UE failed: '+str(folder/(label+'.log')))

if __name__=='__main__':
 import encode_motion_scene_pilot_v1 as encoder
 for site,scene,selections in [('gas_pilot','gas_station',[('MOTION_CAND_008','front_full','portrait'),('MOTION_CAND_030','orbit_360','landscape')]),('parking_pilot','parking',[('MOTION_CAND_001','front_three_quarter_full','landscape'),('MOTION_CAND_003','front_full','portrait')])]:
  planpath=pilot.make_plan(RUN/'sites'/(site+'.json'),scene,selections,revision='v2')
  plan=pilot.read(planpath)
  remote("u.EditorLoadingAndSavingUtils.load_map('/Engine/Maps/Entry')\nprint(p.prepare(u,"+repr(str(planpath))+"))\n",site+'_prepare')
  print(site,'prepared',flush=True)
  for shot in plan['shots']:
   attempt=shot['shot_id']+'_render';receipt=RUN/'render_receipts'/(attempt+'.json')
   if not receipt.exists():remote('print(p.render(u,'+repr(str(planpath))+','+repr(attempt)+','+repr([shot['shot_id']])+'))\n',attempt+'_submit')
   while True:
    if receipt.exists():
     status=pilot.read(receipt)
     if status.get('status') in ('completed','failed','cancelled'):
      if not status.get('success'):raise RuntimeError('Render failed; inspect '+str(receipt))
      break
    time.sleep(5)
   encoder.process(attempt,[planpath],RUN)
   print(shot['shot_id'],'verified',flush=True)
 print('Four pilot clips complete',flush=True)
