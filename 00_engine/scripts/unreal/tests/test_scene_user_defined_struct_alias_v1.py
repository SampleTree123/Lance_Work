"""Focused finite registry-class alias tests; no UE or production edits."""
import copy
import json
from pathlib import Path

import pytest
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ue_scene_folder_organization_v1 as h

OLD = '/Script/Engine.UserDefinedStruct'
NEW = '/Script/CoreUObject.UserDefinedStruct'
ROOT = '/Game/FuturisticMetaCity'


def row(class_name=OLD):
    return {'package': ROOT + '/Structs/F_Struct_Alphabet', 'name': 'F_Struct_Alphabet', 'class': class_name}


def test_actual903_futuristic_records_match_without_rewriting_raw_evidence():
    base = json.loads((h.RUN / 'baseline_FuturisticMetaCity_v1.json').read_text(encoding='utf-8-sig'))
    proof = json.loads((h.RUN / 'futuristic_partial_identity_inspection_v1.json').read_text(encoding='utf-8-sig'))
    before = copy.deepcopy(base)
    actual_before = copy.deepcopy(proof)
    actual = [dict(r, package=h.canon(r['package'], ROOT)) for r in proof['actual_assets']]
    assert len(base['assets']) == len(actual) == 903
    assert proof['missing'] == [row()] and proof['extra'] == [row(NEW)]
    assert h.registry_identities(base['assets']) == h.registry_identities(actual)
    assert base == before and proof == actual_before
    assert h.normalized_records([row()], canonical_classes=False) == [row()]
    assert h.class_redirect_witness(base['assets']) == [h.USER_DEFINED_STRUCT_CLASS_REDIRECT]


@pytest.mark.parametrize('other', [
    '/Script/OtherModule.UserDefinedStruct',
    '/Script/Engine.UserDefinedStruct_C',
    'UserDefinedStruct',
])
def test_similar_struct_names_are_not_aliases(other):
    assert h.canonical_registry_class(other) == other
    assert h.registry_identities([row(other)]) != h.registry_identities([row(NEW)])
    assert h.class_redirect_witness([row(other)]) == []


@pytest.mark.parametrize('field,value', [('package', ROOT + '/Structs/Other'), ('name', 'Other')])
def test_class_alias_cannot_hide_package_or_object_name_change(field, value):
    changed = row(NEW)
    changed[field] = value
    assert h.registry_identities([row()]) != h.registry_identities([changed])


def test_map_actor_class_namespace_change_stays_strict():
    before = {'map': ROOT + '/Maps/ShowcaseMap', 'actor_count': 1, 'levels': [],
              'actors': [{'name': 'Actor', 'class': OLD, 'transform': [0] * 9, 'components': []}]}
    after = copy.deepcopy(before)
    after['actors'][0]['class'] = NEW
    assert not h.compare_map(before, after)[0]
    assert not h.signature_equal({'class': OLD}, {'class': NEW})


def test_two_official_aliases_emit_two_separate_pinned_witnesses():
    records = [row(), dict(row(h.MRQ_CONFIG_CLASS_REDIRECT['old_name']), name='MovieConfig')]
    assert h.class_redirect_witness(records) == [h.MRQ_CONFIG_CLASS_REDIRECT, h.USER_DEFINED_STRUCT_CLASS_REDIRECT]
    assert h.class_redirect_witness([row(NEW)]) == []


@pytest.mark.parametrize('mutation', ['source_hash', 'build_hash', 'missing_literal_with_new_hash'])
def test_user_defined_struct_witness_fails_on_source_or_build_tampering(tmp_path, monkeypatch, mutation):
    source, build = tmp_path / 'BaseEngine.ini', tmp_path / 'Build.version'
    source.write_text('[CoreRedirects]\n' + h.USER_DEFINED_STRUCT_CLASS_REDIRECT['declaration'] + '\n')
    build.write_text('{"MajorVersion":5,"MinorVersion":8,"PatchVersion":1,"Changelist":56057345}')
    pin = dict(h.USER_DEFINED_STRUCT_CLASS_REDIRECT, source=str(source), build_source=str(build),
               source_sha256=h.sha(source), build_sha256=h.sha(build))
    monkeypatch.setattr(h, 'USER_DEFINED_STRUCT_CLASS_REDIRECT', pin)
    if mutation == 'source_hash':
        source.write_text('[CoreRedirects]\n')
    elif mutation == 'build_hash':
        build.write_text('{}')
    else:
        source.write_text('[CoreRedirects]\n+ClassRedirects=(OldName="/Script/Engine.OtherStruct",NewName="/Script/CoreUObject.OtherStruct")\n')
        pin['source_sha256'] = h.sha(source)
    with pytest.raises(RuntimeError, match='Official UserDefinedStruct'):
        h.class_redirect_witness([row()])


def test_official_definition_relocated_into_coreuobject_is_pinned():
    redirect = h.USER_DEFINED_STRUCT_CLASS_REDIRECT
    lines = Path(redirect['source']).read_text(encoding='utf-8-sig').splitlines()
    assert lines[redirect['source_line'] - 1] == redirect['declaration']
    source = Path('D:/UE/UE_5.8/Engine/Source/Runtime/CoreUObject/Public/StructUtils/UserDefinedStruct.h')
    assert h.sha(source) == '796b5e944aba79840e96df856bd85606f27313f888c206eca9159598ccd916c6'
    assert 'class UUserDefinedStruct : public UScriptStruct' in source.read_text(encoding='utf-8-sig')
