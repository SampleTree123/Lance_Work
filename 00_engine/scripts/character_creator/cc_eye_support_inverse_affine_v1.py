"""Offline source-bound inverse-affine fit; runtime verification uses stdlib only.

This is an empirical one-call identity candidate, not an accepted repair or a
claim about CC's internal inverse skinning. All real final gates remain0.002mm.
"""
import hashlib
import json
import math
from pathlib import Path

LIMIT_MM = .002
ORIGIN_LIMIT_MM = .0002
TARGET = {'part_type': '5', 'mesh_name': 'CC_Base_EyeOcclusion', 'vertex_count': 182}


def record(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}


def _points(value):
    if len(value) != 182 or any(len(row) != 3 for row in value) or not all(math.isfinite(float(x)) for row in value for x in row):
        raise ValueError('Exact finite182x3 source-bound coordinates required')
    return [[float(x) for x in row] for row in value]


def deltas(first, second):
    first, second = _points(first), _points(second)
    return [math.dist(a, b)*10 for a,b in zip(first,second)]


def map_rows(points, linear, translation):
    return [[sum(row[i]*linear[i][j] for i in range(3)) + translation[j] for j in range(3)] for row in _points(points)]


def _target(snapshot):
    matches = [m for m in snapshot['geometry']['meshes'] if m['owner']=='avatar/5:CC_Base_EyeOcclusion'
        and m['name']=='CC_Base_EyeOcclusion' and m['vertex_count']==182]
    if len(matches) != 1: raise ValueError('One exact original support required')
    return matches[0]


def fit_from_v3(report_path, before_path, after_path, input_path):
    import numpy as np  # Offline only; never required by the CC-side verifier.
    files = {name: record(path) for name,path in [('report',report_path),('before',before_path),('after',after_path),('input_obj',input_path)]}
    report, before, after = [json.loads(Path(p).read_text(encoding='utf-8-sig')) for p in (report_path,before_path,after_path)]
    if (report.get('success') is not False or report.get('restored_source') is not True
            or report.get('source_unchanged') is not True
            or report.get('error',{}).get('message') != 'Identity changed protected source: after_identity_raw'
            or report.get('replace_status',{}).get('is_error') is not False
            or str(report['replace_status'].get('status_code')) != '0'):
        raise ValueError('Restored actual v3 single-call identity failure required')
    steps=[s for s in report['steps'] if s['phase']=='after_identity_raw']
    if (len(steps)!=1 or max(steps[0]['all_body_local_max_mm'],steps[0]['all_body_world_max_mm'])>LIMIT_MM
            or not steps[0]['eye']['matches'] or not steps[0]['weights_unchanged']
            or not steps[0]['available_material_fingerprint_unchanged']
            or not steps[0]['all_low_high_meshes_and_owners']['available_owner_transforms_preserved']
            or any(row['maximum_local_delta_mm']>LIMIT_MM for row in steps[0]['all_low_high_meshes_and_owners']['meshes']
                   if (row['owner'],row['name'],row['vertex_count'])!=('avatar/5:CC_Base_EyeOcclusion','CC_Base_EyeOcclusion',182))):
        raise ValueError('v3 evidence changed other protected geometry or eye state')
    if not before['support_readbacks']['consistent'] or not after['support_readbacks']['consistent']:
        raise ValueError('Calibration scalar/vector/reacquired reads disagree')
    old, actual = _target(before), _target(after)
    if any(old[k] != actual[k] for k in ('owner','name','vertex_count','face_count','faces_sha256')):
        raise ValueError('Calibration changed target topology')
    source_world = _points(before['target_world']['world']); desired_local = _points(old['vertices'])
    observed_local = _points(actual['vertices'])
    input_world = []
    for line in Path(input_path).read_text(encoding='utf-8-sig').splitlines():
        t=line.split()
        if t[:1]==['v']: input_world.append([float(v) for v in t[1:]])
    if max(deltas(source_world,input_world)) > ORIGIN_LIMIT_MM:
        raise ValueError('Actual submitted input is not same-source SDK world')
    if before['body']['working_subdivision_level'] != 0 or after['body']['working_subdivision_level'] != 0:
        raise ValueError('Actual SubD0 calibration required')
    W=np.asarray(input_world); P=np.asarray(observed_local); L=np.asarray(desired_local)
    center=W.mean(0); scale=W.std(0)
    if np.any(scale<=0): raise ValueError('Degenerate calibration coordinate extent')
    X=np.column_stack(((W-center)/scale,np.ones(len(W))))
    coef,residual,rank,_=np.linalg.lstsq(X,P,rcond=None)
    A=coef[:3]/scale[:,None]; b=coef[3]-center@A
    design_condition=float(np.linalg.cond(X)); linear_condition=float(np.linalg.cond(A)); determinant=float(np.linalg.det(A))
    checks=[]
    for label,train,test in [('even_to_odd',np.arange(0,182,2),np.arange(1,182,2)),
        ('left_to_right',np.arange(91),np.arange(91,182)),('right_to_left',np.arange(91,182),np.arange(91))]:
        subset=np.linalg.lstsq(X[train],P[train],rcond=None)[0]
        error=np.linalg.norm(X[test]@subset-P[test],axis=1)*10
        checks.append({'split':label,'maximum_local_error_mm':float(error.max()),'mean_local_error_mm':float(error.mean())})
    fit_error=np.linalg.norm(X@coef-P,axis=1)*10
    if rank!=4 or max(design_condition,linear_condition)>=100 or abs(determinant)<=1e-6:
        raise ValueError('Ill-conditioned or rank-deficient inverse affine model')
    if max(float(fit_error.max()),max(x['maximum_local_error_mm'] for x in checks)) > LIMIT_MM:
        raise ValueError('Full/held-out affine prediction exceeds unchanged0.002mm gate')
    submitted=np.linalg.solve(A.T,(L-b).T).T
    shift=np.linalg.norm(submitted-W,axis=1)*10
    model={'schema_version':1,'source_project':report['source_project'],'target':TARGET,'source_files':files,
        'fitter':record(__file__),'model_kind':'empirical_same_source_v3_world_input_to_observed_local_affine',
        'causal_mapping_independently_probed':False,'actual_corrected_identity_verified':False,
        'linear_row_vector_3x3':A.tolist(),'translation_cm':b.tolist(),'source_world_cm':source_world,
        'desired_local_cm':desired_local,'observed_v3_local_cm':observed_local,
        'submitted_compensated_input_cm':submitted.tolist(),'faces_sha256':old['faces_sha256'],
        'metrics':{'rank':int(rank),'normalized_design_condition':design_condition,'linear_condition':linear_condition,
            'determinant':determinant,'fit_max_mm':float(fit_error.max()),'held_out':checks,
            'input_shift_max_mm':float(shift.max()),'input_shift_mean_mm':float(shift.mean()),
            'input_axis_span_cm':np.ptp(W,axis=0).tolist(),
            'input_axis_shift_max_cm':np.max(np.abs(submitted-W),axis=0).tolist(),
            'max_normalized_input_shift':float(np.linalg.norm((submitted-W)/scale,axis=1).max())},
        'final_protection_limit_mm':LIMIT_MM,'origin_limit_mm':ORIGIN_LIMIT_MM,
        'scope':'One source-bound compensated identity experiment only. Original post/render/saveReload gates unchanged; no residual iterations or actual lash repair.'}
    verify_model(model)
    return model


