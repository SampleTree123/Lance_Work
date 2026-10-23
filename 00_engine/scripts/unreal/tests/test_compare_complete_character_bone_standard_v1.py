import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('bone_compare', Path(__file__).parents[1] / 'compare_complete_character_bone_standard_v1.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_equivalent_quaternion_sign_and_key_formats():
    old = [{'name': 'root', 'parent': 'None', 'translation': [1, 2, 3], 'rotation': [0, 0, 0, 1], 'scale': [1, 1, 1]}]
    new = [{'name': 'root', 'parent': 'None', 'translation_cm': [1, 2, 3], 'rotation_xyzw': [0, 0, 0, -1], 'scale': [1, 1, 1]}]
    assert module.compare_bones(old, new)['exact_hierarchy_and_local_transform_match']


def test_transform_change_and_parent_mismatch_are_reported():
    old = [{'name': 'root', 'parent': 'None', 'translation': [0, 0, 0], 'rotation': [0, 0, 0, 1], 'scale': [1, 1, 1]}]
    new = [{'name': 'root', 'parent': 'other', 'translation_cm': [.1, 0, 0], 'rotation_xyzw': [0, 0, 0, 1], 'scale': [1, 1, 1]}]
    result = module.compare_bones(old, new)
    assert result['max_translation_difference_mm'] == 1
    assert result['parent_differences']
    assert not result['exact_hierarchy_and_local_transform_match']


def test_duplicate_and_nonfinite_input_rejected():
    bone = {'name': 'root', 'parent': 'None', 'translation': [0, 0, 0], 'rotation': [0, 0, 0, 1], 'scale': [1, 1, 1]}
    with pytest.raises(ValueError, match='Duplicate'):
        module.compare_bones([bone, bone], [bone])
    with pytest.raises(ValueError, match='Non-finite'):
        module.compare_bones([bone], [{**bone, 'translation': [float('nan'), 0, 0]}])


def test_missing_bones_and_empty_input_cannot_pass():
    bone = {'name': 'root', 'parent': 'None', 'translation': [0, 0, 0], 'rotation': [0, 0, 0, 1], 'scale': [1, 1, 1]}
    assert module.compare_bones([bone], [])['missing_bones'] == ['root']
    assert not module.compare_bones([], [])['exact_hierarchy_and_local_transform_match']
