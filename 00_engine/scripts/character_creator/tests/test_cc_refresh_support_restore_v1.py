import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parents[1] / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = load('cc_refresh_material_pixels_v1')
EXPORTER = load('cc_skin_detail_experiment_v1')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, 'cc_skin_detail_experiment_v1', EXPORTER)
    warning = tmp_path / 'warning.png'
    warning.write_bytes(b'warning')
    monkeypatch.setattr(EXPORTER, 'MISSING_TEXTURE_SHA256', {sha(warning)})
    state = {'normal': True, 'failed_remove': False}
    monkeypatch.setattr(EXPORTER, 'looks_like_normal_map', lambda *args: state['normal'])
    monkeypatch.setattr(EXPORTER, 'helper', lambda: SimpleNamespace(compare_png_images=lambda a, b, api:
        {'rgba_pixels_equal': Path(a).read_bytes() == Path(b).read_bytes()}))
    channels = {'diffuse': ('EMaterialTextureChannel_Diffuse', 1), 'bump': ('EMaterialTextureChannel_Bump', 3),
                'roughness': ('EMaterialTextureChannel_Roughness', 4), 'metallic': ('EMaterialTextureChannel_Metallic', 5),
                'opacity': ('EMaterialTextureChannel_Opacity', 6)}
    constants = {name: value for name, value in channels.values()}
    constants.update(EMaterialTextureChannel_Normal=30, EMaterialTextureChannel_Shininess=40)
    rows = {}
    for mesh, material, channel in MODULE.RESTORE_OPERATIONS:
        key = ('avatar', mesh, material)
        rows.setdefault(key, {'owner': 'avatar', 'mesh': mesh, 'material': material,
            'properties': {'GetShader': 'shader'}, 'textures': {}, 'missing_textures': {}})
        operation, enum = MODULE.RESTORE_OPERATIONS[(mesh, material, channel)]
        if operation == 'load_original_texture':
            path = tmp_path / (material + '_' + channel + '.png')
            path.write_bytes((material + channel).encode())
            rows[key]['textures'][channel] = {'path': str(path), 'sha256': sha(path), 'file_decoded': True, 'width': 2, 'height': 2}
        else:
            rows[key]['missing_textures'][channel] = {'reason': 'sdk_known_warning_image',
                'evidence': {'path': str(warning), 'sha256': sha(warning)}}
    before = {'materials': list(rows.values()), 'pixel_capture_complete': True}
    after = copy.deepcopy(before)
    current, differences = {}, []
    for row in after['materials']:
        for mesh, material, channel in MODULE.RESTORE_OPERATIONS:
            if (row['mesh'], row['material']) != (mesh, material):
                continue
            enum = channels[channel][1]
            data = b'after_skin'
            current[(mesh, material, enum)] = data
            if channel in row['textures']:
                row['textures'][channel] = {'path': str(warning), 'sha256': sha(warning), 'file_decoded': True}
            else:
                row['missing_textures'].pop(channel)
                row['textures'][channel] = {'path': str(warning), 'sha256': sha(warning), 'file_decoded': True}
            differences.append({'key': ['avatar', mesh, material], 'channel': channel,
                                'reason': 'protected_channel_availability_changed'})
    proof = tmp_path / 'real_receipt.json'
    proof.write_text(json.dumps({'passed': True, 'writes': [{'key': ['avatar', mesh, material],
        'channel': channel, 'operation': operation, 'load_constant': constant,
        'passed': True, 'missing_after_remove': True if operation.startswith('remove') else None}
        for (mesh, material, channel), (operation, constant) in MODULE.RESTORE_OPERATIONS.items()]}), encoding='utf-8')
    monkeypatch.setattr(MODULE, 'RESTORE_EVIDENCE', ({'path': str(proof), 'sha256': sha(proof)},))
    calls = []

    class Image:
        def __init__(self, data): self.data = data
        def GetWidth(self): return 2
        def GetHeight(self): return 2
        def SaveFile(self, path): Path(path).write_bytes(self.data); return True

    def load_image(mesh, material, enum, path):
        calls.append(('load', mesh, material, enum, path))
        current[(mesh, material, {30: 3, 40: 4}.get(enum, enum))] = Path(path).read_bytes()
        return True

    def remove(mesh, material, enum):
        calls.append(('remove', mesh, material, enum))
        if not ((state['failed_remove'] and enum == 40) or state.get('failed_enum') == enum):
            current[(mesh, material, {40: 4}.get(enum, enum))] = None
        return True

    component = SimpleNamespace(LoadImageToTexture=load_image, RemoveMaterialTexture=remove,
        GetImage=lambda mesh, material, enum: Image(current[(mesh, material, enum)]) if current[(mesh, material, enum)] is not None else None)
    avatar = SimpleNamespace(GetID=lambda: 1, GetHairs=lambda: [], GetAvatarParts=lambda: [])
    api = SimpleNamespace(sha256_file=sha, RLPy=SimpleNamespace(**constants),
        MATERIAL_TEXTURE_CHANNELS=[(name, constant) for name, (constant, _) in channels.items()],
        hair_material_component=lambda *args: (component, 'owner'), checked=lambda *args: None,
        write_json=lambda data, path: Path(path).write_text(json.dumps(data), encoding='utf-8'))
    return avatar, before, after, {'differences': differences}, api, calls, state, proof


