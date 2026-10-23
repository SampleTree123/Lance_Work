"""Lash measurements can never relax protected skin/support geometry."""
from pathlib import Path
import copy
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cc_refresh_eyelash_probe_v1 as lash


def snapshot():
    rows = [[0., 0., 0.] for _ in range(lash.BODY_COUNT)]
    return {'working_subdivision_level': 0, 'local': rows, 'world': copy.deepcopy(rows)}


def test_lash_moves_are_measured_without_automatically_accepted_upper_bound():
    before = snapshot(); after = copy.deepcopy(before)
    for i in lash.LASH:
        after['local'][i][1] = .2
        after['world'][i][1] = .2
    result = lash.body_gate(before, after)
    assert result['passed'] and result['nonlash_vertex_count'] == 13460
    measured = result['lash_measurement']
    assert measured['local_max_mm'] == 2 and measured['vertex_count'] == 704
    assert measured['upper_bound_mm'] is None and measured['upper_bound_accepted'] is False


@pytest.mark.parametrize('space', ['local', 'world'])
def test_one_nonlash_skin_point_over_limit_fails_even_when_lashes_are_unchanged(space):
    before = snapshot(); after = copy.deepcopy(before)
    after[space][7000][2] = .00021
    result = lash.body_gate(before, after)
    assert not result['passed'] and result['nonlash_failed_indices'] == [7000]


def test_no_arbitrary_mask_or_inactive_world_capture_is_accepted():
    before = snapshot(); after = copy.deepcopy(before)
    with pytest.raises(ValueError, match='arbitrary'):
        lash.body_gate(before, after, list(lash.LASH) + [7000])
    after['working_subdivision_level'] = 1
    with pytest.raises(ValueError, match='SubD0'):
        lash.body_gate(before, after)


def test_nonfinite_lash_is_incomparable_not_an_unbounded_measurement_pass():
    before = snapshot(); after = copy.deepcopy(before)
    after['local'][lash.LASH[0]][0] = float('nan')
    with pytest.raises(ValueError, match='finite'):
        lash.body_gate(before, after)


def test_native_material_partition_is_rederived_from_matching_body_topology(tmp_path):
    groups = [('Std_Skin', range(0, 13409)), ('Std_Eyelash', range(13411, 14113)),
              ('Std_Skin', range(14115, 14162))]
    lines = ['g CC_Base_Body\n']; faces = []
    for material, starts in groups:
        lines.append('usemtl ' + material + '\n')
        for i in starts:
            face = [i, i + 1, i + 2]; faces.append(face)
            lines.append('f ' + ' '.join(str(v + 310) for v in face) + '\n')
    resource = tmp_path / 'native.obj'; resource.write_text(''.join(lines))
    partition = lash.native_partition(resource, faces)
    assert partition['native_lash_indices'] == list(lash.LASH)
    assert partition['body_global_offset_in_resource'] == 309
    altered = copy.deepcopy(faces); altered[0] = [0, 1, 3]
    with pytest.raises(ValueError, match='differs'):
        lash.native_partition(resource, altered)


def test_support_filter_keeps_all_low_high_eye_meshes_without_inactive_body_world_queries():
    full = {'meshes': [{'name': name, 'owner': owner, 'vertex_count': count}
                      for name, owner, count in [('CC_Base_Body', 'avatar', 14164),
                        ('CC_Base_Body', 'avatar', 56412), ('CC_Base_Tongue', 'avatar', 309),
                        ('CC_Base_Tongue', 'avatar', 1209), ('CC_Base_Eye', 'avatar/Eyes:Eye', 100),
                        ('CC_Base_Eye', 'avatar/Eyes:Eye', 400)]],
            'parts': [{'owner': 'avatar', 'type': 'Eyes', 'name': 'Eye'}],
            'owner_transforms': [{'owner': 'avatar'}, {'owner': 'avatar/Eyes:Eye'}]}
    before = copy.deepcopy(full)
    result = lash.nonbody_support_snapshot(full)
    assert len(result['meshes']) == 4 and result['parts'] == full['parts']
    assert all(m['name'] != 'CC_Base_Body' for m in result['meshes'])
    assert result['owner_transforms'] == full['owner_transforms'] and full == before
