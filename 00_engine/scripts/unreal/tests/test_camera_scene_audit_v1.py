import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('scene_audit', Path(__file__).parents[1] / 'ue_camera_scene_audit_v1.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def write_manifests(root):
    jobs = [{'shot_id': f'cam_{i:02}', 'map': m.ROOT + f'Maps/L_{i:02}',
             'sequence': m.ROOT + f'Sequences/LS_{i:02}'} for i in range(34)]
    docs = [{'jobs': jobs[:30]}, {'job': jobs[30], 'shot': {'sex': 'female'}}, {'jobs': jobs[31:]}]
    for name, doc in zip(m.MANIFESTS, docs):
        (root / name).write_text(json.dumps(doc), encoding='utf-8')
    (root / 'camera_motion_pilot_plan_v1.json').write_text(json.dumps(
        {'shots': [{'shot_id': j['shot_id'], 'sex': 'female'} for j in jobs[:30]]}), encoding='utf-8')


def test_requires_all_34_jobs_and_exact_plan_ids(tmp_path):
    write_manifests(tmp_path)
    jobs, sex, pins = m.load_jobs(tmp_path)
    assert len(jobs) == 34 and len(pins) == 4 and len(sex) == 31
    (tmp_path / m.MANIFESTS[2]).unlink()
    with pytest.raises(FileNotFoundError):
        m.load_jobs(tmp_path)


def test_incomplete_extra_manifest_cannot_pass(tmp_path):
    write_manifests(tmp_path)
    (tmp_path / m.MANIFESTS[2]).write_text('{"jobs": []}', encoding='utf-8')
    with pytest.raises(ValueError, match='30 primary'):
        m.load_jobs(tmp_path)


@pytest.mark.parametrize('path', ['/Transient/M.M', '/Game/A/../B.B', '/Game/A.A:Body',
                                  '/Unknown/A.A', '/Game/../../outside'])
def test_no_transient_or_unknown_or_traversal_asset_pins(path):
    with pytest.raises(ValueError):
        m.package_file(path)


@pytest.mark.parametrize('prefix', ['/Game/', '/Engine/', '/InterchangeAssets/'])
def test_saved_dependency_mounts_supported(prefix):
    assert m.package_file(prefix + 'Materials/X.X').is_relative_to(m.MOUNTS[prefix].resolve())


def test_planner_identity_requires_scale_and_rotation_and_finite_values():
    assert m.identity_transform([0, 0, 0], [0, 0, 0], [1, 1, 1])
    assert not m.identity_transform([0, 0, 0], [0, -90, 0], [1, 1, 1])
    assert not m.identity_transform([0, 0, 0], [0, 0, 0], [100, 100, 100])
    assert not m.identity_transform([float('nan'), 0, 0], [0, 0, 0], [1, 1, 1])


def test_refuses_dirty_maps_without_saving_or_discarding():
    from types import SimpleNamespace
    package = SimpleNamespace(get_path_name=lambda: m.ROOT + 'L_dirty')
    u = SimpleNamespace(EditorLoadingAndSavingUtils=SimpleNamespace(
        get_dirty_map_packages=lambda: [package], get_dirty_content_packages=lambda: []))
    with pytest.raises(RuntimeError, match='Refusing'):
        m.require_clean_maps(u, [])


def revised_manifest(root):
    write_manifests(root)
    jobs, _, pins = m.load_jobs(root)
    for job in jobs:
        job['map'] = job['map'].replace('/Maps/', '/MapsV2/')
    (root / 'camera_motion_pilot_plan_v3.json').write_bytes((root / 'camera_motion_pilot_plan_v1.json').read_bytes())
    result = {'jobs': jobs, 'source_manifests': pins[:3],
              'plan': m.pin(root / 'camera_motion_pilot_plan_v3.json')}
    (root / 'prepared_jobs_v2.json').write_text(json.dumps(result), encoding='utf-8')
    return result


def test_revised_scope_uses_all_new_maps_and_pins_original_inputs(tmp_path):
    revised_manifest(tmp_path)
    jobs, _, pins = m.load_jobs(tmp_path, revised=True)
    assert len(jobs) == 34 and len(pins) == 6
    assert all('/MapsV2/' in job['map'] for job in jobs)


@pytest.mark.parametrize('fault', ['old_map', 'missing_shot', 'changed_source_hash', 'changed_plan_hash', 'obsolete_v2_plan'])
def test_revised_manifest_cannot_silently_change_or_skip_scope(tmp_path, fault):
    value = revised_manifest(tmp_path)
    if fault == 'old_map':
        value['jobs'][0]['map'] = value['jobs'][0]['map'].replace('/MapsV2/', '/Maps/')
    elif fault == 'missing_shot':
        value['jobs'].pop()
    elif fault == 'changed_source_hash':
        value['source_manifests'][0]['sha256'] = '0' * 64
    elif fault == 'changed_plan_hash':
        value['plan']['sha256'] = '0' * 64
    else:
        old = tmp_path / 'camera_motion_pilot_plan_v2.json'
        old.write_bytes((tmp_path / 'camera_motion_pilot_plan_v3.json').read_bytes())
        value['plan'] = m.pin(old)
    (tmp_path / 'prepared_jobs_v2.json').write_text(json.dumps(value), encoding='utf-8')
    with pytest.raises(ValueError):
        m.load_jobs(tmp_path, revised=True)


def hair_stub(parent, leader, attach_bounds):
    from types import SimpleNamespace
    properties = {'leader_pose_component': leader, 'use_attach_parent_bound': attach_bounds,
        'use_bounds_from_leader_pose_component': True, 'component_use_fixed_skel_bounds': False,
        'bounds_scale': 1., 'forced_lod_model': 0, 'render_static': False, 'hidden_in_game': False}
    return SimpleNamespace(get_attach_parent=lambda: parent, get_editor_property=lambda key: properties[key],
        get_path_name=lambda: '/TestWorld:Actor.HairPart01', get_name=lambda: 'HairPart01', is_visible=lambda: True)


def test_hair_policy_requires_exact_body_parent_leader_and_bounds():
    from types import SimpleNamespace
    body = SimpleNamespace(get_path_name=lambda: '/TestWorld:Actor.Body')
    record = m.hair_bounds_readback(hair_stub(body, body, True), body, required=True)
    assert record['revised_hair_bounds_policy_pass'] and record['bounds_scale'] == 1.


@pytest.mark.parametrize('fault', ['parent', 'leader', 'bounds'])
def test_revised_hair_policy_fails_each_missing_requirement(fault):
    from types import SimpleNamespace
    body = SimpleNamespace(get_path_name=lambda: '/TestWorld:Actor.Body')
    component = hair_stub(None if fault == 'parent' else body, None if fault == 'leader' else body, fault != 'bounds')
    with pytest.raises(RuntimeError, match='Revised hair requires'):
        m.hair_bounds_readback(component, body, required=True)
    # Historic audit only records the old setting; it must not retroactively enforce v2.
    assert not m.hair_bounds_readback(component, body)['revised_hair_bounds_policy_pass']


def test_independent_face_track_requires_parent_bounds_without_leader():
    from types import SimpleNamespace
    body = SimpleNamespace(get_path_name=lambda: '/TestWorld:Actor.Body')
    face = hair_stub(body, None, True)
    face.get_name = lambda: 'Eyes'
    record = m.attached_component_bounds_readback(face, body, required=True)
    assert record['parent_bounds_policy_applicable'] and record['parent_bounds_policy_pass']
    assert record['leader_pose_component'] is None


@pytest.mark.parametrize('name', ['FullBody', 'Footwear', 'Eyes', 'Teeth', 'Tongue', 'Tearline', 'EyeOcclusion'])
def test_each_body_attached_clothing_or_independent_face_requires_parent_bounds(name):
    from types import SimpleNamespace
    body = SimpleNamespace(get_path_name=lambda: '/TestWorld:Actor.Body')
    component = hair_stub(body, None, False)
    component.get_name = lambda: name
    with pytest.raises(RuntimeError, match='non-Body component'):
        m.attached_component_bounds_readback(component, body, required=True)


def test_unrelated_attachment_does_not_infer_leader_or_parent_bounds_requirement():
    from types import SimpleNamespace
    body = SimpleNamespace(get_path_name=lambda: '/TestWorld:Actor.Body')
    record = m.attached_component_bounds_readback(hair_stub(None, None, False), body, required=True)
    assert not record['parent_bounds_policy_applicable'] and record['parent_bounds_policy_pass']


@pytest.mark.parametrize('name', m.FACE_COMPONENTS)
def test_each_face_requires_none_leader_and_exact_persistent_actor_route(name):
    face = hair_stub(None, None, True)
    face.get_name = lambda: name
    tag = 'DM_CCWH_SLOT_COPY_' + name
    result = m.face_route_readback(face, [tag], required=True)
    assert result['independent_face_route_pass'] and result['leader_is_none']
    with pytest.raises(RuntimeError, match='persistent actor route tag'):
        m.face_route_readback(face, ['DM_CCWH_SLOT_' + name], required=True)


def test_route_tag_alone_does_not_hide_reloaded_face_leader_regression():
    from types import SimpleNamespace
    body = SimpleNamespace(get_path_name=lambda: '/TestWorld:Actor.Body')
    face = hair_stub(body, body, True)
    face.get_name = lambda: 'Eyes'
    with pytest.raises(RuntimeError, match='Leader=None'):
        m.face_route_readback(face, ['DM_CCWH_SLOT_COPY_Eyes'], required=True)
    assert not m.face_route_readback(face, ['DM_CCWH_SLOT_COPY_Eyes'])['independent_face_route_pass']
