"""One real Delicate application; independent TearLine response; bounded restore.

Original support deviations stay failed/pending until both are restored. Only
native704 lash geometry is measured and exactly evidenced two type9 parts may
be added. Original6 OBJ attributes stay strict; new lash UV needs complete FBX.
No other Body/support geometry allowance; no residual retries.
"""
import hashlib
import json
import math
import os
import shutil
import sys
import traceback
import types

SELECTORS = {'CC_Base_EyeOcclusion':{'part_type':'5','mesh_name':'CC_Base_EyeOcclusion','vertex_count':182},
             'CC_Base_TearLine':{'part_type':'6','mesh_name':'CC_Base_TearLine','vertex_count':190}}
ORIGINAL_NAMES=frozenset(('CC_Base_Body','CC_Base_Tongue','CC_Base_Eye','CC_Base_Teeth','CC_Base_EyeOcclusion','CC_Base_TearLine'))
NEW_NAMES=frozenset(('Lash_Low_Bushy','Lash_Up_Bushy'))


def omit_meshes(snapshot,names):
    return dict(snapshot,meshes=[m for m in snapshot['meshes'] if m['name'] not in names])


def uv_attributes_equal(before_path,after_path):
    from cc_eye_support_obj_semantics_v1 import read_native
    before,after=read_native(before_path),read_native(after_path)
    topology=lambda s:[[c[0]for c in face['corners']]for face in s['faces']]
    uv=lambda s:[[s['vt'][c[1]]for c in face['corners']]for face in s['faces']]
    state=lambda s:[(f['group'],f['material'],f['smoothing'])for f in s['faces']]
    return {'passed':len(before['v'])==len(after['v'])and topology(before)==topology(after)and uv(before)==uv(after)and state(before)==state(after),
        'topology_exact':topology(before)==topology(after),'uv_per_corner_exact':uv(before)==uv(after),
        'group_material_smoothing_exact':state(before)==state(after)}


def native_group_layouts(path):
    from cc_eye_support_obj_semantics_v1 import read_native
    full=read_native(path); groups={}
    for face in full['faces']:groups.setdefault(face['group'],[]).append(face)
    result={}
    for name,faces in groups.items():
        ids=sorted({c[0]for face in faces for c in face['corners']}); mapping={v:i for i,v in enumerate(ids)}
        result[name]={'vertex_count':len(ids),'faces':[[mapping[c[0]]for c in f['corners']]for f in faces]}
    return result


def native_template_layouts(layouts,source_layouts=None):
    """Observed exporter emits original6 only; SDK retains new2 outside OBJ.

    Never claim this OBJ is a complete avatar transfer or new-lash UV proof.
    """
    if set(layouts)!=set(ORIGINAL_NAMES):raise ValueError("Native replacement template requires exact original six groups")
    return layouts if source_layouts is None else source_layouts


