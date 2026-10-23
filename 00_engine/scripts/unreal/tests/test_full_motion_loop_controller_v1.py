"""Reject five-second or stale-policy replies at the full-loop UI boundary."""
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_cfd40_full_motion_loop_review_v1 as ui


@pytest.mark.parametrize('row', [{}, {'success': True, 'policy': 'oneshot'},
                                  {'success': False, 'policy': ui.POLICY}])
def test_reject_missing_failed_or_wrong_loop_policy(row):
    with pytest.raises(ValueError):
        ui.verify_loop_result({'full_motion_loop_readback': row}, {'action': 'playback'})


def test_accept_verified_loop_and_restore_without_playback():
    result = {'full_motion_loop_readback': {'success': True, 'policy': ui.POLICY}}
    assert ui.verify_loop_result(result, {'action': 'playback'}) is result
    assert ui.verify_loop_result({}, {'action': 'restore'}) == {}