def verify_model(model):
    if model['target'] != TARGET or model['final_protection_limit_mm'] != LIMIT_MM or model['origin_limit_mm'] != ORIGIN_LIMIT_MM:
        raise ValueError('Model target/protection contract changed')
    A=model['linear_row_vector_3x3']; b=model['translation_cm']; metrics=model['metrics']
    if len(A)!=3 or any(len(row)!=3 for row in A) or len(b)!=3 or not all(math.isfinite(float(x)) for row in A+[b] for x in row):
        raise ValueError('Finite3x3 model required')
    measured=[metrics[k] for k in ('normalized_design_condition','linear_condition','determinant','fit_max_mm')]
    measured.extend(row['maximum_local_error_mm'] for row in metrics['held_out'])
    if not measured or not all(math.isfinite(float(x)) for x in measured):
        raise ValueError('Finite rank/condition/prediction evidence required')
    if (metrics['rank']!=4 or max(metrics['normalized_design_condition'],metrics['linear_condition'])>=100
            or abs(metrics['determinant'])<=1e-6 or metrics['fit_max_mm']>LIMIT_MM
            or max(x['maximum_local_error_mm'] for x in metrics['held_out'])>LIMIT_MM):
        raise ValueError('Model prediction/rank/condition evidence failed')
    fit=max(deltas(map_rows(model['source_world_cm'],A,b),model['observed_v3_local_cm']))
    prediction=max(deltas(map_rows(model['submitted_compensated_input_cm'],A,b),model['desired_local_cm']))
    if max(fit,prediction)>LIMIT_MM: raise ValueError('Frozen model arrays no longer predict source local')
    return {'v3_fit_max_mm':fit,'compensated_prediction_max_mm':prediction,
        'actual_verified':False,'final_protection_limit_mm':LIMIT_MM}


def verify_live_origin(model, snapshot):
    verify_model(model)
    target=_target(snapshot)
    local=max(deltas(model['desired_local_cm'],target['vertices']))
    world=max(deltas(model['source_world_cm'],snapshot['target_world']['world']))
    if target['faces_sha256']!=model['faces_sha256'] or max(local,world)>ORIGIN_LIMIT_MM:
        raise ValueError('Current origin differs from source-bound v3 calibration')
    return {'local_origin_max_mm':local,'world_origin_max_mm':world,'limit_mm':ORIGIN_LIMIT_MM}
