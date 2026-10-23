"""Build isolated opposite-sex copies; root dispatches run() in UE.

Does not edit source clips, shared Skeletons, actors, maps or runtime catalogs.
Numeric success is playback readiness, never human visual acceptance.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import math
import traceback
from datetime import datetime

SCRIPTS = Path(__file__).resolve().parent
WORK = SCRIPTS.parents[2]
RUN = WORK / '00_engine/outputs/camera_motion_scene_alignment_20261012_v1/legacy_motion'
CATALOG = WORK / '00_engine/assets/character_creator/current_review_actions_20261012_v1.json'
CONTENT = Path('D:/UE/projects/datatry_02/Content')
DEST = '/Game/DataMake/Validation/CameraMotionSceneAlignment20261012/LegacyCrossSex'
BONES = ('root','pelvis','spine_01','spine_02','neck_01','head','upperarm_l','upperarm_r',
         'hand_l','hand_r','thigh_l','thigh_r','calf_l','calf_r','foot_l','foot_r','ball_l','ball_r')

def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def pin(p):
    p = Path(p).resolve(strict=True)
    return {'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}

def asset_pin(a):
    name = a if isinstance(a,str) else a.get_path_name()
    return dict(pin(CONTENT / (name.split('.')[0].removeprefix('/Game/')+'.uasset')), asset=name)

def load(name):
    spec = importlib.util.spec_from_file_location('_cross_sex_'+name,SCRIPTS/(name+'.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

def write(p, data):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as stream:
        json.dump(data,stream,ensure_ascii=False,indent=2,allow_nan=False)

def run():
    import unreal as u
    assert Path(u.Paths.project_dir()).resolve() == CONTENT.parent.resolve()
    helper = load('ue_complete_character_wardrobe_hair_review_v1')
    composer = load('ue_compose_native_face_body_v1')
    catalog = read(CATALOG)
    assert len(catalog['records']) == 10
    result = {'schema':'legacy_cross_sex_validation_v1','success':False,'catalog':pin(CATALOG),
              'visual_acceptance':'pending_render_and_human_review','actions':[],
              'policy':'Full original duration/rate; explicit 108 local body tracks reconstructed on opposite shared Skeleton. No source or Skeleton edits. No claim of proportion/cloth visual correctness from numerical equality.'}
    before = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    protected = []
    try:
        for row in catalog['records']:
            aid,source_sex = row['action_id'],row['sex']
            sex = 'male' if source_sex == 'female' else 'female'
            output = RUN/(aid+'_'+sex+'_v1.json')
            if output.exists():
                old=read(output)
                assert old['success'] and old['source']['sha256']==row['asset_sha256']
                assert pin(old['target']['path'])['sha256']==old['target']['sha256']
                assert all(pin(r['path'])['sha256']==r['sha256'] for r in old['protected_sources'])
                result['actions'].append(old)
                continue
            source = u.load_asset(row['path'])
            mesh_path = '/Game/DataMake/Validation/CFDNativeBatch4020261006/CFD40_'+('AM' if sex=='male' else 'AF')+'_001/Meshes/cc_base_body'
            mesh = u.load_asset(mesh_path)
            old_prefix = 'F' if source_sex=='female' else 'M'
            source_mesh = u.load_asset('/Game/Vendor/Reallusion/CC5/FirstDataBatch/Looks/'+old_prefix+'_ID01_O01/CC_FB_'+old_prefix+'_ID01_O01')
            assert isinstance(source,u.AnimSequence) and isinstance(mesh,u.SkeletalMesh) and isinstance(source_mesh,u.SkeletalMesh)
            skeleton=mesh.get_editor_property('skeleton')
            assert skeleton.get_path_name().split('.')[0].endswith('/SKEL_CFDShared_'+sex.title()+'_v1')
            records=[asset_pin(v) for v in (source,mesh,source_mesh,skeleton,source.get_skeleton())]
            assert records[0]['sha256']==row['asset_sha256']
            assert not {r['asset'].split('.')[0] for r in records}&before
            protected.extend(records)
            hierarchy=[]
            for m in (source_mesh,mesh):
                mod=u.SkeletonModifier()
                assert mod.set_skeletal_mesh(m)
                hierarchy.append({str(n):str(mod.get_parent_name(n)) for n in mod.get_all_bone_names()})
            assert hierarchy[0]==hierarchy[1] and len(hierarchy[1])==118
            refs=[helper.REFERENCE.reference_bones(m) for m in (source_mesh,mesh)]
            ref_changes=[]
            for bone in sorted(hierarchy[1]):
                a,b=[r[bone][1] for r in refs]
                metrics=composer.transform_metric_errors(composer.transform_values(a),composer.transform_values(b))
                if max(metrics.values())>1e-5:
                    ref_changes.append({'bone':bone,'metrics':metrics})
            names,values=helper.sampled_tracks(source)
            assert set(map(str,names))==set(hierarchy[1])-composer.FACE_BONES and len(names)==108
            assert not u.AnimationLibrary.get_animation_curve_names(source,u.RawCurveTrackTypes.RCT_FLOAT)
            name='A_'+aid.removeprefix('ACT_')+'_'+sex.title()+'_v1'
            folder=DEST+'/'+sex.title()
            path=folder+'/'+name
            assert not u.EditorAssetLibrary.does_asset_exist(path),'Unreceipted target exists; inspect before retry'
            factory=u.AnimSequenceFactory()
            factory.set_editor_property('target_skeleton',skeleton)
            target=u.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,u.AnimSequence,factory)
            assert isinstance(target,u.AnimSequence)
            model=source.data_model_interface
            count=int(getattr(model.get_number_of_frames(),'value',model.get_number_of_frames()))
            c=target.controller
            c.open_bracket('Isolated opposite-sex body motion validation',False)
            try:
                c.set_frame_rate(model.get_frame_rate(),False)
                c.set_number_of_frames(u.FrameNumber(count),False)
                for bone in names:
                    poses=values[str(bone)]
                    c.add_bone_track(bone,False)
                    assert c.set_bone_track_keys(bone,[p.translation for p in poses],[p.rotation for p in poses],[p.scale3d for p in poses],False)
            finally:
                c.close_bracket(False)
            if hasattr(c,'notify_populated'):c.notify_populated()
            target.set_editor_property('enable_root_motion',False)
            comparison=helper.compare_tracks(values,target)
            assert abs(source.get_play_length()-target.get_play_length())<1e-6
            assert target.get_skeleton()==skeleton
            assert u.EditorAssetLibrary.save_loaded_asset(target,False)
            options=u.AnimPoseEvaluationOptions()
            options.set_editor_properties({'evaluation_type':u.AnimDataEvalType.SOURCE,'should_retarget':False,'extract_root_motion':False,'incorporate_root_motion_into_pose':True,'evaluate_curves':False,'optional_skeletal_mesh':mesh})
            duration=float(target.get_play_length())
            times=[i/10 for i in range(math.floor(duration*10)+1)]
            if abs(times[-1]-duration)>1e-8:times.append(duration)
            frames=[]
            for t in times:
                pose=u.AnimPoseExtensions.get_anim_pose_at_time(target,t,options)
                assert u.AnimPoseExtensions.is_valid(pose)
                assert set(BONES)<={str(n) for n in u.AnimPoseExtensions.get_bone_names(pose)}
                bones={}
                for bone in BONES:
                    tf=u.AnimPoseExtensions.get_bone_pose(pose,u.Name(bone),u.AnimPoseSpaces.WORLD)
                    v=tf.translation
                    bones[bone]=[float(v.x),float(v.y),float(v.z)]
                    assert all(math.isfinite(x) for x in composer.transform_values(tf))
                    if bone=='root':
                        r=tf.rotation.rotator();rotation=[float(r.pitch),float(r.yaw),float(r.roll)]
                frames.append({'t':t,'bones':bones,'root_rotation':rotation})
            item={'success':True,'action_id':aid,'source_sex':source_sex,'sex':sex,
                  'source':records[0],'target':asset_pin(target),'reference_mesh':mesh.get_path_name(),
                  'target_skeleton':skeleton.get_path_name(),'hierarchy_equal':True,'body_tracks':108,
                  'reference_pose_differences':ref_changes,
                  'frames_count':count,'duration_seconds':duration,'numeric_comparison':comparison,
                  'sample_fps':10,'frames':frames,'visual_acceptance':'pending',
                  'protected_sources':records}
            assert all(pin(r['path'])['sha256']==r['sha256'] for r in protected)
            dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
            assert not {r['asset'].split('.')[0] for r in protected}&dirty
            assert not {p for p in dirty-before if not p.startswith(DEST+'/')}
            write(output,item)
            result['actions'].append(item)
            print('DM_LEGACY_CROSS_SEX_PROGRESS='+str(len(result['actions']))+'/10')
        result.update(success=True,source_assets_unchanged=True)
    except Exception:
        result['error']=traceback.format_exc()
        raise
    finally:
        suffix='validation_v1.json' if result['success'] else 'failed_validation_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.json'
        write(RUN/suffix,result)
    return {'success':True,'actions':len(result['actions']),'report':str(RUN/'validation_v1.json')}
