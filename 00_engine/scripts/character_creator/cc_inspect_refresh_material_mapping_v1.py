"""Bounded AF005 current-scene material/shader read; no texture exports or writes.

Experimental Assembly Technical. Reuse the established recursive owner adapter
and only GetMeshNames/GetMaterialNames/GetShader/GetShaderParameterNames calls.
"""
import importlib
import os
import traceback


def run(library, output_dir, log, api):
    config = library['material_mapping_inspect']
    if config['character_id'] != 'CFD40_AF_005' or os.path.exists(output_dir) and os.listdir(output_dir):
        raise ValueError('Exact AF005 independent mapping capture required')
    for key in ('failed_report', 'editing_checkpoint'):
        record = config[key]
        if api.sha256_file(record['path']) != record['sha256']:
            raise ValueError('Immutable AF005 evidence changed')
    prior = api.read_json(config['failed_report']['path'])
    if prior['config']['character_id'] != config['character_id']:
        raise ValueError('Own AF005 prior evidence required')
    exporter = importlib.import_module('cc_skin_detail_experiment_v1')
    expected = {}
    for label in ('after_skin', 'after_eyes'):
        pin = prior['pixel_stages'][label]
        if api.sha256_file(pin['path']) != pin['sha256']:
            raise ValueError('Own successful material baseline changed')
        for row in api.read_json(pin['path'])['materials']:
            expected[(row['owner'], row['mesh'], row['material'])] = row['properties']['GetShader']
    os.makedirs(output_dir, exist_ok=True)
    report = dict(success=False, read_only=True, config=config, materials=[], errors=[], owners=[],
                  scope='Actual metadata existence only; no preserved-pixel or geometry acceptance',
                  summary_path=os.path.join(output_dir, 'material_mapping_report.json'))
    try:
        avatars = list(api.RLPy.RScene.GetAvatars() or [])
        selected = [str(x.GetID()) for x in (api.RLPy.RScene.GetSelectedObjects() or [])]
        if len(avatars) != 1 or str(avatars[0].GetID()) != config['expected_avatar_id'] or selected != [config['expected_avatar_id']]:
            raise ValueError('Same current AF005 avatar/selection changed')
        avatar = avatars[0]
        report['avatar'] = dict(id=str(avatar.GetID()), name=str(avatar.GetName()), python_type=type(avatar).__name__,
                                actual_working_subdivision=int(avatar.GetSubdivMeshLevel()))
        report['object_lock_api_available'] = {name: callable(getattr(avatar, name, None)) for name in ('IsLocked', 'GetLock')}
        for owner, owner_path in exporter.material_owners(avatar):
            component, component_source = api.hair_material_component(avatar, owner)
            getter = getattr(owner, 'GetMeshNames', None)
            names = [str(x) for x in (getter() or [])] if callable(getter) else [str(x.GetName()) for x in (owner.GetMeshes(False) or [])]
            report['owners'].append(dict(owner=owner_path, id=str(owner.GetID()), component_source=component_source,
                                         component_present=component is not None, mesh_names_raw=names))
            if component is None:
                raise ValueError('Missing real material component: ' + owner_path)
            for mesh in sorted(set(names)):
                material_names = [str(x) for x in (component.GetMaterialNames(mesh) or [])]
                if not material_names:
                    report['errors'].append(dict(owner=owner_path, mesh=mesh, error='No materials returned'))
                for material in sorted(set(material_names)):
                    row = dict(owner=owner_path, mesh=mesh, material=material)
                    try:
                        row['shader'] = str(component.GetShader(mesh, material))
                        row['shader_parameters'] = sorted(str(x) for x in (component.GetShaderParameterNames(mesh, material) or []))
                        row['shader_parameter_count'] = len(row['shader_parameters'])
                    except Exception as error:
                        report['errors'].append(dict(owner=owner_path, mesh=mesh, material=material, error=str(error)))
                    report['materials'].append(row)
        actual = {(x['owner'], x['mesh'], x['material']): x.get('shader') for x in report['materials']}
        report['comparison'] = dict(expected_rows=len(expected), actual_rows=len(actual),
            missing=[list(k) for k in sorted(set(expected) - set(actual))],
            added=[list(k) for k in sorted(set(actual) - set(expected))],
            changed_shaders=[dict(key=list(k), before=expected[k], current=actual[k]) for k in sorted(set(actual) & set(expected)) if actual[k] != expected[k]])
        report['mapping_matches_own_baselines'] = not report['errors'] and actual == expected
        report['selected_after'] = [str(x.GetID()) for x in (api.RLPy.RScene.GetSelectedObjects() or [])]
        if report['selected_after'] != selected:
            raise ValueError('Selection changed during read-only material inspection')
        report['success'] = True
    except Exception as error:
        report['error'] = dict(type=type(error).__name__, message=str(error), traceback=traceback.format_exc())
    report['updated_at'] = api.now()
    api.write_json(report, report['summary_path'])
    return report
