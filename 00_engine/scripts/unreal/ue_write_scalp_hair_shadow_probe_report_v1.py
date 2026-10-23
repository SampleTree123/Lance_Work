

# RETIRED_EXECUTION_ENTRY_20261001: imports/shared helpers remain available.
if globals().get("__name__") == "__main__":
    raise RuntimeError("Retired execution entry: ue_write_scalp_hair_shadow_probe_report_v1.py. Use the current Character Factory v003/review or canonical FirstBatch workflow; historical evidence remains available.")

import json
from pathlib import Path
from datetime import datetime, timezone
out=Path(r'D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\scalp_hair_pilot_20260923_111307_interchange\hair_shadow_artifact_probe_v1.json')
report={
 'schema_version':1,
 'created_at_utc':datetime.now(timezone.utc).isoformat(),
 'level':'/Game/DataMake/Validation/ScalpHairPilot/L_DM_ScalpHairPilot_Review_v001',
 'scope':'review_level_instance_only',
 'hypothesis':'masked hair card dynamic shadows are producing grain-like shadow artifacts on the face',
 'change':'set cast_shadow=false on every loaded scalp hair SkeletalMeshComponent for M02 and F02 review actors; hair mesh, materials, skeleton and leader pose unchanged',
 'actors':['DM_ScalpHairReview_M02_Average','DM_ScalpHairReview_F02_Average'],
 'components':['BundlePart01','BundlePart02','BundlePart03','BundlePart04'],
 'before':{'cast_shadow':True},
 'after':{'cast_shadow':False},
 'saved_and_reloaded':True,
 'user_visual_confirmation':'pending'
}
out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(out)

