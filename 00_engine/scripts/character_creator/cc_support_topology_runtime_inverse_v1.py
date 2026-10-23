"""One live male response per support plus known topology inverse; stdlib only."""
import math
import cc_support_affine_runtime_v1 as affine
import cc_support_evaluated_inverse_v1 as evaluated


def solve(applied,original,faces,response,proven_topology):
    count=len(original)
    if count not in(182,190)or len(applied)!=count or faces!=proven_topology['faces']:
        raise ValueError('Exact independently proven support topology required')
    rows,corners=evaluated.stencil(faces,count)
    if corners!=proven_topology['corner_identity_indices']:raise ValueError('Proven support corner rule changed')
    matrix=[[row.get(j,0.)for j in range(count)]for row in rows]
    inverse,det=affine.inverse(matrix);condition=affine.infnorm(matrix)*affine.infnorm(inverse)
    if condition>=10:raise ValueError('Topology inverse is ill-conditioned')
    delta=evaluated.sub(original,applied)
    correction=[[sum(inverse[i][j]*delta[j][axis]for j in range(count))for axis in range(3)]for i in range(count)]
    raw=evaluated.add(applied,correction)
    A=response['linear_row_vector_3x3'];b=response['translation_cm'];invA,_=affine.inverse(A)
    submitted=affine.map_rows([[r[j]-b[j]for j in range(3)]for r in raw],invA,[0.,0.,0.])
    prediction=evaluated.add(applied,evaluated.apply(rows,evaluated.sub(affine.map_rows(submitted,A,b),applied)))
    error=evaluated.max_mm(prediction,original)
    if not math.isfinite(error)or error>1e-7:raise ValueError('One-shot support inverse algebra failed')
    return {'count':count,'corner_identity_indices':corners,'operator_rank':count,'operator_condition_inf':condition,
        'pre_evaluation_raw_local_cm':raw,'submitted_corrected_input_cm':submitted,'algebra_predicted_final_max_mm':error,
        'raw_precompensation_vs_original_max_mm':evaluated.max_mm(raw,original),
        'actual_final_evaluated_geometry_verified':False,'additional_response_calls':1,
        'scope':'Live subject import affine only; topology stencil proven independently. Actual final render/saveReload at0.002mm mandatory.'}
