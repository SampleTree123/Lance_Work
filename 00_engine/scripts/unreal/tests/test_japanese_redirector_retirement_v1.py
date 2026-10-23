"""Offline guards for the one-time retirement of one pinned Japanese Village ID."""
import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ue_scene_folder_organization_v1 as relocation

ROOT = '/Game/Japanese_Village'
DESTINATION = '/Game/Scenes/Japanese_Village'
OLD_PACKAGE = ROOT + '/HDRI/pizzo_pernice_puresky_4k'
PREFAB = ROOT + '/HDRI/SKY_HDRI'
NAMES = ('pizzo_pernice_puresky_4k',)


def dump(path, value):
    path.write_text(json.dumps(value), encoding='utf-8')


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    # A small map fixture plus 615 identities exercises the real validators.
    monkeypatch.setattr(relocation, 'RUN', tmp_path)
    retired = [{'package': OLD_PACKAGE, 'name': n, 'class': '/Script/CoreUObject.ObjectRedirector'} for n in NAMES]
    real = [{'package': ROOT + '/Meshes/M_' + str(i), 'name': 'M_' + str(i), 'class': '/Script/Engine.StaticMesh'}
            for i in range(614)]
    real.append({'package': PREFAB, 'name': 'SKY_HDRI', 'class': '/Script/Engine.TextureCube'})
    maps = [{'map': ROOT + '/Maps/' + n, 'actor_count': 1,
             'actors': [{'name': 'Window', 'class': '/Script/Engine.StaticMeshActor', 'transform': [1.0] * 9,
                         'components': [{'name': 'Mesh', 'mesh': ROOT + '/Meshes/M_0.M_0',
                                         'materials': [], 'instances': None}]}],
             'levels': [ROOT + '/Maps/' + n + '.' + n + ':PersistentLevel']}
            for n in ('L_' + str(i) for i in range(23))]
    relative = {m['map']: [{'name': 'Window', 'components': [{'name': 'Mesh', 'transform': [1.0] * 9}]}] for m in maps}
    baseline = {'root': ROOT, 'assets': real + retired, 'maps': maps, 'component_transforms': relative}
    base_path = tmp_path / 'baseline_Japanese_Village_v1.json'
    dump(base_path, baseline)
    monkeypatch.setattr(relocation, 'JAPANESE_BASELINE_SHA256', relocation.sha(base_path))
    backup = tmp_path / 'backup.uasset'
    backup.write_bytes(b'isolated original redirector package')
    monkeypatch.setattr(relocation, 'JAPANESE_REDIRECTOR_BACKUP', backup)
    monkeypatch.setattr(relocation, 'JAPANESE_REDIRECTOR_BACKUP_SHA256', relocation.sha(backup))
    source_project = tmp_path / 'original' / 'source.uproject'
    source_project.parent.mkdir()
    source_project.write_text('{}')
    source_file = source_project.parent / 'Content/Japanese_Village/HDRI/pizzo_pernice_puresky_4k.uasset'
    source_file.parent.mkdir(parents=True)
    source_file.write_bytes(backup.read_bytes())
    targets = [{'object_path': OLD_PACKAGE + '.' + n, 'target': PREFAB + '.SKY_HDRI'} for n in NAMES]
    original = {'schema': 'japanese_original_redirector_targets_v1', 'success': True, 'root': ROOT,
                'source': 'isolated_original_backup_project', 'source_project': str(source_project),
                'source_package_file': str(source_file), 'original_backup_sha256': relocation.sha(backup),
                'source_sha256_before': relocation.sha(backup), 'source_sha256_after': relocation.sha(backup),
                'saved_source_packages': [], 'camera_render_started': False, 'original_redirector_targets': targets}
    original_path = tmp_path / 'japanese_original_redirector_targets_v1.json'
    dump(original_path, original)
    actual = [dict(r, package=DESTINATION + r['package'][len(ROOT):]) for r in real]
    proof = {'schema': 'japanese_redirector_retirement_v1', 'success': True, 'root': ROOT,
             'destination': DESTINATION, 'camera_render_started': False,
             'baseline_sha256': relocation.sha(base_path), 'original_backup': {'path': str(backup), 'sha256': relocation.sha(backup)},
             'original_target_witness': {'path': str(original_path), 'sha256': relocation.sha(original_path)},
             'retired_redirectors': copy.deepcopy(retired),
             'original_redirector_targets': [dict(t, resolved_destination=t['target'].replace(ROOT, DESTINATION, 1)) for t in targets],
             'actual_assets': actual, 'actual_maps': copy.deepcopy(maps), 'component_transforms': copy.deepcopy(relative),
             'old_packages': [OLD_PACKAGE], 'old_referencers': {OLD_PACKAGE: []},
             'destination_dependencies': {r['package']: [] for r in actual}}
    return {'proof': proof, 'baseline': baseline, 'base_path': base_path, 'backup': backup,
            'original': original, 'original_path': original_path, 'source_file': source_file}


