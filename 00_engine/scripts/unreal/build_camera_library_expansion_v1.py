"""Build scoped human feedback and composable camera candidates, without Unreal.

Existing clips are evidence only: never modify their manifest or media.
Candidate combinations are NOT geometry-validated or visually accepted.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

EXCLUDED = {4, 11, 16, 24, 27}
REVISE = {5, 9, 30, 31}
STATIC = {'static_front': (0,0,'full'), 'static_three_quarter': (45,0,'full'),
          'static_side': (90,0,'full'), 'static_rear': (135,0,'full'),
          'static_high': (35,25,'full'), 'static_low': (35,-8,'full'),
          'static_upper': (0,0,'upper'), 'static_head': (15,0,'head'),
          'static_wide': (35,0,'wide')}

def camera(azimuth=0, elevation=0, framing='full', movement='fixed', end=None, orbit=None):
    result = {'direction': {'azimuth_degrees': azimuth, 'elevation_degrees': elevation,
                           'reference': 'pelvis_heading' if movement=='follow' else 'initial_facing'},
              'framing': {'start': framing, 'end': end or framing},
              'movement': {'kind': movement}, 'duration_seconds': 10,
              'horizontal_fov_degrees': 35}
    if orbit is not None: result['movement']['orbit_degrees'] = orbit
    return result

def legacy_camera(shot):
    if shot in STATIC:
        a,e,f=STATIC[shot]; return camera(a,e,f)
    if shot.startswith('follow_'):
        return camera({'follow_front':0,'follow_side':90,'follow_rear':180}[shot],movement='follow')
    if shot.startswith('orbit_'):
        return camera(35,movement='orbit',orbit=int(shot.split('_')[1]))
    return camera(35,movement=shot)

def legacy_adapter(spec):
    """Only represent exact vocabulary matches; no silent camera substitutions.

    This returns a planning hint, never an accepted trajectory. Reusing a prior
    accepted clip requires its frozen trajectory, not regeneration from this hint.
    """
    for name in list(STATIC)+['follow_front','follow_side','follow_rear','orbit_60','orbit_120','orbit_180','dolly_in','dolly_out','pan','zoom_in','zoom_out']:
        if legacy_camera(name)==spec:
            return {'status':'vocabulary_supported','shot_type':name,
                    'follow_mode':'pelvis_heading' if name.startswith('follow_') else 'fixed_world',
                    'requires_new_geometry_and_visual_review':True}
    return {'status':'requires_composable_planner','reason':'No exact v1 direction/framing/movement match; do not approximate.'}

def validate_spec(spec):
    if spec['framing']['start'] not in {'full','upper','head','wide'} or spec['framing']['end'] not in {'full','upper','head','wide'}:
        raise ValueError('Unknown framing')
    if spec['direction']['reference'] not in {'initial_facing','pelvis_heading'}: raise ValueError('Unknown reference')
    if spec['movement']['kind'] not in {'fixed','follow','orbit','dolly_in','dolly_out','pan','zoom_in','zoom_out'}: raise ValueError('Unknown movement')
    if spec['duration_seconds'] != 10: raise ValueError('Duration must remain 10 seconds')

def proposals():
    # Explicit shortlist is first-pass coverage, never a per-action whitelist.
    return [
        ('向前行走','俯视跟拍',camera(35,25,movement='follow'),13),
        ('向前行走','上半身前方跟拍',camera(framing='upper',movement='follow'),13),
        ('向前行走','固定机位转向跟随',camera(35,movement='pan'),13),
        ('舒展舞步','仰视全身',camera(35,-8),21),
        ('舒展舞步','背侧全身',camera(135),21),
        ('舒展舞步','60度环绕',camera(35,movement='orbit',orbit=60),25),
        ('调整站姿','侧面全身',camera(90),1),
        ('调整站姿','60度环绕',camera(35,movement='orbit',orbit=60),1),
        ('调整站姿','明显推进：全身到上半身',camera(35,movement='dolly_in',end='upper'),5),
        ('弯腰伸展','正面全身',camera(),7),
        ('弯腰伸展','明显拉远：较紧全身到较宽全身',camera(35,movement='dolly_out'),9),
        ('甩头转身','俯视全身',camera(35,25),12),
        ('甩头转身','固定机位转向跟随',camera(35,movement='pan'),12),
        ('边走边思考','前方跟拍',camera(movement='follow'),28),
        ('边走边思考','明显拉远：上半身到全身',camera(35,framing='upper',movement='dolly_out',end='full'),30),
        ('好奇探看','上半身',camera(framing='upper'),32),
    ]

def build(manifest_path, output):
    raw=manifest_path.read_bytes(); manifest=json.loads(raw)
    rows=[]
    for clip in manifest['clips']:
        number=int(clip['shot_id'].split('_')[1])
        status='excluded_current_version' if number in EXCLUDED else 'revise_amplitude' if number in REVISE else 'accepted_representative'
        rows.append({'sample_number':number,'shot_id':clip['shot_id'],'motion_label':clip['motion_label'],
                     'sex':clip['sex'],'shot_type':clip['shot_type'],'status':status,
                     'scope':'this reviewed sample; not all identities or a global camera prohibition',
                     'preferred':number==13,'slowdown_natural':number in {32,33},
                     'routine_default':number!=20,'camera':legacy_camera(clip['shot_type']),
                     'source_video':str(manifest_path.parent/clip['video']),
                     'frozen_trajectory_sha256':clip.get('trajectory_sha256')})
    counts={s:sum(r['status']==s for r in rows) for s in ['accepted_representative','excluded_current_version','revise_amplitude']}
    if counts!={'accepted_representative':25,'excluded_current_version':5,'revise_amplitude':4}: raise ValueError(counts)
    feedback={'schema':'camera_human_feedback_v1','feedback_date':'2026-10-10','source':'explicit user conversation review',
              'source_manifest':str(manifest_path),'source_manifest_sha256':hashlib.sha256(raw).hexdigest(),
              'counts':counts,'rows':rows,
              'interpretation_notes':['弯腰伸展 actual four clips: three accepted, one amplitude revision.',
                '边走边思考 actual five clips: three accepted, one excluded, one revision.',
                '180-degree sample 20 accepted via remaining-clips feedback; not selected as routine default.',
                'Front-three-quarter sample 16 excluded only for 甩头转身; sample 26 remains accepted.',
                'Five exclusions are sample-scoped. Unseen combinations remain candidates.']}
    library={'schema':'composable_camera_library_v1','duration_seconds':10,
             'axes':{'direction':{'azimuth_degrees':[0,45,90,135,180],'elevation_degrees':[-8,0,25],'reference':['initial_facing','pelvis_heading']},
                     'framing':['full','upper','head'],
                     'movement':['fixed','follow','orbit','dolly_in','dolly_out','pan'],
                     'orbit_degrees_default':[60,120,360]},
             'legacy_nondefault':['wide framing','zoom_in','zoom_out','orbit_180'],
             'default_status':'candidate_not_tested','acceptance_rule':'Only scoped user-reviewed samples are accepted; geometric pass alone cannot promote candidates.',
             'safety_checks':['whole ten-second framing','key motion stays visible','no underground camera','smooth trajectory','meaningful viewpoint difference'],
             'comparison_rule':'Use same source character/motion/appearance for each camera comparison; existing different-sex examples are not controlled pairs.',
             'paired_edit_rule':'Freeze identical camera trajectory for both endpoints of an edit pair.'}
    candidates=[]
    for index,(motion,label,spec,base) in enumerate(proposals(),1):
        if spec['movement']['kind'].startswith('dolly'):
            spec['movement']['amplitude_policy']='explicit_start_end_framing'
            if motion=='弯腰伸展': spec['movement']['target_stature_screen_fraction']={'start':.85,'end':.58}
        validate_spec(spec)
        candidates.append({'candidate_id':f'expand_{index:02d}','motion_label':motion,'label':label,
                           'camera':spec,'comparison_sample_number':base,'status':'candidate_not_tested',
                           'geometry_status':'pending','render_status':'pending','human_review_status':'pending',
                           'legacy_adapter':legacy_adapter(spec)})
    matrix={'schema':'camera_coverage_candidates_v1','scope':'first 16 prioritized candidates; not an exhaustive support whitelist',
            'unlisted_combinations':'candidate_not_tested','rows':candidates}
    output.mkdir(parents=True,exist_ok=True)
    for name,data in [('human_camera_feedback_v1.json',feedback),('composable_camera_library_v1.json',library),('camera_coverage_candidates_v1.json',matrix)]:
        (output/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return counts

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--manifest',type=Path,required=True); parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); print(json.dumps(build(args.manifest,args.output),ensure_ascii=False))