@pytest.fixture
def closed(env):
    avatar, before, _, _, api, calls, state, proof = env
    lash = next(row for row in before['materials'] if row['material'] == 'Std_Eyelash')
    lash['missing_textures']['ambient_occlusion'] = copy.deepcopy(lash['missing_textures']['roughness'])
    after = copy.deepcopy(before)
    target = next(row for row in after['materials'] if row['material'] == 'Std_Eyelash')
    for channel in ('ambient_occlusion', 'roughness'):
        target['missing_textures'].pop(channel)
        target['textures'][channel] = copy.deepcopy(lash['textures']['bump'])
    target['textures'].pop('bump')
    target['missing_textures']['bump'] = copy.deepcopy(lash['missing_textures']['roughness'])
    api.RLPy.EMaterialTextureChannel_AmbientOcclusion = 7
    api.MATERIAL_TEXTURE_CHANNELS.append(('ambient_occlusion', 'EMaterialTextureChannel_AmbientOcclusion'))
    differences = {'differences': [{'key': ['avatar', 'CC_Base_Body', 'Std_Eyelash'], 'channel': name,
        'reason': 'protected_channel_availability_changed'} for name in ('ambient_occlusion', 'bump', 'roughness')]}
    return avatar, before, after, differences, api, calls, state, proof


def test_post_close_restore_only_three_measured_lash_slots_and_marks_ao_first_verification(closed, tmp_path):
    avatar, before, after, differences, api, calls, _, _ = closed
    result = MODULE.restore_closed_lash_support(avatar, before, after, differences, api, str(tmp_path / 'closed'))
    assert result['passed'] and len(calls) == 3
    assert [(call[0], call[3]) for call in calls] == [('remove', 7), ('load', 30), ('remove', 40)]
    plan = json.loads(Path(result['plan_path']).read_text())
    assert plan['actions'][0]['first_real_verification_required']
    assert not plan['actions'][0]['retained_real_operation_proof']
    assert all(row['retained_real_operation_proof'] for row in plan['actions'][1:])


