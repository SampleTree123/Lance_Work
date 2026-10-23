"""Read-only proof for existing full-duration CFD40 legacy motion copies.

SCENE_CAMERA_SEQUENCE section 11. Never changes a Skeleton, animation, camera
plan or scene. Root alone calls run() in Unreal, then consumes the mapping.
"""
from pathlib import Path
import hashlib,json,math
import ue_motion_body_window_v1 as window

RUN=window.RUN
REPORTS=RUN.parent/'cfd_native_batch40_20261006_v1/runtime/modular_review_20261007_v1/animations'
CONTENT=Path('D:/UE/projects/datatry_02/Content')

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def pin(p):return {'path':str(p),'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()}
def asset_pin(a):
    return dict(pin(CONTENT/(a.split('.')[0].removeprefix('/Game/')+'.uasset')),asset=a)

def inventory():
    samples=read(RUN/'all_motion_samples_v1.json')
    result=[]
    for clip in samples['clips']:
        aid=clip['motion_id']
        if not aid.startswith('ACT_'):continue
        path=REPORTS/(aid+'_v002.json');report=read(path)
        assert report['source'].split('.')[0]==clip['asset'].split('.')[0]
        assert report['source_package_sha256']==clip['source_package']['sha256']
        source,target=asset_pin(report['source']),asset_pin(report['target'])
        assert source['sha256']==report['source_package_sha256'] and target['sha256']==report['target_package_sha256']
        assert report['body_tracks_reconstructed_at_source_frames'] and report['bone_tracks']==108
        assert abs(report['duration_seconds']-clip['duration_seconds'])<1e-5
        assert report['numeric_comparison']['preview_limits']=={'translation_cm':.001,'rotation_degrees':.05,'scale_delta':1e-5}
        assert all(report['numeric_comparison'][k]<=v for k,v in report['numeric_comparison']['preview_limits'].items())
        result.append({'motion_id':aid,'sex':clip['sex'],'source':source,'target':target,'prior_full_frame_proof':pin(path),'prior':report,'sample':clip})
    assert len(result)==10
    return result

def run(output_name='legacy_shared_motion_reuse_v1.json'):
    import unreal as u
    helper=window.module('ue_compose_native_face_body_v1')
    face=window.module('ue_native_face_panel_five_second_v1')
    output=RUN/output_name
    assert output.parent==RUN and not output.exists()
    rows=inventory();before={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    report={'schema':'legacy_shared_motion_reuse_v1','success':False,'scope':'Existing108-track full-duration copies; current target Skeleton/hierarchy/reference inspection and18bone world landmarks at source10Hz. Prior hash-bound report provides every-source-frame local track equivalence. No assets changed.',
            'camera_plan_unchanged':pin(RUN/'camera_trial_plan_v1.json'),'sampling_source':pin(RUN/'all_motion_samples_v1.json'),
            'world_landmark_limit_cm':.1,'actions':[]}
    protected=[]
    try:
        for row in rows:
            old=row['prior'];clip=row['sample'];sex=row['sex']
            source,target=[u.load_asset(row[k]['asset']) for k in ('source','target')]
            choice,_=face.accepted_faces()[(sex,'idle')]
            mesh=u.load_asset(choice['reference_mesh'])
            old_mesh_path='/Game/Vendor/Reallusion/CC5/FirstDataBatch/Looks/'+('F_ID01_O01/CC_FB_F_ID01_O01' if sex=='female' else 'M_ID01_O01/CC_FB_M_ID01_O01')
            old_mesh=u.load_asset(old_mesh_path)
            assert isinstance(source,u.AnimSequence) and isinstance(target,u.AnimSequence)
            assert isinstance(mesh,u.SkeletalMesh) and isinstance(old_mesh,u.SkeletalMesh)
            assert source.get_skeleton()==old_mesh.get_editor_property('skeleton')
            assert target.get_skeleton()==mesh.get_editor_property('skeleton')
            assert target.get_skeleton().get_path_name()==old['target_skeleton']
            records=[asset_pin(a.get_path_name()) for a in (source,target,mesh,old_mesh,source.get_skeleton(),target.get_skeleton())]
            assert not {r['asset'].split('.')[0] for r in records}&before
            protected.extend(records)
            parents=[]
            for body in (old_mesh,mesh):
                modifier=u.SkeletonModifier();assert modifier.set_skeletal_mesh(body)
                parents.append({str(n):str(modifier.get_parent_name(n)) for n in modifier.get_all_bone_names()})
            names={str(n) for n in source.data_model_interface.get_bone_track_names()}
            target_names={str(n) for n in target.data_model_interface.get_bone_track_names()}
            assert names==target_names and len(names)==108
            assert set(parents[0])==set(parents[1]) and len(parents[1])==118
            assert parents[0]==parents[1],'Hierarchy differs; cannot reuse local tracks blindly'
            assert set(parents[1])-names==helper.FACE_BONES,'All non-face bones must be explicitly keyed'
            assert not u.AnimationLibrary.get_animation_curve_names(target,u.RawCurveTrackTypes.RCT_FLOAT)
            sm,tm=source.data_model_interface,target.data_model_interface
            def count(model):
                n=model.get_number_of_frames();return int(getattr(n,'value',n))
            assert count(sm)==count(tm)==old['frames']
            source_fps,target_fps=sm.get_frame_rate(),tm.get_frame_rate()
            assert source_fps.numerator*target_fps.denominator==target_fps.numerator*source_fps.denominator
            assert abs(source.get_play_length()-target.get_play_length())<1e-6
            assert abs(target.get_play_length()-clip['duration_seconds'])<1e-5
            assert abs(target.get_editor_property('rate_scale')-1.)<1e-8
            assert target.get_editor_property('additive_anim_type')==u.AdditiveAnimationType.AAT_NONE
            def options(optional_mesh=None):
                v=u.AnimPoseEvaluationOptions();v.set_editor_properties({'evaluation_type':u.AnimDataEvalType.SOURCE,'should_retarget':False,'extract_root_motion':False,'incorporate_root_motion_into_pose':True,'evaluate_curves':False,'optional_skeletal_mesh':optional_mesh});return v
            a,b=[u.AnimPoseExtensions.get_anim_pose_at_time(anim,0.,options()) for anim in (source,target)]
            assert u.AnimPoseExtensions.is_valid(a) and u.AnimPoseExtensions.is_valid(b)
            ref_changes=[]
            for n in sorted(parents[1]):
                transforms=[u.AnimPoseExtensions.get_ref_bone_pose(p,u.Name(n),u.AnimPoseSpaces.LOCAL) for p in (a,b)]
                metrics=helper.transform_metric_errors(*[helper.transform_values(t) for t in transforms])
                if max(metrics.values())>1e-5:ref_changes.append(dict(bone=n,metrics=metrics,explicit_body_track=n in names))
            # Reference differences are reported, not hidden. They cannot fill
            # any unkeyed body chain because every non-face bone is explicit.
            errors={n:0. for n in clip['frames'][0]['bones']}
            maximum=0.;worst=None
            for frame in clip['frames']:
                p=u.AnimPoseExtensions.get_anim_pose_at_time(target,frame['t'],options(mesh))
                assert u.AnimPoseExtensions.is_valid(p)
                assert set(errors)<={str(n) for n in u.AnimPoseExtensions.get_bone_names(p)}
                for n,expected in frame['bones'].items():
                    t=u.AnimPoseExtensions.get_bone_pose(p,u.Name(n),u.AnimPoseSpaces.WORLD).translation
                    error=math.sqrt(sum((v-w)**2 for v,w in zip((t.x,t.y,t.z),expected)))
                    assert math.isfinite(error);errors[n]=max(errors[n],error)
                    if error>maximum:maximum=error;worst={'bone':n,'t':frame['t'],'distance_cm':error}
            item={k:row[k] for k in ('motion_id','sex','source','target','prior_full_frame_proof')}
            item.update(success=maximum<=.1,full_duration_seconds=float(target.get_play_length()),source_frames=count(sm),body_tracks=108,hierarchy_equal=True,
                        reference_changes=ref_changes,reference_policy='All108 non-face bones explicitly keyed;10 facial-subtree reference differences allowed and replaced by accepted face composition.',
                        camera_landmark_samples=len(clip['frames']),camera_landmark_errors_cm=errors,maximum_world_landmark_error_cm=maximum,worst=worst,rate_scale=1.)
            report['actions'].append(item)
            assert maximum<=.1,'Existing target differs from frozen camera source by more than1mm; inspect before reuse'
        for record in protected:assert pin(record['path'])['sha256']==record['sha256']
        assert before=={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
        assert pin(report['camera_plan_unchanged']['path'])==report['camera_plan_unchanged']
        report.update(success=True,protected_sources=protected,sources_unchanged=True,dirty_packages_unchanged=True,human_acceptance='pending_new_scene_review')
    except Exception:
        import traceback
        report['error']=traceback.format_exc()
        raise
    finally:
        with output.open('x',encoding='utf-8') as stream:json.dump(report,stream,ensure_ascii=False,indent=2)
    return report