def validate(evidence):
    dump(relocation.RUN / 'japanese_redirector_retirement_v1.json', evidence['proof'])
    return relocation.verification_asset_contract(ROOT, evidence['base_path'], evidence['baseline'])


def test_production_pins_are_fixed():
    assert relocation.JAPANESE_BASELINE_SHA256 == 'de33a7b2a1a899efd32857e79d8bcb7ac537ad57067dd5555f6d61c4a295f7d6'
    assert relocation.JAPANESE_REDIRECTOR_BACKUP_SHA256 == 'd44b489762eab059b1363e3d601e25dd1f83cd469becf4ce082da28931b4bce1'


def test_complete_contract_excludes_exactly_one_without_mutating_baseline(evidence):
    before = copy.deepcopy(evidence['baseline'])
    original_bytes = evidence['base_path'].read_bytes()
    expected, witness = validate(evidence)
    assert len(expected) == 615
    assert len(witness['retired_redirectors']) == 1
    assert all(r['class'] != '/Script/CoreUObject.ObjectRedirector' for r in expected)
    assert evidence['baseline'] == before
    assert evidence['base_path'].read_bytes() == original_bytes
    assert witness['sha256'] == relocation.sha(relocation.RUN / 'japanese_redirector_retirement_v1.json')
    assert witness['original_target_witness']['sha256'] == relocation.sha(evidence['original_path'])


def test_missing_contract_preserves_616_strict_identities(evidence):
    expected, witness = relocation.verification_asset_contract(ROOT, evidence['base_path'], evidence['baseline'])
    assert expected == evidence['baseline']['assets'] and witness is None


def test_other_roots_never_inherit_exception_even_with_malformed_receipt(evidence):
    (relocation.RUN / 'japanese_redirector_retirement_v1.json').write_text('{}')
    expected, witness = relocation.verification_asset_contract('/Game/OtherScene', evidence['base_path'], evidence['baseline'])
    assert len(expected) == 616 and witness is None


@pytest.mark.parametrize('field', [
    'schema', 'success', 'root', 'destination', 'camera_render_started', 'baseline_sha256',
    'original_backup', 'original_target_witness', 'retired_redirectors', 'original_redirector_targets',
    'actual_assets', 'actual_maps', 'component_transforms', 'old_packages', 'old_referencers', 'destination_dependencies'])
def test_missing_required_field_fails_closed(evidence, field):
    del evidence['proof'][field]
    with pytest.raises(RuntimeError, match='Invalid Japanese_Village'):
        validate(evidence)


@pytest.mark.parametrize('field,value', [
    ('root', '/Game/OtherScene'), ('destination', '/Game/Scenes/Japanese_VillageExtra'),
    ('success', 1), ('camera_render_started', 0), ('schema', 'generic_redirector_retirement'),
    ('baseline_sha256', '0' * 64)])
def test_wrong_scope_flags_or_pin_fail(evidence, field, value):
    evidence['proof'][field] = value
    with pytest.raises(RuntimeError, match='Invalid Japanese_Village'):
        validate(evidence)


@pytest.mark.parametrize('mutation', ['wrong_name', 'wrong_package', 'wrong_class', 'missing', 'extra'])
def test_only_exact_original_redirector_ids_may_retire(evidence, mutation):
    rows = evidence['proof']['retired_redirectors']
    if mutation == 'missing': rows.pop()
    elif mutation == 'extra': rows.append(copy.deepcopy(evidence['baseline']['assets'][0]))
    else: rows[0][{'wrong_name': 'name', 'wrong_package': 'package', 'wrong_class': 'class'}[mutation]] = 'Wrong'
    with pytest.raises(RuntimeError, match='Invalid Japanese_Village'):
        validate(evidence)


