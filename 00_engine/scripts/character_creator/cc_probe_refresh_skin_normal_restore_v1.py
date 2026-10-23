"""One source-bound LM skin Normal restoration; no character reassembly.

Only four recorded same-case after_skin maps are loaded to the proven SDK
Normal write enum. Bump and Normal reads stay separate. Other standard eight
channels and all actual geometry remain strict. Final full FBX/visual pending.
"""
import copy
import os
import shutil
import traceback
from types import SimpleNamespace

SKINS=frozenset(('Std_Skin_Head','Std_Skin_Body','Std_Skin_Arm','Std_Skin_Leg'))
PAIRED=frozenset(('normal','bump'))


def pixel_compare(before,after,api,allow_four_normal_pairs=False):
    from cc_probe_refresh_skin_material_readonly_v1 import CHANNELS
    from cc_repair_headshot_support_materials_v1 import compare_png_images
    keyed=lambda s:{(r['owner'],r['mesh'],r['material']):r for r in s['materials']}
    a,b=keyed(before),keyed(after);failures=[];metadata=[]
    if len(a)!=len(before['materials'])or len(b)!=len(after['materials']):raise ValueError('Unique exact material inventory required')
    for key in sorted(set(a)|set(b)):
        if key not in a or key not in b:failures.append(dict(key=key,reason='material_inventory_changed'));continue
        if any(a[key].get(f)!=b[key].get(f)for f in ('properties','shader_parameters','component_source')):metadata.append(key)
        for channel,_ in CHANNELS:
            if allow_four_normal_pairs and key==('avatar','CC_Base_Body',key[2])and key[2]in SKINS and channel in PAIRED:continue
            left=a[key]['textures'].get(channel);right=b[key]['textures'].get(channel)
            if left is None and right is None:
                # Availability is compared honestly; warning PNGs are not maps.
                continue
            if left is None or right is None:failures.append(dict(key=key,channel=channel,reason='availability_changed'));continue
            if (left['width'],left['height'])!=(right['width'],right['height']):failures.append(dict(key=key,channel=channel,reason='dimensions_changed'));continue
            if left['sha256']!=right['sha256']and not compare_png_images(left['path'],right['path'],api)['rgba_pixels_equal']:failures.append(dict(key=key,channel=channel,reason='rgba_changed'))
    return dict(passed=bool(before.get('pixel_capture_complete')and after.get('pixel_capture_complete')and not failures),differences=failures,
        allowed_four_skin_normal_bump_pairs=allow_four_normal_pairs,metadata_changes_observed=metadata,channels=[n for n,_ in CHANNELS])


def verify_restored_maps(snapshot,maps,api):
    from cc_repair_headshot_support_materials_v1 import compare_png_images
    rows={(r['owner'],r['mesh'],r['material']):r for r in snapshot['materials']};results={}
    for material,source in maps.items():
        row=rows[('avatar','CC_Base_Body',material)];readbacks={};matches=0
        for channel in sorted(PAIRED):
            actual=row['textures'].get(channel)
            if actual:
                same=(actual['width'],actual['height'])==(source['width'],source['height'])and compare_png_images(source['path'],actual['path'],api)['rgba_pixels_equal']
                readbacks[channel]=dict(available=True,source_pixels_equal=same,image=actual)
                if not same:raise ValueError('Actual restored normal-family map differs from exact same-case source: '+material+'/'+channel)
                matches+=1
            else:readbacks[channel]=dict(available=False,missing=row.get('missing_textures',{}).get(channel))
        if not matches:raise ValueError('Restored map has no actual decoded Bump/Normal readback: '+material)
        results[material]=dict(passed=True,readbacks=readbacks,
            scope='Normal SDK write. Bump is the proven legacy Normal readback; direct Normal getter is recorded independently, never fabricated as available.')
    return results


