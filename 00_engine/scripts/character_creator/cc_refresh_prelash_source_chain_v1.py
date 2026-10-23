"""Bind a stable pre-lash product to the original corrected geometry anchor.

Read-only evidence validation. Geometry/pixels are rechecked after actual load;
prior report success never substitutes for the current real scene gate.
"""
import importlib
import os


def exact_original_geometry(comparison):
    return (comparison.get('passed')is True and comparison.get('maximum_local_delta_mm')==0
        and len(comparison.get('meshes',[]))==12
        and comparison.get('available_owner_transforms_preserved')is True
        and bool(comparison.get('owner_transform_checks'))
        and all(c.get('passed')is True and c.get('translation_delta_mm')==0
            and c.get('quaternion_delta')==0 and c.get('auxiliary_unchanged')is True
            for c in comparison.get('owner_transform_checks',[])))


def validate(config,output_dir,api,lash):
    ref=lambda record,suffix:importlib.import_module('cc_makeup_probe_v1').reference(record,api,suffix,(lash.RUN_ROOT,lash.STAGE_ROOT,lash.CREATION_ROOT))
    source=config['source_project'];anchor=config['original_geometry_anchor'];ref(anchor,'.ccproject')
    report=api.read_json(ref(config['prelash_validation_report'],'.json'))
    v3=api.read_json(ref(config['validated_support_restore_report'],'.json'))
    if (report.get('success')is not True or report.get('stage_validated')is not True
            or report.get('accepted_final')is not False or report.get('recipe_complete')is not False
            or not report.get('candidate_unchanged')or report['candidate']['sha256']!=source['sha256']
            or os.path.normcase(os.path.realpath(report['candidate']['path']))!=os.path.normcase(os.path.realpath(source['path']))):
        raise ValueError('Exact independently stable pre-lash candidate required')
    geometry=report['geometry_checks']
    if (geometry['body_against_original']['maximum_displacement_mm']!=0
            or not exact_original_geometry(geometry['all_native_support_against_original'])
            or any(r.get('passed')is not True for r in geometry.values())
            or len(geometry['all_native_support_against_original']['meshes'])!=12
            or report['pixel_check'].get('passed')is not True
            or report['pixel_check'].get('authorized_materials_not_compared')!=[]
            or report['pixel_check'].get('differences')!=[]):raise ValueError('Pre-lash exact original geometry/strict pixels evidence required')
    if (v3.get('success')is not True or not v3.get('source_unchanged')or not v3.get('restored_source')
            or v3['source_project']['sha256']!=anchor['sha256']
            or v3['evaluated_support_model']['sha256']!=config['evaluated_support_model']['sha256']
            or not v3.get('geometry_restore_completed')):raise ValueError('Successful original-source evaluated support restoration required')
    ref(v3['saved_project'],'.ccproject')
    if any(s['passed']is not True for s in v3['steps']if not s['pending_restoration_supports']):raise ValueError('Successful v3 final gates required')
    if any(s['passed']is not True for s in v3['uv_checks']+v3['normal_semantic_checks']):raise ValueError('Successful original6UV/normal semantics required')
    verifier=importlib.import_module('cc_verify_refresh_prelash_v1');probe=importlib.import_module('cc_makeup_probe_v1')
    runner=importlib.import_module('cc_run_character_refresh_v1');finalizer=importlib.import_module('cc_finalize_refresh_partial_v1')
    prior,candidate,body,native,pixels=verifier.validate(report['config'],output_dir,api,probe,runner,finalizer)
    old=api.read_json(prior['recovery']['original_failed_report']['path'])
    if old['config']['source_project']['sha256']!=anchor['sha256']or old['config']['redness_policy']!='excluded_by_user' or old['config']['include_redness_layers']is not False or old['config']['character_id']!=config['character_id']:
        raise ValueError('Original geometry anchor and no-redness lineage required')
    reference=config['prelash_native_reference']
    for key,name in(('body','same_sha_body_geometry.json'),('native','same_sha_native_geometry.json')):
        ref(reference[key],'.json')
        expected=os.path.join(os.path.dirname(config['prelash_validation_report']['path']),name)
        if os.path.normcase(os.path.realpath(reference[key]['path']))!=os.path.normcase(os.path.realpath(expected)):
            raise ValueError('Exact independently verified same-SHA geometry checkpoint required')
    stable_body=api.read_json(reference['body']['path']);stable_native=api.read_json(reference['native']['path'])
    geometry_module=importlib.import_module('cc_repair_headshot_support_materials_v1')
    if not exact_original_geometry(geometry_module.compare_geometry(native,stable_native)):
        raise ValueError('Pinned stable PRELASH original local/owner geometry differs')
    anchor_local=max(lash._distances(body['local'],stable_body['local']))
    anchor_world=max(lash._distances(body['world'],stable_body['world']))
    if anchor_local!=0 or anchor_world>.002 or stable_body['working_subdivision_level']!=0:
        raise ValueError('Pinned stable PRELASH Body differs from original anchor')
    return {'anchor':anchor,'prelash_validation_report':config['prelash_validation_report'],
        'validated_support_restore_report':config['validated_support_restore_report'],
        'recovery_report':report['config']['recovery_report'],'layer_binding':report['layer_persistence_binding'],
        'body':stable_body,'native':stable_native,'anchor_body':body,'pixels':pixels,'pixel_reference':prior['pixel_stages']['reloaded'],
        'prelash_native_reference':reference,'serialized_body_vs_anchor_local_max_mm':anchor_local,
        'serialized_body_vs_anchor_world_max_mm':anchor_world,
        'prior_layer_signature_retained_without_reopening_editor':True,'accepted_final':False}


def check_loaded(chain,snapshot,compare_geometry,distances):
    geometry=compare_geometry(chain['native'],snapshot['geometry'])
    body_local=max(distances(chain['body']['local'],snapshot['body']['local']))
    body_world=max(distances(chain['body']['world'],snapshot['body']['world']))
    # Provenance reuse is justified by exact original geometry, not a new broad tolerance.
    if not exact_original_geometry(geometry)or body_local!=0 or body_world>.002:raise ValueError('Actual pre-lash geometry is not original anchor within existing world protection')
    anchor_world=max(distances(chain['anchor_body']['world'],snapshot['body']['world']))
    if anchor_world>.002:raise ValueError('Actual product world geometry exceeds original anchor protection')
    return {'all12_native_geometry':geometry,'all_body_local_vs_same_sha_reference_max_mm':body_local,
        'all_body_world_vs_same_sha_reference_max_mm':body_world,
        'all_body_world_vs_original_anchor_max_mm':anchor_world,'original_anchor_world_limit_mm':.002,'passed':True}


def check_anchor_eye_origin(model,snapshot,distances):
    target=model['target'];matches=[m for m in snapshot['geometry']['meshes']if m['name']==target['mesh_name']and m['vertex_count']==target['vertex_count']]
    if len(matches)!=1:raise ValueError('Ambiguous geometry anchor eye support')
    local=max(distances(model['desired_local_cm'],matches[0]['vertices']))
    world=max(distances(model['source_world_cm'],snapshot['target_world']['world']))
    if local!=0 or world>.002 or matches[0]['faces_sha256']!=model['faces_sha256']:
        raise ValueError('Product eye support is not bound to exact local/owner anchor')
    return {'exact_local_origin_max_mm':local,'world_origin_vs_original_anchor_max_mm':world,
        'world_protection_limit_mm':.002,'scope':'Cross-product origin only after exact same-SHA full geometry/source-chain gate; frozen same-source model unchanged.'}
