"""Fail-closed evidence for the single mismatched UrbanJapan MIC name."""
import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ue_scene_folder_organization_v1 as m

ROOT, DEST = '/Game/UrbanJapan', '/Game/Scenes/UrbanJapan'
OLD = ROOT + '/Materials/MI_Ubc_Building.MI_BuildingDetails05'
NEW = DEST + '/Materials/MI_Ubc_Building.MI_Ubc_Building'
REAL = ROOT + '/Materials/MI_BuildingDetails05.MI_BuildingDetails05'


def dump(path, value):
    path.write_text(json.dumps(value), encoding='utf-8')


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(m, 'RUN', tmp_path)
    old_record = {'package': OLD.split('.')[0], 'name': 'MI_BuildingDetails05',
                  'class': '/Script/Engine.MaterialInstanceConstant'}
    real_record = dict(old_record, package=REAL.split('.')[0])
    rows = [old_record, real_record] + [
        {'package': ROOT + '/Meshes/M_' + str(i), 'name': 'M_' + str(i), 'class': '/Script/Engine.StaticMesh'}
        for i in range(484)]
    maps = [{'map': ROOT + '/Maps/' + n, 'actor_count': 1,
             'actors': [{'name': 'Building', 'class': '/Script/Engine.StaticMeshActor', 'transform': [1.0] * 9,
                         'components': [{'name': 'Mesh', 'mesh': ROOT + '/Meshes/M_0.M_0',
                                         'materials': [OLD, REAL], 'instances': None}]}],
             'levels': [ROOT + '/Maps/' + n + '.' + n + ':PersistentLevel']}
            for n in ('Demonstration', 'Overview')]
    relative = {s['map']: [{'name': 'Building', 'components': [{'name': 'Mesh', 'transform': [1.0] * 9}]}]
                for s in maps}
    base = {'root': ROOT, 'assets': rows, 'maps': maps, 'component_transforms': relative,
            'signature_format': 'mid_parameters_v2'}
    base_path = tmp_path / 'baseline_UrbanJapan_v1.json'
    dump(base_path, base)
    monkeypatch.setattr(m, 'URBAN_BASELINE_SHA256', m.sha(base_path))
    backup = tmp_path / 'backup.uasset'
    backup.write_bytes(b'original mismatched material package')
    monkeypatch.setattr(m, 'URBAN_MATERIAL_BACKUP', backup)
    monkeypatch.setattr(m, 'URBAN_MATERIAL_BACKUP_SHA256', m.sha(backup))
    project = tmp_path / 'original' / 'source.uproject'
    project.parent.mkdir()
    project.write_text('{}')
    source = project.parent / 'Content/UrbanJapan/Materials/MI_Ubc_Building.uasset'
    source.parent.mkdir(parents=True)
    source.write_bytes(backup.read_bytes())
    sig = {'schema': 'urban_material_parameters_v1', 'class': '/Script/Engine.MaterialInstanceConstant',
           'parent': ROOT + '/Materials/M_Base.M_Base', 'base': ROOT + '/Materials/M_Base.M_Base',
           'effective': {'scalar': {'roughness': 0.3}, 'vector': {'tint': [1.0, 0.5, 0.25, 1.0]},
                         'texture': {'base': ROOT + '/Textures/T_Base.T_Base'}, 'static_switch': {'use_color': True}},
           'parameter_arrays': {n: [] for n in m.URBAN_PARAMETER_ARRAYS},
           'base_property_overrides': '(bOverride_BlendMode=False)',
           'static_parameter_scope': m.URBAN_STATIC_PARAMETER_SCOPE,
           'static_switch_hierarchy': [
               {'material': '$SELF', 'kind': 'MaterialInstanceConstant',
                'values': {'use_color': {'value': True, 'overridden': False}}},
               {'material': ROOT + '/Materials/M_Base.M_Base', 'kind': 'Material',
                'values': {'use_color': {'value': True, 'overridden': False}}}]}
    sig['parameter_arrays']['scalar_parameter_values'] = ['(ParameterInfo=(Name=Roughness),ParameterValue=0.3)']
    original = {'schema': 'urban_original_material_signature_v1', 'success': True, 'root': ROOT,
                'baseline_sha256': m.sha(base_path), 'source': 'isolated_original_backup_project',
                'source_project': str(project), 'source_package_file': str(source),
                'original_backup_sha256': m.sha(backup), 'source_sha256_before': m.sha(backup),
                'source_sha256_after': m.sha(backup), 'saved_source_packages': [],
                'camera_render_started': False, 'object_path': OLD, 'material_signature': copy.deepcopy(sig)}
    original_path = tmp_path / 'urban_original_material_signature_v1.json'
    dump(original_path, original)
    moved = {'schema': 'urban_material_move_v1', 'success': True, 'rename_returned': True,
             'root': ROOT, 'destination': DEST, 'baseline_sha256': m.sha(base_path),
             'camera_render_started': False, 'method': 'UE EditorAssetSubsystem.rename_loaded_asset',
             'source_object_path': OLD, 'destination_object_path': NEW, 'dirty_after': [],
             'material_before': copy.deepcopy(sig), 'material_after': copy.deepcopy(sig)}
    move_path = tmp_path / 'urban_material_move_v1.json'
    dump(move_path, moved)
    actual = [dict(r, package=r['package'].replace(ROOT, DEST, 1),
                   name='MI_Ubc_Building' if r == old_record else r['name']) for r in rows]
    raw_maps = json.loads(json.dumps(maps).replace(OLD, ROOT + '/Materials/MI_Ubc_Building.MI_Ubc_Building')
                          .replace(ROOT, DEST))
    proof = {'schema': 'urban_material_relocation_v1', 'success': True, 'root': ROOT, 'destination': DEST,
             'baseline_sha256': m.sha(base_path), 'camera_render_started': False,
             'original_backup': {'path': str(backup), 'sha256': m.sha(backup)},
             'original_material_witness': {'path': str(original_path), 'sha256': m.sha(original_path)},
             'move_receipt': {'path': str(move_path), 'sha256': m.sha(move_path)},
             'current_material_signature': copy.deepcopy(sig), 'actual_assets': actual,
             'actual_maps': raw_maps, 'component_transforms': copy.deepcopy(relative), 'old_assets': [],
             'destination_dependencies': {r['package']: [] for r in actual}}
    return dict(base=base, base_path=base_path, backup=backup, source=source, original=original,
                original_path=original_path, moved=moved, move_path=move_path, proof=proof)


