"""Actual evidence plus synthetic negative cases; fixtures are never topology authority."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import types
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cc_refresh_registered_lash_contract_v1 as contract
import cc_refresh_registered_lash_pixels_v1 as pixels
import cc_compile_character_manifest as compiler
import cc_refresh_eyelash_probe_v2 as lash

ROOT=Path(__file__).resolve().parents[4]
REFERENCE=ROOT/'00_engine/outputs/character_refresh_20261018_v1/eyelash_nine_historical_contract_reference.json'
API=types.SimpleNamespace(sha256_file=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest(),read_json=lambda p:json.loads(Path(p).read_text()))
def pin(p):return dict(path=str(p),sha256=API.sha256_file(p))

def test_nine_current_assets_read_exact_historical_names_and_styles_without_invented_topology():
    pool=compiler.facial_pool(API.read_json(lash.REGISTRY),'eyelashes')
    counts=[]
    for asset in pool.values():
        result=contract.load(pin(REFERENCE),asset,API)
        counts.append(len(result['expected_parts']))
        assert result['historical_asset_sha_recorded']is False
        assert result['magnitude_upper_bound_registered']is False
        assert len(result['selected_style_ids'])==2
        assert not any('vertex_count'in r or 'faces_sha256'in r for r in result['expected_parts'])
    assert counts.count(4)==2 and counts.count(2)==7

def test_actual_male_capture_binds_only_this_measured_new_topology():
    path=Path(lash.RUN_ROOT)/'delicate_LM002_prelash_combined_v1'
    if not path.exists():pytest.skip('Actual completed male evidence unavailable')
    before=API.read_json(path/'original_before_asset_snapshot.json')['other_meshes']
    after=API.read_json(path/'applied_rendered_snapshot.json')['other_meshes']
    asset=compiler.facial_pool(API.read_json(lash.REGISTRY),'eyelashes')[lash.DELICATE_ID]
    result=contract.load(pin(REFERENCE),asset,API)
    bound=contract.bind_additions(before,after,result)
    assert len(bound['added_meshes'])==2 and bound['actual_topology_measured']
    changed=copy.deepcopy(after);changed['meshes'][0]['faces_sha256']='f'*64
    with pytest.raises(ValueError):contract.bind_additions(before,changed,result)
    changed=copy.deepcopy(after);changed['parts'].append(dict(owner='avatar',type='9',name='Unexpected'))
    with pytest.raises(ValueError):contract.bind_additions(before,changed,result)

@pytest.mark.parametrize('pairs',[[('Low_Extended','Low_Extend'),('Up','Up')],[('A','A'),('B','B'),('C','C'),('D','D')]])
def test_dynamic_alias_or_four_part_inventory_uses_actual_signatures(pairs):
    # Deliberately tiny synthetic topology: not a production preset lookup table.
    before=dict(meshes=[dict(owner='avatar',name='Existing',vertex_count=3,face_count=1,faces_sha256='0'*64)],parts=[],owner_transforms=[],owner_transform_errors=[])
    spec=dict(asset={},expected_parts=[dict(name=o,mesh_names=[m])for o,m in pairs],expected_mesh_pairs=[['avatar/9:'+o,m]for o,m in pairs])
    after=copy.deepcopy(before)
    for i,(obj,mesh)in enumerate(pairs):
        after['meshes'].append(dict(owner='avatar/9:'+obj,name=mesh,vertex_count=3+i,face_count=1+i,faces_sha256=str(i+1)*64))
        after['parts'].append(dict(owner='avatar',type='9',name=obj))
        after['owner_transforms'] += [dict(owner='avatar/9:'+obj,space=s,value={})for s in ('local','world')]
    bound=contract.bind_additions(before,after,spec)
    check=contract.compare_existing(before,after,bound,lambda *args:dict(passed=True))
    assert check['passed'] and len(bound['added_meshes'])==len(pairs)
    missing=copy.deepcopy(after);missing['meshes'].pop(0)
    assert not contract.compare_existing(before,missing,bound,lambda *args:dict(passed=True))['passed']
    moved=copy.deepcopy(after);moved['meshes'][-1]['faces_sha256']='f'*64
    assert not contract.compare_existing(before,moved,bound,lambda *args:dict(passed=True))['passed']

def test_style_absence_honest_unselected_change_rejected_and_persistence_exact():
    spec=dict(selected_style_ids=['a','b'],all_style_ids=['a','b','c'])
    before={'c':dict(weight=0.,categories=['Actor/Eyelash'])}
    after=dict(before,a=dict(weight=1.),b=dict(weight=1.))
    result=contract.check_selected_styles(before,after,spec)
    assert result['selected_source_absent_ids']==['a','b']
    assert contract.check_persisted_styles(after,copy.deepcopy(after))['passed']
    wrong=copy.deepcopy(after);wrong['c']['weight']=1.
    with pytest.raises(ValueError):contract.check_selected_styles(before,wrong,spec)
    wrong=copy.deepcopy(after);wrong['a']['weight']=.99
    with pytest.raises(ValueError):contract.check_persisted_styles(after,wrong)
    with pytest.raises(ValueError):contract.check_selected_styles(before,wrong,spec)
