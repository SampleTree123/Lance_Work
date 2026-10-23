"""No folder scan or naming heuristic may silently authorize a new review motion."""
import copy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import prepare_motion_extension_inputs_v1 as prepare


@pytest.fixture
def decision(monkeypatch):
    monkeypatch.setattr(prepare.extension, 'checked', lambda *a, **kw: None)
    notes = {'schema': 'motion_selection_review_notes_v1', 'entries': [
        {'candidate_id': 'MOTION_CAND_001', 'label_zh': '运动后放松'},
        {'candidate_id': 'MOTION_CAND_032', 'label_zh': '随音乐舞动'}]}
    document = {'schema': prepare.ACCEPTED_SCHEMA, 'reviewer': 'root_agent',
        'scope': 'explicit_reviewed_candidates_for_panel_not_human_final_acceptance',
        'accepted_candidates': [{'candidate_id': 'MOTION_CAND_032', 'visual_review': {
            'status': 'accepted_for_panel', 'observations': 'Synthetic test review only',
            'evidence': [{'path': 'synthetic_test_only', 'sha256': 'a' * 64}]}}]}
    return document, notes


def test_only_explicit_candidate_in_root_order_is_returned(decision):
    document, notes = decision
    rows, labels = prepare.accepted_entries(document, notes)
    assert [r['candidate_id'] for r in rows] == ['MOTION_CAND_032']
    assert labels[rows[0]['candidate_id']]['label_zh'] == '随音乐舞动'
    rows[0]['candidate_id'] = 'changed'
    assert document['accepted_candidates'][0]['candidate_id'] == 'MOTION_CAND_032'


@pytest.mark.parametrize('issue', ['empty', 'unreviewed', 'no_evidence', 'unknown', 'duplicate', 'not_root', 'wrong_scope', 'partial_override'])
def test_unreviewed_or_ambiguous_selection_fails_before_collection(decision, issue):
    document, notes = decision
    row = document['accepted_candidates'][0]
    if issue == 'empty': document['accepted_candidates'] = []
    elif issue == 'unreviewed': row['visual_review']['status'] = 'pending'
    elif issue == 'no_evidence': row['visual_review']['evidence'] = []
    elif issue == 'unknown': row['candidate_id'] = 'MOTION_CAND_099'
    elif issue == 'duplicate': document['accepted_candidates'].append(copy.deepcopy(row))
    elif issue == 'not_root': document['reviewer'] = 'automatic_filename_classifier'
    elif issue == 'wrong_scope': document['scope'] = 'all_humans_accepted'
    elif issue == 'partial_override': row['variants'] = {'female': {}}
    with pytest.raises(ValueError): prepare.accepted_entries(document, notes)


def test_default_exact_version_paths_do_not_pick_latest_or_scan(tmp_path, monkeypatch):
    monkeypatch.setattr(prepare, 'RUN', tmp_path)
    row = {'candidate_id': 'MOTION_CAND_032'}
    paths = prepare.variant_paths(row, 'male')
    assert paths['import_report'].name == 'motion_cand_032_male_v1.json'
    assert paths['export_binding'].name == 'motion_cand_032_male_export01.json'
    assert paths['preparation_manifest'].parent.name == 'motion_cand_032_male_v1_native5_v1'


def test_missing_one_sex_never_emits_partial_pair(monkeypatch, tmp_path):
    monkeypatch.setattr(prepare, 'RUN', tmp_path)
    with pytest.raises(ValueError, match='Missing'):
        prepare.collect_variant({'candidate_id': 'MOTION_CAND_032'}, {}, 'male', {})
