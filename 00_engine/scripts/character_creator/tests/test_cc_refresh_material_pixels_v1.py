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
def environment(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, 'cc_skin_detail_experiment_v1', EXPORTER)
    monkeypatch.setattr(EXPORTER, 'MISSING_TEXTURE_SHA256', {hashlib.sha256(b'warning').hexdigest()})
    meshes = {'CC_Base_Body': sorted(MODULE.SKINS) + ['Std_Eyelash', 'Std_Nails']}
    meshes.update({mesh: ['Support'] for mesh in MODULE.SUPPORT_MESHES})
    state = {'metadata_error': False, 'bad_decode': False, 'get_qimage_calls': 0, 'material_writes': 0}

    class Image:
        def __init__(self, data):
            self.data = data

        def GetWidth(self):
            return 616 if self.data == b'warning' else 2

        def GetHeight(self):
            return self.GetWidth()

        def SaveFile(self, path):
            Path(path).write_bytes(self.data)
            return True

        def GetQImage(self):
            state['get_qimage_calls'] += 1
            raise AssertionError('Unbound SDK GetQImage must not be used')

    class Decoder:
        def __init__(self, path):
            self.data = Path(path).read_bytes()

        def isNull(self):
            return self.data == b'bad'

        def width(self):
            return 2

        def height(self):
            return 2

    def image(mesh, material, channel):
        if channel == 'opacity':
            return Image(b'warning')
        if state['bad_decode'] and mesh == 'CC_Base_Tongue' and channel == 'diffuse':
            return Image(b'bad')
        return Image((mesh + material + channel).encode())

    def material_call(component, method, *args):
        if state['metadata_error'] and method == 'GetGlossinessWeight':
            raise ValueError('Metadata getter unavailable')
        return 'metadata'

    component = SimpleNamespace(GetMaterialNames=lambda mesh: meshes[mesh],
        GetShaderParameterNames=lambda *args: [], GetImage=image)
    owner = SimpleNamespace(GetMeshNames=lambda: list(meshes), GetHairs=lambda: [], GetAvatarParts=lambda: [], GetID=lambda: 1)
    api = SimpleNamespace(MATERIAL_TEXTURE_CHANNELS=[(name, name) for name in MODULE.CHANNELS | {'glow'}],
        RLPy=SimpleNamespace(**{name: name for name in MODULE.CHANNELS | {'glow'}}),
        QtGui=SimpleNamespace(QImage=Decoder), material_call=material_call,
        hair_material_component=lambda *args: (component, 'owner'), checked=lambda *args: None,
        sha256_file=sha, write_json=lambda value, path: Path(path).write_text(json.dumps(value), encoding='utf-8'))
    monkeypatch.setitem(sys.modules, 'cc_repair_headshot_support_materials_v1', SimpleNamespace(
        compare_png_images=lambda left, right, api: {'rgba_pixels_equal': Path(left).read_bytes() == Path(right).read_bytes()}))
    return owner, api, state


def test_scoped_savefile_capture_decodes_pixels_classifies_warning_and_deduplicates_checkpoints(environment, tmp_path):
    owner, api, state = environment
    first = MODULE.capture_stage(owner, str(tmp_path), 'source', api)
    count = len(list((tmp_path / 'pixel_objects').glob('*.png')))
    second = MODULE.capture_stage(owner, str(tmp_path), 'after_skin', api)
    assert first['pixel_capture_complete'] and second['pixel_capture_complete']
    assert len(list((tmp_path / 'pixel_objects').glob('*.png'))) == count
    assert state['get_qimage_calls'] == state['material_writes'] == 0
    assert all(row['material'] != 'Std_Nails' for row in first['materials'])
    assert all('opacity' in row['missing_textures'] and 'opacity' not in row['textures'] for row in first['materials'])
    assert MODULE.compare_pixels(first, second, api)['passed']
    with pytest.raises(ValueError, match='reuse'):
        MODULE.capture_stage(owner, str(tmp_path), 'source', api)


def test_metadata_getter_error_is_recorded_without_invalidating_good_real_pixels(environment, tmp_path):
    owner, api, state = environment
    state['metadata_error'] = True
    result = MODULE.capture_stage(owner, str(tmp_path), 'source', api)
    assert result['pixel_capture_complete']
    assert result['metadata_observation_errors'] and result['capture_exception']
    assert not result['texture_observation_errors']


