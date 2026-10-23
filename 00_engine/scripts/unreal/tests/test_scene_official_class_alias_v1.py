"""Only the local UE CoreRedirects MRQ Master/Primary class pair is equivalent."""
import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ue_scene_folder_organization_v1 as relocation

OLD = '/Script/MovieRenderPipelineCore.MoviePipelineMasterConfig'
NEW = '/Script/MovieRenderPipelineCore.MoviePipelinePrimaryConfig'


def record(class_name=OLD):
    return {'package': '/Game/Cyberpunk_City/RenderPreset/Movie_Ultra', 'name': 'Movie_Ultra', 'class': class_name}


def test_official_master_primary_pair_is_same_identity_without_rewriting_input():
    original = [record()]
    before = copy.deepcopy(original)
    assert relocation.registry_identities(original) == relocation.registry_identities([record(NEW)])
    assert original == before
    assert relocation.normalized_records(original)[0]['class'] == NEW
    assert relocation.normalized_records(original, canonical_classes=False)[0]['class'] == OLD


def test_legacy_struct_class_repr_can_use_the_same_exact_alias():
    legacy = record('<Struct TopLevelAssetPath {package_name: "/Script/MovieRenderPipelineCore", asset_name: "MoviePipelineMasterConfig"}>')
    assert relocation.registry_identities([legacy]) == relocation.registry_identities([record(NEW)])


@pytest.mark.parametrize('other', [
    '/Script/Engine.Material', '/Script/Engine.StaticMesh', '/Script/Engine.World',
    '/Script/MovieRenderPipelineCore.MoviePipelineShotConfig',
    '/Script/OtherModule.MoviePipelineMasterConfig', 'MoviePipelineMasterConfig',
    '/Script/MovieRenderPipelineCore.MoviePipelineMasterConfig_C',
    '/Game/MovieRenderPipelineCore.MoviePipelineMasterConfig'])
def test_other_types_or_similar_names_never_match_primary(other):
    assert relocation.registry_identities([record(other)]) != relocation.registry_identities([record(NEW)])
    assert relocation.normalized_records([record(other)])[0]['class'] == other


@pytest.mark.parametrize('field,value', [('package', '/Game/Other/RenderPreset/Movie_Ultra'), ('name', 'Movie_Draft')])
def test_alias_never_hides_root_package_or_object_name_change(field, value):
    actual = record(NEW)
    actual[field] = value
    assert relocation.registry_identities([record()]) != relocation.registry_identities([actual])


def test_map_actor_classes_remain_exact_even_for_this_pair():
    assert not relocation.signature_equal({'class': OLD}, {'class': NEW})
    assert not relocation.signature_equal({'class': '/Game/A/BP.BP_C'}, {'class': '/Game/B/BP.BP_C'})


@pytest.fixture
def pinned_source(tmp_path, monkeypatch):
    declaration = '+ClassRedirects=(OldName="' + OLD + '", NewName="' + NEW + '")'
    source = tmp_path / 'BaseEngine.ini'
    source.write_text('[CoreRedirects]\n' + declaration + '\n')
    build = tmp_path / 'Build.version'
    build.write_text('{"MajorVersion":5,"MinorVersion":8,"PatchVersion":1,"Changelist":56057345}')
    pin = dict(relocation.MRQ_CONFIG_CLASS_REDIRECT, source=str(source), build_source=str(build),
               source_sha256=relocation.sha(source), build_sha256=relocation.sha(build))
    monkeypatch.setattr(relocation, 'MRQ_CONFIG_CLASS_REDIRECT', pin)
    return source, build, pin


def test_witness_is_explicit_and_only_emitted_when_alias_used(pinned_source):
    assert relocation.class_redirect_witness([record(NEW)]) == []
    assert relocation.class_redirect_witness([record()]) == [pinned_source[2]]


@pytest.mark.parametrize('mutation', ['source_hash', 'build_hash', 'missing_declaration_with_new_hash'])
def test_official_mapping_or_engine_pin_tampering_fails(pinned_source, mutation):
    source, build, pin = pinned_source
    if mutation == 'source_hash': source.write_text('[CoreRedirects]\n')
    elif mutation == 'build_hash': build.write_text('{}')
    else:
        source.write_text('[CoreRedirects]\n')
        pin['source_sha256'] = relocation.sha(source)
    with pytest.raises(RuntimeError, match='Official MRQ'):
        relocation.class_redirect_witness([record()])


def test_local_official_alias_and_build_have_recorded_pins():
    source = Path(relocation.MRQ_CONFIG_CLASS_REDIRECT['source'])
    if not source.exists(): pytest.skip('Local UE installation not present')
    witness = relocation.class_redirect_witness([record()])[0]
    assert witness['source_line'] == 1181 and witness['section'] == 'CoreRedirects'
    build = json.loads(Path(witness['build_source']).read_text())
    assert (build['MajorVersion'], build['MinorVersion'], build['PatchVersion'], build['Changelist']) == (5, 8, 1, 56057345)


def test_verify_keeps_raw_old_and_current_classes_and_declares_alias(tmp_path, monkeypatch, pinned_source):
    root = '/Game/Cyberpunk_City'
    before = [record()]
    current = [dict(record(NEW), package=record()['package'].replace(root, '/Game/Scenes/Cyberpunk_City', 1))]
    base = {'root': root, 'assets': before, 'maps': [], 'component_transforms': {}}
    monkeypatch.setattr(relocation, 'RUN', tmp_path)
    (tmp_path / 'baseline_Cyberpunk_City_v1.json').write_text(json.dumps(base))
    monkeypatch.setattr(relocation, 'guard', lambda u: None)
    monkeypatch.setattr(relocation, 'select_verification_baseline', lambda root, path: (base, None))
    monkeypatch.setattr(relocation, 'assets', lambda u, path: [SimpleNamespace(record=r) for r in current])
    monkeypatch.setattr(relocation, 'asset_record', lambda a: a.record)
    monkeypatch.setattr(relocation, 'dirty', lambda u: [])
    monkeypatch.setattr(relocation, 'loading_protocol', lambda: {})
    receipts = []
    monkeypatch.setattr(relocation, 'write', lambda name, value: receipts.append(value))
    u = SimpleNamespace(EditorLoadingAndSavingUtils=SimpleNamespace(load_map=lambda path: None))
    relocation.verify(u, root)
    assert receipts[0]['raw_original_asset_records'] == before
    assert receipts[0]['raw_asset_records'] == current
    assert receipts[0]['canonical_class_aliases'] == [pinned_source[2]]
    assert receipts[0]['success'] is True