@pytest.mark.parametrize('failure', ['unrelated_diffuse', 'missing_provenance', 'incomplete_capture', 'wrong_shader', 'not_normal'])
def test_post_close_restore_rejects_unknown_change_before_writes(closed, tmp_path, failure):
    avatar, before, after, differences, api, calls, state, _ = closed
    if failure == 'unrelated_diffuse': differences['differences'][0]['channel'] = 'diffuse'
    elif failure == 'missing_provenance': before['materials'][0]['missing_textures']['ambient_occlusion']['reason'] = 'unknown'
    elif failure == 'incomplete_capture': after['pixel_capture_complete'] = False
    elif failure == 'wrong_shader': after['materials'][0]['properties']['GetShader'] = 'different'
    else: state['normal'] = False
    with pytest.raises(ValueError):
        MODULE.restore_closed_lash_support(avatar, before, after, differences, api, str(tmp_path / 'closed'))
    assert not calls


def test_post_close_ao_remove_failed_readback_stops_before_normal_load(closed, tmp_path, monkeypatch):
    avatar, before, after, differences, api, calls, state, _ = closed
    component, _ = api.hair_material_component(None, None)
    original = component.GetImage
    class StillThere:
        def GetWidth(self): return 2
        def GetHeight(self): return 2
        def SaveFile(self, path): Path(path).write_bytes(b'unremoved AO'); return True
    component.GetImage = lambda mesh, material, enum: StillThere() if enum == 7 else original(mesh, material, enum)
    with pytest.raises(ValueError, match='readback differs'):
        MODULE.restore_closed_lash_support(avatar, before, after, differences, api, str(tmp_path / 'closed'))
    assert len(calls) == 1 and calls[0][3] == 7


def test_evidenced_restore_uses_normal_and_proved_remove_slots_without_loading_warning(env, tmp_path):
    avatar, before, after, differences, api, calls, _, _ = env
    result = MODULE.restore_evidenced_support(avatar, before, after, differences, api, str(tmp_path / 'restore'))
    assert result['passed'] and len(result['writes']) == 8
    assert any(call[:4] == ('load', 'CC_Base_Body', 'Std_Eyelash', 30) for call in calls)
    assert not any(call[0] == 'load' and call[3] == 3 for call in calls)
    assert any(call[:4] == ('remove', 'CC_Base_Body', 'Std_Eyelash', 40) for call in calls)
    assert any(call[:4] == ('remove', 'CC_Base_Tongue', 'Std_Tongue', 3) for call in calls)
    assert all(Path(call[4]).read_bytes() != b'warning' for call in calls if call[0] == 'load')


@pytest.mark.parametrize('failure', ['normal_semantic', 'unknown_difference', 'changed_evidence', 'warning_source', 'unknown_missing'])
def test_preflight_rejects_unsupported_or_untrusted_restore_before_any_write(env, tmp_path, failure):
    avatar, before, after, differences, api, calls, state, proof = env
    if failure == 'normal_semantic': state['normal'] = False
    elif failure == 'unknown_difference': differences['differences'][0]['channel'] = 'ambient_occlusion'
    elif failure == 'changed_evidence': proof.write_bytes(b'changed')
    elif failure == 'warning_source':
        row = next(row for row in before['materials'] if row['material'] == 'Std_Eyelash')
        row['textures']['bump'] = dict(row['missing_textures']['metallic']['evidence'], file_decoded=True)
    else:
        row = next(row for row in before['materials'] if row['material'] == 'Std_Eyelash')
        row['missing_textures']['roughness']['reason'] = 'unknown'
    with pytest.raises(ValueError):
        MODULE.restore_evidenced_support(avatar, before, after, differences, api, str(tmp_path / 'restore'))
    assert calls == []


def test_clear_readback_failure_stops_before_later_diffuse_writes(env, tmp_path):
    avatar, before, after, differences, api, calls, state, _ = env
    state['failed_remove'] = True
    with pytest.raises(ValueError, match='readback differs'):
        MODULE.restore_evidenced_support(avatar, before, after, differences, api, str(tmp_path / 'restore'))
    assert not any(call[0] == 'load' and call[3] == 1 for call in calls)
    receipt = json.loads((tmp_path / 'restore/readbacks/support_restore_readbacks.json').read_text())
    assert not receipt['passed'] and receipt['writes'][-1]['missing_after_remove'] is False