def test_undecodable_map_is_incomplete_not_a_preserved_pixel_claim(environment, tmp_path):
    owner, api, state = environment
    state['bad_decode'] = True
    result = MODULE.capture_stage(owner, str(tmp_path), 'source', api)
    assert not result['pixel_capture_complete'] and result['decode_errors']


def test_authorized_eye_change_does_not_authorize_tearline_or_tongue_changes(environment, tmp_path):
    owner, api, _ = environment
    before = MODULE.capture_stage(owner, str(tmp_path), 'source', api)
    after = copy.deepcopy(before)
    altered = tmp_path / 'altered.png'
    altered.write_bytes(b'changed pixels')

    def change(mesh):
        row = next(row for row in after['materials'] if row['mesh'] == mesh)
        row['textures']['diffuse'].update(path=str(altered), sha256=sha(altered))

    change('CC_Base_Eye')
    assert not MODULE.compare_pixels(before, after, api)['passed']
    assert MODULE.compare_pixels(before, after, api, allow_eye_changes=True)['passed']
    change('CC_Base_TearLine')
    result = MODULE.compare_pixels(before, after, api, allow_eye_changes=True)
    assert not result['passed'] and result['differences'][0]['reason'] == 'protected_rgba_pixels_changed'


def test_missing_original_support_map_and_metadata_difference_are_distinguished(environment, tmp_path):
    owner, api, _ = environment
    before = MODULE.capture_stage(owner, str(tmp_path), 'source', api)
    after = copy.deepcopy(before)
    after['materials'][0]['properties'] = {'shader_metadata_changed': True}
    assert MODULE.compare_pixels(before, after, api)['passed']
    assert MODULE.compare_pixels(before, after, api)['metadata_changes_observed_not_rejected']
    tongue = next(row for row in after['materials'] if row['mesh'] == 'CC_Base_Tongue')
    tongue['textures'].pop('diffuse')
    tongue['missing_textures']['diffuse'] = {'reason': 'sdk_known_warning_image'}
    result = MODULE.compare_pixels(before, after, api)
    assert not result['passed'] and result['differences'][0]['reason'] == 'protected_channel_availability_changed'


def test_after_eyes_capture_only_exports_eye_occlusion_and_tearline(environment, tmp_path):
    owner, api, state = environment
    result = MODULE.capture_stage(owner, str(tmp_path), 'after_eyes', api)
    assert result['pixel_capture_complete']
    assert {row['mesh'] for row in result['materials']} == MODULE.EYE_SUPPORT_MESHES
    assert result['skin_diffuse_coverage'] == []
    assert set(result['required_support_meshes']) == MODULE.EYE_SUPPORT_MESHES
    assert state['get_qimage_calls'] == state['material_writes'] == 0
    full = MODULE.capture_stage(owner, str(tmp_path), 'saved', api)
    assert MODULE.compare_eye_pixels(result, full, api)['passed']


def test_post_eye_baseline_never_allows_makeup_to_replace_authorized_eye_pixels(environment, tmp_path):
    owner, api, _ = environment
    before = MODULE.capture_stage(owner, str(tmp_path), 'after_eyes', api)
    after = MODULE.capture_stage(owner, str(tmp_path), 'saved', api)
    altered = tmp_path / 'post_makeup_changed_eye.png'
    altered.write_bytes(b'changed eye pixels')
    row = next(row for row in after['materials'] if row['mesh'] == 'CC_Base_Eye')
    row['textures']['diffuse'].update(path=str(altered), sha256=sha(altered))
    # Source-to-output authorization must not leak into the post-eye baseline.
    assert MODULE.compare_pixels(before, {'materials': [row for row in after['materials'] if row['mesh'] in MODULE.EYE_SUPPORT_MESHES],
        'pixel_capture_complete': True}, api, allow_eye_changes=True)['passed']
    result = MODULE.compare_eye_pixels(before, after, api)
    assert not result['passed']
    assert result['authorized_materials_not_compared'] == []
    assert result['differences'][0]['reason'] == 'protected_rgba_pixels_changed'
    missing = copy.deepcopy(before)
    missing['materials'] = [row for row in missing['materials'] if row['mesh'] != 'CC_Base_TearLine']
    assert not MODULE.compare_eye_pixels(missing, missing, api)['passed']
