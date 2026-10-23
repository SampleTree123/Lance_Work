"""Source-bound support render response: fixed topology smoothing, no calibration.

The operator is not fitted: interior Catmull-Clark old vertices, boundary
.75/.125/.125, and identity for a vertex incident to exactly one face.
Actual v2 raw/render evidence must support every row before one inverse is used.
"""
import math


def stencil(faces,count):
    vf=[[]for _ in range(count)];adj=[set()for _ in range(count)];edges={}
    for fi,face in enumerate(faces):
        if len(face)!=4 or len(set(face))!=4 or any(type(i)is not int or i<0 or i>=count for i in face):
            raise ValueError('Exact support quad topology required')
        for i in face:vf[i].append(fi)
        for a,b in zip(face,face[1:]+face[:1]):
            edges.setdefault(tuple(sorted((a,b))),[]).append(fi);adj[a].add(b);adj[b].add(a)
    boundary=[set()for _ in range(count)]
    for (a,b),linked in edges.items():
        if len(linked)>2:raise ValueError('Nonmanifold support edge')
        if len(linked)==1:boundary[a].add(b);boundary[b].add(a)
    rows=[];corners=[]
    for i,linked in enumerate(vf):
        if not linked:raise ValueError('Unsupported orphan vertex')
        if len(linked)==1:row={i:1.};corners.append(i)
        elif boundary[i]:
            if len(boundary[i])!=2:raise ValueError('Ambiguous support boundary')
            row={i:.75,**{j:.125 for j in boundary[i]}}
        else:
            n=len(linked);row={i:(n-3)/n}
            for fi in linked:
                for j in faces[fi]:row[j]=row.get(j,0.)+1/(n*n*len(faces[fi]))
            for j in adj[i]:
                row[i]=row.get(i,0.)+1/(n*len(adj[i]));row[j]=row.get(j,0.)+1/(n*len(adj[i]))
        if abs(sum(row.values())-1)>1e-12:raise ValueError('Invalid topology row sum')
        rows.append(row)
    return rows,corners


def apply(rows,value):return [[sum(w*value[j][axis]for j,w in row.items())for axis in range(3)]for row in rows]
def add(a,b):return [[x+y for x,y in zip(i,j)]for i,j in zip(a,b)]
def sub(a,b):return [[x-y for x,y in zip(i,j)]for i,j in zip(a,b)]
def max_mm(a,b):return max(math.dist(i,j)*10 for i,j in zip(a,b))
def affine(value,A,b):return [[sum(v[k]*A[k][j]for k in range(3))+b[j]for j in range(3)]for v in value]


def verify_support(row):
    n=row['count'];keys=('source_local_cm','applied_local_cm','v2_raw_local_cm','v2_rendered_local_cm','desired_pre_evaluation_raw_local_cm','submitted_corrected_input_cm')
    if any(len(row[k])!=n or any(len(v)!=3 or not all(math.isfinite(x)for x in v)for v in row[k])for k in keys):raise ValueError('Invalid support model arrays')
    S,corners=stencil(row['faces'],n)
    if corners!=row['corner_identity_indices']:raise ValueError('Single-face identity corner rule changed')
    original,applied,raw,rendered,target,submitted=[row[k]for k in keys]
    prediction=add(applied,apply(S,sub(raw,applied)))
    error=max_mm(prediction,rendered)
    if error>.002 or abs(error-row['render_prediction_max_mm'])>1e-8:raise ValueError('Actual evaluated response does not support topology operator')
    if row['operator_rank']!=n or row['operator_condition2']>=10:raise ValueError('Unsupported evaluated operator inverse')
    inverse_error=max_mm(add(applied,apply(S,sub(target,applied))),original)
    import_error=max_mm(affine(submitted,row['import_linear_row_vector_3x3'],row['import_translation_cm']),target)
    if max(inverse_error,import_error)>1e-7:raise ValueError('Frozen inverse does not solve desired evaluated target')
    return {'count':n,'corner_identity_indices':corners,'actual_v2_render_prediction_max_mm':error,'inverse_algebra_max_mm':inverse_error,'import_algebra_max_mm':import_error,'actual_corrected_render_verified':False}


def verify_model(model):
    if model['source_project']['sha256']!='3abfa1d12f129ee86ceaacf6f80a467e243cf4c3fd0045173e97b875b9f125f8' or set(model['supports'])!={'CC_Base_EyeOcclusion','CC_Base_TearLine'}:
        raise ValueError('Exact original corrected source/support model required')
    result={name:verify_support(row)for name,row in model['supports'].items()}
    if result['CC_Base_EyeOcclusion']['count']!=182 or result['CC_Base_TearLine']['count']!=190:raise ValueError('Support topology count changed')
    return result


def verify_pinned_evidence(model,read_json):
    files=model['source_files'];report=read_json(files['v2_report']['path'])
    if (report.get('success')is not False or not report.get('restored_source')or not report.get('source_unchanged')
            or report['source_project']['sha256']!=model['source_project']['sha256']
            or report.get('error',{}).get('message')!='Nonpending protected geometry changed: restored_rendered'):
        raise ValueError('Exact restored v2 evaluated-response evidence required')
    snapshots={key:read_json(files[key]['path'])for key in('original','applied','raw','rendered')}
    for name,row in model['supports'].items():
        for snapshot,key in(('original','source_local_cm'),('applied','applied_local_cm'),('raw','v2_raw_local_cm'),('rendered','v2_rendered_local_cm')):
            meshes=[m for m in snapshots[snapshot]['other_meshes']['meshes']if m['name']==name and m['vertex_count']==row['count']]
            if len(meshes)!=1 or meshes[0]['vertices']!=row[key]:raise ValueError('Model arrays do not match pinned actual evidence')
        if snapshots['original']['worlds'][name]['faces']!=row['faces']:raise ValueError('Pinned support faces changed')
        imported=read_json(files[row['import_model_key']]['path'])
        if imported['linear_row_vector_3x3']!=row['import_linear_row_vector_3x3']or imported['translation_cm']!=row['import_translation_cm']:
            raise ValueError('Actual import response model changed')
    return {'actual_v2_report_and_all_arrays_bound':True,'additional_calibration_calls':0}


def verify_live_applied(model,geometry):
    result={}
    for name,row in model['supports'].items():
        mesh=[m for m in geometry['meshes']if m['name']==name and m['vertex_count']==row['count']]
        if len(mesh)!=1:raise ValueError('Ambiguous applied support model origin')
        error=max_mm(mesh[0]['vertices'],row['applied_local_cm']);result[name]=error
        if error>.0002:raise ValueError('Applied support origin differs from pinned actual v2')
    return result
