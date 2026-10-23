"""Read-only exact per-case stable normal PRELASH and topology-evidence binding."""
import importlib
import os


def validate(config,output_dir,api,lash):
    probe=importlib.import_module('cc_makeup_probe_v1')
    ref=lambda r,s:probe.reference(r,api,s,(lash.RUN_ROOT,lash.STAGE_ROOT,lash.CREATION_ROOT))
    report=api.read_json(ref(config['prelash_validation_report'],'.json'));source=config['source_project'];anchor=config['original_geometry_anchor']
    ref(source,'.ccproject');ref(anchor,'.ccproject')
    if (report.get('status')!='prelash_checkpoint_validated_not_final'or config['sex']not in('male','female')or report.get('success')is not True or report.get('stage_validated')is not True
            or report.get('accepted_final')is not False or report.get('recipe_complete')is not False or report.get('source_unchanged')is not True
            or report['config']['character_id']!=config['character_id']or report['config']['sex']!=config['sex'] or report['candidate']!=report['saved_candidate']
            or report['candidate']['sha256']!=source['sha256']or os.path.normcase(os.path.realpath(report['candidate']['path']))!=os.path.normcase(os.path.realpath(source['path']))
            or report['config']['source_project']['sha256']!=anchor['sha256']):raise ValueError('Exact successful same-case stable PRELASH source required')
    if report['config']['redness_policy']!='excluded_by_user'or report['config']['include_redness_layers']is not False:raise ValueError('No-redness source required')
    selected=report['config']['assets']['eyelashes']
    if selected['asset_id']!=config['eyelash_asset_id']or selected['sha256']!=config['selected_eyelash']['sha256']:raise ValueError('Same actual PRELASH selected registered asset required')
    if not report.get('layer_persistence_passed')or not report.get('editing_checkpoint_unchanged')or report['layers_before_save']!=report['layers_after_reload']:
        raise ValueError('Actual saved/reloaded layer persistence required')
    brow=report['layers_after_reload']['makeup']['eyebrow']
    if brow['opacity']!=brow['slider_opacity']or not isinstance(brow['opacity'],(float,int)):raise ValueError('Actual per-case saved layer opacity binding required')
    exact=importlib.import_module('cc_refresh_prelash_source_chain_v1').exact_original_geometry
    checks=report['closed_geometry_checks']
    if not checks or any(not exact(s['all_native_support_against_original'])or s['body_against_original']['maximum_displacement_mm']!=0 or s['body_against_original']['passed']is not True for s in checks):
        raise ValueError('All actual original12 geometry checkpoints must be exact')
    last=checks[-1]
    if last['phase']!='same_sha_reloaded_after_preview'or report['final_working_subdivision_level']!=0 or report['editor_off_after_stability_reload']['isChecked']:
        raise ValueError('Stable rendered same-SHA actual0/editoroff checkpoint required')
    if any(report['pixel_checks'][k]['passed']is not True for k in('serialized_to_same_sha_reload_no_allowances','source_to_saved_non_lash_support','source_to_reloaded_non_lash_support','saved_to_first_reload_non_skin_support','selected_eyes_to_reloaded_no_allowances','selected_eyes_to_saved_no_allowances')):
        raise ValueError('Stable product and unchanged selected-eye/nonlash pixels required')
    body=api.read_json(ref(last['body_snapshot'],'.json'));native=api.read_json(ref(last['native_snapshot'],'.json'))
    original=api.read_json(ref(report['source_native_geometry'],'.json'))
    geometry=importlib.import_module('cc_repair_headshot_support_materials_v1')
    if not exact(geometry.compare_geometry(original,native)):raise ValueError('Stable native original geometry differs')
    pixel_record=report['pixel_stages']['reloaded'];pixels=api.read_json(ref(pixel_record,'.json'))
    if not pixels.get('pixel_capture_complete')or not pixels['materials']:raise ValueError('Complete actual stable source pixels required')
    for row in pixels['materials']:
        for texture in list(row['textures'].values())+[r['evidence']for r in row.get('missing_textures',{}).values()if r.get('evidence')]:ref(texture,'.png')
    v3=api.read_json(ref(config['evaluated_topology_success_report'],'.json'))
    model=api.read_json(ref(config['evaluated_topology_model'],'.json'))
    if not v3.get('success')or not v3.get('restored_source')or v3['evaluated_support_model']['sha256']!=config['evaluated_topology_model']['sha256']:
        raise ValueError('Actual independent topology-render success evidence required')
    evaluated=importlib.import_module('cc_support_evaluated_inverse_v1')
    if api.sha256_file(evaluated.__file__)!=model['verification_implementation']['sha256']:raise ValueError('Topology evidence implementation changed')
    for record in model['source_files'].values():ref(record,'.json')
    evaluated.verify_model(model);evaluated.verify_pinned_evidence(model,api.read_json)
    return {'anchor':anchor,'prelash_validation_report':config['prelash_validation_report'],'body':body,'native':native,'pixels':pixels,
        'pixel_reference':pixel_record,'body_reference':last['body_snapshot'],'native_reference':last['native_snapshot'],
        'layer_binding':report['layers_after_reload'],'topology_proof':model['supports'],
        'topology_success_report':config['evaluated_topology_success_report'],'topology_model':config['evaluated_topology_model'],
        'female_import_affine_reused':False,'accepted_final':False}


def check_loaded(chain,snapshot,compare_geometry,distances):
    exact=importlib.import_module('cc_refresh_prelash_source_chain_v1').exact_original_geometry
    geometry=compare_geometry(chain['native'],snapshot['geometry'])
    local=max(distances(chain['body']['local'],snapshot['body']['local']));world=max(distances(chain['body']['world'],snapshot['body']['world']))
    if not exact(geometry)or local!=0 or world>.002:raise ValueError('Actual same-case source geometry differs from stable product')
    return {'all12_native_geometry':geometry,'local_max_mm':local,'world_max_mm':world,'world_protection_limit_mm':.002,'passed':True}
