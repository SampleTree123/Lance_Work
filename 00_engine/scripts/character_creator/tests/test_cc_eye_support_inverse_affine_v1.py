"""A frozen empirical model predicts one origin; it never accepts geometry."""
import copy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cc_eye_support_inverse_affine_v1 as inverse


@pytest.fixture
def actual_model():
    root=Path(__file__).resolve().parents[4]
    output=root/'00_engine/outputs/character_creator_bridge/artifacts/character_refresh_20261018_v1/eye_occlusion_WF003_identity_v3'
    if not (output/'after_identity_raw_snapshot.json').exists():
        pytest.skip('Actual source-bound v3 evidence unavailable')
    return inverse.fit_from_v3(output/'eye_support_identity_report.json',output/'post_source_export_snapshot.json',
        output/'after_identity_raw_snapshot.json',output/'IDENTITY_same_support_world.obj'),output


def test_actual_fit_well_conditioned_crossvalidated_and_only_empirically_predicts(actual_model):
    model,output=actual_model
    metrics=model['metrics']
    assert metrics['rank']==4 and metrics['normalized_design_condition']<2
    assert metrics['linear_condition']<1.001
    assert metrics['fit_max_mm']<.0002
    assert max(r['maximum_local_error_mm'] for r in metrics['held_out'])<.0003
    assert metrics['input_shift_max_mm']==pytest.approx(.25675830266,abs=1e-7)
    assert not model['causal_mapping_independently_probed'] and not model['actual_corrected_identity_verified']
    checked=inverse.verify_model(model)
    assert checked['compensated_prediction_max_mm']<1e-8 and checked['actual_verified'] is False
    before=json.loads((output/'post_source_export_snapshot.json').read_text())
    assert inverse.verify_live_origin(model,before)['local_origin_max_mm']==0


@pytest.mark.parametrize('kind',['rank','condition','held_out','nan_input','changed_candidate','changed_origin'])
def test_model_evidence_and_live_origin_fail_closed(actual_model,kind):
    model,output=actual_model;model=copy.deepcopy(model)
    if kind=='rank':model['metrics']['rank']=3
    elif kind=='condition':model['metrics']['linear_condition']=101
    elif kind=='held_out':model['metrics']['held_out'][0]['maximum_local_error_mm']=.0021
    elif kind=='nan_input':model['submitted_compensated_input_cm'][0][0]=float('nan')
    elif kind=='changed_candidate':model['submitted_compensated_input_cm'][0][0]+=.001
    elif kind=='changed_origin':
        before=json.loads((output/'post_source_export_snapshot.json').read_text())
        before['target_world']['world'][0][0]+=.00003
        with pytest.raises(ValueError,match='origin'):
            inverse.verify_live_origin(model,before)
        return
    with pytest.raises(ValueError):inverse.verify_model(model)
