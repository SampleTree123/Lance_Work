import copy
import hashlib
import json
from pathlib import Path
import sys
import types
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cc_refresh_prelash_source_chain_v1 as chain
import cc_refresh_eyelash_probe_v2 as lash
import cc_repair_headshot_support_materials_v1 as geometry


def actual_inputs():
    root=Path(__file__).resolve().parents[4];stage=root/'00_engine/scripts/character_creator/runtime_staging/character_refresh_20261018_v1'
    run=root/'00_engine/outputs/character_creator_bridge/artifacts/character_refresh_20261018_v1'
    report=run/'WF003_verify_prelash_v2/verify_prelash_report.json'
    if not report.exists():pytest.skip('Actual prelash evidence unavailable')
    rec=lambda p:dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    base=json.loads((stage/'delicate_WF003_support_restore_v3.json').read_text())['refresh_delicate_support_restore'];pre=json.loads(report.read_text())
    config=dict(base,character_id='CFD40_WF_003',source_project=pre['candidate'],original_geometry_anchor=base['source_project'],prelash_validation_report=rec(report),validated_support_restore_report=rec(run/'delicate_WF003_support_restore_v3/delicate_support_restore_report.json'),prelash_native_reference={'body':rec(run/'WF003_verify_prelash_v2/same_sha_body_geometry.json'),'native':rec(run/'WF003_verify_prelash_v2/same_sha_native_geometry.json')})
    api=types.SimpleNamespace(sha256_file=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest(),read_json=lambda p:json.loads(Path(p).read_text()))
    return config,api,run


def test_actual_independent_prelash_and_successful_v3_form_exact_source_chain():
    config,api,run=actual_inputs()
    result=chain.validate(config,str(run/'delicate_WF003_prelash_combined_v4'),api,lash)
    source={'geometry':api.read_json(run/'WF003_verify_prelash_v2/same_sha_native_geometry.json'),'body':api.read_json(run/'WF003_verify_prelash_v2/same_sha_body_geometry.json')}
    assert chain.check_loaded(result,source,geometry.compare_geometry,lash._distances)['passed']
    assert result['serialized_body_vs_anchor_world_max_mm']==pytest.approx(.0003071068227406429)
    assert len(result['native']['meshes'])==12 and result['layer_binding']['actual_signature']['makeup']['eyebrow']['opacity']==90
    assert result['accepted_final']is False


@pytest.mark.parametrize('kind',['source','pixels','geometry'])
def test_provenance_does_not_replace_exact_source_and_pixel_proof(kind):
    config,api,run=actual_inputs();original_read=api.read_json
    if kind=='source':config['source_project']=dict(config['source_project'],sha256='different')
    else:
        def altered(path):
            r=original_read(path)
            if str(path)==config['prelash_validation_report']['path']:
                if kind=='pixels':r['pixel_check']['differences']=[dict(reason='actual_changed_pixel')]
                else:r['geometry_checks']['all_native_support_against_original']['owner_transform_checks'][0]['translation_delta_mm']=.001
            return r
        api.read_json=altered
    with pytest.raises(ValueError):chain.validate(config,str(run/'delicate_WF003_prelash_combined_v4'),api,lash)


def test_cross_product_eye_world_uses_existing_point002mm_gate_and_local_origin_stays_exact():
    m=dict(target=dict(mesh_name='CC_Base_EyeOcclusion',vertex_count=182),desired_local_cm=[[0.,0.,0.]]*182,
        source_world_cm=[[0.,0.,0.]]*182,faces_sha256='exact')
    snapshot=dict(geometry=dict(meshes=[dict(name='CC_Base_EyeOcclusion',vertex_count=182,vertices=copy.deepcopy(m['desired_local_cm']),faces_sha256='exact')]),
        target_world=dict(world=[[0.,0.,.0000307]]*182))
    assert chain.check_anchor_eye_origin(m,snapshot,lash._distances)['world_origin_vs_original_anchor_max_mm']==pytest.approx(.000307)
    snapshot['target_world']['world'][0][2]=.0003
    with pytest.raises(ValueError):chain.check_anchor_eye_origin(m,snapshot,lash._distances)
    snapshot['target_world']['world'][0][2]=0.;snapshot['geometry']['meshes'][0]['vertices'][0][0]=.000001
    with pytest.raises(ValueError):chain.check_anchor_eye_origin(m,snapshot,lash._distances)