def validate_inputs(config,api):
    import cc_refresh_eyelash_probe_v2 as roots
    from cc_skin_detail_experiment_v1 import MISSING_TEXTURE_SHA256
    source=config['source_project']
    def checked_file(record):
        if not os.path.isfile(record['path'])or api.sha256_file(record['path'])!=record['sha256']:raise ValueError('Immutable experiment input changed')
        return record
    if (config.get('character_id')!='CFD40_LM_002'or config.get('sex')!='male'or config.get('operation')!='restore_only_four_same_case_skin_normal_slots'
            or config.get('save_current_scene_backup')is not True or config.get('working_subdivision_level')!=0):raise ValueError('Explicit bounded LM-only operation/backup/actual0 required')
    if not any(roots.inside(source['path'],r)for r in(roots.RUN_ROOT,roots.STAGE_ROOT)):raise ValueError('Approved immutable assembled source required')
    checked_file(source)
    receipt=api.read_json(checked_file(config['completed_assembly_receipt'])['path']);assembly=api.read_json(checked_file(config['prelash_report'])['path'])
    if (receipt.get('status')!='completed'or receipt.get('character_id')!=config['character_id']or receipt['result_project']['sha256']!=source['sha256']
            or assembly.get('success')is not True or assembly['config']['character_id']!=config['character_id']or receipt['prelash_project']['sha256']!=assembly['candidate']['sha256']
            or assembly['config']['assets']['skin']['sha256']!=config['selected_skin']['sha256']):raise ValueError('Same completed source/PRELASH/selected skin lineage required')
    original=api.read_json(checked_file(config['after_skin_materials'])['path']);maps=config['skin_normal_maps']
    if set(maps)!=SKINS:raise ValueError('Exactly four real skin maps required')
    rows={r['material']:r for r in original['materials']if r['owner']=='avatar'and r['mesh']=='CC_Base_Body'and r['material']in SKINS}
    for material,record in maps.items():
        checked_file(record);old=rows[material]['textures']['bump']
        if record['sha256']!=old['sha256']or record['path']!=old['path']or record['sha256']in MISSING_TEXTURE_SHA256:raise ValueError('Only exact own after_skin actual images allowed, never warning maps')
        image=api.QtGui.QImage(record['path'])
        if image.isNull()or(image.width(),image.height())!=(record['width'],record['height'])or(record['width'],record['height'])!=(2048,2048):raise ValueError('Real decoded same-case2048 maps required')
    proof=api.read_json(checked_file(config['normal_write_evidence'])['path'])
    if not proof.get('passed')or not any(w.get('passed')and w.get('load_constant')=='EMaterialTextureChannel_Normal'and w.get('operation')=='load_original_texture'and w.get('pixel_comparison',{}).get('rgba_pixels_equal')for w in proof['writes']):raise ValueError('Actual proven Normal LoadImageToTexture signature/readback required')
    checked_file(config['normal_write_implementation']);checked_file(config['geometry_snapshot']);checked_file(config['baseline_pixel_materials'])
    return maps


