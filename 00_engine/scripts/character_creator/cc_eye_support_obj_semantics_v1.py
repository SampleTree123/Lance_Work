"""Scoped native support OBJ semantics; no arbitrary normal-angle tolerance.

Changed normals must be explained by the actual geometry using the observed
CC fan-triangle area-weighted rule, within one6-decimal displayed integer unit
per component on each export independently. UV/topology/material/s stay exact.
"""
import hashlib
import math
import re

NORMAL_QUANTUM = 1e-6
GEOMETRY_LIMIT_MM = .002


def sub(a,b): return [x-y for x,y in zip(a,b)]
def cross(a,b): return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def unit(v):
    length=math.sqrt(dot(v,v))
    if not math.isfinite(length) or length<=1e-20: raise ValueError('Finite nonzero native normal required')
    return [x/length for x in v]
def angle(a,b):
    return math.degrees(math.atan2(math.sqrt(dot(cross(a,b),cross(a,b))),dot(a,b)))


def read_native(path):
    values={'v':[],'vt':[],'vn':[]}; normals_text=[]; faces=[]; group=''; material=None; smoothing=None
    with open(path,encoding='utf-8-sig') as handle:
        for line in handle:
            t=line.split()
            if not t or t[0].startswith('#'): continue
            if t[0] in values:
                row=[float(x)for x in t[1:]]
                if len(row) not in ((2,3)if t[0]=='vt' else(3,)) or not all(math.isfinite(x)for x in row):
                    raise ValueError('Finite native OBJ attributes required')
                values[t[0]].append(row)
                if t[0]=='vn':normals_text.append(t[1:])
            elif t[0]in('g','o'):group=' '.join(t[1:])
            elif t[0]=='usemtl':material=' '.join(t[1:])
            elif t[0]=='s':smoothing=' '.join(t[1:])
            elif t[0]=='f':
                corners=[]
                for token in t[1:]:
                    fields=token.split('/')
                    if len(fields)!=3 or any(not x or int(x)<=0 for x in fields):
                        raise ValueError('Complete positive native corner references required')
                    corners.append([int(x)-1 for x in fields])
                if len(corners)<3:raise ValueError('Native polygon needs3corners')
                faces.append({'corners':corners,'group':group,'material':material,'smoothing':smoothing})
    if not faces or not values['v'] or not values['vt'] or not values['vn']:
        raise ValueError('Complete native support mesh required')
    for face in faces:
        for corner in face['corners']:
            if any(index>=len(values[k])for k,index in zip(('v','vt','vn'),corner)):
                raise ValueError('Native corner reference outside attribute array')
    return dict(values,faces=faces,normals_text=normals_text)


def geometry_vertex_normals(mesh):
    accum=[[0.,0.,0.]for _ in mesh['v']]
    states={face['smoothing']for face in mesh['faces']}
    if len(states)!=1 or next(iter(states)) in(None,'off','0'):
        raise ValueError('Observed normal-rebuild rule requires one explicit smooth group')
    for face in mesh['faces']:
        ids=[c[0]for c in face['corners']]
        for j in range(1,len(ids)-1):
            a,b,c=ids[0],ids[j],ids[j+1]
            vector=cross(sub(mesh['v'][b],mesh['v'][a]),sub(mesh['v'][c],mesh['v'][a]))
            for index in(a,b,c):accum[index]=[x+y for x,y in zip(accum[index],vector)]
    return [unit(v)for v in accum]


def explain_normals(mesh):
    computed=geometry_vertex_normals(mesh)
    if any(not re.fullmatch(r'-?\d+\.\d{6}',s)for row in mesh['normals_text']for s in row):
        raise ValueError('Expected observed CC six-decimal native normal representation')
    maximum_units=0; maximum_component=0.; maximum_vector=0.; maximum_angle=0.
    for face in mesh['faces']:
        for vi,ti,ni in face['corners']:
            expected=computed[vi]; stored=mesh['vn'][ni]
            units=[abs(round(x/NORMAL_QUANTUM)-round(y/NORMAL_QUANTUM))for x,y in zip(expected,stored)]
            maximum_units=max(maximum_units,max(units)); maximum_component=max(maximum_component,max(abs(x-y)for x,y in zip(expected,stored)))
            maximum_vector=max(maximum_vector,math.dist(expected,stored));maximum_angle=max(maximum_angle,angle(expected,stored))
    return {'passed':maximum_units<=1,'maximum_displayed_component_units':int(maximum_units),
        'normal_component_quantum':NORMAL_QUANTUM,'allowed_displayed_component_units':1,
        'maximum_component_residual':maximum_component,'maximum_vector_residual':maximum_vector,
        'maximum_angle_residual_degrees':maximum_angle,
        'rule':'OBJ-order fan triangulation; area-weighted adjacent triangle cross products; normalize per vertex',
        'scope':'Each export independently explains normals from its own geometry; no global normal-change angle allowance'},computed


def compare_native_semantics(before_path,after_path):
    before,after=read_native(before_path),read_native(after_path)
    topology=lambda m:[[c[0]for c in f['corners']]for f in m['faces']]
    states=lambda m:[(f['group'],f['material'],f['smoothing'])for f in m['faces']]
    uvs=lambda m:[[m['vt'][c[1]]for c in f['corners']]for f in m['faces']]
    normal_values=lambda m:[m['vn'][c[2]]for f in m['faces']for c in f['corners']]
    same=(len(before['v'])==len(after['v'])and topology(before)==topology(after))
    state_same=states(before)==states(after);uv_same=uvs(before)==uvs(after)
    result={'passed':False,'topology_vertex_order_unchanged':same,'group_material_smoothing_per_face_unchanged':state_same,
        'uv_per_corner_exact':uv_same,'geometry_limit_mm':GEOMETRY_LIMIT_MM,'normal_component_quantum':NORMAL_QUANTUM,
        'before_sha256':hashlib.sha256(open(before_path,'rb').read()).hexdigest(),
        'after_sha256':hashlib.sha256(open(after_path,'rb').read()).hexdigest(),
        'normal_angle_limit_used':False,'text_sha_equality_required':False}
    if not same or not state_same or not uv_same:return result
    geometry=max(math.dist(a,b)*10 for a,b in zip(before['v'],after['v']))
    old,new=normal_values(before),normal_values(after)
    angles=[angle(a,b)for a,b in zip(old,new)];flips=sum(dot(a,b)<=0 for a,b in zip(old,new))
    unchanged=old==new
    result.update(native_vertex_max_delta_mm=geometry,normal_numeric_per_corner_unchanged=unchanged,
        normal_flip_count=flips,normal_change_max_degrees=max(angles),normal_change_mean_degrees=sum(angles)/len(angles),
        normal_vector_max_delta=max(math.dist(a,b)for a,b in zip(old,new)))
    if unchanged:
        explained=True;result['normal_semantics']='Exact resolved corner vectors'
    else:
        source,C=explain_normals(before);actual,D=explain_normals(after)
        explained=source['passed']and actual['passed']
        result.update(before_normal_geometry_explanation=source,after_normal_geometry_explanation=actual,
            geometry_predicted_normal_change_max_degrees=max(angle(a,b)for a,b in zip(C,D)),
            normal_semantics='Both independently match native geometric rebuild within one displayed component unit')
    result['passed']=geometry<=GEOMETRY_LIMIT_MM and flips==0 and explained
    return result