def validate(e):
    dump(m.RUN / 'urban_material_relocation_v1.json', e['proof'])
    return m.verification_asset_contract(ROOT, e['base_path'], e['base'])


def repin(e, kind):
    path = e[kind + '_path']
    dump(path, e['original' if kind == 'original' else 'moved'])
    e['proof']['original_material_witness' if kind == 'original' else 'move_receipt']['sha256'] = m.sha(path)


def test_production_pins():
    assert m.URBAN_BASELINE_SHA256 == '53308d60d3bd9cab47e0a3606c003a88d0248a6bdc34d12e2398995dfaa24a3f'
    assert m.URBAN_MATERIAL_BACKUP_SHA256 == '37b97ff708b16b6ef3f175b76aaf8ce6bf749c20e7bd1a5cbfe2163b2cd4abb7'


def test_complete_evidence_repairs_one_name_without_mutating_any_raw_records(evidence):
    original = copy.deepcopy(evidence)
    baseline_bytes = evidence['base_path'].read_bytes()
    expected, witness = validate(evidence)
    assert len(expected) == 486
    changes = [(a, b) for a, b in zip(evidence['base']['assets'], expected) if a != b]
    assert len(changes) == 1
    assert changes[0][1] == dict(changes[0][0], name='MI_Ubc_Building')
    assert evidence == original
    assert evidence['base_path'].read_bytes() == baseline_bytes
    assert witness['object_path_alias'] == {'old': OLD, 'new': NEW}
    assert len(witness) > 3


def test_missing_proof_keeps_exact_486_original_names(evidence):
    expected, witness = m.verification_asset_contract(ROOT, evidence['base_path'], evidence['base'])
    assert expected == evidence['base']['assets'] and witness is None


def test_other_scene_does_not_read_urban_proof(evidence):
    (m.RUN / 'urban_material_relocation_v1.json').write_text('{}')
    expected, witness = m.verification_asset_contract('/Game/Elsewhere', evidence['base_path'], evidence['base'])
    assert expected == evidence['base']['assets'] and witness is None


def test_alias_requires_validated_witness_and_does_not_modify_generic_canon(evidence):
    _, witness = validate(evidence)
    with pytest.raises(RuntimeError, match='validated witness'):
        m.urban_comparison_signature(NEW, dict(witness))
    assert m.canon(NEW, ROOT) == ROOT + '/Materials/MI_Ubc_Building.MI_Ubc_Building'
    assert m.urban_comparison_signature(NEW, witness) == OLD
    assert m.urban_comparison_signature(REAL.replace(ROOT, DEST), witness) == REAL
    assert m.urban_comparison_signature(NEW + ':Child', witness) != OLD
    assert m.urban_comparison_signature(NEW.replace('MI_Ubc_Building.', 'MI_Other.'), witness) != OLD


