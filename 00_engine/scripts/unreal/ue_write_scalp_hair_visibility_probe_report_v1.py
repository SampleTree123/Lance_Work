

# RETIRED_EXECUTION_ENTRY_20261001: imports/shared helpers remain available.
if globals().get("__name__") == "__main__":
    raise RuntimeError("Retired execution entry: ue_write_scalp_hair_visibility_probe_report_v1.py. Use the current Character Factory v003/review or canonical FirstBatch workflow; historical evidence remains available.")

import json
from pathlib import Path
from datetime import datetime, timezone
out=Path(r'D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\scalp_hair_pilot_20260923_111307_interchange\hair_visibility_probe_v1.json')
report={
 'schema_version':1,
 'created_at_utc':datetime.now(timezone.utc).isoformat(),
 'level':'/Game/DataMake/Validation/ScalpHairPilot/L_DM_ScalpHairPilot_Review_v001',
 'scope':'review_level_instance_only',
 'hypothesis_test':'hide all scalp hair meshes to determine whether face artifact depends on hair geometry/material',
 'actors':['DM_ScalpHairReview_M02_Average','DM_ScalpHairReview_F02_Average'],
 'components':['BundlePart01','BundlePart02','BundlePart03','BundlePart04'],
 'change':'visibility=false; body, outfit, lights and camera unchanged',
 'saved_and_reloaded':True,
 'user_visual_confirmation':'pending'
}
out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(out)

