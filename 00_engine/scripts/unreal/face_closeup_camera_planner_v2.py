"""Portrait closeup revision after the ten-shot v1 pilot.

Default writes only a numerical preview. --freeze writes the immutable v2 plan.
Landscape shot objects remain byte-for-byte equivalent at canonical JSON level;
their original configuration pins remain in the v1 plan dependency.
"""
from pathlib import Path
import argparse
import copy
import json
import numpy as np
import face_closeup_camera_planner_v1 as base

RUN = base.ROOT / 'outputs/camera_face_closeup_20261014_v2'
V1 = base.RUN


def build(freeze=False):
    v1_path = V1/'camera_trial_plan_v1.json'
    original = base.read(v1_path)
    if base.pin(v1_path)['sha256'] != 'b5f59b4b2d3c586f0d51d658fa3a098e1fdacd5355603de876a52d7096d01b6c':
        raise ValueError('Frozen face v1 plan changed')
    old_shots = {(s['motion_id'], s['orientation']): s for s in original['shots']}
    config = copy.deepcopy(base.read(V1/'camera_face_closeup_config_v1.json'))
    config.update(schema='camera_face_closeup_config_v2', previous_config=base.pin(V1/'camera_face_closeup_config_v1.json'),
                  revision_reason='v1 portrait pilot includes waist; tighten to head and shoulders with upper chest',
                  landscape_policy='retain complete v1 shot objects and their original config SHA')
    config['orientations']['portrait'].update(nominal_distance_cm=60., target_offset_from_head_cm=[0., 0., 3.],
        composition_intent='whole head, shoulders and small upper chest; no waist context')
    config['portrait_tracking_overrides'] = {'MOTION_CAND_029': {'sigma_seconds': .18},
                                             'MOTION_CAND_030': {'sigma_seconds': .18}}
    sources_path = base.ACCEPTED/'motion_sources_v1.json'
    sources = base.read(sources_path)['actions']
    samples_path = base.prior.RUN/'all_motion_samples_v1.json'
    clips = {c['clip_id']: c for c in base.read(samples_path)['clips']}
    shots, reports, actions = [], [], []
    for source in sources:
        frames = base.prior.resample(clips[source['source_clip_id']],source['source_start_seconds'],
                                     source['duration_seconds'],source['source_body_play_rate'])
        filtered, tracking = base.action_tracking(frames, source['motion_id'])
        if source['motion_id'] in config['portrait_tracking_overrides']:
            tracking = copy.deepcopy(tracking)
            sigma = config['portrait_tracking_overrides'][source['motion_id']]['sigma_seconds']
            raw = np.array([f['bones']['head'] for f in frames])
            filtered = base.stable.low_frequency(raw, np.array([f['t'] for f in frames]), sigma)
            residual = raw-filtered
            tracking.update(sigma_seconds=sigma, per_action_override=True,
                revision_scope='portrait only; complete v1 landscape object retained',
                residual_xyz_max_abs_cm=np.abs(residual).max(axis=0).tolist(),
                residual_distance_p95_cm=float(np.quantile(np.linalg.norm(residual, axis=1), .95)),
                filtered_head_xyz_range_cm=np.ptp(filtered, axis=0).tolist())
        per_orientation = {}
        for orientation in ('landscape', 'portrait'):
            if orientation == 'landscape':
                shot = copy.deepcopy(old_shots[(source['motion_id'], orientation)])
            else:
                shot = base.make_shot(source, frames, filtered, tracking, orientation, config['orientations'][orientation], config)
                shot['shot_id'] = shot['shot_id'].removesuffix('_v1')+'_v2'
                shot['supersedes_shot_id'] = old_shots[(source['motion_id'], orientation)]['shot_id']
            checks = base.checks(shot, source)
            checks['landscape_object_exact_if_retained'] = orientation != 'landscape' or shot == old_shots[(source['motion_id'], orientation)]
            if not all(checks.values()):
                raise ValueError('Bounded v2 checks failed: '+str(checks))
            shots.append(shot)
            reports.append({'shot_id':shot['shot_id'],'checks':checks})
            per_orientation[orientation] = {'shot_id':shot['shot_id'], 'distance_cm':shot['endpoint_distances_cm'][0],
                                           'framing':shot['framing_diagnostics']['head']}
        actions.append({'motion_id':source['motion_id'],'motion_label':source['motion_label'],'sex':source['sex'],
                        'tracking':tracking,'source_clock':{k:source[k] for k in base.CLOCK_FIELDS},'orientations':per_orientation})
    pilots = [s['shot_id'] for m in base.PILOTS for s in shots if s['motion_id'] == m]
    preview = {'schema':'face_closeup_preview_v2','frozen':freeze,'v1_plan':base.pin(v1_path),
               'config':config,'actions':actions,'pilot_shot_ids':pilots,
               'landscape_complete_shot_objects_retained':30,'source_clocks_exact':True,
               'all_60_bounded_checks_pass':True,'human_acceptance':'pending'}
    RUN.mkdir(parents=True,exist_ok=True)
    # Preview is explicitly mutable and never a runtime plan or freeze artifact.
    (RUN/'face_closeup_preview_v2.json').write_text(json.dumps(preview,ensure_ascii=False,indent=2),encoding='utf-8')
    if freeze:
        base.RUN = RUN
        base.save('camera_face_closeup_config_v2.json',config)
        plan = {'schema':'camera_face_closeup_trial_v1','revision':2,'shots':shots,
            'matrix':original['matrix'],'source_pins':original['source_pins']+[base.pin(v1_path),base.pin(Path(__file__))],
            'source_samples_sha256':original['source_samples_sha256'],'decisions_path':original['decisions_path'],
            'reference_config':base.pin(RUN/'camera_face_closeup_config_v2.json'),
            'pilot_shot_ids':pilots,'smoke_shot_ids':pilots,
            'portrait_pilot_shot_ids':[s for s in pilots if '_p_' in s],
            'retained_landscape_shot_ids':[s['shot_id'] for s in shots if s['orientation']=='landscape'],
            'landscape_objects_preserved_from':base.pin(v1_path),
            'human_acceptance':'pending','complete_window':True,'face_closeups_only':True,
            'face_visibility_guaranteed':False,'cropping_allowed':True,'nonface_plan_modified':False}
        base.save('camera_trial_plan_v1.json',plan)
        plan_pin=base.pin(RUN/'camera_trial_plan_v1.json')
        base.save('face_closeup_action_parameters_v2.json',{'schema':'face_closeup_action_parameters_v2',
            'plan':plan_pin,'actions':actions,'pilot_shot_ids':pilots})
        base.save('face_closeup_targeted_checks_v2.json',{'schema':'face_closeup_targeted_checks_v2','success':True,
            'plan':plan_pin,'reports':reports,'landscape_complete_objects_exact':True,
            'accepted_nonface_plan_sha_unchanged':base.pin(base.ACCEPTED/'camera_trial_plan_v1.json')['sha256']==base.ACCEPTED_SHA,
            'scope':'60 clock/key/head-margin/depth/floor checks; retained landscape object equality',
            'not_full_audit':True,'human_acceptance':'pending'})
        base.save('face_closeup_freeze_v2.json',{'schema':'face_closeup_freeze_v2','plan':plan_pin,
            'config':base.pin(RUN/'camera_face_closeup_config_v2.json'),
            'action_parameters':base.pin(RUN/'face_closeup_action_parameters_v2.json'),
            'targeted_checks':base.pin(RUN/'face_closeup_targeted_checks_v2.json'),
            'pilot_shot_ids':pilots,'portrait_pilot_shot_ids':plan['portrait_pilot_shot_ids'],
            'matrix':plan['matrix'],'reused_landscape_objects':30,'ue_operations':False,'rendered':False,'human_acceptance':'pending'})
    print(json.dumps({'frozen':freeze,'plan':base.pin(RUN/'camera_trial_plan_v1.json') if freeze else None,
        'pilots':[{'motion_id':a['motion_id'],'portrait_distance_cm':a['orientations']['portrait']['distance_cm'],
                   'head_height_fraction_range':a['orientations']['portrait']['framing']['head_envelope_height_fraction_range']}
                  for a in actions if a['motion_id'] in base.PILOTS]},ensure_ascii=False))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze',action='store_true')
    build(parser.parse_args().freeze)
