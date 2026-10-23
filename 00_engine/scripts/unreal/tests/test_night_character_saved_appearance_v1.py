"""Saved-site looks survive removal of known colors, without weakening validation."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import night_character_review_v1 as night
from motion_library_review_adapter_v1 import PrivateModules


@pytest.fixture
def domain():
    contract = PrivateModules().load('scene_site_appearance_v1')
    contract.formal_runtime = lambda: None
    contract.slots = SimpleNamespace(validate_choice=lambda sex, choice: {
        'normalized_choice': copy.deepcopy(choice)})
    data = {'sources': {'formal_catalog': 'same', 'character_revision': 'current'},
            'identities': [{'id': 'CFD40_AF_001', 'sex': 'female'}],
            'hair_colors': [{'id': color} for color in (
                'original', 'black', 'gold', 'silver_white', 'red', 'blue', 'pink')],
            'faces': [{'sex': 'female', 'face_id': 'smile'}]}
    selection = {'character_id': 'CFD40_AF_001', 'sex': 'female',
                 'choice': {'family_id': 'saved_outfit', 'hair_id': 'saved_hair'},
                 'hair_color': 'original', 'eye_color': 'original', 'face_id': 'smile',
                 'sources': copy.deepcopy(data['sources'])}
    return contract, data, selection


@pytest.mark.parametrize('color', ['purple', 'teal', 'orange'])
def test_linked_legacy_appearance_loads_in_memory_without_rewriting_saved_bytes(domain, tmp_path, color):
    contract, data, selection = domain
    selection['hair_color'] = color
    selection['sources']['character_revision'] = 'previous_delivery'
    before = copy.deepcopy(selection)
    identifier = 'appearance_' + 'a' * 32
    document = {'schema': contract.SCHEMA, 'id': identifier, 'name': 'saved look',
                'selection': selection, 'selection_sha256': contract.io.digest(selection)}
    path = tmp_path / (identifier + '.json')
    contract.io.write(path, document)
    saved_bytes = path.read_bytes()
    night.bind_saved_selections(contract, data)

    loaded = contract.load_configuration(identifier, data, root=tmp_path)

    expected = {**before, 'hair_color': 'original', 'sources': copy.deepcopy(data['sources'])}
    assert loaded['selection'] == expected
    assert loaded['id'] == identifier
    assert path.read_bytes() == saved_bytes
    assert selection == before
    assert [r['id'] for r in data['hair_colors']] == [
        'original', 'black', 'gold', 'silver_white', 'red', 'blue', 'pink']


@pytest.mark.parametrize('color', ['original', 'black', 'gold', 'silver_white', 'red', 'blue', 'pink'])
def test_current_colors_are_preserved(domain, color):
    contract, data, selection = domain
    selection['hair_color'] = color
    night.bind_saved_selections(contract, data)
    assert contract.validate_selection(selection, data) == selection


def test_fallback_keeps_other_source_color_identity_and_face_validation(domain):
    contract, data, selection = domain
    unwrapped = contract.validate_selection
    night.bind_saved_selections(contract, data)
    selection['hair_color'] = 'purple'
    # Production's underlying validator still rejects a removed menu option.
    with pytest.raises(ValueError, match='发色'):
        unwrapped(selection, data)
    for field, value, message in (
        ('hair_color', 'unknown_future_color', '发色'),
        ('eye_color', 'blue', '发色'),
        ('character_id', 'missing_character', '角色'),
        ('face_id', 'unknown_expression', '表情'),
        ('sources', {**data['sources'], 'formal_catalog': 'changed'}, '目录已变化'),
    ):
        bad = {**selection, field: value}
        with pytest.raises(ValueError, match=message):
            contract.validate_selection(bad, data)


def test_saved_digest_is_checked_before_color_fallback(domain, tmp_path):
    contract, data, selection = domain
    identifier = 'appearance_' + 'b' * 32
    document = {'schema': contract.SCHEMA, 'id': identifier, 'selection': selection,
                'selection_sha256': contract.io.digest(selection)}
    selection['hair_color'] = 'purple'  # Simulate an unrecorded saved-file edit.
    contract.io.write(tmp_path / (identifier + '.json'), document)
    night.bind_saved_selections(contract, data)
    with pytest.raises(ValueError, match='内容校验失败'):
        contract.load_configuration(identifier, data, root=tmp_path)
