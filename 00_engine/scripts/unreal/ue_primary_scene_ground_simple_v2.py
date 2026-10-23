"""Fresh, diagnostic-bound simple-collision ground checks in a private v1 clone.

Only ground object traces become simple. Body/camera/standing stay complex
Visibility queries. Simple collision support is not exact rendered mesh support.
"""
from pathlib import Path
import ast
import importlib.util
import math
import uuid
import scene_site_review_geometry_v1 as geo
import scene_site_survey_v1 as offline

S=Path(__file__).resolve().parent
BASE=S/'ue_primary_scene_ground_objects_v1.py'
_session=None


def _diagnostic(pin,position,component_path):
    if not isinstance(pin,dict) or not pin.get('path') or not pin.get('sha256'):
        raise ValueError('Require explicit diagnostic pin with path and sha256')
    actual=geo.pin(pin['path'])
    if actual['sha256']!=pin['sha256']:raise ValueError('Diagnostic source changed')
    data=offline.read(actual['path'])
    if data.get('component')!=component_path:raise ValueError('Diagnostic must name the exact intended ground component')
    downward=[]
    for row in data.get('traces',[]):
        a,b=row.get('start',[]),row.get('end',[])
        if len(a)!=3 or len(b)!=3 or not all(math.isfinite(float(v)) for v in [*a,*b]):continue
        if a[2]<=b[2] or any(abs(a[i]-b[i])>1e-3 or abs(a[i]-position[i])>1e-3 for i in (0,1)):continue
        downward.append(row)
    hits=[row for row in downward if row.get('complex') is False and isinstance(row.get('parsed'),dict)]
    misses=[row for row in downward if row.get('complex') is True and row.get('parsed') is None]
    if not hits or not misses:raise ValueError('Require same-XY complex miss and simple downward hit diagnostic')
    hit=hits[0];parsed=hit['parsed'];point=parsed.get('point',[]);normal=parsed.get('normal',[])
    if len(point)!=3 or len(normal)!=3 or not all(math.isfinite(float(v)) for v in [*point,*normal]):
        raise ValueError('Diagnostic requires finite support point and normal')
    if any(abs(point[i]-position[i])>1e-3 for i in (0,1)) or normal[2]<.94:
        raise ValueError('Diagnostic is not a flat simple ground hit at requested XY')
    if component_path not in str(hit.get('hit','')):
        raise ValueError('Raw diagnostic hit must retain exact supporting component identity')
    return actual,data


def _private_adapter(diagnostic_pin):
    spec=importlib.util.spec_from_file_location('_dm_simple_ground_'+uuid.uuid4().hex,BASE)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    tree=ast.parse(BASE.read_text(encoding='utf-8-sig'))
    ray=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_object_ray')
    calls=[n for n in ast.walk(ray) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
        and n.func.attr=='line_trace_single_for_objects']
    if len(calls)!=1 or not isinstance(calls[0].args[4],ast.Constant) or calls[0].args[4].value is not True:
        raise ValueError('Frozen v1 ground object trace changed')
    calls[0].args[4]=ast.Constant(False)
    for n in ast.walk(ray):
        if isinstance(n,ast.Constant) and n.value=='object_type_complex':n.value='object_type_simple'
    start=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='start_point')
    policies=[n.value for n in start.body if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id=='policy' for t in n.targets)]
    if len(policies)!=1:raise ValueError('Frozen v1 policy constructor changed')
    policy=policies[0];changes=0
    for i,key in enumerate(policy.keys):
        if key.value=='id':policy.values[i]=ast.Constant('targeted_object_type_ground_simple_v2');changes+=1
        if key.value=='trace_complex':policy.values[i]=ast.Constant(False);changes+=1
    if changes!=2:raise ValueError('Frozen v1 policy fields changed')
    for key,value in (
        ('diagnostic_evidence',ast.Name(id='SIMPLE_DIAGNOSTIC_PIN',ctx=ast.Load())),
        ('base_adapter_source',ast.Name(id='SIMPLE_BASE_PIN',ctx=ast.Load())),
        ('simple_collision_surface_limitation',ast.Constant('Simple collision proxy ground only; measured collision height does not certify exact rendered mesh contact. Visual ground contact,background and exposure require review.'))):
        policy.keys.append(ast.Constant(key));policy.values.append(value)
    # The fresh attempt pins both the unchanged implementation and diagnostic.
    appended=0
    for n in ast.walk(start):
        if isinstance(n,ast.AugAssign) and isinstance(n.target,ast.Subscript) and isinstance(n.target.slice,ast.Constant) and n.target.slice.value=='source_pins':
            n.value.elts += [ast.Name(id='SIMPLE_DIAGNOSTIC_PIN',ctx=ast.Load()),ast.Name(id='SIMPLE_BASE_PIN',ctx=ast.Load())];appended+=1
    if appended!=1:raise ValueError('Frozen v1 source pin constructor changed')
    module.SIMPLE_DIAGNOSTIC_PIN=diagnostic_pin;module.SIMPLE_BASE_PIN=geo.pin(BASE)
    for node in (ray,start):
        ast.fix_missing_locations(node)
        exec(compile(ast.Module(body=[node],type_ignores=[]),__file__+'::<private-simple-ground>','exec'),module.__dict__)
    # Every new adapter_source pin must identify this wrapper; BASE is separately pinned.
    module.__file__=__file__
    return module


def start_point(position,yaw,*,reason,diagnostic_pin,support_component_path,
                allow_screen_findings=False,run_root=offline.RUN,round_index=6):
    global _session
    position=[float(v) for v in position]
    if len(position)!=3 or not all(math.isfinite(v) for v in position):raise ValueError('Require finite XYZ')
    pin,data=_diagnostic(diagnostic_pin,position,support_component_path)
    private=_private_adapter(pin)
    targets=private._targets(None,None,support_component_path)
    if len(targets)!=1 or targets[0]['static_mesh'] not in str(data.get('mesh','')):
        raise ValueError('Current target mesh must match diagnostic mesh')
    _session=private
    return private.start_point(position,yaw,reason=reason,support_component_path=support_component_path,
        allow_screen_findings=allow_screen_findings,run_root=run_root,round_index=round_index)


def poll():return _session.poll() if _session else {'status':'idle'}
def cancel():return _session.cancel() if _session else {'status':'idle'}
