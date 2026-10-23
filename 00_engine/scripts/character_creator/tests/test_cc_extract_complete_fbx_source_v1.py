import copy
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cc_extract_complete_fbx_source_v1 import summarize_nodes


def obj(oid, cls, name, subtype, children=None):
    return {'name': cls, 'props': [oid, name + '\x00' + cls, subtype], 'children': children or []}


def nodes():
    objects = [obj(1, 'Geometry', 'Body', 'Mesh'), obj(2, 'Model', 'Body', 'Mesh'),
               obj(3, 'Deformer', 'Blend', 'BlendShape'), obj(4, 'Deformer', 'Smile', 'BlendShapeChannel'),
               obj(5, 'Geometry', 'SmileShape', 'Shape', [{'name': 'Vertices', 'props': [np.array([0, .1, 0])]}]),
               obj(6, 'Deformer', 'Noise', 'BlendShapeChannel'),
               obj(7, 'Geometry', 'NoiseShape', 'Shape', [{'name': 'Vertices', 'props': [np.array([0, .000015, 0])]}]),
               obj(8, 'Model', 'Head', 'LimbNode'), obj(9, 'Material', 'Std_Skin', '')]
    links = [(1, 2), (3, 1), (4, 3), (5, 4), (6, 3), (7, 6), (9, 2)]
    return {'Objects': {'children': objects}, 'Connections': {'children': [{'props': ['OO', a, b]} for a, b in links]}}


def test_presence_and_tiny_delta_are_separate():
    summary = summarize_nodes(nodes())
    mesh = summary['expected_meshes'][0]
    assert mesh['fbx_morph_names'] == ['Noise', 'Smile']
    assert mesh['expected_nonzero_morph_names'] == ['Noise', 'Smile']
    assert {r['threshold_cm']: r['channel_count'] for r in mesh['position_delta_audit']}[.01] == 1
    assert mesh['expected_materials'] == ['Std_Skin']
    assert summary['bone_count'] == 1


def test_shape_deltas_must_be_finite():
    data = nodes()
    data['Objects']['children'][4]['children'][0]['props'][0][0] = np.nan
    with pytest.raises(ValueError, match='nonfinite'):
        summarize_nodes(data)


def test_channel_parent_ambiguity_rejected():
    data = nodes()
    data['Connections']['children'].append({'props': ['OO', 4, 3]})
    with pytest.raises(ValueError, match='Ambiguous'):
        summarize_nodes(data)


def test_exact_zero_source_channel_is_not_omitted_from_names():
    data = nodes()
    data['Objects']['children'][6]['children'][0]['props'][0][:] = 0
    mesh = summarize_nodes(data)['expected_meshes'][0]
    assert mesh['fbx_morph_names'] == ['Noise', 'Smile']
    assert mesh['expected_nonzero_morph_names'] == ['Smile']
