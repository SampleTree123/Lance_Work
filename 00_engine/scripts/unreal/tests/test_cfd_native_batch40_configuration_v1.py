"""Source-bound configuration round-trips and batch-only material exceptions."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_cfd_native_batch40_modular_review_v1 as controller
import cfd_native_batch40_configuration_v1 as preset
import cfd_native_batch40_modular_contract_v1 as identity
from test_cfd_native_batch40_modular_worker_v1 import functions, Body


@pytest.fixture(scope='module')
def data():
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(controller.identities, 'face_catalog', lambda: {'entries': []})
        return controller.load_catalog()


def test_full_configuration_restores_identity_barefoot_hair_color_motion_and_playing(data, tmp_path):
    request = controller.initial_request(data)
    request['character_ids']['female'] = 'CFD40_BF_003'
    request['choices']['female'] = copy.deepcopy(next(r['choice'] for r in data['presets_by_sex']['female'] if r['index'] == 89))
    request['choices']['female']['shared_shoe_id'] = None
    request['appearance']['female']['hair_color'] = 'silver_white'
    request['appearance']['male']['hair_color'] = 'red'
    request.update(action_index=3, playing=True, view='side', focus='female')
    result = {'success': True, 'sources': data['sources'], 'request': request}
    path = tmp_path / 'configuration.json'
    preset.save_configuration(path, result, data, controller.validate_request)
    restored = preset.load_configuration(path, data, controller.validate_request)
    assert restored == request
    changed = identity.switch_identity(restored, 'female', 'CFD40_WF_005', data['identities'])
    assert changed['appearance'] == request['appearance'] and changed['choices'] == request['choices']
    assert changed['playing'] and changed['action_index'] == 3


def test_config_tampering_changed_sources_and_future_faces_rejected(data, tmp_path):
    request = controller.initial_request(data)
    path = tmp_path / 'configuration.json'
    document = preset.build_configuration({'success': True, 'sources': data['sources'], 'request': request}, data, controller.validate_request)
    document['content']['request']['character_ids']['female'] = 'CFD40_AF_002'
    identity.write(path, document)
    with pytest.raises(ValueError, match='校验'):
        preset.load_configuration(path, data, controller.validate_request)
    document['content_sha256'] = preset.digest(document['content'])
    identity.write(path, document)
    changed = copy.deepcopy(data)
    changed['sources']['appearance_palette']['sha256'] = 'new-palette'
    with pytest.raises(ValueError, match='版本'):
        preset.load_configuration(path, changed, controller.validate_request)
    request['appearance']['female']['face_id'] = 'unimplemented_expression'
    with pytest.raises(ValueError, match='face_id'):
        controller.validate_request(request, data)


def test_palette_uses_helper_values_without_duplicate_or_recomputed_colors(data):
    import hair_eye_color_runtime_v1 as helper
    assert data['appearance']['hair'] == ['original', *helper.PRESETS['hair']]
    assert len(data['appearance']['hair']) == 10
    assert data['appearance']['source'] == identity.source(Path(helper.__file__))


def test_no_hair_defers_tint_but_retains_requested_color():
    bodies = {sex: Body(sex) for sex in identity.SEXES}
    request = identity.default_appearance()
    request['female']['hair_color'] = 'purple'
    calls = []
    ns = functions('apply_identity', fixed=SimpleNamespace(body_for=bodies.__getitem__, object_path=lambda v: v,
        actor_for=lambda s: s, actor_components=lambda actor: {}),
        _apply=lambda plan, prepared: {'success': True}, colors=SimpleNamespace(apply=lambda *args: calls.append(args)))
    prepared = {sex: {'body_mesh': body.mesh} for sex, body in bodies.items()}
    assert ns['apply_identity']({'appearance': request}, prepared)['success']
    assert not calls and request['female']['hair_color'] == 'purple'


def test_color_exemption_does_not_hide_other_binding_or_body_override_errors():
    value = {'characters': {'female': {'components': [
        {'component_name': 'HairPart01', 'errors': ['stale_material_override', 'copy_pose_binding']},
        {'component_name': 'Body', 'errors': ['stale_material_override']}]}},
        'errors': ['female/HairPart01/stale_material_override', 'female/HairPart01/copy_pose_binding',
                   'female/Body/stale_material_override']}
    ns = functions('readback', _checking_colors=True, _readback=lambda *args: copy.deepcopy(value),
                   appearance_readback=lambda plan: ({'female': {'success': True}}, {'female': {'HairPart01'}}))
    result = ns['readback']({})
    assert result['errors'] == ['female/HairPart01/copy_pose_binding', 'female/Body/stale_material_override']
    assert result['success'] is False


def test_failed_color_readback_cannot_be_exempted():
    def failure(plan):
        raise RuntimeError('Wrong isolated color material')
    ns = functions('readback', _checking_colors=True, _readback=lambda *args: {}, appearance_readback=failure)
    with pytest.raises(RuntimeError, match='Wrong isolated'):
        ns['readback']({})
