"""Offline guardrails for identity switching; no UE, sockets or visible UI."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cfd_native_batch40_modular_contract_v1 as identity
import run_cfd_native_batch40_modular_review_v1 as controller


@pytest.fixture(scope='module')
def data():
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(controller.identities, 'face_catalog', lambda: {'entries': []})
        return controller.load_catalog()


def test_registry_covers_40_six_parts_two_shared_skeletons(data):
    catalog = data['identities']
    assert {sex: len(rows) for sex, rows in catalog['by_sex'].items()} == {'female': 20, 'male': 20}
    assert len({c['skeleton'] for c in catalog['cases']}) == 2
    assert len({m['path'] for c in catalog['cases'] for m in c['meshes']}) == 240
    # Current recovered imports remain authoritative; no invented /Meshes path.
    assert any('MeshesRecovery' in m['path'] for c in catalog['cases'] for m in c['meshes'])


@pytest.mark.parametrize('mutation', ('missing', 'duplicate', 'skeleton', 'part', 'foreign_mesh'))
def test_invalid_batch_rejected(data, mutation):
    document = {'cases': copy.deepcopy(data['identities']['cases'])}
    cases = document['cases']
    if mutation == 'missing':
        cases.pop()
    elif mutation == 'duplicate':
        cases[-1] = copy.deepcopy(cases[0])
    elif mutation == 'skeleton':
        cases[0]['skeleton'] = data['identities']['skeletons']['female']
    elif mutation == 'part':
        cases[0]['meshes'][0]['role'] = 'body'
    else:
        cases[0]['meshes'][0]['path'] = cases[1]['meshes'][0]['path']
    with pytest.raises(ValueError):
        identity.validate_registry(document)


def test_switch_preserves_exact_clothes_hair_motion_camera_and_other_sex(data):
    before = controller.initial_request(data)
    before.update(action_index=3, playing=True, view='back', framing='feet', focus='female')
    before['choices']['female'] = copy.deepcopy(data['presets_by_sex']['female'][-1]['choice'])
    after = identity.switch_identity(before, 'female', 'CFD40_WF_005', data['identities'])
    assert after['character_ids'] == {'female': 'CFD40_WF_005', 'male': 'CFD40_AM_001'}
    assert {k: v for k, v in before.items() if k != 'character_ids'} == {
        k: v for k, v in after.items() if k != 'character_ids'}
    assert before['character_ids']['female'] == 'CFD40_AF_001'
    with pytest.raises(ValueError):
        identity.switch_identity(before, 'female', 'CFD40_AM_001', data['identities'])


def result_for(request, data):
    return {'success': True, 'request': copy.deepcopy(request), 'level': identity.LEVEL,
            'sources': copy.deepcopy(data['sources']), 'plan_sha256': 'test-plan',
            'appearance_readback': {sex: {'success': True, 'requested': copy.deepcopy(request['appearance'][sex])}
                                    for sex in identity.SEXES},
            'bindings': {'success': True, 'errors': [], 'plan_sha256': 'test-plan', 'characters': {
                sex: {'character_id': identifier, 'body_skeleton': data['identities']['by_id'][identifier]['skeleton'],
                      'components': [{'mesh_path': m['path'], 'errors': []}
                                     for m in data['identities']['by_id'][identifier]['meshes']]}
                for sex, identifier in request['character_ids'].items()}}}


@pytest.mark.parametrize('mutation', ('identity', 'skeleton', 'missing_part', 'source'))
def test_reply_cannot_confirm_wrong_identity_or_missing_base_parts(data, mutation, monkeypatch):
    monkeypatch.setattr(controller.identities, 'face_catalog', lambda: data['face_library'])
    request = controller.initial_request(data)
    result = result_for(request, data)
    assert controller.verify_result(result, request) is result
    actual = result['bindings']['characters']['female']
    if mutation == 'identity':
        actual['character_id'] = 'CFD40_AF_002'
    elif mutation == 'skeleton':
        actual['body_skeleton'] = data['identities']['skeletons']['male']
    elif mutation == 'missing_part':
        actual['components'].pop()
    else:
        result['sources']['character_registry']['sha256'] = 'stale'
    with pytest.raises(RuntimeError):
        controller.verify_result(result, request)


def test_cli_extended_ids_and_stale_registry_guard(data):
    args = controller.build_parser().parse_args(['--action', 'show', '--female-character', 'CFD40_BF_003',
                                               '--male-character', 'CFD40_LM_004', '--action-index', '2', '--playing'])
    request = controller.cli_request(args, data)
    assert request['character_ids'] == {'female': 'CFD40_BF_003', 'male': 'CFD40_LM_004'}
    assert request['action_index'] == 2 and request['playing']
    request['character_registry_sha256'] = 'stale'
    with pytest.raises(ValueError, match='角色索引版本'):
        controller.validate_request(request, data)


def test_observation_state_detects_identity_change(data):
    request = controller.initial_request(data)
    other = identity.switch_identity(request, 'male', 'CFD40_LM_002', data['identities'])
    assert controller.panel.state_of(request) != controller.panel.state_of(other)


def test_identity_editor_callback_changes_only_identity(data):
    before = controller.initial_request(data)
    before.update(action_index=4, playing=True, view='side')
    snapshot = copy.deepcopy(before)
    calls = []
    fake = SimpleNamespace(sex='female', identity=SimpleNamespace(current=lambda: 1),
                           identity_rows=data['identities']['by_sex']['female'], data=data,
                           changed=lambda: calls.append(True))
    controller.IdentitySexEditor._identity_changed(fake)
    assert calls == [True] and before['character_ids']['female'] == 'CFD40_AF_002'
    assert {k: v for k, v in before.items() if k != 'character_ids'} == {
        k: v for k, v in snapshot.items() if k != 'character_ids'}


def test_import_does_not_retarget_historical_controller():
    import run_complete_character_slot_review_v1 as historical
    assert historical.ROOT != identity.ROOT
    assert historical.LEVEL != identity.LEVEL
    assert historical.SexEditor is not controller.IdentitySexEditor