@pytest.mark.parametrize('field', ['schema', 'success', 'root', 'destination', 'baseline_sha256',
    'camera_render_started', 'original_backup', 'original_material_witness', 'move_receipt',
    'current_material_signature', 'actual_assets', 'actual_maps', 'component_transforms', 'old_assets',
    'destination_dependencies'])
def test_missing_proof_field_fails(evidence, field):
    del evidence['proof'][field]
    with pytest.raises(RuntimeError, match='Invalid UrbanJapan'):
        validate(evidence)


@pytest.mark.parametrize('mutation', ['source', 'backup', 'baseline', 'argument', 'original_pin', 'move_pin'])
def test_modified_files_or_baseline_argument_fail(evidence, mutation):
    if mutation in ('source', 'backup', 'baseline'):
        evidence['base_path' if mutation == 'baseline' else mutation].write_bytes(b'changed')
    elif mutation == 'argument': evidence['base']['maps'][0]['actor_count'] = 4
    else: evidence['proof']['original_material_witness' if mutation == 'original_pin' else 'move_receipt']['sha256'] = '0' * 64
    with pytest.raises(RuntimeError, match='Invalid UrbanJapan'):
        validate(evidence)


@pytest.mark.parametrize('field,value', [('success', 1), ('rename_returned', False),
    ('source_object_path', REAL), ('destination_object_path', REAL.replace(ROOT, DEST)),
    ('dirty_after', ['/Game/Unsaved']), ('method', 'Package.rename'), ('camera_render_started', True)])
def test_move_receipt_flags_never_replace_official_scope(evidence, field, value):
    evidence['moved'][field] = value
    repin(evidence, 'move')
    with pytest.raises(RuntimeError, match='Invalid UrbanJapan'):
        validate(evidence)


@pytest.mark.parametrize('field', ['parent', 'base', 'static_switch_hierarchy', 'static_parameter_scope', 'base_property_overrides',
                                 'parameter_arrays', 'effective'])
def test_incomplete_signature_rejected_even_if_all_four_match(evidence, field):
    for s in (evidence['original']['material_signature'], evidence['moved']['material_before'],
              evidence['moved']['material_after'], evidence['proof']['current_material_signature']):
        del s[field]
    repin(evidence, 'original')
    repin(evidence, 'move')
    with pytest.raises(RuntimeError, match='Invalid UrbanJapan'):
        validate(evidence)


@pytest.mark.parametrize('where', ['original', 'before', 'after', 'current'])
def test_each_independent_parameter_capture_is_compared(evidence, where):
    signatures = {'original': evidence['original']['material_signature'], 'before': evidence['moved']['material_before'],
                  'after': evidence['moved']['material_after'], 'current': evidence['proof']['current_material_signature']}
    signatures[where]['effective']['scalar']['roughness'] += 1e-7
    repin(evidence, 'original')
    repin(evidence, 'move')
    with pytest.raises(RuntimeError, match='material parameters differ'):
        validate(evidence)


@pytest.mark.parametrize('mutation', ['missing', 'extra', 'duplicate', 'wrong_name', 'wrong_class',
                                    'wrong_package', 'genuine_same_name_changed'])
def test_all_486_asset_identities_remain_exact(evidence, mutation):
    rows = evidence['proof']['actual_assets']
    if mutation == 'missing': rows.pop()
    elif mutation == 'extra': rows.append(dict(rows[-1], package=DEST + '/Meshes/Extra'))
    elif mutation == 'duplicate': rows[-1] = dict(rows[-2])
    elif mutation == 'wrong_name': rows[0]['name'] = 'MI_BuildingDetails05'
    elif mutation == 'wrong_class': rows[0]['class'] = '/Script/Engine.Material'
    elif mutation == 'wrong_package': rows[0]['package'] = DEST + '/Materials/Other'
    else: rows[1]['name'] = 'MI_Ubc_Building'
    with pytest.raises(RuntimeError, match='Invalid UrbanJapan'):
        validate(evidence)


@pytest.mark.parametrize('mutation', ['actor_transform', 'component_transform', 'mesh', 'genuine_material',
                                    'instance_count', 'actor_count', 'levels', 'missing_map', 'raw_old_map'])
