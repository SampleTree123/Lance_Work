"""Extension boundaries: paired evidence, immutable indices and configuration locks."""
import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import motion_library_extension_contract_v1 as contract
import motion_library_review_adapter_v1 as adapter


def base_catalog():
    return {'sources': {'wardrobe': {'sha256': 'old'}}, 'actions_by_sex': {
        s: [{'index': i, 'action_id': f'ACT_{s.upper()}_{i}'} for i in range(1, 6)] for s in contract.SEXES}}


@pytest.fixture
def motion(monkeypatch):
    base = base_catalog()
    pair = {'index': 6, 'motion_id': 'MOTION_CAND_032', 'label': '舞蹈', 'variants': {}}
    reports, documents = {}, {}
    rec = lambda p, sha='a' * 64: {'path': p, 'sha256': sha}
    for sex in contract.SEXES:
        source_motion, fbx, export = rec('motion'), rec(sex + '.fbx'), rec(sex + '_export.json')
        body = dict(rec(sex + '.uasset'), asset='/Game/Body_' + sex)
        proof, binding = rec(sex + '_import.json'), rec(sex + '_binding.json')
        variant = {'action_id': 'ACT_NEW_' + sex.upper(), 'source_motion': source_motion,
            'source_fbx': fbx, 'export_report': export, 'export_binding': binding, 'import_report': proof,
            'body_only': body, 'duration_seconds': 10., 'skeleton_path': contract.faces.SKELETONS[sex]}
        pair['variants'][sex] = variant
        reports[proof['path']] = ({'body_only': {}, 'imported': {}, 'source_fbx': fbx,
            'protected_sources': [{'asset': variant['skeleton_path']}],
            'verification': {'face_reference_baseline': {'asset': variant['skeleton_path']}}},
            {'original_body': body, 'duration_seconds': 10.})
        documents[export['path']] = {'success': True}
        documents[binding['path']] = {'schema': 'motion_export_binding_v1', 'sex': sex,
            'source_motion': source_motion, 'export_report': export, 'source_fbx': fbx, 'source_motion_unchanged': True}
    monkeypatch.setattr(contract.pilot, 'import_source', lambda record, sex: reports[record['path']])
    monkeypatch.setattr(contract, 'checked', lambda record, **kwargs: documents.get(record['path']))
    doc = {'schema': contract.MOTION_SCHEMA, 'status': 'validated_review', 'base_catalog_sources': base['sources'], 'actions': [pair]}
    return base, doc, reports, documents


def test_pair_append_preserves_original_rows_and_stable_ids(motion):
    base, doc, _, _ = motion
    before = copy.deepcopy(base)
    result = contract.validate_motion_catalog(doc, base)
    assert base == before
    for sex in contract.SEXES:
        assert result['actions_by_sex'][sex][:5] == base['actions_by_sex'][sex]
        assert result['actions_by_sex'][sex][5]['motion_id'] == 'MOTION_CAND_032'
        assert result['actions_by_sex'][sex][5]['action_id'] == 'ACT_NEW_' + sex.upper()


@pytest.mark.parametrize('change', ['one_sex', 'gap', 'duplicate_id', 'wrong_rig', 'short', 'base_changed', 'unbound_export', 'mixed_motion'])
def test_catalog_rejects_invalid_pair_authority(motion, change):
    base, doc, reports, documents = motion
    pair = doc['actions'][0]
    f, m = pair['variants']['female'], pair['variants']['male']
    if change == 'one_sex': del pair['variants']['male']
    elif change == 'gap': pair['index'] = 7
    elif change == 'duplicate_id': m['action_id'] = f['action_id']
    elif change == 'wrong_rig': m['skeleton_path'] = contract.faces.SKELETONS['female']
    elif change == 'short': reports[f['import_report']['path']][1]['duration_seconds'] = 4.9
    elif change == 'base_changed': doc['base_catalog_sources'] = {}
    elif change == 'unbound_export': documents[f['export_binding']['path']]['source_motion_unchanged'] = False
    elif change == 'mixed_motion': m['source_motion']['sha256'] = 'b' * 64
    with pytest.raises(ValueError): contract.validate_motion_catalog(doc, base)


