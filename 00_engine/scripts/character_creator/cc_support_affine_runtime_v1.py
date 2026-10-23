"""Small normalized affine response fit for one support, using stdlib only.

A single actual input/output cloud supplies an empirical predictor; held-out
points and all final real geometry gates remain mandatory. No iteration.
"""
import math


def inverse(matrix):
    n=len(matrix); a=[list(map(float,row))+[float(i==j)for j in range(n)]for i,row in enumerate(matrix)]
    determinant=1.
    for col in range(n):
        pivot=max(range(col,n),key=lambda r:abs(a[r][col]))
        if abs(a[pivot][col])<=1e-12:raise ValueError('Rank-deficient support response')
        if pivot!=col:a[col],a[pivot]=a[pivot],a[col];determinant=-determinant
        value=a[col][col];determinant*=value;a[col]=[v/value for v in a[col]]
        for row in range(n):
            if row!=col:
                factor=a[row][col];a[row]=[v-factor*w for v,w in zip(a[row],a[col])]
    return [row[n:]for row in a],determinant


def mm_error(a,b):return math.dist(a,b)*10

def infnorm(matrix):return max(sum(abs(v)for v in row)for row in matrix)

def _solve(X,Y):
    gram=[[sum(row[i]*row[j]for row in X)for j in range(4)]for i in range(4)]
    inv,det=inverse(gram)
    rhs=[[sum(x[i]*y[j]for x,y in zip(X,Y))for j in range(3)]for i in range(4)]
    coefficients=[[sum(inv[i][k]*rhs[k][j]for k in range(4))for j in range(3)]for i in range(4)]
    return coefficients,math.sqrt(infnorm(gram)*infnorm(inv))


def map_rows(rows,linear,translation):
    return [[sum(row[i]*linear[i][j]for i in range(3))+translation[j]for j in range(3)]for row in rows]


def fit_response(input_world,observed_local,desired_local,count):
    if count<12 or any(len(rows)!=count or any(len(row)!=3 for row in rows)for rows in(input_world,observed_local,desired_local)):
        raise ValueError('Complete comparable support3D arrays required')
    if not all(math.isfinite(float(v))for rows in(input_world,observed_local,desired_local)for row in rows for v in row):
        raise ValueError('Finite support response arrays required')
    center=[sum(row[j]for row in input_world)/count for j in range(3)]
    scale=[math.sqrt(sum((row[j]-center[j])**2 for row in input_world)/count)for j in range(3)]
    if min(scale)<=1e-12:raise ValueError('Degenerate response input extent')
    X=[[(row[j]-center[j])/scale[j]for j in range(3)]+[1.]for row in input_world]
    C,design_condition=_solve(X,observed_local)
    A=[[C[i][j]/scale[i]for j in range(3)]for i in range(3)]
    b=[C[3][j]-sum(center[i]*A[i][j]for i in range(3))for j in range(3)]
    invA,det=inverse(A);linear_condition=infnorm(A)*infnorm(invA)
    predicted=map_rows(input_world,A,b);error=max(mm_error(x,y)for x,y in zip(predicted,observed_local))
    half=count//2;checks=[]
    for label,train,test in [('even_to_odd',list(range(0,count,2)),list(range(1,count,2))),
        ('first_to_second',list(range(half)),list(range(half,count))),
        ('second_to_first',list(range(half,count)),list(range(half)))]:
        subset,_=_solve([X[i]for i in train],[observed_local[i]for i in train])
        values=[[sum(X[i][k]*subset[k][j]for k in range(4))for j in range(3)]for i in test]
        checks.append({'split':label,'maximum_local_error_mm':max(mm_error(v,observed_local[i])for i,v in zip(test,values))})
    if max(design_condition,linear_condition)>=100 or abs(det)<=1e-6 or max([error]+[c['maximum_local_error_mm']for c in checks])>.002:
        raise ValueError('Support response condition/held-out prediction exceeds fixed contract')
    submitted=map_rows([[row[j]-b[j]for j in range(3)]for row in desired_local],invA,[0.,0.,0.])
    shifts=[mm_error(x,y)for x,y in zip(submitted,input_world)]
    return {'count':count,'linear_row_vector_3x3':A,'translation_cm':b,'submitted_input_cm':submitted,
        'rank':4,'normalized_design_condition_upper_bound':design_condition,'linear_condition_inf':linear_condition,
        'determinant':det,'fit_max_mm':error,'held_out':checks,'input_shift_max_mm':max(shifts),
        'prediction_max_mm':max(mm_error(x,y)for x,y in zip(map_rows(submitted,A,b),desired_local)),
        'actual_corrected_result_verified':False,'protection_limit_mm':.002,
        'scope':'One empirical same-scene support response and one correction; final raw/render/save/reload gates mandatory.'}
