"""Addition authorization cannot mask a real original-support mutation."""
from pathlib import Path
import copy
import json
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cc_refresh_eyelash_probe_v2 as lash
from cc_repair_headshot_support_materials_v1 import compare_geometry


def snapshots():
    transform = {'translation': dict(x=0., y=0., z=0.),
                 'rotation': dict(x=0., y=0., z=0., w=1.), 's': dict(x=1., y=1., z=1.)}
    before = {'meshes': [{'owner': 'avatar/5:CC_Base_EyeOcclusion', 'name': 'CC_Base_EyeOcclusion',
        'vertex_count': 1, 'face_count': 1, 'faces_sha256': 'old', 'vertices': [[0., 0., 0.]]}],
        'parts': [dict(owner='avatar', type='5', name='CC_Base_EyeOcclusion')],
        'owner_transforms': [dict(owner=owner, space=space, value=copy.deepcopy(transform))
            for owner in ('avatar', 'avatar/5:CC_Base_EyeOcclusion') for space in ('local', 'world')],
        'owner_transform_errors': [], 'working_subdivision': 0, 'expression_count': 379}
    after = copy.deepcopy(before)
    for key in lash.DELICATE_ADDITIONS:
        after['meshes'].append(dict(zip(('owner', 'name', 'vertex_count', 'face_count', 'faces_sha256'), key),
                                    vertices=[[0., 0., 0.]] * key[2]))
        after['parts'].append(dict(owner='avatar', type='9', name=key[1]))
        after['owner_transforms'].extend(dict(owner=key[0], space=space, value=copy.deepcopy(transform))
                                        for space in ('local', 'world'))
    return before, after


def check(before, after):
    return lash.compare_existing_supports(before, after, compare_geometry)


def test_exact_additions_pass_without_positional_mesh_or_transform_order_dependency():
    before, after = snapshots()
    after['meshes'].reverse(); after['parts'].reverse(); after['owner_transforms'].reverse()
    result = check(before, after)
    assert result['passed'] and len(result['meshes']) == 1
    assert result['maximum_local_delta_mm'] == 0


@pytest.mark.parametrize('mutation', ['remove_old', 'move_old', 'alter_topology', 'wrong_part_type',
                                    'duplicate', 'new_unknown', 'remove_old_transform', 'move_old_transform',
                                    'missing_new_transform'])
def test_original_protection_and_exact_addition_contract_fail_closed(mutation):
    before, after = snapshots()
    if mutation == 'remove_old': after['meshes'].pop(0)
    elif mutation == 'move_old': after['meshes'][0]['vertices'][0][0] = .00021
    elif mutation == 'alter_topology': after['meshes'][1]['faces_sha256'] = 'different'
    elif mutation == 'wrong_part_type': after['parts'][1]['type'] = '8'
    elif mutation == 'duplicate': after['meshes'].append(copy.deepcopy(after['meshes'][0]))
    elif mutation == 'new_unknown': after['parts'].append(dict(owner='avatar', type='9', name='Unknown'))
    elif mutation == 'remove_old_transform': after['owner_transforms'].pop(0)
    elif mutation == 'move_old_transform': after['owner_transforms'][0]['value']['translation']['x'] = .00021
    elif mutation == 'missing_new_transform': after['owner_transforms'].pop()
    assert not check(before, after)['passed']


def test_actual_delicate_observation_still_fails_two_original_low_support_meshes():
    root = Path(__file__).resolve().parents[4]
    output = root / '00_engine/outputs/character_creator_bridge/artifacts/character_refresh_20261018_v1/eyelash_WF003_Delicate_v1'
    if not (output / 'after_apply_snapshot.json').exists():
        pytest.skip('Local archived actual CC observations unavailable')
    before = json.loads((output / 'before_snapshot.json').read_text())
    after = json.loads((output / 'after_apply_snapshot.json').read_text())
    result = check(before['other_meshes'], after['other_meshes'])
    assert result['allowed_new_parts_exact'] and result['available_owner_transforms_preserved']
    assert not result['passed']
    moved = [(m['name'], m['vertex_count']) for m in result['meshes'] if m['maximum_local_delta_mm'] > .002]
    assert moved == [('CC_Base_EyeOcclusion', 182), ('CC_Base_TearLine', 190)]
    assert result['maximum_local_delta_mm'] == pytest.approx(.7217283901230565)
    assert lash.body_gate(before['body'], after['body'])['passed']


def test_only_exact_asset_and_evidence_provenance_can_authorize_added_parts():
    class API:
        @staticmethod
        def sha256_file(path): return 'wrong'
    with pytest.raises(ValueError, match='Only evidenced'):
        lash.validate_addition_evidence({}, {'asset_id': 'other', 'sha256': lash.DELICATE_SHA}, {}, API, compare_geometry)
    with pytest.raises(ValueError, match='evidence path/SHA'):
        lash.validate_addition_evidence({'new_lash_parts_evidence': {name: {'path': 'D:/outside.json', 'sha256': 'expected'}
              for name in ('report', 'before_snapshot', 'after_apply_snapshot')}},
              {'asset_id': lash.DELICATE_ID, 'sha256': lash.DELICATE_SHA}, {}, API, compare_geometry)