def run(library,output_dir,log,api):
    import cc_refresh_eyelash_probe_v2 as roots
    import cc_skin_detail_experiment_v1 as exporter
    import cc_refresh_selected_lash_pixels_v1 as scope
    import cc_refresh_material_pixels_v1 as original
    import cc_probe_refresh_skin_material_readonly_v1 as channels
    import cc_repair_headshot_support_materials_v1 as geometry
    import cc_capture_assembly_geometry_v1 as body_capture
    import cc_skingen_controls_v1 as ui
    config=library['refresh_skin_normal_restore'];maps=validate_inputs(config,api);source=config['source_project']
    if not roots.inside(output_dir,roots.RUN_ROOT)or os.path.realpath(output_dir)==os.path.realpath(roots.RUN_ROOT):raise ValueError('Independent refresh output child required')
    if os.path.exists(output_dir)and os.listdir(output_dir):raise ValueError('Refuse existing experiment output')
    if any(not hasattr(api.RLPy,enum)for _,enum in channels.CHANNELS):raise ValueError('All eight actual SDK channel enums required')
    os.makedirs(output_dir,exist_ok=True)
    report_path=os.path.join(output_dir,'skin_normal_restore_report.json');summary_path=os.path.join(output_dir,'validation_result.json')
    report=dict(success=False,character_id=config['character_id'],source_project=source,config=config,implementation_sha256=api.sha256_file(__file__),
        report_path=report_path,summary_path=summary_path,accepted_final=False,recipe_complete=False,complete_export_verified=False,visual_acceptance='pending',writes=[],pixel_checks=[],geometry_checks=[],pixel_stages={})
    baseline=None;before=None;working=None;attempted=False
    def checkpoint(phase):report['phase']=phase;api.write_json(report,report_path);log('Skin Normal-only restoration: '+phase)
    def avatar():
        avatars=list(api.RLPy.RScene.GetAvatars()or[])
        if len(avatars)!=1:raise ValueError('Exactly one source avatar required')
        return avatars[0]
    def load(record,label):
        if api.sha256_file(record['path'])!=record['sha256']:raise ValueError('Source/project changed')
        status,dialogs=api.load_file_with_optional_undo_warning(record['path'],label);report.setdefault('loads',[]).append(dict(label=label,status=status,dialogs=dialogs));api.RLPy.RScene.SelectObject(avatar())
    def product():
        a=avatar();widget=ui.unique_widget(list(api.QtWidgets.QApplication.allWidgets()),*ui.SELECTORS['editor'])
        value=dict(actual_subdivision=int(a.GetSubdivMeshLevel()),editor=ui.widget_record(widget))
        if value['actual_subdivision']!=0 or widget.isChecked()or str(widget.text())!='Activate Editor':raise ValueError('Actual0 and editor-closed source/product required; no UI activation performed')
        return value
    raw_api=SimpleNamespace(_transform_data=api._transform_data)
    def capture_geometry(label):
        value=dict(geometry=geometry.capture_geometry(avatar(),api=raw_api),body=body_capture.capture_body_snapshot(avatar(),api=raw_api,include_world=True),eye=api.capture_eye_integrity_state(avatar()),weights=api.capture_eye_part_morph_weights(avatar()),product=product())
        if value['body']['scene_explicitly_settled']or value['body']['working_subdivision_level']!=0:raise ValueError('Raw real actual0 geometry required')
        path=os.path.join(output_dir,label+'_geometry.json');api.write_json(value,path);value['file']=api.bodyfit_freeze_file_record(path);return value
    def geometry_check(label,actual):
        comparison=geometry.compare_geometry(baseline['geometry'],actual['geometry'])
        body=max(max(roots._distances(baseline['body'][space],actual['body'][space]))for space in('local','world'))
        eyes=api.compare_neutral_eye_states(baseline['eye'],actual['eye'],tolerance=.0002,include_world=True,include_runtime_ids=False,t_pose_tolerance=.0002,world_translation_tolerance=.0002)
        weights={r['id']:r['weight']for r in baseline['weights']}=={r['id']:r['weight']for r in actual['weights']}
        result=dict(phase=label,all_native_geometry=comparison,all_14164_body_max_mm=body,eye=eyes,eye_weights_exact=weights,passed=comparison['passed']and body<=.002 and eyes['matches']and weights)
        report['geometry_checks'].append(result);checkpoint(label+'_geometry_checked')
        if not result['passed']:raise ValueError('Protected geometry changed in material-only experiment: '+label)
    def capture_pixels(label):
        checkpoint('pixels_'+label);scoped=scope.Api(api);scoped.MATERIAL_TEXTURE_CHANNELS=list(channels.CHANNELS)
        path=os.path.join(output_dir,'pixels_'+label);error=None
        try:value=exporter.capture_materials(avatar(),path,scoped)
        except Exception as exc:
            error=str(exc);value=api.read_json(os.path.join(path,'materials.json'))
        bad=[]
        for row in value['materials']:
            for channel,texture in row['textures'].items():
                image=api.QtGui.QImage(texture['path'])
                if image.isNull()or(image.width(),image.height())!=(texture['width'],texture['height']):bad.append(dict(material=row['material'],channel=channel))
                texture['file_decoded']=not image.isNull()
        texture_errors=[e for e in value.get('observation_errors',[])if str(e.get('stage','')).startswith('texture:')or e.get('stage')in dict(channels.CHANNELS)]
        skins={r['material']for r in value['materials']if r['owner']=='avatar'and r['mesh']=='CC_Base_Body'and r['textures'].get('diffuse')and r['material']in SKINS}
        new={r['mesh']for r in value['materials']if scope.new_lash_row(r)and r['textures']}
        supports={r['mesh']for r in value['materials']if r['mesh']in original.SUPPORT_MESHES}
        value.update(pixel_capture_complete=not bad and not texture_errors and skins==SKINS and new==scope.NEW_MESHES and original.SUPPORT_MESHES<=supports,
            capture_exception=error,decode_errors=bad,texture_errors=texture_errors,channel_scope=list(channels.CHANNELS),scope='Original material scope plus exact Delicate meshes; all8 standard channels independently read. Custom shader texture slots outside scope.')
        api.write_json(value,os.path.join(path,'materials.json'));report['pixel_stages'][label]=api.bodyfit_freeze_file_record(os.path.join(path,'materials.json'))
        if not value['pixel_capture_complete']:raise ValueError('Eight-channel actual capture incomplete: '+label)
        return value
    def pixels_check(label,reference,actual,allow=False):
        check=pixel_compare(reference,actual,api,allow);report['pixel_checks'].append(dict(phase=label,comparison=check));checkpoint(label+'_pixels_checked')
        if not check['passed']:raise ValueError('Protected material pixels changed: '+label)
    def render(label):
        path=os.path.join(output_dir,label+'.png');api.render_preview(path);return api.bodyfit_freeze_file_record(path)
    try:
        checkpoint('backup_current_scene');backup=os.path.join(output_dir,'scene_before_probe.ccProject');api.checked('Backup current scene',api.RLPy.RFileIO.SaveProject(backup));report['scene_backup']=api.bodyfit_freeze_file_record(backup)
        path=os.path.join(output_dir,'immutable_assembled_source.ccProject');shutil.copyfile(source['path'],path);working=api.bodyfit_freeze_file_record(path);report['working_source']=working
        if working['sha256']!=source['sha256']:raise ValueError('Working source SHA mismatch')
        attempted=True;load(working,'Load independent assembled source for four Normal slots')
        baseline=capture_geometry('before');before=capture_pixels('before')
        baseline_pixels=original.compare_pixels(api.read_json(config['baseline_pixel_materials']['path']),before,api)
        report['bound_completed_six_channel_pixels']=baseline_pixels
        if not baseline_pixels['passed']:raise ValueError('Loaded product differs from bound completed standard-pixel source')
        expected=api.read_json(config['geometry_snapshot']['path'])
        initial=geometry.compare_geometry(expected['geometry'],baseline['geometry']);report['bound_completed_geometry']=initial
        if not initial['passed']:raise ValueError('Loaded geometry differs from bound completed source')
        rows={(r['owner'],r['mesh'],r['material']):r for r in before['materials']}
        for material in SKINS:
            row=rows[('avatar','CC_Base_Body',material)]
            if row['textures'].get('normal')or row['textures'].get('bump'):raise ValueError('This exact repair requires observed missing Normal/Bump source; healthy source is not rewritten')
        component=avatar().GetMaterialComponent();report['actual_method_docstring']=str(component.LoadImageToTexture.__doc__)
        for material in sorted(SKINS):
            record=maps[material];checkpoint('load_normal_'+material)
            status=api.checked('Restore exact own skin Normal texture',component.LoadImageToTexture('CC_Base_Body',material,api.RLPy.EMaterialTextureChannel_Normal,record['path']))
            report['writes'].append(dict(mesh='CC_Base_Body',material=material,write_constant='EMaterialTextureChannel_Normal',source=record,status=status));checkpoint('normal_written_'+material)
        report['after_render']=render('after_normal_restoration');geometry_check('after',capture_geometry('after'))
        after=capture_pixels('after');report['normal_readbacks_after']=verify_restored_maps(after,maps,api);pixels_check('before_to_after_only_four_normal_pairs',before,after,True)
        target=os.path.join(output_dir,'CANDIDATE_LM002_four_skin_normals_restored.ccProject');api.checked('Save independent Normal-restored candidate',api.RLPy.RFileIO.SaveProject(target));report['saved_project']=api.bodyfit_freeze_file_record(target)
        geometry_check('post_save',capture_geometry('post_save'));post=capture_pixels('post_save');verify_restored_maps(post,maps,api);pixels_check('after_to_post_save_all8',after,post)
        load(report['saved_project'],'Reload independent Normal-restored candidate');report['reload_render']=render('reloaded_normal_restoration')
        geometry_check('reloaded',capture_geometry('reloaded'));reloaded=capture_pixels('reloaded');report['normal_readbacks_reloaded']=verify_restored_maps(reloaded,maps,api);pixels_check('after_to_reloaded_all8',after,reloaded)
        report['material_restoration_verified']=True
    except Exception as exc:report['error']=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc())
    finally:
        restored=False
        if attempted and working:
            try:
                checkpoint('restore_immutable_assembled_source');load(working,'Restore exact assembled source after Normal-only experiment');report['rollback_render']=render('rollback_source')
                if baseline:geometry_check('rollback',capture_geometry('rollback'))
                if before:pixels_check('rollback_all8',before,capture_pixels('rollback'))
                restored=True
            except Exception as exc:report['rollback_error']=str(exc)
        report['source_unchanged']=api.sha256_file(source['path'])==source['sha256'];report['restored_source']=restored
        report['success']=bool(report.get('material_restoration_verified')and restored and report['source_unchanged']and not report.get('error'))
        report['status']='four_skin_Normal_write_readback_save_reload_supported_pending_FBX_visual'if report['success']else'failed_four_skin_Normal_experiment'
        checkpoint(report['status'])
    summary={k:report[k]for k in('success','status','report_path','summary_path','accepted_final','recipe_complete','complete_export_verified','visual_acceptance','source_unchanged','restored_source')}
    summary.update(saved_project=report.get('saved_project'),error=report.get('error'));api.write_json(summary,summary_path);return summary
