import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import types

import pytest

SPEC = importlib.util.spec_from_file_location('skin_experiment', Path(__file__).parents[1] / 'cc_skin_detail_experiment_v1.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def material_snapshot(skin_value=0, support_value=0):
    def row(name, value):
        return {'owner': 'avatar', 'mesh': 'CC_Base_Body', 'material': name,
                'component_source': 'owner', 'properties': {'roughness': value},
                'shader_parameters': {}, 'textures': {}}
    return {'materials': [row('Std_Skin_Head', skin_value), row('Std_Eyelash', support_value)],
            'scope': 'standard channels'}


@pytest.fixture
def environment(tmp_path, monkeypatch):
    run, stage = tmp_path / 'run', tmp_path / 'stage'
    run.mkdir()
    stage.mkdir()
    source = stage / 'source.ccProject'
    source.write_bytes(b'original')
    skin = tmp_path / 'candidate.ccSkin'
    skin.write_bytes(b'candidate skin')
    output = run / 'case'
    monkeypatch.setattr(MODULE, 'RUN_ROOT', str(run))
    monkeypatch.setattr(MODULE, 'STAGE_ROOT', str(stage))
    state = {'skin': 0, 'support': 0, 'geometry': True, 'skin_calls': 0, 'load_calls': 0, 'save_calls': 0}
    config = {'mode': 'C_skin_only', 'character_id': 'TEST',
              'source_project': {'path': str(source), 'sha256': sha(source)},
              'skin_asset': {'slot': 'skin', 'path': str(skin), 'sha256': sha(skin)}}
    avatar = types.SimpleNamespace(GetSubdivMeshLevel=lambda: 0)

    def load(path, label):
        state['load_calls'] += 1
        state['skin'] = 0
        return True, []

    def apply(path, label):
        state['skin_calls'] += 1
        state['skin'] = 1
        return True, []

    def save(path):
        state['save_calls'] += 1
        Path(path).write_bytes(b'isolated output')
        return True

    def write(data, path):
        Path(path).write_text(json.dumps(data), encoding='utf-8')

    def checked(label, status):
        if not status:
            raise ValueError(label)

    api = types.SimpleNamespace(sha256_file=sha, now=lambda: 'test-time', write_json=write,
        load_file_with_optional_undo_warning=load, load_file_with_skin_material_dialog=apply,
        force_avatar_scene_evaluation=lambda a: None, checked=checked,
        QtWidgets=types.SimpleNamespace(QApplication=types.SimpleNamespace(processEvents=lambda: None)),
        RLPy=types.SimpleNamespace(RScene=types.SimpleNamespace(GetAvatars=lambda: [avatar], SelectObject=lambda a: None),
                                  RFileIO=types.SimpleNamespace(SaveProject=save)))
    geometry = {'meshes': [{'name': n} for n in ('CC_Base_Body', 'CC_Base_Eye', 'CC_Base_Teeth', 'CC_Base_Tongue')]}
    helpers = types.SimpleNamespace(capture_geometry=lambda a, api: geometry,
                                   compare_geometry=lambda a, b: {'passed': state['geometry'], 'tolerance_mm': .002})
    monkeypatch.setattr(MODULE, 'helper', lambda: helpers)
    monkeypatch.setattr(MODULE, 'capture_materials', lambda a, path, api: material_snapshot(state['skin'], state['support']))
    return config, str(output), api, state, source


def test_c_applies_only_skin_and_saves_independent_project(environment):
    config, output, api, state, source = environment
    result = MODULE.run({'skin_detail_experiment': config}, output, lambda _: None, api)
    assert result['success'] and result['source_unchanged']
    assert state['skin_calls'] == 1 and state['save_calls'] == 1
    assert source.read_bytes() == b'original'
    assert len(result['geometry_checks']) == 3
    assert result['material_preservation']['skin_changed']


def test_a_never_calls_skin_application(environment):
    config, output, api, state, _ = environment
    config['mode'] = 'A_capture'
    del config['skin_asset']
    result = MODULE.run({'skin_detail_experiment': config}, output, lambda _: None, api)
    assert result['success'] and state['skin_calls'] == 0
    assert not result['material_preservation']['skin_changed']


def test_geometry_failure_stops_save_and_restores_input(environment):
    config, output, api, state, _ = environment
    state['geometry'] = False
    result = MODULE.run({'skin_detail_experiment': config}, output, lambda _: None, api)
    assert not result['success'] and state['save_calls'] == 0
    assert result['recovery']['status'] == 'restored_input'
    assert state['load_calls'] == 2


def test_new_run_cannot_overwrite_receipt(environment):
    config, output, api, _, _ = environment
    Path(output).mkdir()
    Path(output, 'skin_experiment_report.json').write_text('{}')
    with pytest.raises(ValueError, match='rerun'):
        MODULE.validate_config(config, output, api)


def test_source_must_be_independent_and_sha_bound(environment, tmp_path):
    config, output, api, _, source = environment
    source.write_bytes(b'changed')
    with pytest.raises(ValueError, match='SHA'):
        MODULE.validate_config(config, output, api)
    config['source_project'] = {'path': str(tmp_path / 'official.ccProject'), 'sha256': 'bad'}
    with pytest.raises(ValueError, match='independent'):
        MODULE.validate_config(config, output, api)


def test_skin_change_allowed_but_support_and_slot_changes_rejected():
    before = material_snapshot()
    assert MODULE.compare_materials(before, material_snapshot(1), None)['passed']
    assert not MODULE.compare_materials(before, material_snapshot(1, 2), None)['passed']
    assert not MODULE.compare_materials(before, material_snapshot(1), None, protect_skin=True)['passed']
    after = material_snapshot(1)
    after['materials'].pop()
    assert not MODULE.compare_materials(before, after, None)['passed']


def test_restore_rejects_parameter_changes_before_texture_writes(monkeypatch):
    monkeypatch.setattr(MODULE, 'material_owners', lambda avatar: [])
    before, after = material_snapshot(), material_snapshot(1, 2)
    comparison = MODULE.compare_materials(before, after, None)
    api = types.SimpleNamespace(MATERIAL_TEXTURE_CHANNELS=[])
    with pytest.raises(ValueError, match='shader/parameter'):
        MODULE.restore_support_textures(None, before, after, comparison, api, 'unused')


def test_texture_only_restoration_uses_original_png(monkeypatch, tmp_path):
    path = tmp_path / 'original.png'
    path.write_bytes(b'original pixels')
    before = material_snapshot()
    record = {'path': str(path), 'sha256': sha(path)}
    before['materials'][1]['textures']['diffuse'] = record
    after = copy.deepcopy(before)
    after['materials'][1]['textures']['diffuse']['sha256'] = 'changed'
    changes = {'differences': [{'key': ['avatar', 'CC_Base_Body', 'Std_Eyelash'], 'changed': ['texture:diffuse']}]}
    calls = []
    class Readback:
        def GetWidth(self): return 1
        def GetHeight(self): return 1
        def SaveFile(self, target):
            Path(target).write_bytes(path.read_bytes())
            return True
    component = types.SimpleNamespace(LoadImageToTexture=lambda *args: calls.append(args) or True,
                                      GetImage=lambda *args: Readback())
    monkeypatch.setattr(MODULE, 'material_owners', lambda avatar: [(object(), 'avatar')])
    monkeypatch.setattr(MODULE, 'helper', lambda: types.SimpleNamespace(compare_png_images=lambda a, b, api: {
        'rgba_pixels_equal': Path(a).read_bytes() == Path(b).read_bytes()}))
    api = types.SimpleNamespace(MATERIAL_TEXTURE_CHANNELS=[('diffuse', 'Diffuse')],
                                RLPy=types.SimpleNamespace(Diffuse=7), sha256_file=sha,
                                hair_material_component=lambda a, b: (component, 'owner'),
                                checked=lambda label, status: None,
                                write_json=lambda data, target: Path(target).write_text(json.dumps(data)))
    result = MODULE.restore_support_textures(None, before, after, changes, api, str(tmp_path / 'readback'))
    assert len(result) == 1
    assert calls == [('CC_Base_Body', 'Std_Eyelash', 7, str(path))]


def test_capture_deduplicates_sdk_names_within_owner_only(monkeypatch, tmp_path):
    class Image:
        def GetWidth(self): return 2
        def GetHeight(self): return 2
        def SaveFile(self, path):
            Path(path).write_bytes(b'pixels')
            return True

    materials = list(MODULE.SKIN_MATERIALS) + ['Std_Eyelash']
    component = types.SimpleNamespace(GetMaterialNames=lambda mesh: materials + materials,
        GetShaderParameterNames=lambda mesh, material: [], GetImage=lambda *args: Image())
    owner = types.SimpleNamespace(GetMeshNames=lambda: ['CC_Base_Body', 'CC_Base_Body'])
    monkeypatch.setattr(MODULE, 'material_owners', lambda avatar: [(owner, 'avatar'), (owner, 'avatar/part:other')])
    api = types.SimpleNamespace(MATERIAL_TEXTURE_CHANNELS=[('diffuse', 'Diffuse')],
        RLPy=types.SimpleNamespace(Diffuse=7), sha256_file=sha,
        hair_material_component=lambda a, b: (component, 'owner'),
        material_call=lambda *args: 0, checked=lambda label, status: None,
        write_json=lambda data, path: Path(path).write_text(json.dumps(data)))
    result = MODULE.capture_materials(owner, str(tmp_path / 'capture'), api)
    keys = [(r['owner'], r['mesh'], r['material']) for r in result['materials']]
    assert len(keys) == len(set(keys)) == 10
    assert {k[0] for k in keys} == {'avatar', 'avatar/part:other'}
    assert len(result['sdk_duplicate_name_observations']) == 4
    assert MODULE.compare_materials(result, result, api, protect_skin=True)['passed']


@pytest.mark.parametrize('readback_ok', [True, False])
def test_restoration_uses_load_semantics_and_stops_on_wrong_pixels(monkeypatch, tmp_path, readback_ok):
    before, after = material_snapshot(), material_snapshot()
    for channel in ('diffuse', 'bump', 'roughness'):
        path = tmp_path / (channel + '.png')
        path.write_bytes(channel.encode())
        before['materials'][1]['textures'][channel] = {'path': str(path), 'sha256': sha(path)}
    after = copy.deepcopy(before)
    comparison = {'differences': [{'key': ['avatar', 'CC_Base_Body', 'Std_Eyelash'],
                                  'changed': ['texture:diffuse', 'texture:bump', 'texture:roughness']}]}
    calls, current_data = [], {}
    class Readback:
        def __init__(self, data): self.data = data
        def GetWidth(self): return 1
        def GetHeight(self): return 1
        def SaveFile(self, path):
            Path(path).write_bytes(self.data)
            return True
    def load(mesh, material, enum, path):
        calls.append(enum)
        # Read API enums differ from write API enums for these two channels.
        read_enum = {30: 3, 40: 4, 1: 1}[enum]
        current_data[read_enum] = Path(path).read_bytes() if readback_ok or enum != 40 else b'inverted'
        return True
    component = types.SimpleNamespace(LoadImageToTexture=load, GetImage=lambda mesh, material, enum: Readback(current_data[enum]))
    monkeypatch.setattr(MODULE, 'material_owners', lambda avatar: [(object(), 'avatar')])
    monkeypatch.setattr(MODULE, 'looks_like_normal_map', lambda path, api: True)
    monkeypatch.setattr(MODULE, 'helper', lambda: types.SimpleNamespace(compare_png_images=lambda a, b, api: {
        'rgba_pixels_equal': Path(a).read_bytes() == Path(b).read_bytes()}))
    api = types.SimpleNamespace(MATERIAL_TEXTURE_CHANNELS=[('diffuse', 'Diffuse'), ('bump', 'Bump'), ('roughness', 'Roughness')],
        RLPy=types.SimpleNamespace(Diffuse=1, Bump=3, Roughness=4,
                                  EMaterialTextureChannel_Normal=30, EMaterialTextureChannel_Shininess=40),
        sha256_file=sha, hair_material_component=lambda a, b: (component, 'owner'),
        checked=lambda label, status: None,
        write_json=lambda data, path: Path(path).write_text(json.dumps(data)))
    output = str(tmp_path / 'immediate_readbacks')
    if readback_ok:
        result = MODULE.restore_support_textures(None, before, after, comparison, api, output)
        assert calls == [30, 40, 1]  # Diffuse is last.
        assert all(row['passed'] for row in result)
    else:
        with pytest.raises(ValueError, match='readback differs'):
            MODULE.restore_support_textures(None, before, after, comparison, api, output)
        assert calls == [30, 40]  # Do not continue even to Diffuse after failure.
        evidence = json.loads(Path(output, 'support_restore_readbacks.json').read_text())
        assert not evidence['passed']
        assert not evidence['writes'][-1]['pixel_comparison']['rgba_pixels_equal']


def test_capture_classifies_known_warning_as_missing(monkeypatch, tmp_path):
    warning_sha = hashlib.sha256(b'warning').hexdigest()
    monkeypatch.setattr(MODULE, 'MISSING_TEXTURE_SHA256', {warning_sha})
    class Image:
        def __init__(self, data): self.data = data
        def GetWidth(self): return 616 if self.data == b'warning' else 2
        def GetHeight(self): return self.GetWidth()
        def SaveFile(self, path):
            Path(path).write_bytes(self.data)
            return True
    component = types.SimpleNamespace(GetMaterialNames=lambda mesh: list(MODULE.SKIN_MATERIALS) + ['Std_Eyelash'],
        GetShaderParameterNames=lambda *args: [], GetImage=lambda mesh, material, channel: Image(b'warning' if channel == 2 else b'valid'))
    owner = types.SimpleNamespace(GetMeshNames=lambda: ['CC_Base_Body'])
    monkeypatch.setattr(MODULE, 'material_owners', lambda a: [(owner, 'avatar')])
    api = types.SimpleNamespace(MATERIAL_TEXTURE_CHANNELS=[('diffuse', 'Diffuse'), ('roughness', 'Roughness')],
        RLPy=types.SimpleNamespace(Diffuse=1, Roughness=2), sha256_file=sha,
        hair_material_component=lambda a, b: (component, 'owner'), material_call=lambda *args: 0,
        checked=lambda label, status: None, write_json=lambda data, path: Path(path).write_text(json.dumps(data)))
    result = MODULE.capture_materials(owner, str(tmp_path / 'capture'), api)
    for row in result['materials']:
        assert set(row['textures']) == {'diffuse'}
        assert row['missing_textures']['roughness']['evidence']['sha256'] == warning_sha
    assert MODULE.compare_materials(result, result, api, protect_skin=True)['passed']


@pytest.mark.parametrize('removal_works', [True, False])
def test_restore_missing_removes_texture_never_loads_warning(monkeypatch, tmp_path, removal_works):
    warning_sha = hashlib.sha256(b'warning').hexdigest()
    monkeypatch.setattr(MODULE, 'MISSING_TEXTURE_SHA256', {warning_sha})
    before, after = material_snapshot(), material_snapshot()
    before['materials'][1]['missing_textures'] = {'roughness': {'reason': 'sdk_known_warning_image'}}
    after['materials'][1]['textures']['roughness'] = {'path': 'not-read.png', 'sha256': 'valid'}
    after['materials'][1]['missing_textures'] = {}
    comparison = MODULE.compare_materials(before, after, None)
    assert not comparison['passed']
    calls = []
    class Image:
        def GetWidth(self): return 616
        def GetHeight(self): return 616
        def SaveFile(self, path):
            Path(path).write_bytes(b'warning' if removal_works else b'still-valid-texture')
            return True
    component = types.SimpleNamespace(RemoveMaterialTexture=lambda *args: calls.append(args) or True,
        LoadImageToTexture=lambda *args: pytest.fail('Never load the missing-texture graphic'), GetImage=lambda *args: Image())
    monkeypatch.setattr(MODULE, 'material_owners', lambda a: [(object(), 'avatar')])
    api = types.SimpleNamespace(MATERIAL_TEXTURE_CHANNELS=[('roughness', 'Roughness')],
        RLPy=types.SimpleNamespace(Roughness=4, EMaterialTextureChannel_Shininess=40),
        sha256_file=sha, hair_material_component=lambda a, b: (component, 'owner'),
        checked=lambda label, status: None, write_json=lambda data, path: Path(path).write_text(json.dumps(data)))
    output = str(tmp_path / 'readbacks')
    if removal_works:
        result = MODULE.restore_support_textures(None, before, after, comparison, api, output)
        assert result[0]['operation'] == 'remove_to_restore_missing'
        assert result[0]['passed'] and result[0]['missing_after_remove']
    else:
        with pytest.raises(ValueError, match='readback differs'):
            MODULE.restore_support_textures(None, before, after, comparison, api, output)
    assert calls == [('CC_Base_Body', 'Std_Eyelash', 40)]
