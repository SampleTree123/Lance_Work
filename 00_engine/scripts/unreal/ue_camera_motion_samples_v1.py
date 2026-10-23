"""Read-only source-pose sampling for the camera pilot, no scene mutation.

Technical owner: SCENE_CAMERA_SEQUENCE.md section 7.
"""
from pathlib import Path
import hashlib, json, math

RUN=Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/camera_motion_pilot_20261009_v1')
SOURCE=RUN.parent/'motion_library_expansion_20261009_v1/final_motion_catalog_v1.json'
IDS=('MOTION_CAND_002','MOTION_CAND_003','MOTION_CAND_008','MOTION_CAND_029','MOTION_CAND_030','MOTION_CAND_035')
BONES=('root','pelvis','spine_01','spine_02','neck_01','head','upperarm_l','upperarm_r',
       'hand_l','hand_r','thigh_l','thigh_r','calf_l','calf_r','foot_l','foot_r','ball_l','ball_r')
def pin(path):
    path=Path(path)
    return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
def package(path):
    return Path('D:/UE/projects/datatry_02/Content')/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def run():
    import unreal as u
    assert Path(u.Paths.project_dir()).resolve()==Path('D:/UE/projects/datatry_02').resolve()
    out=RUN/'motion_samples_v1.json'
    if out.exists():raise ValueError('Do not overwrite sampled evidence')
    source=json.loads(SOURCE.read_text(encoding='utf-8'))
    rows=[r for r in source['actions'] if r['motion_id'] in IDS]
    assert len(rows)==len(IDS)
    before_dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    samples={'schema':'camera_motion_samples_v1','fps':10,'source':pin(SOURCE),'clips':[],
             'coordinates':'AnimPoseSpaces.WORLD model space; pilot actor identity transform',
             'geometry_scope':'Bone landmarks with later conservative padding, not actual mesh silhouettes',
             'render_duration_seconds':None,'render_duration_status':'uniform_duration_pending_user_selection'}
    for row in rows:
        for sex in ('female','male'):
            variant=row['variants'][sex]
            assert pin(variant['body_only']['path'])['sha256']==variant['body_only']['sha256']
            anim=u.load_asset(variant['body_only']['asset'])
            assert isinstance(anim,u.AnimSequence)
            duration=float(anim.get_play_length())
            assert abs(duration-variant['duration_seconds'])<1e-5
            source_pin=pin(package(anim.get_path_name()))
            options=u.AnimPoseEvaluationOptions()
            options.set_editor_properties({'evaluation_type':u.AnimDataEvalType.SOURCE,'should_retarget':False,
                'extract_root_motion':False,'incorporate_root_motion_into_pose':True,'evaluate_curves':False})
            limit=min(15.,math.floor(duration*10)/10)
            clip={'clip_id':row['motion_id'].lower()+'_'+sex,'sex':sex,'action_index':row['index'],
                  'label':row['label'],'animation_path':anim.get_path_name(),'source_package':source_pin,
                  'duration_seconds':duration,'window_start_seconds':0.,'window_duration_seconds':limit,
                  'sample_duration_note':'Analysis extent only; final videos use one separately selected duration',
                  'actor_transform':{'location':[0,0,0],'rotation_pitch_yaw_roll':[0,0,0],'scale':[1,1,1]},'frames':[]}
            for i in range(round(limit*10)+1):
                t=i/10.
                pose=u.AnimPoseExtensions.get_anim_pose_at_time(anim,t,options)
                assert u.AnimPoseExtensions.is_valid(pose)
                names={str(n) for n in u.AnimPoseExtensions.get_bone_names(pose)}
                assert set(BONES)<=names,sorted(set(BONES)-names)
                bones={}
                for name in BONES:
                    transform=u.AnimPoseExtensions.get_bone_pose(pose,u.Name(name),u.AnimPoseSpaces.WORLD)
                    v=transform.translation
                    bones[name]=[float(v.x),float(v.y),float(v.z)]
                    if name=='root':
                        rot=transform.rotation.rotator()
                        rotation=[float(rot.pitch),float(rot.yaw),float(rot.roll)]
                clip['frames'].append({'t':t,'bones':bones,'root_rotation':rotation})
            assert source_pin==pin(package(anim.get_path_name()))
            samples['clips'].append(clip)
    after_dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    assert after_dirty==before_dirty,'Read-only sampling changed dirty packages'
    samples['success']=True
    samples['source_assets_unchanged']=True
    RUN.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(samples,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'success':True,'clips':len(samples['clips']),'report':str(out)}))
if __name__=='__main__':run()
