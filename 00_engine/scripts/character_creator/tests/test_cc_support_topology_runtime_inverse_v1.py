import copy
import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cc_support_topology_runtime_inverse_v1 as solve
import cc_support_evaluated_inverse_v1 as topology


def actual():
    p=Path(__file__).resolve().parents[1]/'runtime_staging/character_refresh_20261018_v1/delicate_WF003_evaluated_support_model_v1.json'
    if not p.exists():pytest.skip('Actual topology proof unavailable')
    return json.loads(p.read_text())


@pytest.mark.parametrize('name',['CC_Base_EyeOcclusion','CC_Base_TearLine'])
def test_stdlib_inverse_matches_independent_saved_solution_and_uses_current_response(name):
    row=actual()['supports'][name]
    current=dict(linear_row_vector_3x3=row['import_linear_row_vector_3x3'],translation_cm=row['import_translation_cm'])
    result=solve.solve(row['applied_local_cm'],row['source_local_cm'],row['faces'],current,row)
    assert topology.max_mm(result['submitted_corrected_input_cm'],row['submitted_corrected_input_cm'])<1e-8
    assert result['operator_condition_inf']<10 and not result['actual_final_evaluated_geometry_verified']
    # A different live subject's transform produces a different input yet the
    # same desired evaluated local geometry, without borrowing old coefficients.
    changed=copy.deepcopy(current);changed['translation_cm'][0]+=.2
    other=solve.solve(row['applied_local_cm'],row['source_local_cm'],row['faces'],changed,row)
    assert topology.max_mm(other['submitted_corrected_input_cm'],result['submitted_corrected_input_cm'])>1
    assert other['algebra_predicted_final_max_mm']<1e-7


def test_topology_or_corner_mismatch_is_not_calibrated_away():
    row=actual()['supports']['CC_Base_EyeOcclusion'];current=dict(linear_row_vector_3x3=row['import_linear_row_vector_3x3'],translation_cm=row['import_translation_cm'])
    wrong=copy.deepcopy(row);wrong['corner_identity_indices']=[]
    with pytest.raises(ValueError):solve.solve(row['applied_local_cm'],row['source_local_cm'],row['faces'],current,wrong)
