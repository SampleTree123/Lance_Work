"""Offline boundary tests for the additive, single-asset pink-coat correction."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
RUN = SCRIPTS.parents[1] / 'outputs/production_workflow_20261017_v1'


@pytest.fixture
def correction(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('test_pink_correction_helper', RUN / 'asset_inventory_formal_runtime_v1.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    monkeypatch.setattr(helper, 'RUN', tmp_path)
    monkeypatch.setattr(helper, 'CONTENT', tmp_path / 'Content')
    root = '/Game/DataMake/Appearance/Wardrobe/Female/bikini_ruana/Coats/'
    old = root + 'Bikini_Cover_up_Pink/Meshes/old.old'
    new = root + 'Bikini_Cover_up_Pink/Corrected/pink.pink'
    source = root + 'Bikini_Cover_up_Blue/Meshes/blue.blue'
    source_mi = root + 'Bikini_Cover_up_Blue/Materials/MI_blue.MI_blue'
    material = root + 'Bikini_Cover_up_Pink/Corrected/MI_pink.MI_pink'
    pins = []
    for obj in (old, new, source, source_mi, material):
        file = helper.CONTENT / (obj.split('.')[0].removeprefix('/Game/') + '.uasset')
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(obj.encode())
        pins.append(helper.record(file))
    catalog = tmp_path / 'catalog.json'
    catalog.write_text('{}', encoding='utf-8')
    binding = helper.record(catalog)
    doc = {'catalogs': {'registry': {'families': [{'assets': [
        {'asset_id': 'female.bikini_ruana.asset.da1e675a22e4', 'ue_mesh_paths': [old]}]}]}}}
    manifest = {'schema': 'wardrobe_component_corrections_v1', 'complete': True, 'catalog': binding,
                'corrections': [{'asset_id': 'female.bikini_ruana.asset.da1e675a22e4', 'old_object': old,
                                 'new_object': new, 'source_objects': [source, source_mi],
                                 'derived_material_objects': [material]}], 'asset_pins': pins}
    path = tmp_path / 'wardrobe_component_corrections_v1.json'
    def publish():
        path.write_text(json.dumps(manifest), encoding='utf-8')
    publish()
    return helper, doc, binding, manifest, path, publish


def test_verified_correction_only_adds_overlay_and_pins(correction):
    h, doc, source, manifest, path, _ = correction
    original = copy.deepcopy(doc)
    overlay, pins = h.wardrobe_component_corrections(doc, source)
    row = manifest['corrections'][0]
    assert overlay == {row['old_object']: row['new_object'],
                       row['old_object'].split('.')[0]: row['new_object'].split('.')[0]}
    assert pins == [h.record(path), *manifest['asset_pins']]
    assert doc == original


@pytest.mark.parametrize('failure', ['catalog', 'asset_id', 'old_mesh', 'shared_old_mesh', 'target_scope',
                                     'missing_pin', 'changed_file', 'incomplete', 'missing_material'])
def test_invalid_correction_is_rejected(correction, failure):
    h, doc, source, manifest, path, publish = correction
    row = manifest['corrections'][0]
    if failure == 'catalog': manifest['catalog']['sha256'] = '0' * 64
    elif failure == 'asset_id': row['asset_id'] = 'different'
    elif failure == 'old_mesh': row['old_object'] = '/Game/Other.Other'
    elif failure == 'shared_old_mesh':
        doc['catalogs']['registry']['families'][0]['assets'].append({'asset_id': 'other', 'ue_mesh_paths': [row['old_object']]})
    elif failure == 'target_scope': row['new_object'] = '/Game/Outside/Mesh.Mesh'
    elif failure == 'missing_pin': manifest['asset_pins'].pop()
    elif failure == 'changed_file': Path(manifest['asset_pins'][1]['path']).write_bytes(b'changed')
    elif failure == 'incomplete': manifest['complete'] = False
    elif failure == 'missing_material': row['derived_material_objects'] = []
    publish()
    # The independently supplied catalog identity is immutable even if the
    # manifest fixture mutates its own nested record above.
    with pytest.raises(ValueError):
        h.wardrobe_component_corrections(doc, h.record(path.parent / 'catalog.json'))


def test_absent_manifest_preserves_original_runtime(correction):
    h, doc, source, _, _, _ = correction
    h.RUN = h.RUN / 'not_published'
    assert h.wardrobe_component_corrections(doc, source) == ({}, [])


def test_republished_catalog_preserves_verified_original_correction(correction, monkeypatch):
    h, doc, original, manifest, path, _ = correction
    current = {'path': str(path.parent / 'cleaned_catalog.json'), 'sha256': 'a' * 64}
    monkeypatch.setattr(h, '_previous_publication_source_bundles',
                        lambda value: [{'wardrobe_registry': copy.deepcopy(original)}])
    overlay, pins = h.wardrobe_component_corrections(doc, current)
    assert overlay[manifest['corrections'][0]['old_object']] == manifest['corrections'][0]['new_object']
    assert pins[0] == h.record(path)


def test_republished_catalog_rejects_unverified_history(correction, monkeypatch):
    h, doc, _, _, path, _ = correction
    def reject(_):
        raise ValueError('Previous publication selection semantics differ')
    monkeypatch.setattr(h, '_previous_publication_source_bundles', reject)
    with pytest.raises(ValueError, match='semantics differ'):
        h.wardrobe_component_corrections(doc, {'path': 'other', 'sha256': 'a' * 64})


def test_scene_contract_cache_tracks_helper_and_correction_publication(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    import scene_site_appearance_v1 as appearance
    helper, pointer, correction_path = (tmp_path / name for name in ('helper.py', 'active.json', 'corrections.json'))
    helper.write_text('# fixture', encoding='utf-8')
    pointer.write_text('{}', encoding='utf-8')
    monkeypatch.setattr(appearance, 'FORMAL_HELPER', helper)
    monkeypatch.setattr(appearance, 'FORMAL_POINTER', pointer)
    monkeypatch.setattr(appearance, 'FORMAL_CORRECTIONS', correction_path)
    trial_catalog, trial_runtime = tmp_path / 'trial_catalog.py', tmp_path / 'trial_runtime.py'
    trial_catalog.write_text('# three IDs', encoding='utf-8')
    monkeypatch.setattr(appearance, 'FORMAL_COLOR_TRIAL_CATALOG', trial_catalog)
    monkeypatch.setattr(appearance, 'FORMAL_COLOR_TRIAL_RUNTIME', trial_runtime)
    monkeypatch.setattr(appearance, '_formal_cache', None)
    calls = []
    class Loader:
        def create_module(self, spec):
            return None

        def exec_module(self, module):
            def contract():
                calls.append(object())
                return calls[-1]
            module.appearance_contract = contract
    monkeypatch.setattr(appearance.importlib.util, 'spec_from_file_location',
                        lambda *args: importlib.util.spec_from_loader('fixture_correction_cache', Loader()))
    first = appearance.formal_runtime()[1]
    assert appearance.formal_runtime()[1] is first
    correction_path.write_text('{}', encoding='utf-8')
    second = appearance.formal_runtime()[1]
    assert second is not first
    helper.write_text('# changed helper', encoding='utf-8')
    third = appearance.formal_runtime()[1]
    assert third is not second
    trial_runtime.write_text('# published later', encoding='utf-8')
    fourth = appearance.formal_runtime()[1]
    assert fourth is not third
    trial_catalog.write_text('# updated three IDs', encoding='utf-8')
    assert appearance.formal_runtime()[1] is not fourth
    assert len(calls) == 5
