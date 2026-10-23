"""Build ten opposite-sex overview candidates only from real UE validation.

Owner: SCENE_CAMERA_SEQUENCE. Keeps frozen 1260-shot calibration plan unchanged.
The caller owns UE scheduling and subsequent human visual acceptance.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import camera_calibration_planner_v1 as camera

S = Path(__file__).resolve().parent
RUN = S.parents[1] / 'outputs/camera_motion_scene_alignment_20261012_v1'
PRIOR = S.parents[1] / 'outputs/unreal_character_import/motion_portrait_scene_pilot_20261011_v1'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def pin(path):
    path = Path(path).resolve(strict=True)
    return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def check(record):
    if pin(record['path'])['sha256'] != record['sha256']:
        raise ValueError('Validated source/target changed: '+record['path'])


def build(run=RUN, prior=PRIOR):
    run, prior = Path(run), Path(prior)
    destination = run/'legacy_cross_sex_camera_plan_v1.json'
    if destination.exists(): raise FileExistsError('Do not overwrite frozen cross-sex plan')
    proof_path = run/'legacy_motion/validation_v1.json'
    proof = read(proof_path)
    if not proof.get('success') or not proof.get('source_assets_unchanged') or len(proof['actions']) != 10:
        raise ValueError('Ten successful real UE cross-sex validations required')
    check(proof['catalog'])
    original = [s for s in read(prior/'camera_trial_plan_v1.json')['shots'] if s['group']=='motions']
    current_plan_path = run/'camera_trial_plan_v2.json'
    current_plan = read(current_plan_path)
    current_shots = {s['shot_id']:s for s in current_plan['shots']}
    decisions = {d['motion_id']:d for d in read(prior/'motion_window_decisions_v2.json')['actions']}
    config_path = run/'camera_calibration_reference_v2.json'
    config = read(config_path)
    front = next(p for p in camera.prior.library.presets() if p['id']=='front_full')
    shots=[];pins=[pin(proof_path),pin(current_plan_path),pin(config_path),pin(prior/'motion_window_decisions_v2.json')]
    seen=set()
    for record in proof['actions']:
        action = record['action_id'];sex = record['sex'];source_sex = record['source_sex']
        if action in seen: raise ValueError('Duplicate cross-sex action')
        seen.add(action)
        if sex not in ('male','female') or sex==source_sex or source_sex not in ('male','female'):
            raise ValueError('Not an opposite-sex target')
        if not record['success'] or not record['hierarchy_equal'] or record['body_tracks']!=108:
            raise ValueError('Incomplete motion validation')
        item_path=run/'legacy_motion'/(action+'_'+sex+'_v1.json')
        if read(item_path)!=record: raise ValueError('Aggregate validation differs from individual receipt')
        pins.append(pin(item_path));check(record['target'])
        for source in record['protected_sources']:check(source)
        matches=[s for s in original if s['motion_id']==action and s['sex']==source_sex]
        if len(matches)!=1:raise ValueError('Missing unique previously approved source action')
        before=matches[0];decision=decisions[action]
        if before['source_animation'].split('.')[0] != record['source']['asset'].split('.')[0]:
            raise ValueError('Cross-sex source does not match approved action')
        if abs(decision['window_start_seconds']-before['source_start_seconds'])>1e-7 or abs(decision['body_play_rate']-before['source_body_play_rate'])>1e-7:
            raise ValueError('Previously approved clock is inconsistent')
        clip={'clip_id':action.lower()+'_'+sex+'_cross_sex','animation_path':record['target']['asset'],'frames':record['frames']}
        shot=camera.make_shot(clip,decision,sex,front,'landscape',config,group='legacy_cross_sex')
        for field in ('source_start_seconds','source_end_seconds','source_body_play_rate','window_start_seconds','duration_seconds','frame_count'):
            if abs(float(shot[field])-float(before[field]))>1e-7:raise ValueError('Cross-sex plan changed approved clock: '+field)
        counterpart='cameras_'+action.lower()+'_'+source_sex+'_l_front_full_v2'
        if counterpart not in current_shots:raise ValueError('Missing original-sex calibrated counterpart')
        shot.update(cross_sex_validation=pin(item_path),source_sex=source_sex,
                    compare_to_camera_shot_id=counterpart,compare_to_original_overview_shot_id=before['shot_id'],
                    visual_acceptance='pending_render_and_human_review')
        shots.append(shot)
    plan={'schema':'legacy_cross_sex_camera_plan_v1','shots':shots,'source_pins':pins,
          'scope':'Ten opposite-sex front-full landscape overviews; original approved window and source speed retained',
          'human_acceptance':'pending','matrix_1260_unchanged':pin(current_plan_path)}
    with destination.open('x',encoding='utf-8') as f:json.dump(plan,f,ensure_ascii=False,separators=(',',':'),allow_nan=False)
    return {'shots':len(shots),'plan':pin(destination),'full_proxy_exceptions':[s['shot_id'] for s in shots if s['exceptions_require_review']]}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',type=Path,default=RUN);parser.add_argument('--prior',type=Path,default=PRIOR)
    args=parser.parse_args();print(json.dumps(build(args.run,args.prior),ensure_ascii=False))