def test_complete_maps_and_relative_transforms_remain_strict(evidence, mutation):
    maps = evidence['proof']['actual_maps']
    a, c = maps[0]['actors'][0], maps[0]['actors'][0]['components'][0]
    if mutation == 'actor_transform': a['transform'][0] += 1
    elif mutation == 'component_transform': evidence['proof']['component_transforms'][ROOT + '/Maps/Demonstration'][0]['components'][0]['transform'][0] += 1
    elif mutation == 'mesh': c['mesh'] = DEST + '/Meshes/Other.Other'
    elif mutation == 'genuine_material': c['materials'][1] = NEW
    elif mutation == 'instance_count': c['instances'] = 3
    elif mutation == 'actor_count': maps[0]['actor_count'] = 2
    elif mutation == 'levels': maps[0]['levels'] = []
    elif mutation == 'missing_map': maps.pop()
    else: maps[0]['map'] = ROOT + '/Maps/Demonstration'
    with pytest.raises(RuntimeError, match='Invalid UrbanJapan'):
        validate(evidence)


@pytest.mark.parametrize('mutation', ['old_asset', 'old_dependency', 'incomplete_dependencies'])
def test_old_root_reference_coverage(evidence, mutation):
    if mutation == 'old_asset': evidence['proof']['old_assets'] = [evidence['base']['assets'][0]]
    elif mutation == 'old_dependency': next(iter(evidence['proof']['destination_dependencies'].values())).append(ROOT + '/Materials/MI_Ubc_Building')
    else: evidence['proof']['destination_dependencies'].pop(next(iter(evidence['proof']['destination_dependencies'])))
    with pytest.raises(RuntimeError, match='Invalid UrbanJapan'):
        validate(evidence)


def capture_api(prefix=ROOT):
    class Base:
        def get_path_name(self): return prefix + '/Materials/M_Base.M_Base'
    class Export:
        def __init__(self, value): self.value = value
        def export_text(self): return self.value
    class MIC:
        def __init__(self):
            self.props = {name: [] for name in m.URBAN_PARAMETER_ARRAYS}
            self.props.update(parent=Base(), base_property_overrides=Export('(bOverride=False)'),
                user_scene_texture_overrides=[], lightmass_settings=Export('(EmissiveBoost=1.0)'),
                phys_material=None, phys_material_mask=None, subsurface_profile=None,
                nanite_override_material=Export('(OverrideMaterial=None)'))
            self.props['texture_parameter_values'] = [Export('(ParameterValue=Texture2D\'' + prefix + '/Textures/T.T\')')]
        def get_path_name(self): return NEW if prefix == DEST else OLD
        def get_editor_property(self, name): return self.props[name]
        def get_base_material(self): return self.props['parent']
    library = SimpleNamespace(
        get_scalar_parameter_names=lambda a: ['Roughness'],
        get_vector_parameter_names=lambda a: ['Tint'],
        get_texture_parameter_names=lambda a: ['Color'],
        get_static_switch_parameter_names=lambda a: ['Use_Color'],
        get_material_instance_scalar_parameter_value=lambda a, n: 0.3,
        get_material_instance_vector_parameter_value=lambda a, n: SimpleNamespace(r=1, g=0.5, b=0.25, a=1),
        get_material_instance_texture_parameter_value=lambda a, n: SimpleNamespace(get_path_name=lambda: prefix + '/Textures/T.T'),
        get_material_instance_static_switch_parameter_value=lambda a, n: True,
        is_material_instance_parameter_overridden=lambda a, n: isinstance(a, MIC),
        get_material_default_static_switch_parameter_value=lambda a, n: True)
    return SimpleNamespace(MaterialInstanceConstant=MIC, Material=Base, MaterialEditingLibrary=library), MIC()


def test_production_capture_uses_public_arrays_and_named_static_switches_only():
    original_u, original = capture_api()
    current_u, current = capture_api(DEST)
    left, right = m.urban_material_parameters(original_u, original), m.urban_material_parameters(current_u, current)
    assert left == right
    assert set(left['parameter_arrays']) == set(m.URBAN_PARAMETER_ARRAYS)
    assert 'static_parameters' not in left
    assert 'static_parameters_runtime' not in left['additional_properties']
    assert left['static_switch_hierarchy'][0]['values']['use_color']['overridden'] is True
    assert left['static_switch_hierarchy'][-1]['values']['use_color']['overridden'] is False
    assert DEST not in json.dumps(left)