@pytest.mark.parametrize('mutation', ['missing', 'extra', 'duplicate', 'class', 'name', 'package'])
def test_all_real_asset_identity_changes_fail(evidence, mutation):
    rows = evidence['proof']['actual_assets']
    if mutation == 'missing': rows.pop()
    elif mutation == 'extra': rows.append(dict(rows[0], package=DESTINATION + '/Unexpected'))
    elif mutation == 'duplicate': rows[-1] = copy.deepcopy(rows[0])
    else: rows[0][mutation] = 'Wrong'
    with pytest.raises(RuntimeError, match='Invalid Japanese_Village'):
        validate(evidence)


@pytest.mark.parametrize('mutation', ['missing_actor', 'class', 'transform', 'mesh', 'materials', 'instances', 'levels', 'missing_map'])
def test_map_structure_stays_strict(evidence, mutation):
    maps = evidence['proof']['actual_maps']
    actor = maps[0]['actors'][0]
    if mutation == 'missing_map': maps.pop()
    elif mutation == 'missing_actor': maps[0]['actors'] = []; maps[0]['actor_count'] = 0
    elif mutation == 'levels': maps[0]['levels'] = []
    elif mutation == 'transform': actor['transform'][0] += 0.001
    elif mutation == 'class': actor['class'] = 'Wrong'
    else: actor['components'][0][mutation] = [] if mutation == 'instances' else 'Wrong'
    with pytest.raises(RuntimeError, match='Invalid Japanese_Village'):
        validate(evidence)


def test_component_transforms_stay_exact(evidence):
    rows = next(iter(evidence['proof']['component_transforms'].values()))
    rows[0]['components'][0]['transform'][0] += 0.000001
    with pytest.raises(RuntimeError, match='component transforms'):
        validate(evidence)


@pytest.mark.parametrize('mutation', ['outside_referencer', 'missing_refs', 'old_dependency', 'case_old_dependency', 'missing_dependencies'])
def test_reference_graph_evidence_must_be_complete_and_closed(evidence, mutation):
    proof = evidence['proof']
    if mutation == 'outside_referencer': proof['old_referencers'][OLD_PACKAGE] = [DESTINATION + '/Maps/Japanese_Village']
    elif mutation == 'missing_refs': proof['old_referencers'] = {}
    elif mutation == 'missing_dependencies': proof['destination_dependencies'].pop(next(iter(proof['destination_dependencies'])))
    else: proof['destination_dependencies'][next(iter(proof['destination_dependencies']))] = [ROOT.upper() + '/Meshes/M_0' if mutation == 'case_old_dependency' else ROOT + '/Meshes/M_0']
    with pytest.raises(RuntimeError, match='Invalid Japanese_Village'):
        validate(evidence)


@pytest.mark.parametrize('mutation', ['witness_bytes', 'witness_pin', 'backup_bytes', 'source_bytes', 'baseline_bytes', 'baseline_argument'])
def test_bound_evidence_tampering_is_rejected(evidence, mutation):
    if mutation == 'witness_bytes': evidence['original_path'].write_text('{}')
    elif mutation == 'witness_pin': evidence['proof']['original_target_witness']['sha256'] = '0' * 64
    elif mutation == 'backup_bytes': evidence['backup'].write_bytes(b'changed')
    elif mutation == 'source_bytes': evidence['source_file'].write_bytes(b'changed')
    elif mutation == 'baseline_bytes': evidence['base_path'].write_text('{}')
    else: evidence['baseline']['assets'][0]['name'] = 'Changed'
    with pytest.raises(RuntimeError, match='Invalid Japanese_Village'):
        validate(evidence)


@pytest.mark.parametrize('mutation', ['missing_field', 'wrong_target', 'saved_source', 'changed_before_hash', 'production_source'])
def test_original_target_receipt_is_semantically_validated_even_with_matching_sha(evidence, mutation):
    original = evidence['original']
    if mutation == 'missing_field': del original['source_sha256_before']
    elif mutation == 'wrong_target': original['original_redirector_targets'][0]['target'] = ROOT + '/Wrong'
    elif mutation == 'saved_source': original['saved_source_packages'] = [OLD_PACKAGE]
    elif mutation == 'production_source': original['source_project'] = str(relocation.PROJECT / 'datatry_02.uproject')
    else: original['source_sha256_before'] = '0' * 64
    dump(evidence['original_path'], original)
    evidence['proof']['original_target_witness']['sha256'] = relocation.sha(evidence['original_path'])
    with pytest.raises(RuntimeError, match='Invalid Japanese_Village'):
        validate(evidence)