@pytest.mark.parametrize('index', [-1, 7, True, 6., '6'])
def test_catalog_bound_index_rejects_foreign_values(index):
    data = base_catalog()
    for sex in contract.SEXES: data['actions_by_sex'][sex].append({'index': 6})
    with pytest.raises(ValueError): contract.check_index(index, data)
    assert contract.check_index(6, data) == 6


def test_private_controller_import_does_not_mutate_existing_modules():
    import run_cfd_native_batch40_modular_review_v1 as old
    before = (old.panel, old.identities.face_catalog, old.panel.WORKER, old.panel.STATE_KEYS)
    a, b = adapter.PrivateModules(), adapter.PrivateModules()
    private_a = a.load('run_cfd_native_batch40_modular_review_v1')
    private_b = b.load('run_cfd_native_batch40_modular_review_v1')
    assert private_a.panel is not private_b.panel and private_a.panel is not old.panel
    assert private_a.identities is not old.identities
    private_a.panel.STATE_KEYS += ('temporary',)
    assert before == (old.panel, old.identities.face_catalog, old.panel.WORKER, old.panel.STATE_KEYS)
    assert a.reload(private_a) is private_a
    with pytest.raises(ValueError): a.reload(old)


def request_data():
    data = base_catalog()
    data['sources']['motion_extension'] = {'path': 'motion.json', 'sha256': 'motion'}
    data['face_library'] = {'registry_source': {'path': 'face.json', 'sha256': 'face'}}
    request = {'action': 'show', 'action_index': 5, 'appearance': {s: {'face_id': 'smile'} for s in contract.SEXES},
               'face_registry_sha256': contract.BASE_REGISTRY_SHA}
    return request, data


def test_only_recognized_old_face_pin_and_unchanged_old_index_migrate():
    request, data = request_data()
    actual = adapter.migrate_request(request, data, from_base=True)
    assert actual['action_index'] == 5 and actual['face_registry_sha256'] == 'face'
    assert actual[adapter.PIN] == 'motion' and adapter.PIN not in request
    with pytest.raises(ValueError): adapter.migrate_request(dict(request, action_index=6), data, from_base=True)
    with pytest.raises(ValueError): adapter.migrate_request(dict(request, face_registry_sha256='unknown'), data, from_base=True)
    with pytest.raises(ValueError): adapter.migrate_request(actual, data, from_base=True)
    with pytest.raises(ValueError): adapter.migrate_request(dict(actual, motion_catalog_sha256='changed'), data)


def test_configuration_preserves_all_other_source_locks(tmp_path):
    graph = adapter.PrivateModules()
    app = graph.load('run_cfd_native_batch40_modular_review_v1')
    adapter.install_configurations(app)
    request, data = request_data()
    data['appearance'] = {'palette': 'unchanged'}
    data['sources']['native_face_library'] = data['face_library']['registry_source']
    old_sources = copy.deepcopy(data['sources'])
    old_sources.pop('motion_extension')
    old_sources['native_face_library'] = contract.source(contract.faces.PANEL_REGISTRY)
    document = {'schema': app.configurations.SCHEMA, 'content': {'request': request,
        'sources': old_sources, 'level': app.identities.LEVEL, 'palette': data['appearance']}}
    path = tmp_path / 'old.json'
    def write():
        document['content_sha256'] = app.configurations.digest(document['content'])
        path.write_text(json.dumps(document), encoding='utf-8')
    write()
    loaded = app.configurations.load_configuration(path, data, lambda r, d: r)
    assert loaded[adapter.PIN] == 'motion'
    document['content']['sources']['wardrobe'] = {'sha256': 'different'}
    write()
    with pytest.raises(ValueError, match='locks'): app.configurations.load_configuration(path, data, lambda r, d: r)


