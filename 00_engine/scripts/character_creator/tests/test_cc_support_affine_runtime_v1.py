from pathlib import Path
import json
import sys
import math
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cc_support_affine_runtime_v1 as fit


def points(n):return [[(i%n)/n,math.sin(i*.3),math.cos(i*.7)]for i in range(n)]


def test_independent190point_response_and_inverse_recover_desired_origin():
    W=points(190);A=[[.98,.001,0.],[0.,.98,.002],[.001,0.,.98]];b=[.03,-.01,.02]
    P=fit.map_rows(W,A,b);desired=[[x+.02,y-.03,z+.01]for x,y,z in W]
    result=fit.fit_response(W,P,desired,190)
    predicted=fit.map_rows(result['submitted_input_cm'],A,b)
    assert max(math.dist(a,b)*10 for a,b in zip(predicted,desired))<1e-8
    assert result['rank']==4 and not result['actual_corrected_result_verified']


@pytest.mark.parametrize('kind',['rank','nonfinite','nonlinear'])
def test_unsupported_mapping_cannot_become_restoration_input(kind):
    W=points(190);P=[r[:]for r in W]
    if kind=='rank':W=[[x,0.,0.]for x,y,z in W]
    elif kind=='nonfinite':P[0][0]=float('nan')
    else:P=[[x+x*x*.1,y,z]for x,y,z in P]
    with pytest.raises(ValueError):fit.fit_response(W,P,points(190),190)


def test_runtime_stdlib_solver_matches_actual_v3_empirical_response():
    root=Path(__file__).resolve().parents[4]
    model=root/'00_engine/outputs/character_refresh_20261018_v1/eye_occlusion_WF003_inverse_model_v1.json'
    if not model.exists():pytest.skip('Actual v3 model unavailable')
    actual=json.loads(model.read_text())
    result=fit.fit_response(actual['source_world_cm'],actual['observed_v3_local_cm'],actual['desired_local_cm'],182)
    assert result['fit_max_mm']==pytest.approx(.0001494091,abs=1e-8)
    assert max(math.dist(a,b)*10 for a,b in zip(result['submitted_input_cm'],actual['submitted_compensated_input_cm']))<1e-8
