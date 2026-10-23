import hashlib
import json
from pathlib import Path
import sys
import types
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cc_refresh_male_prelash_source_chain_v1 as chain
import cc_refresh_eyelash_probe_v2 as lash
import cc_repair_headshot_support_materials_v1 as geometry


def inputs():
    root=Path(__file__).resolve().parents[4];run=root/'00_engine/outputs/character_creator_bridge/artifacts/character_refresh_20261018_v1'
    stage=root/'00_engine/scripts/character_creator/runtime_staging/character_refresh_20261018_v1'
    report=run/'LM002_assembly_v1/refresh_partial_report.json'
    if not report.exists():pytest.skip('Actual male PRELASH evidence unavailable')
    rec=lambda p:dict(path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    male=json.loads(report.read_text());female=json.loads((stage/'delicate_WF003_support_restore_v3.json').read_text())['refresh_delicate_support_restore']
    config=dict(character_id='CFD40_LM_002',source_project=male['candidate'],original_geometry_anchor=male['config']['source_project'],prelash_validation_report=rec(report),
        addition_evidence_original_source=female['source_project'],eyelash_asset_id=lash.DELICATE_ID,
        evaluated_topology_success_report=rec(run/'delicate_WF003_support_restore_v3/delicate_support_restore_report.json'),evaluated_topology_model=female['evaluated_support_model'])
    api=types.SimpleNamespace(sha256_file=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest(),read_json=lambda p:json.loads(Path(p).read_text()))
    return config,api,run


def test_actual_male_stable_product_uses_own_source_and_only_reuses_topology_proof():
    config,api,run=inputs();proof=chain.validate(config,str(run/'delicate_LM002_prelash_combined_v1'),api,lash)
    snapshot=dict(geometry=proof['native'],body=proof['body'])
    assert chain.check_loaded(proof,snapshot,geometry.compare_geometry,lash._distances)['passed']
    assert proof['female_import_affine_reused']is False
    assert proof['layer_binding']['makeup']['eyebrow']['opacity']==100
    assert len(proof['native']['meshes'])==12 and len(proof['pixels']['materials'])==26


@pytest.mark.parametrize('kind',['different_source','different_asset','unstable_pixels'])
def test_changed_male_source_or_asset_or_product_proof_is_rejected(kind):
    config,api,run=inputs();read=api.read_json
    if kind=='different_source':config['source_project']=dict(config['source_project'],sha256='wrong')
    elif kind=='different_asset':config['eyelash_asset_id']='another_asset'
    else:
        def altered(path):
            result=read(path)
            if str(path)==config['prelash_validation_report']['path']:result['pixel_checks']['serialized_to_same_sha_reload_no_allowances']['passed']=False
            return result
        api.read_json=altered
    with pytest.raises(ValueError):chain.validate(config,str(run/'delicate_LM002_prelash_combined_v1'),api,lash)
