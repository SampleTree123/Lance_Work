import json
from pathlib import Path
p=Path(r'D:\UE\Lance_Work\20_planning\data_design\character_creator\full_process\project_management\status\PROJECT_STATE.json')
data=json.loads(p.read_text(encoding='utf-8'))
data['updated_at']='2026-09-23T20:25:00+08:00'
lw=data.setdefault('local_work',{})
scope=lw.setdefault('second_batch_scope',{})
# preserve existing shape while adding explicit pilot fact
scope['hair_export_pilot_status']='pilot_export_to_ue_runtime_visual_confirmed_user_20260923'
try:
    pilot=scope['dimensions']['hair_export_pilot']
except Exception:
    pilot=None
# The canonical hair pilot object is stored in the local_work dimensions-adjacent state below.
# Locate it recursively and update only known status fields.
def walk(obj):
    if isinstance(obj, dict):
        for k,v in obj.items():
            if k=='hair_export_pilot' and isinstance(v,dict):
                v['next_user_action']='Prepare the 40-hair batch from the verified export and UE structure pilot using short roots, unique names and motion=false; then run hair x outfit visual exclusions before matrix freeze.'
                imp=v.get('ue_import_pilot')
                if isinstance(imp,dict):
                    imp['visual_review_status']='pilot_user_confirmed_hair_normal_artifact_deferred'
                    imp['formal_runtime_hair_slot']=False
            else:
                walk(v)
    elif isinstance(obj,list):
        for v in obj: walk(v)
walk(data)
if 'hair_visibility_probe' in lw:
    lw['hair_visibility_probe']['status']='user_confirmed_hair_normal; artifact_deferred'
if 'hair_shadow_artifact_probe' in lw:
    lw['hair_shadow_artifact_probe']['status']='user_confirmed_hair_normal; artifact_deferred'
lw['hair_review_visibility_restored']=True
lw['hair_review_visibility_restore_script']='00_engine/scripts/unreal/ue_restore_scalp_hair_visibility_v1.py'
data['next_action']='Prepare the 40-hair batch from the verified export and UE structure pilot using short roots, unique names and motion=false; then run hair x outfit visual exclusions before matrix freeze.'
p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('updated')

