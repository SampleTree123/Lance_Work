"""Offline page, source and draft guards; never connect to Unreal."""
import copy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hair_group_color_review_contract_v1 as contract
import run_hair_group_color_review_v1 as runner


@pytest.fixture
def data():
    indices = {'male': [1, 2, 3, 5, 6, 11, 27, 28, 30, 31, 32, 37, 39],
               'female': [1, 2, 3, 5, 8, 9, 11, 14, 16, 17, 19, 22, 23, 24, 25, 26, 29, 33, 35, 38]}
    return {'sources': {'registry': {'path': 'registry.json', 'sha256': 'current'}},
            'hairs_by_sex': {sex: [{'index': index, 'hair_id': f'HAIR_{index}', 'label': f'Hair {index}',
                                   'sex': sex, 'fit': {'meshes': [{'path': f'/Game/{sex}/Hair{index}'}]}}
                                  for index in values] for sex, values in indices.items()},
            'characters_by_sex': {}, 'colors': {'hair': list(contract.HAIR_COLORS), 'eye': list(contract.EYE_COLORS)}}


def reply(request, data):
    order = contract.expected_order(data, request)
    return {'success': True, 'level': contract.LEVEL, 'request': request, 'sources': data['sources'],
            'page_order': order, 'displayed': order if request['focus'] == 'all' else [order[int(request['focus']) - 1]]}


def test_page_coverage_keeps_sex_lists_original_gapped_numbers_and_fits(data):
    for sex, pages, last_count in [('male', 3, 1), ('female', 4, 2)]:
        assert contract.page_count(data, sex) == pages
        rows = [row for page in range(1, pages + 1) for row in contract.page_hairs(data, {'sex': sex, 'page': page})]
        assert rows == data['hairs_by_sex'][sex]
        assert len(contract.page_hairs(data, {'sex': sex, 'page': pages})) == last_count
    assert contract.page_hairs(data, {'sex': 'male', 'page': 2})[0]['index'] == 27


@pytest.mark.parametrize('selection', [
    {'sex': 'male', 'page': 4}, {'sex': 'female', 'page': 4, 'focus': '6'},
    {'sex': 'male', 'page': 3, 'focus': '4'}, {'page': True}, {'save': 1},
    {'sex': 'other'}, {'unexpected': 'field'}, {'focus': 1}])
def test_invalid_or_nonexistent_page_slot_rejected(data, selection):
    with pytest.raises(ValueError):
        contract.normalize_request(selection, data)


def test_probe_can_restrict_colors_without_silent_fallback(data):
    data['colors'] = contract.validate_colors({'hair': ['original', 'black'], 'eye': ['original']})
    assert contract.normalize_request({'hair_color': 'black'}, data)['hair_color'] == 'black'
    with pytest.raises(ValueError):
        contract.normalize_request({'eye_color': 'blue'}, data)
    with pytest.raises(ValueError):
        contract.validate_colors({'hair': ['black'], 'eye': ['original']})


def test_expanded_dye_palette_keeps_eyes_original_and_supports_user_colors(data):
    import hair_eye_color_runtime_v1 as runtime
    assert set(contract.HAIR_COLORS) == set(runtime.CAPABILITIES['hair'])
    for color in ('blue', 'pink', 'purple', 'red', 'teal', 'orange', 'gold', 'silver_white'):
        assert contract.normalize_request({'hair_color': color}, data)['eye_color'] == 'original'
    assert contract.EYE_COLORS == ('original',)
    with pytest.raises(ValueError):
        contract.normalize_request({'eye_color': 'green'}, data)
    for removed in ('green', 'brown', 'copper', 'golden_brown'):
        with pytest.raises(ValueError):
            contract.normalize_request({'hair_color': removed}, data)


@pytest.mark.parametrize('mutation', ['order', 'focused_hair', 'sources', 'level'])
def test_result_guards_actual_hair_identity_and_source_binding(data, mutation):
    request = contract.normalize_request({'sex': 'female', 'page': 2, 'focus': '2', 'view': 'back'}, data)
    result = copy.deepcopy(reply(request, data))
    assert contract.verify_result(result, request, data) is result
    if mutation == 'order':
        result['page_order'].reverse()
    elif mutation == 'focused_hair':
        result['displayed'][0]['hair_id'] = 'different'
    elif mutation == 'sources':
        result['sources']['registry']['sha256'] = 'old'
    else:
        result['level'] = '/Game/OldReview'
    with pytest.raises(RuntimeError):
        contract.verify_result(result, request, data)


def test_target_is_new_run_not_previous_batch_editor():
    assert runner.target.TARGET_FILE == contract.ROOT.parent / 'ue_target.json'
    assert 'female_shared_shoes_hair_color_20261007_v1' in str(runner.target.RUN)


def test_draft_is_sex_and_hair_specific_without_formal_acceptance(data, tmp_path, monkeypatch):
    monkeypatch.setattr(contract, 'ROOT', tmp_path)
    monkeypatch.setattr(contract, 'catalog', lambda: copy.deepcopy(data))
    request = contract.normalize_request({'sex': 'female', 'page': 2, 'focus': '2'}, data)
    result = copy.deepcopy(reply(request, data))
    path = tmp_path / 'controller/run/display.json'
    contract.write(path, result)
    result.update(controller_result_file=str(path), controller_result_sha256=contract.source(path)['sha256'])
    with pytest.raises(ValueError):
        runner.record_draft(result, data, 1, 'draft A', '')
    draft = runner.record_draft(result, data, 2, 'draft A', 'side silhouette')
    assert draft['sex'] == 'female' and draft['original_index'] == 14
    assert draft['status'] == 'draft_pending_user_confirmation'
    assert draft['formal_configuration_written'] is False
    assert contract.read(tmp_path / 'grouping_drafts.json')['drafts'] == [draft]
    path.write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError):
        runner.record_draft(result, data, 2, 'draft A', 'tampered')