@pytest.mark.parametrize('field', list(m.URBAN_PARAMETER_ARRAYS) + ['base_property_overrides', 'lightmass_settings'])
def test_capture_never_omits_failed_public_property(field):
    u, asset = capture_api()
    del asset.props[field]
    with pytest.raises(RuntimeError, match='no property was omitted'):
        m.urban_material_parameters(u, asset)


def test_static_override_and_parent_defaults_change_capture():
    u, asset = capture_api()
    before = m.urban_material_parameters(u, asset)
    u.MaterialEditingLibrary.is_material_instance_parameter_overridden = lambda a, n: False
    after = m.urban_material_parameters(u, asset)
    assert before != after
    u.MaterialEditingLibrary.get_material_default_static_switch_parameter_value = lambda a, n: False
    assert after != m.urban_material_parameters(u, asset)


def prepare_verify(e, monkeypatch):
    validate(e)
    monkeypatch.setattr(m, 'guard', lambda u: None)
    monkeypatch.setattr(m, 'dirty', lambda u: [])
    monkeypatch.setattr(m, 'loading_protocol', lambda: {'method': 'test'})
    monkeypatch.setattr(m, 'assets', lambda u, root: e['proof']['actual_assets'] if root == DEST else [])
    monkeypatch.setattr(m, 'asset_record', lambda a: dict(a))
    current = SimpleNamespace(get_path_name=lambda: NEW)
    subsystem = SimpleNamespace(load_asset=lambda p: current)
    u = SimpleNamespace(EditorAssetSubsystem=object(), get_editor_subsystem=lambda s: subsystem,
        EditorLoadingAndSavingUtils=SimpleNamespace(load_map=lambda p: True),
        AssetRegistryDependencyOptions=lambda **kwargs: None,
        AssetRegistryHelpers=SimpleNamespace(get_asset_registry=lambda: SimpleNamespace(
            get_dependencies=lambda p, opts: e['proof']['destination_dependencies'][p])))
    live_signature = copy.deepcopy(e['proof']['current_material_signature'])
    monkeypatch.setattr(m, 'urban_material_parameters', lambda u, a: copy.deepcopy(live_signature))
    calls = []
    def capture(u, path, root, legacy_materials=False):
        calls.append(root)
        return copy.deepcopy(e['proof']['actual_maps'][len(calls) - 1])
    monkeypatch.setattr(m, 'settled_signature', capture)
    monkeypatch.setattr(m, 'component_transforms', lambda u: copy.deepcopy(
        e['base']['component_transforms'][e['base']['maps'][len(calls) - 1]['map']]))
    return u, live_signature, calls


def test_verify_validates_witness_first_captures_raw_maps_and_retains_original_records(evidence, monkeypatch):
    u, _, calls = prepare_verify(evidence, monkeypatch)
    m.verify(u, ROOT, receipt_filename='verified_UrbanJapan_vtest.json')
    receipt = json.loads((m.RUN / 'verified_UrbanJapan_vtest.json').read_text())
    assert receipt['success'] is True
    assert calls == [DEST, DEST]
    assert receipt['raw_original_asset_records'] == evidence['base']['assets']
    assert receipt['raw_asset_records'] == evidence['proof']['actual_assets']
    assert receipt['maps'] == evidence['proof']['actual_maps']
    assert receipt['maps'][0]['actors'][0]['components'][0]['materials'] == [NEW, REAL.replace(ROOT, DEST)]
    assert receipt['material_relocation_witness']['object_path_alias'] == {'old': OLD, 'new': NEW}
    assert receipt['redirector_retirement_witness'] is None and receipt['retired_redirectors'] == []
    assert receipt['original_asset_count'] == receipt['asset_count'] == 486


def test_verify_rechecks_live_material_after_proof(evidence, monkeypatch):
    u, live, calls = prepare_verify(evidence, monkeypatch)
    live['effective']['scalar']['roughness'] += 0.01
    with pytest.raises(RuntimeError, match='changed since validated'):
        m.verify(u, ROOT, receipt_filename='verified_UrbanJapan_vtest.json')
    assert calls == []


def test_verify_without_proof_never_repairs_name_or_activates_path_alias(evidence, monkeypatch):
    u, _, calls = prepare_verify(evidence, monkeypatch)
    (m.RUN / 'urban_material_relocation_v1.json').unlink()
    with pytest.raises(RuntimeError, match='identity/class set differs'):
        m.verify(u, ROOT, receipt_filename='verified_UrbanJapan_vtest.json')
    assert calls == []
