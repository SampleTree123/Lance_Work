import copy
import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cc_support_evaluated_inverse_v1 as model


def actual():
    path=Path(__file__).resolve().parents[1]/'runtime_staging/character_refresh_20261018_v1/delicate_WF003_evaluated_support_model_v1.json'
    if not path.exists():pytest.skip('Actual v2 evaluated model unavailable')
    return json.loads(path.read_text())


def test_actual_v2_render_is_explained_by_fixed_topology_and_inverse_is_solved():
    data=actual();result=model.verify_model(data)
    assert model.verify_pinned_evidence(data,lambda p:json.loads(Path(p).read_text()))['additional_calibration_calls']==0
    assert result['CC_Base_EyeOcclusion']['actual_v2_render_prediction_max_mm']==pytest.approx(.00022650110045589425)
    assert result['CC_Base_TearLine']['actual_v2_render_prediction_max_mm']==pytest.approx(.0002408132103477519)
    assert result['CC_Base_EyeOcclusion']['corner_identity_indices']==[0,3,48,51,91,94,139,142]
    assert result['CC_Base_TearLine']['corner_identity_indices']==[]
    assert not result['CC_Base_EyeOcclusion']['actual_corrected_render_verified']


@pytest.mark.parametrize('damage',['corner','render','inverse','import','source'])
def test_wrong_operator_or_unbound_solution_cannot_be_submitted(damage):
    data=copy.deepcopy(actual());row=data['supports']['CC_Base_EyeOcclusion']
    if damage=='corner':row['corner_identity_indices']=[]
    elif damage=='render':row['v2_rendered_local_cm'][30][0]+=.001
    elif damage=='inverse':row['desired_pre_evaluation_raw_local_cm'][30][0]+=.001
    elif damage=='import':row['submitted_corrected_input_cm'][30][0]+=.001
    else:data['source_project']['sha256']='different'
    with pytest.raises(ValueError):model.verify_model(data)


def test_array_provenance_and_live_applied_origin_stay_strict():
    data=actual();row=data['supports']['CC_Base_TearLine'];row['source_local_cm'][0][0]+=.00001
    with pytest.raises(ValueError):model.verify_pinned_evidence(data,lambda p:json.loads(Path(p).read_text()))
    geometry={'meshes':[dict(name=name,vertex_count=r['count'],vertices=copy.deepcopy(r['applied_local_cm']))for name,r in data['supports'].items()]}
    assert max(model.verify_live_applied(data,geometry).values())==0
    geometry['meshes'][0]['vertices'][0][0]+=.00003
    with pytest.raises(ValueError):model.verify_live_applied(data,geometry)
