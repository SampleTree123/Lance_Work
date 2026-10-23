import copy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import scene_path_relocation_v1 as relocation


def overlay(status='verified'):
    return {'schema':'scene_folder_relocation_v1','status':'in_progress','mappings':[
        {'old_prefix':'/Game/Foo','new_prefix':'/Game/Scenes/Foo','status':status}]}


@pytest.mark.parametrize('source,expected',[
    ('/Game/Foo','/Game/Scenes/Foo'),
    ('/Game/Foo/Maps/L_A','/Game/Scenes/Foo/Maps/L_A'),
    ('/Game/Foo/Maps/L_A.L_A:PersistentLevel.Actor','/Game/Scenes/Foo/Maps/L_A.L_A:PersistentLevel.Actor'),
    ('/Game/Foobar/Maps/L_A','/Game/Foobar/Maps/L_A'),
    ('/Game/Scenes/Foo/Maps/L_A','/Game/Scenes/Foo/Maps/L_A'),
    ('/Game/DataMake/Maps/L_A','/Game/DataMake/Maps/L_A')])
def test_exact_prefix_boundaries(source,expected):
    assert relocation.resolve_path(source,overlay())==expected


def test_unverified_mapping_is_not_applied():
    with pytest.raises(ValueError,match='not verified'):
        relocation.resolve_path('/Game/Foo/Maps/A',overlay('pending'))


def test_index_mapping_does_not_mutate_history():
    original={'scenes':[{'id':'s','maps':['/Game/Foo/Maps/A'],'status':'imported_verified'}]}
    before=copy.deepcopy(original)
    current=relocation.relocate_index(original,overlay())
    assert original==before
    assert current['scenes'][0]['original_locations']['maps']==original['scenes'][0]['maps']
    assert current['scenes'][0]['maps']==['/Game/Scenes/Foo/Maps/A']


def test_verified_registry_requires_real_successful_receipt(tmp_path):
    receipt=tmp_path/'receipt.json';receipt.write_text('{"success":true}')
    data=overlay();data['mappings'][0]['verification_receipt']={'path':str(receipt),'sha256':relocation.sha(receipt)}
    registry=tmp_path/'registry.json';registry.write_text(json.dumps(data))
    assert relocation.read_overlay(registry)==data
    receipt.write_text('{"success":false}')
    with pytest.raises(ValueError,match='receipt changed'):relocation.read_overlay(registry)
    data['mappings'][0]['verification_receipt']['sha256']=relocation.sha(receipt)
    registry.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='successful verification'):relocation.read_overlay(registry)


def test_new_index_can_never_overwrite_old_source(tmp_path,monkeypatch):
    monkeypatch.setattr(relocation,'RUN',tmp_path/'new_run')
    source=tmp_path/'old_index.json';source.write_text('{"scenes":[]}')
    registry=tmp_path/'registry.json';registry.write_text(json.dumps({**overlay(),'mappings':[]}))
    before=source.read_bytes()
    with pytest.raises(ValueError,match='new relocation run'):
        relocation.build_current_index(source,registry_path=registry,output_path=source)
    current=relocation.build_current_index(source,registry_path=registry)
    assert source.read_bytes()==before
    assert current['source_index']['sha256']==relocation.sha(source)
    assert (tmp_path/'new_run/gallery_scene_index_relocated_v1.json').is_file()


def test_overlapping_prefixes_rejected():
    data=overlay();data['mappings'].append({'old_prefix':'/Game/Foo/Sub','new_prefix':'/Game/Scenes/Foo/Sub','status':'verified'})
    with pytest.raises(ValueError,match='overlapping'):relocation.validate_overlay(data)
