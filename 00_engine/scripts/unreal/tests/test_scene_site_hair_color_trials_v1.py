"""Canonical ten only; retired experiments load through compatibility aliases."""
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
RUN = SCRIPTS.parents[1] / 'outputs/production_workflow_20261017_v1'
ALIASES = {'black_neutral_v1': 'black', 'blue_neutral_v1': 'blue', 'pink_neutral_v1': 'pink'}
SOFT = {'black_soft_reflection_v1': 'black', 'blue_soft_reflection_v1': 'blue',
        'silver_white_soft_reflection_v1': 'silver_white'}


@pytest.fixture
def formal(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    spec = importlib.util.spec_from_file_location('hair_trial_test_formal_helper', RUN / 'asset_inventory_formal_runtime_v1.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    source = helper.read(RUN / 'asset_inventory_formal_runtime_active_v1.json')['catalog']
    # Exercise actual immutable selection semantics without rehashing large UE
    # files. Asset binding itself is covered by the bounded offline validation.
    doc = helper.read(source['path'])
    monkeypatch.setattr(helper, 'load', lambda: copy.deepcopy(doc))
    monkeypatch.setattr(helper, 'wardrobe_component_corrections', lambda *_: ({}, []))
    return helper, helper.appearance_contract(), doc


def test_canonical_ten_retained_without_promoting_rejected_experiments(formal):
    helper, contract, doc = formal
    before = copy.deepcopy(doc['catalogs']['palette'])
    palette = helper.current_palette(before)
    data = contract.catalog()
    assert palette['hair'] == before['hair']
    assert palette['eye'] == before['eye']
    assert before == doc['catalogs']['palette']
    assert [r['id'] for r in data['hair_colors']] == palette['hair']
    assert len(data['hair_colors']) == 10
    assert not any(r.get('experimental') or '反光' in r['label'] or '对照' in r['label'] for r in data['hair_colors'])
    assert [r['method'] for r in data['hair_colors']] == ['original'] + ['neutral_base_v2'] * 9
    spec = importlib.util.spec_from_file_location('rejected_comparison_palette',
        RUN / 'panel_followup_audit/hair_color_soft_reflection_catalog_before_canonical_ten_restore.py')
    previous = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(previous)
    current = helper.private('scene_site_hair_color_trials_v1')
    assert data['hair_colors'] == previous.catalog()[:10]
    assert current.NEUTRAL_TINTS == previous.NEUTRAL_TINTS
    assert current.NEUTRAL_SCALAR_OVERRIDES == previous.NEUTRAL_SCALAR_OVERRIDES
    assert current.NEUTRAL_TINTS['silver_white'] == (4., 4., 4.2, 1.)
    assert current.NEUTRAL_SCALAR_OVERRIDES == {'silver_white': {'Compensate Color Power': .4}}
    assert next(r for r in data['hair_colors'] if r['id']=='silver_white')['label'] == '白色（微银）'
    assert current.ALIASES == {**ALIASES, 'silver_white_legacy_v1': 'silver_white', **SOFT}
    assert data['sources']['hair_color_trials'] == helper.record(SCRIPTS / 'scene_site_hair_color_trials_v1.py')
    assert data['sources']['hair_color_method'] == {
        **data['sources']['hair_color_trials'], 'method': 'neutral_base_v2'}
    assert helper.current_palette(before, include_trials=False)['hair'] == before['hair']


@pytest.mark.parametrize('source_kind', ['current_pretrial', 'original', 'previous_formal'])
def test_old_saved_appearance_loads_without_writing_and_preserves_look(formal, tmp_path, source_kind):
    _, contract, _ = formal
    data = contract.catalog()
    selection = contract.default_selection(data)
    selection.update(hair_color='pink', face_id='none')
    if source_kind == 'current_pretrial':
        selection['sources'].pop('hair_color_trials')
        selection['sources'].pop('hair_color_method')
    elif source_kind == 'original':
        selection['sources'] = copy.deepcopy(contract.formal_migration_from)
    else:
        selection['sources'] = copy.deepcopy(contract.formal_previous_source_bundles[1])
    old = copy.deepcopy(selection)
    identifier = 'appearance_' + 'a' * 32
    path = tmp_path / (identifier + '.json')
    stored = {'schema': contract.SCHEMA, 'id': identifier, 'name': '原有粉色人物', 'created_at': 'fixture',
              'selection': selection, 'selection_sha256': contract.io.digest(selection)}
    path.write_text(json.dumps(stored, ensure_ascii=False), encoding='utf-8')
    raw = path.read_bytes()
    loaded = contract.load_configuration(identifier, data, root=tmp_path)
    assert path.read_bytes() == raw
    assert selection == old
    assert {k: v for k, v in loaded['selection'].items() if k != 'sources'} == {
        k: v for k, v in old.items() if k != 'sources'}
    assert loaded['selection']['sources'] == data['sources']


def test_three_trial_ids_normalize_to_canonical_and_unknown_inputs_are_rejected(formal, tmp_path):
    helper, contract, _ = formal
    data = contract.catalog()
    for color, canonical in ALIASES.items():
        selection = contract.default_selection(data)
        selection['hair_color'] = color
        saved = contract.save_configuration(color, selection, data, root=tmp_path)
        assert saved['selection']['hair_color'] == canonical
        assert contract.load_configuration(saved['id'], data, root=tmp_path)['selection'] == saved['selection']
    unknown = contract.default_selection(data)
    unknown['hair_color'] = 'red_neutral_v1'
    with pytest.raises(ValueError, match='当前目录中的发色'):
        contract.validate_selection(unknown, data)
    changed = contract.default_selection(data)
    changed['sources']['hair_color_trials']['sha256'] = '0' * 64
    with pytest.raises(ValueError, match='目录已变化'):
        contract.validate_selection(changed, data)


@pytest.mark.parametrize('alias,canonical', ALIASES.items())
def test_saved_trial_snapshot_loads_with_exact_old_source_and_without_disk_edits(formal, tmp_path, alias, canonical):
    helper, contract, _ = formal
    data = contract.catalog()
    selection = contract.default_selection(data)
    selection['hair_color'] = alias
    selection['sources'].pop('hair_color_method')
    selection['sources']['hair_color_trials'] = helper._legacy_trial_source()
    identifier = 'appearance_' + 'b' * 32
    stored = {'schema': contract.SCHEMA, 'id': identifier, 'name': alias, 'created_at': 'fixture',
              'selection': selection, 'selection_sha256': contract.io.digest(selection)}
    path = tmp_path / (identifier + '.json')
    path.write_text(json.dumps(stored, ensure_ascii=False), encoding='utf-8')
    raw = path.read_bytes()
    loaded = contract.load_configuration(identifier, data, root=tmp_path)
    assert loaded['selection']['hair_color'] == canonical
    assert loaded['selection']['sources'] == data['sources']
    assert loaded['selection']['choice'] == selection['choice']
    assert path.read_bytes() == raw
    selection['sources']['hair_color_trials']['sha256'] = '0' * 64
    with pytest.raises(ValueError, match='目录已变化'):
        contract.validate_selection(selection, data)


@pytest.mark.parametrize('color', ['original', 'pink', 'silver_white', 'silver_white_legacy_v1'])
@pytest.mark.parametrize('previous_kind', ['neutral_ten', 'silver_comparison_eleven', 'white_refinement_eleven', 'soft_fourteen'])
def test_saved_neutral_v2_source_bundle_loads_unchanged(formal, tmp_path, color, previous_kind):
    helper, contract, _ = formal
    data = contract.catalog()
    selection = contract.default_selection(data)
    selection['hair_color'] = color
    previous = {'neutral_ten': helper._previous_neutral_palette_source,
                'silver_comparison_eleven': helper._previous_silver_comparison_source,
                'white_refinement_eleven': helper._previous_white_refinement_source,
                'soft_fourteen': helper._previous_soft_reflection_source}[previous_kind]()
    selection['sources']['hair_color_trials'] = copy.deepcopy(previous)
    selection['sources']['hair_color_method'] = {**previous, 'method': 'neutral_base_v2'}
    identifier = 'appearance_' + 'c' * 32
    stored = {'schema': contract.SCHEMA, 'id': identifier, 'name': color, 'created_at': 'fixture',
              'selection': selection, 'selection_sha256': contract.io.digest(selection)}
    path = tmp_path / (identifier + '.json')
    path.write_text(json.dumps(stored, ensure_ascii=False), encoding='utf-8')
    raw = path.read_bytes()
    loaded = contract.load_configuration(identifier, data, root=tmp_path)
    assert path.read_bytes() == raw
    assert loaded['selection'] == {**selection, 'sources': data['sources'],
                                  'hair_color': 'silver_white' if color=='silver_white_legacy_v1' else color}
    selection['sources']['hair_color_method']['sha256'] = '0' * 64
    with pytest.raises(ValueError, match='目录已变化'):
        contract.validate_selection(selection, data)


def test_legacy_silver_comparison_normalizes_to_current_white(formal, tmp_path):
    _, contract, _ = formal
    data = contract.catalog()
    selection = contract.default_selection(data)
    selection['hair_color'] = 'silver_white_legacy_v1'
    saved = contract.save_configuration('旧版银白色对照', selection, data, root=tmp_path)
    loaded = contract.load_configuration(saved['id'], data, root=tmp_path)
    assert saved['selection']['hair_color'] == loaded['selection']['hair_color'] == 'silver_white'


@pytest.mark.parametrize('color', SOFT)
def test_retired_soft_reflection_snapshot_loads_as_base_without_editing_saved_file(formal, tmp_path, color):
    helper, contract, _ = formal
    palette = helper.private('scene_site_hair_color_trials_v1')
    assert palette.canonical_color(color) == SOFT[color]
    data = contract.catalog()
    selection = contract.default_selection(data)
    selection['hair_color'] = color
    previous = helper._previous_soft_reflection_source()
    selection['sources']['hair_color_trials'] = copy.deepcopy(previous)
    selection['sources']['hair_color_method'] = {**previous, 'method': 'neutral_base_v2'}
    identifier = 'appearance_' + 'd' * 32
    stored = {'schema': contract.SCHEMA, 'id': identifier, 'name': color, 'created_at': 'fixture',
              'selection': selection, 'selection_sha256': contract.io.digest(selection)}
    path = tmp_path / (identifier + '.json')
    path.write_text(json.dumps(stored, ensure_ascii=False), encoding='utf-8')
    raw = path.read_bytes()
    loaded = contract.load_configuration(identifier, data, root=tmp_path)
    assert loaded['selection'] == {**selection, 'sources': data['sources'], 'hair_color': SOFT[color]}
    assert path.read_bytes() == raw


def test_catalog_cannot_publish_another_comparison_id(formal, monkeypatch):
    helper, _, doc = formal
    rows = [{'id': v} for v in doc['catalogs']['palette']['hair'] + ['silver_white_legacy_v1', 'red_neutral_v1']]
    module = SimpleNamespace(ORIGINAL_IDS=tuple(doc['catalogs']['palette']['hair']),
                             ALIASES=ALIASES, TRIAL_IDS=tuple(ALIASES), catalog=lambda: rows,
                             NEUTRAL_METHOD='neutral_base_v2', NEUTRAL_TINTS={},
                             LEGACY_SILVER_ID='silver_white_legacy_v1')
    monkeypatch.setattr(helper, 'private', lambda _: module)
    with pytest.raises(ValueError, match='approved ten canonical IDs'):
        helper.current_palette(doc['catalogs']['palette'])
