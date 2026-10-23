"""Read-only export of the exact six-axis subset used by the topology study."""
from pathlib import Path
import hashlib
import json
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sources={
    'identities':ROOT/'00_engine/outputs/character_refresh_20261018_v1/user_edited_night_import_20261020_v1/delivery.json',
    'motions':ROOT/'00_engine/assets/character_creator/production_motion_library_20261017_v1.json',
    'cameras':ROOT/'00_engine/outputs/pair_scene_review_20261019_v1/site_review_catalog_v1.json',
    'checkpoint':ROOT/'00_engine/outputs/review_progress_sync_20261021_v1/checkpoint.json',
    'selection_policy':ROOT/'00_engine/scripts/unreal/scene_review_selection_policy_v1.py',
    'palette_policy':ROOT/'00_engine/scripts/unreal/night_character_review_v1.py',
}
data={k:json.loads(p.read_text(encoding='utf-8-sig')) for k,p in sources.items() if p.suffix == '.json'}
motions=[r for r in data['motions']['motions'] if r['motion_id'] != 'MOTION_CAND_007']
out={
    'kind':'read_only_six_axis_inventory_subset_for_synthetic_topology',
    'identities':[{'id':r['character_id'],'sex':r['sex']} for r in data['identities']['cases']],
    'actions':[r['motion_id'] for r in motions],
    'action_sexes':{r['motion_id']:sorted(r['variants']) for r in motions},
    'cameras':[r['camera_id'] for r in data['cameras']['cameras']],
    'aspects':['landscape','portrait'],
    'hair_colors':['original','black','gold','silver_white','red','blue','pink'],
    'sources':{k:{'path':str(p.relative_to(ROOT)).replace('\\','/'),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for k,p in sources.items()},
    'limitations':['six_axis_projection_not_complete_render_config','outfit_hair_face_held_as_abstract_domain_default_not_UE_validated','no_asset_or_editor_access'],
}
assert len(out['identities']) == 40
assert len(out['actions']) == 25
assert len(out['cameras']) == 21
assert len(data['checkpoint']['sites']) == 21
fixed='--fixed-landscape' in sys.argv
if fixed:
    out['aspects']=['landscape']
    out['limitations'].append('landscape_only_sensitivity_no_aspect_edit')
path=HERE/('topology_inventory_landscape.json' if fixed else 'topology_inventory.json')
path.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(path)
