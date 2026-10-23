"""Exercise the finite driver with simulated receipts, never a UE connection."""
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_cfd40_native_face_integration_v1 import base_data, data
import run_cfd_native_batch40_modular_review_v1 as controller

FILE = Path(__file__).resolve().parents[3] / 'outputs/unreal_character_import/character_runtime_face_library_20261007_v1/runtime_validation/validate_face_configuration_v1.py'
spec = importlib.util.spec_from_file_location('face_validation_driver', FILE)
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


@pytest.fixture
def prepared(data, tmp_path):
    originals = copy.deepcopy(data['face_library']['entries'])
    data['face_library']['entries'] = []
    for face_id in driver.FACE_IDS:
        for row in originals:
            changed = copy.deepcopy(row)
            changed['face_id'] = face_id
            changed['animation_path'] += '_' + face_id  # test-only object path, never loaded
            data['face_library']['entries'].append(changed)
    # This driver is simulated, so build its fixture from the current catalog.
    # The historical saved file must remain byte-identical and strict loading
    # must continue rejecting its obsolete source pins.
    baseline = json.loads((driver.ROOT / 'complete_configuration.json').read_text(encoding='utf-8'))
    request = copy.deepcopy(baseline['content']['request'])
    request = controller.pin_face_registry(request, data)
    fixture = controller.configurations.build_configuration(
        {'success': True, 'request': request, 'sources': copy.deepcopy(data['sources'])},
        data, controller.validate_request)
    fixture_path = tmp_path / 'current_test_configuration.json'
    fixture_path.write_text(json.dumps(fixture), encoding='utf-8')
    request = driver.preflight(controller, data, fixture_path)
    return data, request


def receipt(data, request):
    source = driver.ROOT / 'configuration_restored.json'
    value = json.loads(source.read_text(encoding='utf-8'))
    value.update(request=copy.deepcopy(request), sources=copy.deepcopy(data['sources']), face_readback={},
                 inspection_before_reassembly=request['action'] == 'reload')
    roles = {'body': 'Body', 'eyes': 'Eyes', 'teeth': 'Teeth', 'tongue': 'Tongue', 'tearline': 'Tearline', 'eye_occlusion': 'EyeOcclusion'}
    for sex in driver.SEXES:
        case = data['identities']['by_id'][request['character_ids'][sex]]
        char = value['bindings']['characters'][sex]
        char['character_id'], char['body_skeleton'] = case['character_id'], case['skeleton']
        meshes = {roles[r['role']]: r['path'] for r in case['meshes']}
        for component in char['components']:
            if component['component_name'] in meshes:
                component['mesh_path'] = component['expected_mesh_path'] = meshes[component['component_name']]
        appearance = value['appearance_readback'][sex]
        appearance['requested'] = copy.deepcopy(request['appearance'][sex])
        action_id = controller.identities.body_action_id(data, sex, request['action_index'])
        face_id = request['appearance'][sex]['face_id']
        selected = controller.identities.face_library.resolve(data['face_library'], sex, face_id, action_id,
            body_animation_path=driver.base_motion_path(data, sex, request['action_index']))
        animation = selected['animation_path']
        value['face_readback'][sex] = {'success': True, 'face_id': face_id, 'body_action_id': action_id,
            'animation': animation, 'expected_animation': animation, 'looping': bool(animation),
            'native_follower_curves': True, 'python_morph_broadcast': False}
        value['animation'][sex].update(animation=animation, expected_animation=animation,
            playing=bool(animation and request['playing']), expected_playing=bool(animation and request['playing']))
    return value


def test_all_24_steps_save_restore_and_read_before_reassembly(prepared, tmp_path):
    data, request = prepared
    calls = []
    def execute(request, node):
        calls.append(copy.deepcopy(request))
        return receipt(data, request)
    fake = SimpleNamespace(identities=controller.identities, configurations=controller.configurations,
        validate_request=controller.validate_request, pin_face_registry=controller.pin_face_registry,
        panel=SimpleNamespace(execute=execute, state_of=controller.panel.state_of))
    run = driver.Validation(fake, data, request, tmp_path)
    run.run()
    progress = json.loads((tmp_path / 'validation_progress.json').read_text(encoding='utf-8'))
    assert progress['complete'] and len(calls) == 24
    assert calls[-2]['action'] == 'reload' and calls[-1]['action'] == 'playback' and not calls[-1]['playing']
    assert len(list(tmp_path.glob('*_receipt.json'))) == 24
    assert all(r['appearance']['female']['hair_color'] == 'pink' and r['appearance']['male']['hair_color'] == 'blue' for r in calls)
    assert calls[11]['character_ids']['female'] == 'CFD40_AF_002'
    assert calls[12]['character_ids']['female'] == 'CFD40_AF_003'
    assert calls[13]['choices'] != calls[12]['choices'] and calls[14]['choices'] == calls[12]['choices']


def test_request_failure_is_recorded_before_any_engine_dispatch(prepared, tmp_path):
    data, request = prepared
    def reject(*args): raise ValueError('changed request')
    fake = SimpleNamespace(pin_face_registry=controller.pin_face_registry, validate_request=reject)
    with pytest.raises(ValueError, match='changed request'):
        driver.Validation(fake, data, request, tmp_path).check('baseline_body_static')
    report = json.loads((tmp_path / 'validation_progress.json').read_text(encoding='utf-8'))
    assert report['failed_step'] == 'baseline_body_static' and not report['checks']
    assert len(list(tmp_path.glob('*_failure.json'))) == 1


@pytest.mark.parametrize('fault', ['wrong_clip', 'playing', 'fixed_component', 'garment_mesh', 'reload_flag'])
def test_bad_receipts_stop_and_preserve_evidence_without_recovery(prepared, tmp_path, fault):
    data, request = prepared
    calls = []
    def execute(request, node):
        calls.append(request)
        result = receipt(data, request)
        if fault == 'reload_flag':
            if request['action'] == 'reload': result['inspection_before_reassembly'] = False
        elif len(calls) == 2:
            if fault == 'wrong_clip': result['face_readback']['female']['animation'] = None
            elif fault == 'playing': result['animation']['male']['playing'] = False
            elif fault == 'fixed_component': result['bindings']['characters']['female']['components'][0]['component_path'] = 'different'
            elif fault == 'garment_mesh':
                row = next(r for r in result['bindings']['characters']['female']['components'] if r['component_name'] not in driver.BASE_NAMES and not r['component_name'].startswith('HairPart'))
                row['mesh_path'] = row['expected_mesh_path'] = '/Game/OtherMesh.OtherMesh'
        return result
    fake = SimpleNamespace(identities=controller.identities, configurations=controller.configurations,
        validate_request=controller.validate_request, pin_face_registry=controller.pin_face_registry,
        panel=SimpleNamespace(execute=execute, state_of=controller.panel.state_of))
    with pytest.raises(AssertionError):
        driver.Validation(fake, data, request, tmp_path).run()
    progress = json.loads((tmp_path / 'validation_progress.json').read_text(encoding='utf-8'))
    assert not progress['complete'] and progress['failed_step']
    assert len(calls) == (23 if fault == 'reload_flag' else 2)
    assert len(list(tmp_path.glob('*_failure.json'))) == 1
    assert len(list(tmp_path.glob('*_receipt.json'))) == len(calls)


def test_historical_configuration_is_not_silently_rebound(data):
    with pytest.raises(ValueError, match='不能静默替换'):
        controller.configurations.load_configuration(
            driver.ROOT / 'complete_configuration.json', data, controller.validate_request)
