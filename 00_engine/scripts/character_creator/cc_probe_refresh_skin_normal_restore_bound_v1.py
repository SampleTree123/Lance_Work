"""WF-only lineage adapter over the frozen, actually successful Normal engine.

No source edits or public-module monkeypatching. A private module instance reuses
all four writes/captures/save/reload/rollback. Only input-lineage validation is
WF-specific. The frozen engine's legacy candidate filename remains in its raw
report; a same-byte WF alias is reported separately after successful rollback.
"""
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil

ENGINE=Path(__file__).with_name('cc_probe_refresh_skin_normal_restore_v1.py')
ENGINE_SHA='e006a14092c55da20465c5c498aeacf1a47be33229a34637251397566e02b52d'
SKINS=frozenset(('Std_Skin_Head','Std_Skin_Body','Std_Skin_Arm','Std_Skin_Leg'))


def private_engine():
    if hashlib.sha256(ENGINE.read_bytes()).hexdigest()!=ENGINE_SHA:raise ValueError('Frozen successful engine changed')
    spec=importlib.util.spec_from_file_location('_refresh_skin_normal_private_frozen_v1',ENGINE)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def validate_bound(config,api):
    import cc_refresh_eyelash_probe_v2 as roots
    from cc_skin_detail_experiment_v1 import MISSING_TEXTURE_SHA256
    def file(record):
        if not os.path.isfile(record['path'])or api.sha256_file(record['path'])!=record['sha256']:raise ValueError('Bound female source/input changed')
        return record
    def document(record):return api.read_json(file(record)['path'])
    if (config.get('character_id')!='CFD40_WF_003'or config.get('sex')!='female'
            or config.get('operation')!='restore_only_four_same_case_skin_normal_slots'
            or config.get('save_current_scene_backup')is not True or config.get('working_subdivision_level')!=0):raise ValueError('Explicit independent same-case female Normal experiment required')
    source=file(config['source_project'])
    if not any(roots.inside(source['path'],root)for root in(roots.RUN_ROOT,roots.STAGE_ROOT)):raise ValueError('Approved completed source required')
    receipt=document(config['completed_assembly_receipt']);assembly=document(config['assembly_before_save_report'])
    verified=document(config['prelash_report']);combined=document(config['combined_support_report'])
    if (receipt.get('status')!='completed'or receipt.get('character_id')!=config['character_id']or receipt.get('sex')!='female'
            or receipt['result_project']['sha256']!=source['sha256']or receipt['assets']['skin']['sha256']!=config['selected_skin']['sha256']
            or receipt['assembly_before_save_report']['sha256']!=config['assembly_before_save_report']['sha256']
            or receipt['prelash_validation_report']['sha256']!=config['prelash_report']['sha256']
            or receipt['combined_support_report']['sha256']!=config['combined_support_report']['sha256']):raise ValueError('Exact completed female chain required')
    if (verified.get('success')is not True or verified.get('stage_validated')is not True or verified.get('candidate_unchanged')is not True
            or verified['candidate']['sha256']!=receipt['prelash_project']['sha256']
            or assembly['config']['character_id']!=config['character_id']or assembly['config']['sex']!='female'
            or assembly['config']['assets']['skin']['sha256']!=config['selected_skin']['sha256']
            or assembly['config']['source_project']['sha256']!=receipt['geometry_project']['sha256']):raise ValueError('Own original female skin/PRELASH verification required; failed v9 alone cannot authorize')
    if (not all(combined.get(k)is True for k in('success','restored_source','source_unchanged','material_pixels_verified','geometry_restore_completed'))
            or combined['saved_project']['sha256']!=source['sha256']or combined['source_project']['sha256']!=receipt['prelash_project']['sha256']
            or combined['prelash_source_binding']['layer_binding']['original_before_save_report']['sha256']!=config['assembly_before_save_report']['sha256']
            or combined['pixel_stages']['reloaded']['sha256']!=config['baseline_pixel_materials']['sha256']):raise ValueError('Actual successful female combined product chain required')
    after=document(config['after_skin_materials']);file(config['geometry_snapshot']);file(config['baseline_pixel_materials'])
    if assembly['pixel_stages']['after_skin']['sha256']!=config['after_skin_materials']['sha256']:raise ValueError('Exact own after_skin material evidence required')
    maps=config['skin_normal_maps']
    if set(maps)!=SKINS:raise ValueError('Exactly four own real maps required')
    rows={r['material']:r for r in after['materials']if r['owner']=='avatar'and r['mesh']=='CC_Base_Body'and r['material']in SKINS}
    for material,record in maps.items():
        file(record);actual=rows[material]['textures']['bump']
        if record['path']!=actual['path']or record['sha256']!=actual['sha256']or record['sha256']in MISSING_TEXTURE_SHA256:raise ValueError('Own exact after_skin real map only; never male or warning map')
        image=api.QtGui.QImage(record['path'])
        if image.isNull()or(image.width(),image.height())!=(2048,2048)or(record['width'],record['height'])!=(2048,2048):raise ValueError('Actual decoded same-case2048 images required')
    file(config['normal_write_evidence']);file(config['normal_write_implementation'])
    proof=document(config['proven_runtime_report']);terminal=document(config['proven_runtime_bridge_result']);library=file(config['proven_runtime_library'])
    if (not all(proof.get(k)is True for k in('success','material_restoration_verified','restored_source','source_unchanged'))
            or proof.get('implementation_sha256')!=ENGINE_SHA or terminal.get('status')!='succeeded'
            or terminal.get('command')!='validate_bodyfit_library'
            or Path(terminal['result']['output_dir']).resolve()!=Path(config['proven_runtime_report']['path']).resolve().parent
            or Path(terminal['result']['library_file']).resolve()!=Path(library['path']).resolve()
            or len(proof['writes'])!=4 or {w['material']for w in proof['writes']}!=SKINS
            or any(w['write_constant']!='EMaterialTextureChannel_Normal'for w in proof['writes'])):raise ValueError('Actual frozen-engine4 Normal-write/save/reload/rollback success required')
    file(proof['saved_project'])
    return maps


