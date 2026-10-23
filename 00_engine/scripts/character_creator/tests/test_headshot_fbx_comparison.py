"""Regression cases for invalid numeric FBX data and changing semantic names."""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location('headshot_fbx_comparison', Path(__file__).parents[1] / 'cc_audit_headshot_fbx_v1.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def scene(normals, material='Hair1'):
    return {'Objects': {'children': [
        {'name': 'Geometry', 'props': [1, 'Body\0\1Geometry', 'Mesh'], 'children': [
            {'name': 'Vertices', 'props': [np.array([0., 0., 0.])], 'children': []},
            {'name': 'Normals', 'props': [np.array(normals)], 'children': []}]},
        {'name': 'Material', 'props': [2, material + '\0\1Material', ''], 'children': []}
    ]}, 'Connections': {'children': []}}


def compare(monkeypatch, first, second):
    monkeypatch.setattr(audit, 'read_nodes', lambda name: (7200, first if name == 'a' else second))
    result = audit.compare('a', 'b')
    json.dumps(result, allow_nan=False)
    return result


def test_identical_nan_arrays_cannot_pass(monkeypatch):
    value = scene([float('nan'), 0., 1.])
    result = compare(monkeypatch, value, value)
    assert not result['numeric_repeatability_passed']
    assert result['nonfinite_arrays'][0]['a_nonfinite'] == 1
    assert result['nonfinite_arrays'][0]['b_nonfinite'] == 1


def test_finite_subtraction_overflow_is_explicit(monkeypatch):
    result = compare(monkeypatch, scene([1.7e308, 0., 0.]), scene([-1.7e308, 0., 0.]))
    assert not result['numeric_repeatability_passed']
    assert result['array_differences'][0]['finite_subtraction_overflow']
    assert result['array_differences'][0]['max_abs_delta'] is None


def test_equal_vertices_do_not_hide_material_name_change(monkeypatch):
    result = compare(monkeypatch, scene([0., 0., 1.], 'Hair1'), scene([0., 0., 1.], 'Hair2'))
    assert result['mesh_max_vertex_delta_mm'] == 0
    assert not result['numeric_repeatability_passed']
    assert result['semantic_keys_only_a'] == ['Material::Hair1']
    assert result['semantic_keys_only_b'] == ['Material::Hair2']


def test_exact_finite_input_passes(monkeypatch):
    value = scene([0., 0., 1.])
    assert compare(monkeypatch, value, value)['numeric_repeatability_passed']
