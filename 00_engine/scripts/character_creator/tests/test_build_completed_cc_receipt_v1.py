"""Small negative boundary checks; no app/Bridge or fabricated acceptance."""
import copy
from pathlib import Path
import sys

import pytest

RUN = Path(__file__).resolve().parents[4] / '00_engine/outputs/character_refresh_20261018_v1'
sys.path.insert(0, str(RUN))
import build_completed_cc_receipt_v1 as builder


@pytest.mark.parametrize('status', ['pending', 'failed'])
def test_pending_or_failed_never_writes_completed_output(tmp_path, monkeypatch, status):
    state = dict(status=status, facts={}, steps={})
    original = copy.deepcopy(state)
    def incomplete(*args):
        builder.require_ready_state(state)
        pytest.fail('pending must reject')
    monkeypatch.setattr(builder, 'load_facts', incomplete)
    output = tmp_path / 'not_created'
    with pytest.raises(ValueError, match='Pending/failed/incomplete'):
        builder.build('order', 'CFD40_AM_001', 'not_approved', 'not_authorized', output)
    assert not output.exists() and state == original


def test_pending_visual_document_cannot_be_promoted():
    approval = dict(schema='cfd40_refresh_root_export_source_review_v1', character_id='CFD40_AM_001',
                    reviewer='root_agent', decision='pending')
    with pytest.raises(ValueError, match='actual-four-image approval'):
        builder.require_authorizations(approval, {}, 'CFD40_AM_001')


def test_measured_max_without_explicit_registered_bound_cannot_authorize():
    approval = dict(schema='cfd40_refresh_root_export_source_review_v1', character_id='CFD40_AM_001',
                    reviewer='root_agent', decision='approved_for_CC_export_source')
    exception = dict(schema='cfd40_refresh_source_asset_native704_exception_v1', character_id='CFD40_AM_001',
                     name='AM001_own_Straight', measured_local_max_mm=3.2, measured_world_max_mm=3.4,
                     bounded_upper_limit_mm=None, magnitude_bound_registered=False)
    with pytest.raises(ValueError, match='no automatic bound'):
        builder.require_authorizations(approval, exception, 'CFD40_AM_001')