def run(library,output_dir,log,api):
    config=library['refresh_skin_normal_restore_bound'];engine=private_engine()
    # This private object is never installed as the public cached v1 module.
    engine.validate_inputs=validate_bound
    result=engine.run({'refresh_skin_normal_restore':config},output_dir,log,api)
    full=api.read_json(result['report_path'])
    report=dict(schema_version=1,kind='source_bound_skin_normal_restore_wrapper_v1',character_id=config['character_id'],sex=config['sex'],
        success=result['success'],status=result['status'],source_project=config['source_project'],restored_source=result['restored_source'],source_unchanged=result['source_unchanged'],
        accepted_final=False,recipe_complete=False,complete_export_verified=False,visual_acceptance='pending',
        implementation_sha256=api.sha256_file(__file__),frozen_engine=dict(path=str(ENGINE),sha256=ENGINE_SHA),
        private_override='WF source/input lineage only; SDK writes/captures/save/reload/rollback are unchanged frozen engine.',
        engine_full_report=api.bodyfit_freeze_file_record(result['report_path']),engine_summary=api.bodyfit_freeze_file_record(result['summary_path']),
        engine_saved_project=result.get('saved_project'),config=config,error=result.get('error'),
        material_restoration_verified=full.get('material_restoration_verified',False))
    if result['success']:
        source=result['saved_project'];alias=os.path.join(output_dir,'CANDIDATE_WF003_four_skin_normals_restored.ccProject')
        if os.path.exists(alias):raise ValueError('Refuse existing WF candidate alias')
        shutil.copyfile(source['path'],alias);report['saved_project']=api.bodyfit_freeze_file_record(alias)
        if report['saved_project']['sha256']!=source['sha256']:raise ValueError('Same-byte female alias copy mismatch')
        report['same_byte_candidate_alias']=True
    path=os.path.join(output_dir,'skin_normal_restore_bound_report.json');summary=os.path.join(output_dir,'bound_validation_result.json')
    report.update(report_path=path,summary_path=summary);api.write_json(report,path)
    answer={k:report.get(k)for k in('success','status','report_path','summary_path','saved_project','source_unchanged','restored_source','material_restoration_verified','accepted_final','recipe_complete','complete_export_verified','visual_acceptance','error')}
    api.write_json(answer,summary);return answer
