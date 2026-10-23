import json
from pathlib import Path
p=Path(r'D:\UE\Lance_Work\20_planning\data_design\character_creator\full_process\project_management\status\PROJECT_STATE.json')
data=json.loads(p.read_text(encoding='utf-8'))
data['updated_at']='2026-09-23T20:05:00+08:00'
lw=data.setdefault('local_work',{})
lw['hair_shadow_artifact_probe']={
 'level':'/Game/DataMake/Validation/ScalpHairPilot/L_DM_ScalpHairPilot_Review_v001',
 'status':'staged_manual_review_pending_shadow_check',
 'scope':'review_level_instance_only',
 'actors':['DM_ScalpHairReview_M02_Average','DM_ScalpHairReview_F02_Average'],
 'components':['BundlePart01','BundlePart02','BundlePart03','BundlePart04'],
 'change':'cast_shadow=false; mesh/material/opacity/leader_pose unchanged',
 'evidence':'%OUTPUT_ROOT%/unreal_character_import/scalp_hair_pilot_20260923_111307_interchange/hair_shadow_artifact_probe_v1.json',
 'formal_runtime_hair_slot':False
}
p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('updated',p)

