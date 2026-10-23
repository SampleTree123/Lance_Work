"""Rebind byte-identical portrait baseline media after presentation metadata only.

Original full-decode receipts remain pinned and copied separately. Derived
receipts are explicit about the metadata derivation; no render is claimed.
"""
from pathlib import Path
import copy
import json
import build_camera_follow_general_correction_v2 as general
import run_all_motion_camera_review_v1 as runner

RUN=general.OUT
PLAN=RUN/'follow_comparison_plan_v2.json'
SOURCE=general.repair.NONFACE
META=('comparison_group_id','comparison_variant_label_zh')


def reuse():
    source_hash=runner.sha(SOURCE);plan_hash=runner.sha(PLAN)
    plan=runner.read(PLAN);source=runner.read(SOURCE)
    originals={s['shot_id']:s for s in source['shots']}
    selected={s['shot_id']:s for s in plan['shots'] if s['orientation']=='portrait'
        and s.get('comparison_variant_label_zh')=='修正前'}
    if len(selected)!=7:
        raise ValueError('Expected seven original portrait baseline clips')
    proofs=[]
    for sid,shot in selected.items():
        stripped={k:v for k,v in shot.items() if k not in META}
        if stripped!=originals.get(sid):
            raise ValueError('Baseline render fields changed: '+sid)
        proofs.append({'shot_id':sid,'only_changed_fields':list(META),
            'source_shot_sha256':runner.object_sha(originals[sid]),
            'derived_shot_sha256':runner.object_sha(shot),
            'all_render_fields_exact':True})
    report_path=RUN/'media_validation_reused_follow_portrait_baseline_v2.json'
    if report_path.exists():
        report=runner.read(report_path)
        if report.get('comparison_plan_sha256')!=plan_hash or len(report['videos'])!=7:
            raise ValueError('Existing portrait reuse report differs')
        verified=runner.verified_rows(selected,RUN)
        if set(verified)!=set(selected):
            raise ValueError('Existing portrait reuse no longer verified')
        return {'success':True,'reused':7,'report':str(report_path)}
    rows=runner.verified_rows({sid:originals[sid] for sid in selected},SOURCE.parent)
    if set(rows)!=set(selected):
        raise ValueError('Missing verified original portrait clips')
    pins=[general.repair.pin(SOURCE),general.repair.pin(PLAN)]
    derived=[];attempts=set()
    for sid,row in rows.items():
        old=originals[sid];shot=selected[sid]
        receipt=runner.checked_media(row,old,SOURCE.parent,full_decode=True)
        attempts.add(receipt['attempt'])
        for key in ('video','poster','timeline_contact'):
            pins.append(runner.copy_pinned(runner.owned(SOURCE.parent,SOURCE.parent/row[key]),
                runner.owned(RUN,RUN/row[key])))
        original_receipt=runner.owned(SOURCE.parent,SOURCE.parent/row['verification_receipt'])
        preserved=RUN/'reuse_source_reports'/('follow_portrait_'+sid+'_encoded_receipt.json')
        pins.append(runner.copy_pinned(original_receipt,preserved))
        evidence=copy.deepcopy(receipt)
        evidence['shot_plan_sha256']=runner.object_sha(shot)
        evidence['derived_media_reuse']={'schema':'camera_follow_metadata_only_reuse_v2',
            'source_receipt':general.repair.pin(original_receipt),
            'preserved_source_receipt':general.repair.pin(preserved),
            'source_plan':pins[0],'target_plan':pins[1],
            'source_shot_sha256':runner.object_sha(old),
            'only_changed_fields':list(META),'all_render_fields_exact':True,
            'video_bytes_unchanged':True,'fresh_source_full_decode_success':True,
            'render_claim':'original render reused; derived receipt only rebinds presentation metadata'}
        receipt_rel=Path('media_receipts')/('reused_follow_portrait_v2_'+sid+'.json')
        general.save(receipt_rel,evidence)
        result=copy.deepcopy(row)
        result['verification_receipt']=receipt_rel.as_posix()
        result['verification_receipt_sha256']=runner.sha(RUN/receipt_rel)
        runner.checked_media(result,shot,RUN,full_decode=True)
        derived.append(result)
    for attempt in sorted(attempts):
        relative=Path('render_receipts')/(attempt+'.json')
        pins.append(runner.copy_pinned(SOURCE.parent/relative,RUN/relative))
    for path in sorted(SOURCE.parent.glob('media_validation_*.json')):
        if any(r['shot_id'] in selected for r in runner.read(path).get('videos',[])):
            pins.append(runner.copy_pinned(path,RUN/'reuse_source_reports'/('follow_portrait_'+path.name)))
    if runner.sha(SOURCE)!=source_hash or runner.sha(PLAN)!=plan_hash or any(runner.sha(p['path'])!=p['sha256'] for p in pins):
        raise ValueError('Reuse source or target changed')
    general.save(report_path.name,{'schema':'motion_scene_media_validation_v1','success':True,
        'attempt':'reused_follow_portrait_baseline_v2','videos':derived,
        'comparison_plan_sha256':plan_hash,'source_plans':[pins[1],pins[0]],
        'reuse_source_root':str(SOURCE.parent),'reuse_source_pins':pins,
        'reuse_policy':'byte-identical original portrait media, fresh complete source and destination decode, derived receipts for two presentation-only metadata fields',
        'metadata_only_derivation_proofs':proofs,'visual_review':'pending','human_acceptance':'pending',
        'raw_frames_deleted':False})
    verified=runner.verified_rows(selected,RUN)
    if set(verified)!=set(selected):
        raise ValueError('Derived portrait receipts failed runner verification')
    return {'success':True,'reused':7,'runner_verified':len(verified),'report':str(report_path)}


if __name__=='__main__':
    print(json.dumps(reuse(),ensure_ascii=True))
