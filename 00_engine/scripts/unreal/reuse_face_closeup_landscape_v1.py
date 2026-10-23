"""Reuse the five verified, unchanged landscape pilot shots into revision 2."""
from pathlib import Path
import run_all_motion_camera_review_v1 as base

ROOT = Path(__file__).resolve().parents[2] / 'outputs'
SOURCE = ROOT / 'camera_face_closeup_20261014_v1'
DEST = ROOT / 'camera_face_closeup_20261014_v2'


def run():
    old = {s['shot_id']:s for s in base.read(SOURCE/'camera_trial_plan_v1.json')['shots']}
    new = {s['shot_id']:s for s in base.read(DEST/'camera_trial_plan_v1.json')['shots'] if s['orientation']=='landscape'}
    if len(new)!=30 or any(old.get(sid)!=shot for sid,shot in new.items()):
        raise ValueError('Landscape shot objects must be identical')
    rows = base.verified_rows(new,SOURCE)
    if len(rows)!=5:
        raise ValueError('Only the five approved pilot landscape media are reusable')
    pins=[]
    for row in rows.values():
        for key in ('video','poster','timeline_contact','verification_receipt'):
            pins.append(base.copy_pinned(base.owned(SOURCE,SOURCE/row[key]),base.owned(DEST,DEST/row[key])))
        proof=base.read(SOURCE/row['verification_receipt'])
        receipt=Path('render_receipts')/(proof['attempt']+'.json')
        pins.append(base.copy_pinned(SOURCE/receipt,DEST/receipt))
        base.checked_media(row,new[row['shot_id']],DEST)
    result={'schema':'motion_scene_media_validation_v1','success':True,
            'attempt':'reused_v1_landscape_pilot','videos':list(rows.values()),
            'source_plans':[{'path':str(p),'sha256':base.sha(p)} for p in
                (SOURCE/'camera_trial_plan_v1.json',DEST/'camera_trial_plan_v1.json')],
            'reuse_source_pins':pins,'human_acceptance':'pending',
            'policy':'exact shot objects and verified media receipts copied; original evidence preserved'}
    base.atomic_json(DEST/'media_validation_reused_landscape_pilot_v1.json',result)
    return {'reused':len(rows)}


if __name__=='__main__':
    print(run())
