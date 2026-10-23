"""Root-dispatched creation of formal source copies and 10s BodyOnly sequences.

No editor operation at import. Uses the existing audited SOURCE evaluator and
AnimDataController path. Original source/Skeleton/mesh packages remain protected.
"""
from __future__ import annotations
import importlib.util
import json
import math
from pathlib import Path
import traceback
import copy
import struct
import production_motion_contract_v1 as contract

PROJECT=Path('D:/UE/projects/datatry_02')
RUN=contract.RUN
SCRIPTS=Path(__file__).resolve().parent
LIMITS={'translation_cm':.00035,'rotation_degrees':.025,'scale_abs':.00001}
SCALE_CONSTANT_LIMIT=1e-4
SCALE_DEFAULT_MATCH_LIMIT=1e-6
ROTATION_SINGULAR_LIMIT=.12
ROTATION_PREDICTION_COMPONENT_LIMIT=1e-5
ROTATION_ENGINE_SOURCES=(
    (Path('D:/UE/UE_5.8/Engine/Source/Runtime/Core/Private/Math/UnrealMath.cpp'),'640-687','FQuat4f::Rotator projects quaternions with |Z*X-W*Y|>0.4999995f to exact pitch90 and roll0.'),
    (Path('D:/UE/UE_5.8/Engine/Plugins/Animation/AnimationData/Source/AnimationData/Private/AnimSequencerController.cpp'),'2789-2805','Quaternion input stored as Euler channels through RotationalKeys[i].Euler().'),
    (Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/character_runtime_face_library_20261007_v1/research/ue_quaternion_storage_bound_v2.md'),'threshold_derivation','Known singularity projection bound0.115349898 degrees from native float32 threshold.'))
SCALE_ENGINE_SOURCES=(
    (Path('D:/UE/UE_5.8/Engine/Plugins/Animation/AnimationData/Source/AnimationData/Private/AnimSequencerController.cpp'),'2790-2942','Each scale channel within1e-4 of its first key is stored as a constant first-key default.'),
    (Path('D:/UE/UE_5.8/Engine/Source/Runtime/Core/Public/Math/UnrealMathUtility.h'),'131','UE_KINDA_SMALL_NUMBER is1.e-4f.'))
LANDMARKS=('root','pelvis','spine_01','spine_02','neck_01','head','upperarm_l','upperarm_r',
           'hand_l','hand_r','thigh_l','thigh_r','calf_l','calf_r','foot_l','foot_r','ball_l','ball_r')


def module(name):
    spec=importlib.util.spec_from_file_location('_production_motion_'+name,SCRIPTS/(name+'.py'))
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def validate_task(task):
    if not isinstance(task,dict) or set(task)!={'motion_id','sex','contract','report_path'} or task['sex'] not in ('female','male'):
        raise ValueError('Exact production task fields required')
    if task['contract'] != contract.pin(contract.CONTRACT):
        raise ValueError('Pinned production contract changed')
    data=contract.load_contract()
    rows=[x for x in data['motions'] if x['motion_id']==task['motion_id']]
    if len(rows)!=1:raise ValueError('Unknown retained motion')
    output=Path(task['report_path']).resolve()
    if output.suffix!='.json' or not output.is_relative_to(RUN.resolve()):
        raise ValueError('Report must stay within production motion output run')
    return rows[0],output


def scale_constant_proof(expected,actual):
    """Prove every >1e-5 scale error is native constant-channel simplification.

    The strict scale gate remains unchanged for varying channels. An exception
    requires expected values all within UE's1e-4 first-key test, actual values
    all matching that first key within1e-6, and output error itself <=1e-4.
    """
    channels=[]
    for bone,source in expected.items():
        target=actual[bone]
        for axis in range(3):
            errors=[abs(a[axis]-b[axis]) for a,b in zip(source,target)]
            maximum=max(errors)
            if maximum<=LIMITS['scale_abs']:continue
            first=source[0][axis]
            deviation=max(abs(row[axis]-first) for row in source)
            default_error=max(abs(row[axis]-first) for row in target)
            constant=maximum<=SCALE_CONSTANT_LIMIT and deviation<=SCALE_CONSTANT_LIMIT and default_error<=SCALE_DEFAULT_MATCH_LIMIT
            worst=max(range(len(errors)),key=errors.__getitem__)
            channels.append({'bone':bone,'axis':'xyz'[axis],'maximum_error':maximum,'worst_frame':worst,
                'expected_at_worst':source[worst][axis],'actual_at_worst':target[worst][axis],
                'first_expected_value':first,'expected_max_deviation_from_first':deviation,
                'actual_max_deviation_from_expected_first':default_error,'native_constant_channel_proven':constant})
    return {'schema':'ue_native_constant_scale_proof_v1','success':bool(channels) and all(row['native_constant_channel_proven'] for row in channels),
        'strict_scale_limit':LIMITS['scale_abs'],'constant_channel_limit':SCALE_CONSTANT_LIMIT,
        'first_default_match_limit':SCALE_DEFAULT_MATCH_LIMIT,'channels':channels,
        'scope':'Only channels explicitly proven constant to the first input key; no general scale tolerance relaxation.'}


def _float32(value):return struct.unpack('f',struct.pack('f',value))[0]


def singular_rotation_prediction(quaternion):
    """The explicit native float32 singular branch, with UE quaternion signs."""
    f=_float32;x,y,z,w=map(f,quaternion)
    test=f(f(z*x)-f(w*y));threshold=f(.4999995)
    if abs(test)<=threshold:return None
    pitch=90. if test>0 else -90.
    radians_to_degrees=f(f(180.)/f(math.pi))
    yaw=f(f((2. if test>0 else -2.)*f(math.atan2(x,w)))*radians_to_degrees)
    yaw=yaw%360
    if yaw>180:yaw-=360
    sp=math.sin(math.radians(pitch)/2);cp=math.cos(math.radians(pitch)/2)
    sy=math.sin(math.radians(yaw)/2);cy=math.cos(math.radians(yaw)/2)
    return {'float32_singularity_test':test,'float32_threshold':threshold,
            'predicted_pitch_yaw_roll':[pitch,yaw,0.],
            'predicted_quaternion':[sp*sy,-sp*cy,cp*sy,cp*cy]}


def rotation_singularity_proof(failures):
    rows=[]
    for failure in failures:
        row=copy.deepcopy(failure)
        prediction=singular_rotation_prediction(row['expected_local_transform'][3:7])
        proven=False
        if prediction:
            a=row['actual_local_transform'][3:7];q=prediction['predicted_quaternion']
            length=math.sqrt(sum(v*v for v in a));a=[v/length for v in a]
            sign=-1 if sum(x*y for x,y in zip(a,q))<0 else 1
            delta=max(abs(x-sign*y) for x,y in zip(a,q))
            row.update(prediction,predicted_actual_max_quaternion_component_error=delta)
            proven=row['error']<=ROTATION_SINGULAR_LIMIT and delta<=ROTATION_PREDICTION_COMPONENT_LIMIT
        row['native_singularity_projection_proven']=proven;rows.append(row)
    return {'schema':'ue_native_euler_singularity_proof_v1','success':bool(rows) and all(row['native_singularity_projection_proven'] for row in rows),
        'strict_rotation_limit_degrees':LIMITS['rotation_degrees'],'singularity_rotation_limit_degrees':ROTATION_SINGULAR_LIMIT,
        'prediction_component_limit':ROTATION_PREDICTION_COMPONENT_LIMIT,'theoretical_float32_projection_bound_degrees':.115349898,
        'scope':'Only native near-pitch90 singularity projections individually predicted from each expected quaternion; no general rotation gate relaxation.',
        'samples':rows}


def run(task,reverify_existing=False):
    entry,output=validate_task(task)
    variant=entry['variants'][task['sex']]
    contract.verify_pin(variant['source'])
    for source in contract.read(task['contract']['path'])['sources']:contract.verify_pin(source)
    # Successful receipts are idempotent; existing unreceipted assets are never
    # adopted or overwritten. Root may inspect and clean failed isolated outputs.
    previous=None
    if output.exists():
        old=contract.read(output)
        if old.get('task')!=task:
            raise ValueError('Existing report is failed or belongs to another task')
        if old.get('success') is True:
            for record in old['sources']+[old['source_asset_record'],old['asset_record']]:contract.verify_pin(record)
            return old
        if not reverify_existing or old.get('sources_unchanged') is not True or old.get('dirty_sources')!=[] or old.get('new_dirty_packages_outside_target')!=[] or 'Mapped all-frame production pose verification failed' not in old.get('error',''):
            raise ValueError('Only explicit revalidation of source-preserved numerical failures is allowed')
        for record in old['sources']+[old['source_asset_record']]:contract.verify_pin(record)
        previous=old
    import unreal as u
    composer=module('ue_compose_native_face_body_v1');face=module('ue_native_face_panel_five_second_v1')
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise ValueError('Wrong UE project')
    accepted,_=face.accepted_faces()[(task['sex'],'idle')]
    source=u.load_asset(variant['source']['asset']);mesh=u.load_asset(accepted['reference_mesh'])
    if not isinstance(source,u.AnimSequence) or not isinstance(mesh,u.SkeletalMesh):raise ValueError('Expected source sequence and accepted reference mesh')
    skeleton=source.get_skeleton()
    if skeleton!=mesh.get_editor_property('skeleton') or skeleton.get_path_name().split('.')[0]!=variant['shared_skeleton'].split('.')[0]:
        raise ValueError('Body/reference shared skeleton mismatch')
    if source.get_editor_property('additive_anim_type')!=u.AdditiveAnimationType.AAT_NONE:raise ValueError('Additive source unsupported')
    sources=[composer.asset_record(a.get_path_name()) for a in (source,mesh,skeleton)]
    if sources[0]['sha256']!=variant['source']['sha256']:raise ValueError('Source provenance changed')
    before={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if before & {x['asset'].split('.')[0] for x in sources}:raise ValueError('Protected source packages are dirty')
    source_dest=variant['source_destination'];dest=variant['production_destination']
    if previous is not None and before & {source_dest,dest}:raise ValueError('Revalidation requires saved formal assets')
    exists=[u.EditorAssetLibrary.does_asset_exist(p) for p in (source_dest,dest)]
    if previous is None and any(exists):
        raise ValueError('Unreceipted formal asset already exists')
    if previous is not None and not all(exists):raise ValueError('Revalidation requires both existing formal assets')
    tracks={str(n) for n in source.data_model_interface.get_bone_track_names()}
    if tracks & composer.FACE_BONES or not {'root','pelvis','head','neck_01','neck_02'} <= tracks:
        raise ValueError('Expected BodyOnly tracks')
    if list(u.AnimationLibrary.get_animation_notify_events(source)):raise ValueError('Notify timing unsupported')
    modifier=u.SkeletonModifier()
    if not modifier.set_skeletal_mesh(mesh):raise ValueError('Cannot inspect reference mesh')
    bones=sorted(str(n) for n in modifier.get_all_bone_names())
    if len(bones)!=118 or tracks!=set(bones)-composer.FACE_BONES:raise ValueError('Expected exactly108 body tracks and118 bones')
    model=source.data_model_interface;rate=model.get_frame_rate();raw=model.get_number_of_frames();source_count=int(getattr(raw,'value',raw))
    fps=rate.numerator/rate.denominator
    if (rate.numerator,rate.denominator)!=(variant['source_frame_rate']['numerator'],variant['source_frame_rate']['denominator']) or source_count!=variant['source_frame_count']:
        raise ValueError('Pinned source frame grid changed')
    if abs(source_count/fps-variant['source_duration_seconds'])>1e-5 or abs(source.get_play_length()-source_count/fps)>1e-5:
        raise ValueError('Pinned source duration changed')
    count=round(10*fps)
    if abs(count/fps-10)>1e-8:raise ValueError('Ten seconds not native-frame representable')
    times=[i/fps for i in range(count+1)]
    curves=sorted(composer.curve_name_index([str(n) for n in u.AnimationLibrary.get_animation_curve_names(source,u.RawCurveTrackTypes.RCT_FLOAT)]).values())
    options=u.AnimPoseEvaluationOptions();options.set_editor_properties({'evaluation_type':u.AnimDataEvalType.SOURCE,'should_retarget':False,
        'extract_root_motion':False,'incorporate_root_motion_into_pose':True,'evaluate_curves':True,'optional_skeletal_mesh':mesh})

    def pose(asset,t):
        p=u.AnimPoseExtensions.get_anim_pose_at_time(asset,t,options)
        if not u.AnimPoseExtensions.is_valid(p) or not set(bones)<={str(n) for n in u.AnimPoseExtensions.get_bone_names(p)} or not composer.curve_names_present(curves,[str(n) for n in u.AnimPoseExtensions.get_curve_names(p)]):
            raise RuntimeError('SOURCE evaluator missing bones or curves')
        transforms={n:u.AnimPoseExtensions.get_bone_pose(p,u.Name(n),u.AnimPoseSpaces.LOCAL) for n in bones}
        values={n:float(u.AnimPoseExtensions.get_curve_weight(p,u.Name(n))) for n in curves}
        if not all(math.isfinite(v) for tr in transforms.values() for v in composer.transform_values(tr)) or not all(math.isfinite(v) for v in values.values()):
            raise RuntimeError('Nonfinite SOURCE pose')
        return transforms,values

    def expected(t):
        weighted=contract.map_output_time(entry,t,sex=task['sex'])
        samples=[pose(source,row['source_seconds']) for row in weighted]
        if len(samples)==1:return samples[0]
        alpha=weighted[1]['weight'];transforms={}
        for n in bones:
            value=composer.blend_transform_values(composer.transform_values(samples[0][0][n]),composer.transform_values(samples[1][0][n]),alpha)
            tr=u.Transform();tr.set_editor_properties({'translation':u.Vector(*value[:3]),'rotation':u.Quat(*value[3:7]),'scale3d':u.Vector(*value[7:])});transforms[n]=tr
        values={n:(1-alpha)*samples[0][1][n]+alpha*samples[1][1][n] for n in curves}
        return transforms,values

    report={'schema':'production_motion_bake_v1','success':False,'task':task,'motion_id':entry['motion_id'],'label_zh':entry['label_zh'],
        'source_destination':source_dest,'destination':dest,'sources':sources,'production10':entry['production10'],
        'faces_included':False,'human_naturalness_acceptance':'pending','camera_retime_required':True,'source_full_duration_seconds':source_count/fps}
    try:
        samples=[expected(t) for t in times]
        formal=u.load_asset(source_dest) if previous else u.EditorAssetLibrary.duplicate_asset(source.get_path_name().split('.')[0],source_dest)
        if not isinstance(formal,u.AnimSequence) or not previous and not u.EditorAssetLibrary.save_loaded_asset(formal,only_if_is_dirty=False):raise RuntimeError('Could not save formal source copy')
        if int(getattr(formal.data_model_interface.get_number_of_frames(),'value',formal.data_model_interface.get_number_of_frames()))!=source_count or formal.get_skeleton()!=skeleton:
            raise RuntimeError('Formal source copy frame grid or skeleton changed')
        source_maxima={key:0. for key in LIMITS}
        for t in (0.,source_count/fps/2,source_count/fps):
            a,b=pose(formal,t),pose(source,t)
            for n in bones:
                for key,error in composer.transform_metric_errors(composer.transform_values(a[0][n]),composer.transform_values(b[0][n])).items():source_maxima[key]=max(source_maxima[key],error)
            if any(abs(a[1][n]-b[1][n])>1e-4 for n in curves):raise RuntimeError('Formal source curves changed')
        if any(source_maxima[k]>LIMITS[k] for k in LIMITS):raise RuntimeError('Formal source copy pose changed')
        report['source_asset_record']=composer.asset_record(formal.get_path_name())
        report['source_copy_validation']={'sample_times_seconds':[0.,source_count/fps/2,source_count/fps],'maximum_physical_errors':source_maxima,'full_duration_frame_grid_preserved':True,'method':'EditorAssetLibrary.duplicate_asset without modifying source-copy tracks'}
        target=u.load_asset(dest) if previous else u.EditorAssetLibrary.duplicate_asset(formal.get_path_name().split('.')[0],dest)
        if not isinstance(target,u.AnimSequence):raise RuntimeError('Could not duplicate production animation')
        target_before=composer.asset_record(target.get_path_name()) if previous else None
        if previous:
            if abs(target.get_editor_property('rate_scale')-1)>1e-8:raise ValueError('Existing production rate scale changed')
        else:
            target.set_editor_property('rate_scale',1.)
            controller=target.controller;controller.open_bracket('Approved 26-motion ten-second body resampling',False)
            try:
                if controller.remove_all_attributes(False):raise ValueError('Timed source attributes unsupported')
                controller.set_number_of_frames(u.FrameNumber(value=count),False)
                for n in sorted(tracks):
                    values=[p[0][n] for p in samples]
                    if not controller.set_bone_track_keys(u.Name(n),[v.translation for v in values],[v.rotation for v in values],[v.scale3d for v in values],False):raise RuntimeError('Bone bake failed:'+n)
                for n in curves:
                    u.AnimationLibrary.remove_curve(target,u.Name(n),False);u.AnimationLibrary.add_curve(target,u.Name(n),u.RawCurveTrackTypes.RCT_FLOAT,False)
                    u.AnimationLibrary.add_float_curve_keys(target,u.Name(n),times,[p[1][n] for p in samples])
            finally:controller.close_bracket(False)
        if abs(target.get_play_length()-10)>1e-6 or target.get_skeleton()!=skeleton or {str(n) for n in target.data_model_interface.get_bone_track_names()}!=tracks:raise RuntimeError('Production output contract differs')
        actual_rate=target.data_model_interface.get_frame_rate()
        if (actual_rate.numerator,actual_rate.denominator)!=(rate.numerator,rate.denominator):raise RuntimeError('Production frame rate changed')
        if composer.curve_name_index([str(n) for n in u.AnimationLibrary.get_animation_curve_names(target,u.RawCurveTrackTypes.RCT_FLOAT)]).keys()!=composer.curve_name_index(curves).keys():raise RuntimeError('Production curve inventory changed')
        if not previous and not u.EditorAssetLibrary.save_loaded_asset(target,only_if_is_dirty=False):raise RuntimeError('Could not save production body')
        maximum={key:0. for key in LIMITS};curve_error=0.;root_error=0.;landmarks=[];worst={};rotation_failures=[]
        actual_scales={n:[] for n in bones}
        for i,t in enumerate(times):
            actual=pose(target,t)
            for n in bones:
                actual_scales[n].append(composer.transform_values(actual[0][n])[7:])
                actual_values=composer.transform_values(actual[0][n]);expected_values=composer.transform_values(samples[i][0][n])
                for key,error in composer.transform_metric_errors(actual_values,expected_values).items():
                    if error>maximum[key]:
                        maximum[key]=error
                        worst[key]={'bone':n,'frame':i,'time_seconds':t,'error':error,'expected_local_transform':expected_values,'actual_local_transform':actual_values}
                    if key=='rotation_degrees' and error>LIMITS[key]:
                        rotation_failures.append({'bone':n,'frame':i,'time_seconds':t,'error':error,'expected_local_transform':expected_values,'actual_local_transform':actual_values})
                if n=='root':root_error=max(root_error,composer.transform_error(actual[0][n],samples[i][0][n]))
            for n in curves:curve_error=max(curve_error,abs(actual[1][n]-samples[i][1][n]))
            if math.isclose(t*10,round(t*10),abs_tol=1e-7):
                p=u.AnimPoseExtensions.get_anim_pose_at_time(target,t,options)
                world={n:u.AnimPoseExtensions.get_bone_pose(p,u.Name(n),u.AnimPoseSpaces.WORLD).translation for n in LANDMARKS}
                landmarks.append({'t':t,'bones':{n:[float(v.x),float(v.y),float(v.z)] for n,v in world.items()}})
        report['verification']={'duration_seconds':float(target.get_play_length()),'fps':fps,'all_frame_count':len(times),'bone_count':len(bones),'body_tracks':len(tracks),
            'maximum_physical_errors':maximum,'physical_limits':LIMITS,'maximum_curve_error':curve_error,'maximum_root_component_error':root_error,
            'root_and_curve_limit':1e-4,'all_frames_verified':True,'root_trajectory_mapped_not_zeroed':True,'worst':worst}
        scale_pass=maximum['scale_abs']<=LIMITS['scale_abs']
        if not scale_pass:
            expected_scales={n:[composer.transform_values(p[0][n])[7:] for p in samples] for n in bones}
            proof=scale_constant_proof(expected_scales,actual_scales)
            proof['engine_precision_basis']=[dict(contract.pin(p),lines=lines,reason=reason) for p,lines,reason in SCALE_ENGINE_SOURCES]
            report['verification']['native_constant_scale_proof']=proof
            scale_pass=proof['success']
        rotation_pass=maximum['rotation_degrees']<=LIMITS['rotation_degrees']
        if not rotation_pass:
            proof=rotation_singularity_proof(rotation_failures)
            proof['engine_precision_basis']=[dict(contract.pin(p),lines=lines,reason=reason) for p,lines,reason in ROTATION_ENGINE_SOURCES]
            report['verification']['native_euler_singularity_proof']=proof
            rotation_pass=proof['success']
        if maximum['translation_cm']>LIMITS['translation_cm'] or not rotation_pass or not scale_pass or curve_error>1e-4 or root_error>1e-4:raise RuntimeError('Mapped all-frame production pose verification failed')
        report['asset_record']=composer.asset_record(target.get_path_name())
        report['production_landmarks']={'motion_id':entry['motion_id'],'sex':task['sex'],'asset':target.get_path_name(),'animation_path':target.get_path_name(),
            'clip_id':entry['motion_id'].lower()+'_'+task['sex']+'_production10','duration_seconds':10.,'window_start_seconds':0.,'window_duration_seconds':10.,
            'source_frame_count':count,'source_frame_rate':{'numerator':rate.numerator,'denominator':rate.denominator},'source_skeleton':skeleton.get_path_name(),
            'source_package':report['asset_record'],'coordinates':'SOURCE WORLD bone landmarks, cm, actor identity','fps':10,'frames':landmarks}
        report['success']=True
        if previous:
            if composer.asset_record(target.get_path_name())!=target_before:raise RuntimeError('Read-only revalidation changed target package')
            if {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}!=before:raise RuntimeError('Read-only revalidation changed dirty packages')
            report['read_only_revalidation']={'target_unchanged':True,'target_at_start':target_before,
                'scope':'Existing body source and production assets were loaded and evaluated only; no asset setters, controller writes or saves.'}
    except Exception:
        report['success']=False
        report['error']=traceback.format_exc();raise
    finally:
        try:report.update(face.preservation(composer,u,sources,before,dest))
        except Exception:report.update(success=False,protection_error=traceback.format_exc())
        output.parent.mkdir(parents=True,exist_ok=True)
        if previous:
            # Keep the original failed evidence byte-for-byte before replacing
            # its canonical receipt with the new complete independent proof.
            archive=output.parent/'history'/(output.stem+'_failed_'+contract.pin(output)['sha256'][:12]+'.json')
            archive.parent.mkdir(parents=True,exist_ok=True)
            if archive.exists():
                if archive.read_bytes()!=output.read_bytes():raise RuntimeError('Failed report archive collision')
            else:
                with archive.open('xb') as stream:stream.write(output.read_bytes())
            report['original_failed_report']=contract.pin(archive)
            temp=output.with_suffix('.revalidated.partial')
            temp.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8');temp.replace(output)
        else:
            with output.open('x',encoding='utf-8') as stream:json.dump(report,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
    if report['success'] is not True:raise RuntimeError('Source preservation failed; inspect report')
    return report


if 'DM_PRODUCTION_MOTION_TASK' in globals():run(globals()['DM_PRODUCTION_MOTION_TASK'])
