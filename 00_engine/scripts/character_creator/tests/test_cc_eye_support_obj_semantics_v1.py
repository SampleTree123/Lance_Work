"""Resolved corner semantics distinguish recompute noise from changed normals."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cc_eye_support_obj_semantics_v1 as semantics

OBJ=('g Support\nv 0 0 0\nv 1 0 0\nv 0 1 0\n'
     'vt 0 0\nvt 1 0\nvt 0 1\n'
     'vn 0.000000 0.000000 1.000000\nvn 0.000000 0.000000 1.000000\n'
     's 8\nf 1/1/1 2/2/1 3/3/2\n')


def test_reordered_corner_attribute_arrays_do_not_fail_semantics(tmp_path):
    a=tmp_path/'a.obj';b=tmp_path/'b.obj';a.write_text(OBJ)
    b.write_text(OBJ.replace('vt 0 0\nvt 1 0\nvt 0 1','vt 0 1\nvt 1 0\nvt 0 0')
        .replace('f 1/1/1 2/2/1 3/3/2','f 1/3/2 2/2/2 3/1/1'))
    result=semantics.compare_native_semantics(a,b)
    assert result['passed'] and result['before_sha256']!=result['after_sha256']
    assert result['uv_per_corner_exact'] and result['normal_numeric_per_corner_unchanged']


@pytest.mark.parametrize('change',['uv','topology','material','smoothing','normal_small','normal_flip','geometry'])
def test_no_arbitrary_normal_angle_or_protected_attribute_allowance(tmp_path,change):
    text=OBJ
    if change=='uv':text=text.replace('vt 0 0','vt 0.000001 0')
    elif change=='topology':text=text.replace('f 1/1/1 2/2/1 3/3/2','f 1/1/1 3/3/2 2/2/1')
    elif change=='material':text=text.replace('s 8','usemtl Changed\ns 8')
    elif change=='smoothing':text=text.replace('s 8','s 1')
    elif change=='normal_small':text=text.replace('vn 0.000000 0.000000 1.000000','vn 0.000100 0.000000 1.000000')
    elif change=='normal_flip':text=text.replace('vn 0.000000 0.000000 1.000000','vn 0.000000 0.000000 -1.000000')
    elif change=='geometry':text=text.replace('v 0 0 0','v 0.001 0 0')
    a=tmp_path/'a.obj';b=tmp_path/'b.obj';a.write_text(OBJ);b.write_text(text)
    assert not semantics.compare_native_semantics(a,b)['passed']


def test_actual_v4_hash_difference_is_explained_by_geometric_rebuild(tmp_path):
    root=Path(__file__).resolve().parents[4]
    output=root/'00_engine/outputs/character_creator_bridge/artifacts/character_refresh_20261018_v1/eye_occlusion_WF003_identity_v4'
    if not (output/'native_after_identity.obj').exists():pytest.skip('Actual v4 native exports unavailable')
    result=semantics.compare_native_semantics(output/'native_source.obj',output/'native_after_identity.obj')
    assert result['passed'] and result['uv_per_corner_exact'] and result['topology_vertex_order_unchanged']
    assert result['normal_flip_count']==0 and result['normal_angle_limit_used'] is False
    assert result['normal_change_max_degrees']==pytest.approx(.05180529333625794)
    assert result['geometry_predicted_normal_change_max_degrees']==pytest.approx(.05179610812006977)
    assert result['before_normal_geometry_explanation']['maximum_displayed_component_units']==1
    assert result['after_normal_geometry_explanation']['maximum_displayed_component_units']==1
    # Rotate an observed normal by an amount smaller than the actual maximum
    # angle above. It still fails because geometry does not explain that edit.
    lines=(output/'native_after_identity.obj').read_text().splitlines()
    for i,line in enumerate(lines):
        if line.startswith('vn '):
            fields=line.split();fields[1]=format(float(fields[1])+.0001,'.6f');lines[i]=' '.join(fields);break
    tampered=tmp_path/'tampered.obj';tampered.write_text('\n'.join(lines)+'\n')
    assert not semantics.compare_native_semantics(output/'native_source.obj',tampered)['passed']