def test_claimed_resolved_target_cannot_differ_from_original_mapping(evidence):
    evidence['proof']['original_redirector_targets'][0]['resolved_destination'] = DESTINATION + '/Wrong'
    with pytest.raises(RuntimeError, match='resolved redirector targets'):
        validate(evidence)


@pytest.fixture
def live_verification(evidence, monkeypatch):
    """Mock only UE observations; run the actual final verify control flow."""
    validate(evidence)
    state = {'assets': copy.deepcopy(evidence['proof']['actual_assets']), 'old_assets': [],
             'maps': copy.deepcopy(evidence['baseline']['maps']),
             'relative': copy.deepcopy(evidence['baseline']['component_transforms']),
             'dependencies': {}, 'receipts': []}
    def asset_rows(u, path):
        rows = state['old_assets'] if path == ROOT else state['assets']
        return [SimpleNamespace(package_name=r['package'], record=r) for r in rows]
    def capture(u, path, root, **kwargs):
        original_path = ROOT + path[len(DESTINATION):]
        state['active_map'] = original_path
        return next(m for m in state['maps'] if m['map'] == original_path)
    registry = SimpleNamespace(get_dependencies=lambda package, options: state['dependencies'].get(package, []))
    u = SimpleNamespace(AssetRegistryHelpers=SimpleNamespace(get_asset_registry=lambda: registry),
                        AssetRegistryDependencyOptions=lambda **kwargs: kwargs,
                        EditorLoadingAndSavingUtils=SimpleNamespace(load_map=lambda path: None))
    monkeypatch.setattr(relocation, 'guard', lambda u: None)
    monkeypatch.setattr(relocation, 'select_verification_baseline', lambda root, path: (evidence['baseline'], None))
    monkeypatch.setattr(relocation, 'assets', asset_rows)
    monkeypatch.setattr(relocation, 'asset_record', lambda asset: asset.record)
    monkeypatch.setattr(relocation, 'settled_signature', capture)
    monkeypatch.setattr(relocation, 'component_transforms', lambda u: state['relative'][state['active_map']])
    monkeypatch.setattr(relocation, 'dirty', lambda u: [])
    monkeypatch.setattr(relocation, 'loading_protocol', lambda: {})
    monkeypatch.setattr(relocation, 'write', lambda name, result: state['receipts'].append(copy.deepcopy(result)))
    return u, state


def test_verify_reports_retirement_and_original_count_explicitly(live_verification):
    u, state = live_verification
    relocation.verify(u, ROOT)
    receipt = state['receipts'][0]
    assert receipt['success'] is True
    assert receipt['original_asset_count'] == 616 and receipt['asset_count'] == 615
    assert len(receipt['retired_redirectors']) == 1
    assert receipt['redirector_retirement_witness']['sha256']


@pytest.mark.parametrize('mutation', ['missing_asset', 'extra_asset', 'old_asset', 'new_old_dependency', 'map_actor_loss', 'relative_change'])
def test_successful_historical_retirement_proof_never_overrides_live_failures(live_verification, mutation):
    u, state = live_verification
    if mutation == 'missing_asset': state['assets'].pop()
    elif mutation == 'extra_asset': state['assets'].append(dict(state['assets'][0], name='Extra', package=DESTINATION + '/Extra'))
    elif mutation == 'old_asset': state['old_assets'] = [{'package': OLD_PACKAGE, 'name': NAMES[0], 'class': '/Script/CoreUObject.ObjectRedirector'}]
    elif mutation == 'new_old_dependency': state['dependencies'][state['assets'][0]['package']] = [ROOT.upper() + '/Obsolete']
    elif mutation == 'map_actor_loss': state['maps'][0]['actors'] = []; state['maps'][0]['actor_count'] = 0
    else: state['relative'][next(iter(state['relative']))][0]['components'][0]['transform'][0] += 1
    with pytest.raises(RuntimeError):
        relocation.verify(u, ROOT)
    assert not state['receipts'] or state['receipts'][0]['success'] is False