def test_face_overlay_cannot_publish_partial_matrix(monkeypatch):
    motion = base_catalog()
    motion['sources']['motion_extension'] = {'path': 'motion', 'sha256': 'm'}
    for sex in contract.SEXES: motion['actions_by_sex'][sex].append({'action_id': 'ACT_' + sex})
    base_record = {'path': 'base', 'sha256': contract.BASE_REGISTRY_SHA}
    selection = {'path': 'selection', 'sha256': 's'}
    visual = {'path': 'visual', 'sha256': 'v'}
    monkeypatch.setattr(contract, 'source', lambda path: base_record if path == contract.faces.PANEL_REGISTRY else selection)
    docs = {'selection': {'entries': []}, 'visual': {'reviewer': 'root_agent', 'status': 'reviewed_for_panel',
        'scope': 'representative_combinations_only', 'observations': 'reviewed', 'evidence': [{'path': 'image'}], 'animation_paths': ['missing']}}
    monkeypatch.setattr(contract, 'checked', lambda record, **kw: docs.get(record['path']))
    doc = {'schema': contract.FACE_SCHEMA, 'status': 'validated_review', 'sources': {'base_registry': base_record,
        'accepted_selection': selection, 'motion_catalog': motion['sources']['motion_extension'], 'root_visual': visual}, 'entries': []}
    with pytest.raises(ValueError, match='coverage'): contract.validate_face_overlay(doc, motion, base_library={'entries': []})


def test_controller_accepts_sixth_action_with_pin_and_rejects_fallback(monkeypatch, tmp_path):
    base = base_catalog()
    base['sources']['registry'] = {'sha256': 'wardrobe'}
    base['presets_by_sex'] = {s: [{'choice': {'hair_id': 'hair2'}}] for s in contract.SEXES}
    base['hairs_by_sex'] = {s: [{'index': 2, 'hair_id': 'hair2'}] for s in contract.SEXES}
    extended = copy.deepcopy(base)
    motion_record, face_record = {'path': 'motion', 'sha256': 'm'}, {'path': 'face', 'sha256': 'f'}
    extended['sources']['motion_extension'] = motion_record
    for sex in contract.SEXES: extended['actions_by_sex'][sex].append({'index': 6, 'action_id': 'ACT_NEW_' + sex})
    library = {'entries': [], 'registry_source': face_record}
    def load(self):
        self._snapshot = (copy.deepcopy(extended), copy.deepcopy(library))
        return self._snapshot
    monkeypatch.setattr(adapter.BoundCatalog, 'load', load)
    monkeypatch.setattr(adapter.BoundCatalog, 'library', lambda self: copy.deepcopy(library))
    app = adapter.controller(motion_record, face_record)
    app._load = lambda: copy.deepcopy(base)
    app.panel.contract.validate_choice = lambda *a: None
    ids = {s: app.identities.DEFAULT_CHARACTER_IDS[s] for s in contract.SEXES}
    app.identities.identity_catalog = lambda: {'source': {'sha256': 'identity'},
        'by_id': {ids[s]: {'sex': s} for s in contract.SEXES}}
    data = app.load_catalog()
    request = app.initial_request(data)
    request.update(action_index=6, playing=True)
    assert app.validate_request(request, data)['action_index'] == 6
    with pytest.raises(ValueError): app.validate_request(dict(request, action_index=7), data)
    with pytest.raises(ValueError): app.validate_request({k: v for k, v in request.items() if k != adapter.PIN}, data)
    assert 'DM_MOTION_CATALOG' in app.panel.command_payload(request)
    assert 'DM_MOTION_FACE_REGISTRY' in app.panel.command_payload(request)
    request['framing'] = 'motion_panorama'
    assert app.validate_request(request, data)['framing'] == 'motion_panorama'
    assert app.build_parser().parse_args(['--framing', 'motion_panorama']).framing == 'motion_panorama'
    config_path = tmp_path / 'panorama_configuration.json'
    app.configurations.save_configuration(config_path, {'success': True, 'sources': data['sources'], 'request': request}, data, app.validate_request)
    restored = app.configurations.load_configuration(config_path, data, app.validate_request)
    assert restored['framing'] == 'motion_panorama' and restored['action_index'] == 6


def test_dependency_cache_observes_transitive_checked_record_and_invalidates(tmp_path):
    path = tmp_path / 'package.bin'
    path.write_bytes(b'original')
    record = contract.source(path)
    with contract.trace_dependencies() as observed:
        contract.checked(record)
    assert observed == [record]
    dependencies = adapter.dependency_snapshot(observed)
    assert adapter.unchanged(dependencies)
    # Same length still invalidates through nanosecond modification/change time.
    path.write_bytes(b'changed!')
    assert not adapter.unchanged(dependencies)
    with pytest.raises(ValueError): adapter.dependency_snapshot(observed)
    path.unlink()
    assert not adapter.unchanged(dependencies)