def run(library,output_dir,log,api):
    directory=os.path.dirname(__file__)
    if directory not in sys.path:sys.path.insert(0,directory)
    import cc_refresh_eyelash_probe_v2 as lash
    import cc_probe_eye_support_identity_v5 as identity
    import cc_eye_support_inverse_affine_v1 as eye_inverse
    import cc_support_affine_runtime_v1 as response
    import cc_eye_support_obj_semantics_v1 as semantics
    import cc_refresh_eye_support_diagnostic_v1 as queries
    import cc_repair_headshot_support_materials_v1 as capture
    import cc_capture_assembly_geometry_v1 as body_capture
    from cc_compile_character_manifest import facial_pool
    c=library['refresh_delicate_support_restore'];source=c['source_project']
    if (c.get('operation')!='apply_delicate_fit_tearline_restore_original_once'
            or c.get('save_current_scene_backup')is not True or c.get('maximum_response_calls')!=1
            or c.get('maximum_restores_per_support')!=1
            or c.get('native_template_scope')!='original6_new_lash_uv_pending_complete_fbx'):raise ValueError('Explicit one-shot real Delicate restoration contract required')
    if (not any(lash.inside(source['path'],root)for root in(lash.CREATION_ROOT,lash.RUN_ROOT,lash.STAGE_ROOT))
            or api.sha256_file(source['path'])!=source['sha256']):raise ValueError('Immutable original source changed')
    if not lash.inside(output_dir,lash.RUN_ROOT)or os.path.realpath(output_dir)==os.path.realpath(lash.RUN_ROOT):raise ValueError('New independent output required')
    if os.path.exists(output_dir)and os.listdir(output_dir):raise ValueError('Refuse existing restoration outputs')
    for record,path in((c['registry'],lash.REGISTRY),(c['native_lash_resource'],lash.RESOURCE)):
        if os.path.normcase(os.path.realpath(record['path']))!=os.path.normcase(os.path.realpath(path))or api.sha256_file(path)!=record['sha256']:
            raise ValueError('Registry/native partition reference changed')
    pool=facial_pool(api.read_json(lash.REGISTRY),'eyelashes');selected=pool.get(c['eyelash_asset_id'])
    if len(pool)!=9 or not selected or selected['asset_id']!=lash.DELICATE_ID or selected['sha256']!=lash.DELICATE_SHA or api.sha256_file(selected['path'])!=selected['sha256']:
        raise ValueError('Only exact evidenced Delicate asset allowed')
    asset={k:selected.get(k)for k in('asset_id','display_name','asset_type','asset_form','application_mode','slot','path','sha256')}
    asset.update(extension=os.path.splitext(asset['path'])[1].lower(),verification_mode='scene_inventory')
    addition=lash.validate_addition_evidence(c,asset,source,api,capture.compare_geometry)
    evidence=c['validated_eye_occlusion_identity'];model_record=c['eye_occlusion_inverse_model']
    if (not lash.inside(evidence['path'],lash.RUN_ROOT)or api.sha256_file(evidence['path'])!=evidence['sha256']
            or not lash.inside(model_record['path'],lash.STAGE_ROOT)or api.sha256_file(model_record['path'])!=model_record['sha256']):
        raise ValueError('Validated identity/model evidence changed')
    v5=api.read_json(evidence['path']);eye_model=api.read_json(model_record['path'])
    if (v5.get('success')is not True or not v5.get('restored_source')or not v5.get('source_unchanged')
            or v5['source_project']['sha256']!=source['sha256']
            or v5['inverse_affine_model']['sha256']!=model_record['sha256']
            or eye_model['source_project']['sha256']!=source['sha256']):raise ValueError('Exact successful same-source EyeOcclusion identity required')
    for file in eye_model['source_files'].values():
        if not lash.inside(file['path'],lash.RUN_ROOT)or api.sha256_file(file['path'])!=file['sha256']:raise ValueError('Original EyeOcclusion model input changed')
    if api.sha256_file(eye_inverse.__file__)!=eye_model['fitter']['sha256']:raise ValueError('Validated EyeOcclusion inverse helper changed')
    eye_inverse.verify_model(eye_model)
    os.makedirs(output_dir,exist_ok=True)
    rp=os.path.join(output_dir,'delicate_support_restore_report.json');sp=os.path.join(output_dir,'validation_result.json')
    report={'schema_version':1,'success':False,'status':'running_independent_probe','source_project':source,
        'asset':asset,'addition_evidence':addition,'validated_eye_occlusion_identity':evidence,'eye_occlusion_inverse_model':model_record,
        'visual_acceptance':'pending','lash_upper_bound_registered':False,'material_pixels_verified':False,
        'new_lash_UV_verified':False,'complete_export_verified':False,'assembly_accepted':False,
        'new_lash_UV_pending':'Complete FBX readback required. Native OBJ emits original6 only; SDK new2 geometry/topology/owners remain protected.',
        'implementation_sha256':api.sha256_file(__file__),'steps':[],'uv_checks':[],'normal_semantic_checks':[],
        'report_path':rp,'summary_path':sp,'source_rollback_required':True,
        'scope':'Native OBJ is original6 replacement template only;new2lash UV pending completeFBX. Native704 measured only;13460 Body points0.002mm; original nonBody low/high and owners0.002mm after restoration; exact original UV; exact evidenced new2lash parts persist. Inactive Body high arrays recorded, excluded from active native704 contract.',
        'dependencies':{name:api.sha256_file(os.path.join(directory,name))for name in
            ('cc_refresh_eyelash_probe_v2.py','cc_probe_eye_support_identity_v5.py','cc_eye_support_inverse_affine_v1.py',
             'cc_support_affine_runtime_v1.py','cc_eye_support_obj_semantics_v1.py','cc_refresh_eye_support_diagnostic_v1.py',
             'cc_repair_headshot_support_materials_v1.py','cc_capture_assembly_geometry_v1.py')}}
    R=api.RLPy;raw_api=types.SimpleNamespace(_transform_data=api._transform_data)
    baseline=None;asset_baseline=None;working=None;attempted=False;source_exports=None;asset_exports=None
    def checkpoint(phase):
        report['phase']=phase;report['updated_at']=api.now();api.write_json(report,rp);log('Delicate support restoration: '+phase)
    def avatar():
        items=list(R.RScene.GetAvatars()or[])
        if len(items)!=1:raise ValueError('One independent avatar required')
        return items[0]
    def load(record,label):
        if api.sha256_file(record['path'])!=record['sha256']:raise ValueError('Load source changed')
        status,dialogs=api.load_file_with_optional_undo_warning(record['path'],label)
        report.setdefault('loads',[]).append({'label':label,'status':status,'dialogs':dialogs});R.RScene.SelectObject(avatar())
    def snapshot(label):
        a=avatar();full=capture.capture_geometry(a,api=raw_api)
        value={'geometry':full,'other_meshes':lash.nonbody_support_snapshot(full),
            'body':body_capture.capture_body_snapshot(a,api=raw_api,include_world=True),
            'support_queries':queries.query_support_levels(a),
            'worlds':{name:identity.target_world(a,selector)for name,selector in SELECTORS.items()},
            'eye':api.capture_eye_integrity_state(a),'weights':api.capture_eye_part_morph_weights(a)}
        if value['body']['working_subdivision_level']!=0 or value['body']['scene_explicitly_settled']or not value['support_queries']['consistent']:
            raise ValueError('Consistent raw activeSubD0 captures required')
        path=os.path.join(output_dir,label+'_snapshot.json');api.write_json(value,path)
        value['file']=api.bodyfit_freeze_file_record(path);return value
    def desired(name):
        matches=[m for m in baseline['other_meshes']['meshes']if m['name']==name and m['vertex_count']==SELECTORS[name]['vertex_count']]
        if len(matches)!=1:raise ValueError('Ambiguous original support target')
        return matches[0]['vertices']
    def check(label,actual,pending=(),asset_pending=()):
        body=lash.body_gate(baseline['body'],actual['body'])
        eye=api.compare_neutral_eye_states(baseline['eye'],actual['eye'],tolerance=.0002,include_world=True,include_runtime_ids=False,t_pose_tolerance=.0002,world_translation_tolerance=.0002)
        before={x['id']:float(x['weight'])for x in baseline['weights']};after={x['id']:float(x['weight'])for x in actual['weights']}
        weights=set(before)==set(after)and all(abs(before[k]-after[k])<=1e-7 for k in before)
        full=lash.compare_existing_supports(baseline['other_meshes'],actual['other_meshes'],capture.compare_geometry)
        retained=lash.compare_existing_supports(omit_meshes(baseline['other_meshes'],set(pending)),omit_meshes(actual['other_meshes'],set(pending)),capture.compare_geometry)
        persistence=None;body_persistence=None
        if asset_baseline is not None:
            persistence=capture.compare_geometry(omit_meshes(asset_baseline['other_meshes'],set(asset_pending)),omit_meshes(actual['other_meshes'],set(asset_pending)))
            body_persistence=max(max(lash._distances(asset_baseline['body'][space],actual['body'][space]))for space in('local','world'))
        targets={name:max(lash._distances(baseline['worlds'][name]['world'],actual['worlds'][name]['world']))for name in SELECTORS}
        original_pass=body['passed']and full['passed']and eye['matches']and weights and max(targets.values())<=.002
        must_pass=body['passed']and retained['passed']and eye['matches']and weights
        if persistence is not None:must_pass=must_pass and persistence['passed']and body_persistence<=.002
        if not pending:must_pass=must_pass and original_pass
        step={'phase':label,'original_protection_passed':original_pass,'original_supports':full,'body':body,'eye':eye,'weights_preserved':weights,
            'pending_restoration_supports':list(pending),'nonpending_protection_passed':must_pass,'nonpending_supports':retained,
            'applied_asset_persistence':persistence,'all_body_vs_applied_asset_max_mm':body_persistence,'target_world_vs_original_max_mm':targets,
            'candidate_accepted':False,'passed':must_pass if not pending else False}
        report['steps'].append(step);checkpoint(label+'_checked')
        if not must_pass:raise ValueError('Nonpending protected geometry changed: '+label)
        return step
    def original_unchanged(label,actual):
        full=capture.compare_geometry(baseline['geometry'],actual['geometry'])
        body=max(max(lash._distances(baseline['body'][space],actual['body'][space]))for space in('local','world'))
        if not full['passed']or body>.002:raise ValueError('Original source changed before asset: '+label)
    def export(label,expected=None):
        path=os.path.join(output_dir,label+'_whole_avatar.obj');flags=R.EExport3DFileOption_AllClothes|R.EExport3DFileOption_FullBodyPart
        api.checked('Export native whole-avatar layout',R.RFileIO.ExportObjFile(avatar(),path,flags))
        layouts=native_group_layouts(path)
        if expected is None:expected=native_template_layouts(layouts,None if source_exports is None else source_exports['layouts'])
        elif set(layouts)!=set(expected):raise ValueError('Native export template group set changed')
        templates={}
        for name,row in expected.items():
            target=os.path.join(output_dir,label+'_'+name+'.obj')
            extraction=identity.extract_native_group(path,target,name,row['vertex_count'],row['faces'])
            templates[name]={'path':target,'parsed':identity.parse_native_obj(target,name,row['vertex_count'],row['faces']),'extraction':extraction}
        report.setdefault('native_exports',[]).append({'phase':label,'whole_avatar':api.bodyfit_freeze_file_record(path),
            'templates':{name:api.bodyfit_freeze_file_record(row['path'])for name,row in templates.items()}})
        return {'layouts':expected,'templates':templates}
    def uv_check(label,actual_exports):
        comparisons={name:uv_attributes_equal(source_exports['templates'][name]['path'],actual_exports['templates'][name]['path'])for name in ORIGINAL_NAMES}
        item={'phase':label,'per_mesh':comparisons,'passed':all(x['passed']for x in comparisons.values())};report['uv_checks'].append(item);checkpoint(label+'_UV_checked')
        if not item['passed']:raise ValueError('Protected original six UV/topology/material/s changed')
    def normal_check(label,exports):
        results={name:semantics.compare_native_semantics(source_exports['templates'][name]['path'],exports['templates'][name]['path'])for name in SELECTORS}
        report['normal_semantic_checks'].append({'phase':label,'per_support':results,'passed':all(r['passed']for r in results.values())});checkpoint(label+'_normals_checked')
        if not all(r['passed']for r in results.values()):raise ValueError('Restored support normal/UV semantics changed')
    def replace(name,world,label):
        row=asset_exports['templates'][name];path=os.path.join(output_dir,label+'.obj')
        details=identity.write_identity_world_obj(row['parsed'],world,path)
        copied=identity.parse_native_obj(path,name,SELECTORS[name]['vertex_count'],baseline['worlds'][name]['faces'])
        if copied['uv_normal_material_corner_sha256']!=row['parsed']['uv_normal_material_corner_sha256']:raise ValueError('Replacement changed copied native attributes')
        checkpoint(label)
        result=api.checked('One bounded support mesh replacement',identity.resolve_target(avatar(),SELECTORS[name])[1].ReplaceMesh(path,R.EReplaceMeshOption_ZUp,False))
        report.setdefault('replacements',[]).append({'support':name,'label':label,'input':api.bodyfit_freeze_file_record(path),'status':result,'attribute_copy':details})
    def render(label):
        path=os.path.join(output_dir,label+'.png');api.render_preview(path);return api.bodyfit_freeze_file_record(path)
    try:
        checkpoint('backup_current_scene');path=os.path.join(output_dir,'scene_before_probe.ccProject')
        api.checked('Backup current scene',R.RFileIO.SaveProject(path));report['current_scene_backup']=api.bodyfit_freeze_file_record(path)
        path=os.path.join(output_dir,'immutable_original_source.ccProject');shutil.copyfile(source['path'],path);working=api.bodyfit_freeze_file_record(path)
        if working['sha256']!=source['sha256']:raise ValueError('Working copy mismatch')
        report['working_source']=working;attempted=True;load(working,'Load original Delicate restoration source')
        baseline=snapshot('original_before_asset')
        # Bind validated EyeOcclusion model to this exact current origin.
        eye_snapshot={'geometry':baseline['geometry'],'target_world':baseline['worlds']['CC_Base_EyeOcclusion']}
        report['eye_model_live_origin']=eye_inverse.verify_live_origin(eye_model,eye_snapshot)
        bodymesh=[m for m in avatar().GetMeshes(False)if m.GetName()=='CC_Base_Body'and m.GetVerticesCount()==lash.BODY_COUNT]
        if len(bodymesh)!=1:raise ValueError('One original native Body required')
        bodyfaces=[list(bodymesh[0].GetFace(i))for i in range(bodymesh[0].GetFacesCount())]
        report['native_lash_partition']=lash.native_partition(lash.RESOURCE,bodyfaces)
        source_exports=export('original_native');original_unchanged('original_native_export',snapshot('original_after_export'))
        checkpoint('apply_actual_Delicate');_,application=api.apply_appearance_assets(avatar(),[asset],cleanup_names=[],allow_missing_cleanup=True,
            progress_callback=lambda phase,detail=None:checkpoint('apply:'+phase))
        report['application']=application
        if len(application.get('steps',[]))!=1 or any(application['steps'][0].get(k)is not True for k in('character_preset_verified','eye_geometry_preserved','eye_support_preserved')):
            raise ValueError('Existing exact asset/eye guards did not confirm application')
        report['applied_render']=render('applied_asset_evaluation')
        applied=snapshot('applied_rendered');check('applied_rendered',applied,pending=tuple(SELECTORS));asset_baseline=applied
        asset_exports=export('applied_native');check('applied_native_export',snapshot('applied_after_export'),pending=tuple(SELECTORS),asset_pending=())
        uv_check('applied_native',asset_exports)
        tear='CC_Base_TearLine';eye='CC_Base_EyeOcclusion'
        before_calibration=snapshot('before_tearline_response');input_world=before_calibration['worlds'][tear]['world']
        replace(tear,input_world,'CALIBRATION_TearLine_same_world_once')
        observed=snapshot('after_tearline_response_raw');check('after_tearline_response_raw',observed,pending=tuple(SELECTORS),asset_pending=(tear,))
        local=next(m['vertices']for m in observed['other_meshes']['meshes']if m['name']==tear and m['vertex_count']==190)
        fitted=response.fit_response(input_world,local,desired(tear),190)
        fitted['source_project']=source;fitted['target']=SELECTORS[tear];fitted['input_snapshot']=before_calibration['file'];fitted['output_snapshot']=observed['file']
        model_path=os.path.join(output_dir,'actual_TearLine_response_model.json');api.write_json(fitted,model_path);report['tearline_response_model']=api.bodyfit_freeze_file_record(model_path);report['tearline_response_metrics']={k:v for k,v in fitted.items()if k!='submitted_input_cm'}
        replace(eye,eye_model['submitted_compensated_input_cm'],'RESTORE_EyeOcclusion_source_local_once')
        after_eye=snapshot('after_eye_restore_raw');check('after_eye_restore_raw',after_eye,pending=tuple(SELECTORS),asset_pending=tuple(SELECTORS))
        replace(tear,fitted['submitted_input_cm'],'RESTORE_TearLine_source_local_once')
        raw=snapshot('after_both_restore_raw');check('after_both_restore_raw',raw,pending=tuple(SELECTORS),asset_pending=tuple(SELECTORS))
        for name in SELECTORS:
            actual=next(m['vertices']for m in raw['other_meshes']['meshes']if m['name']==name and m['vertex_count']==SELECTORS[name]['vertex_count'])
            if max(lash._distances(desired(name),actual))>.002:raise ValueError('Restored active low support failed original target')
        report['restored_render']=render('restored_support_evaluation')
        final=snapshot('restored_rendered');check('restored_rendered',final,asset_pending=tuple(SELECTORS))
        final_exports=export('restored_native',asset_exports['layouts']);check('restored_native_export',snapshot('restored_after_export'),asset_pending=tuple(SELECTORS));uv_check('restored_native',final_exports);normal_check('restored_native',final_exports)
        candidate=os.path.join(output_dir,'CANDIDATE_Delicate_original_supports_restored.ccProject');api.checked('Save independent restored candidate',R.RFileIO.SaveProject(candidate));report['saved_project']=api.bodyfit_freeze_file_record(candidate)
        check('post_save',snapshot('post_save'),asset_pending=tuple(SELECTORS));load(report['saved_project'],'Reload independent restored Delicate candidate')
        check('reloaded',snapshot('reloaded'),asset_pending=tuple(SELECTORS));reloaded_exports=export('reloaded_native',asset_exports['layouts'])
        check('reloaded_native_export',snapshot('reloaded_after_export'),asset_pending=tuple(SELECTORS));uv_check('reloaded_native',reloaded_exports);normal_check('reloaded_native',reloaded_exports)
        report['geometry_restore_completed']=True
    except Exception as error:
        report['error']={'type':type(error).__name__,'message':str(error),'traceback':traceback.format_exc()}
    finally:
        restored=False
        if attempted and working:
            try:
                checkpoint('restore_original_source');load(working,'Rollback original source after independent Delicate probe');actual=snapshot('rollback_original')
                if baseline:
                    original_unchanged('rollback_original',actual)
                    eye=api.compare_neutral_eye_states(baseline['eye'],actual['eye'],tolerance=.0002,include_world=True,include_runtime_ids=False,t_pose_tolerance=.0002,world_translation_tolerance=.0002)
                    old={x['id']:float(x['weight'])for x in baseline['weights']};new={x['id']:float(x['weight'])for x in actual['weights']}
                    restored=eye['matches']and old==new
                    report['rollback']={'restored':restored,'body_local_max_mm':max(lash._distances(baseline['body']['local'],actual['body']['local'])),
                        'all_original_geometry':capture.compare_geometry(baseline['geometry'],actual['geometry']),'eye':eye,'weights_exact':old==new}
            except Exception as error:report['rollback']={'restored':False,'error':str(error)}
        report['source_unchanged']=api.sha256_file(source['path'])==source['sha256'];report['restored_source']=restored
        report['success']=bool(report.get('geometry_restore_completed')and restored and report['source_unchanged']and not report.get('error'))
        report['status']='geometry_supported_without_visual_acceptance'if report['success']else'failed_Delicate_support_restore'
        checkpoint(report['status'])
    summary={k:report[k]for k in('success','status','source_unchanged','restored_source','report_path','summary_path','visual_acceptance','lash_upper_bound_registered','material_pixels_verified','new_lash_UV_verified','complete_export_verified','assembly_accepted')}
    summary.update(saved_project=report.get('saved_project'),error=report.get('error'));api.write_json(summary,sp);return summary
