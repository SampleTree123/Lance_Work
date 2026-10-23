"""Freeze assembled preview MIDs into owned, reusable saved material assets.

Import is inert. The caller owns the actor and saves its map after this step.
Source materials, meshes, and actors other than the supplied actor are untouched.
"""
from __future__ import annotations

import hashlib
import json
import re


VERSION = 'dataset_persistent_materials_v2'
OWNER = 'DM_DatasetPersistentMaterialSpec'
PARAMETER_FIELDS = ('scalar_parameter_values', 'vector_parameter_values',
                    'texture_parameter_values')


def _path(value):
    return value.get_path_name() if value is not None else None


def _base_semantics(text):
    """Ignore inherited inactive storage; compare enabled values and usage bits."""
    fields, start, depth = {}, 0, 0
    body = text[1:-1] if text.startswith('(') and text.endswith(')') else text
    for index, char in enumerate(body + ','):
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
        elif char == ',' and depth == 0:
            name, value = body[start:index].split('=', 1)
            fields[name.strip()] = value.strip()
            start = index + 1
    flags = {name: value for name, value in fields.items() if name.startswith('bOverride_')}
    active = {}
    for flag, value in flags.items():
        suffix = flag[len('bOverride_'):]
        if suffix == 'UsageFlags':
            mask = int(value)
            if mask:
                active['UsageFlags'] = int(fields['UsageFlags']) & mask
        elif value.lower() not in ('false', '0'):
            field = suffix if suffix in fields else 'b' + suffix
            if field not in fields:
                raise RuntimeError('Unknown active material base override: ' + flag)
            active[field] = fields[field]
    return {'flags': flags, 'active_values': active}


def _snapshot(material):
    """Use reflected structs, preserving names, associations, indices and GUIDs."""
    arrays = {name: list(material.get_editor_property(name)) for name in PARAMETER_FIELDS}
    base = material.get_editor_property('base_property_overrides')
    # MIC updates fill expression GUIDs from the parent shader; MIDs use zeros.
    evidence = {name: sorted(re.sub(r'\bExpressionGUID=[0-9A-Fa-f]{32}\b',
                                    'ExpressionGUID=<editor-generated>', str(row.export_text()))
                            for row in rows)
                for name, rows in arrays.items()}
    evidence['base_property_overrides'] = _base_semantics(str(base.export_text()))
    return arrays, base, evidence


def freeze_actor(u, actor, asset_root):
    """Persist only dynamic skeletal-component overrides and return readbacks.

    ``asset_root`` must be an owned Render/Capture/Validation folder. Identical local
    parameters over the same saved parent reuse the same MIC. Component binding
    is deferred until every required MIC has been saved and checked.
    """
    if not isinstance(asset_root, str) or not re.fullmatch(
            r'/Game/DataMake/(?:Render|Capture|Validation)/[A-Za-z0-9_/]+', asset_root):
        raise ValueError('Persistent materials require an owned Render/Capture/Validation folder')
    asset_root = asset_root.rstrip('/')
    resolved, visiting, materials, pending = {}, set(), [], []

    def freeze(material):
        if not isinstance(material, u.MaterialInstanceDynamic):
            path = _path(material)
            if not path or path.startswith(('/Engine/Transient', '/Temp/')):
                raise RuntimeError('Dynamic material lacks a saved persistent parent: ' + str(path))
            return material
        source = _path(material)
        if source in resolved:
            return resolved[source]
        if source in visiting:
            raise RuntimeError('Cyclic dynamic material parent chain: ' + source)
        visiting.add(source)
        parent = freeze(material.get_editor_property('parent'))
        arrays, base, values = _snapshot(material)
        spec = json.dumps({'version': VERSION, 'parent': _path(parent),
                           'local_overrides': values}, sort_keys=True, separators=(',', ':'))
        digest = hashlib.sha256(spec.encode('utf-8')).hexdigest()
        target = asset_root + '/MI_' + digest[:24]
        created = not u.EditorAssetLibrary.does_asset_exist(target)
        if created:
            folder, label = target.rsplit('/', 1)
            instance = u.AssetToolsHelpers.get_asset_tools().create_asset(
                label, folder, u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
            if not isinstance(instance, u.MaterialInstanceConstant):
                raise RuntimeError('Cannot create persistent material: ' + target)
            u.MaterialEditingLibrary.set_material_instance_parent(instance, parent)
            for name, rows in arrays.items():
                instance.set_editor_property(name, rows)
            instance.set_editor_property('base_property_overrides', base)
            u.MaterialEditingLibrary.update_material_instance(instance)
            u.EditorAssetLibrary.set_metadata_tag(instance, OWNER, spec)
        else:
            instance = u.load_asset(target)
        if not isinstance(instance, u.MaterialInstanceConstant):
            raise RuntimeError('Persistent material has wrong class: ' + target)
        actual_spec = str(u.EditorAssetLibrary.get_metadata_tag(instance, OWNER))
        actual_parent = _path(instance.get_editor_property('parent'))
        actual_values = _snapshot(instance)[2]
        differences = {}
        if actual_spec != spec:
            differences['metadata'] = {'before': spec, 'after': actual_spec}
        if actual_parent != _path(parent):
            differences['parent'] = {'before': _path(parent), 'after': actual_parent}
        for field, expected in values.items():
            if actual_values.get(field) != expected:
                differences[field] = {'before': expected, 'after': actual_values.get(field)}
        if differences:
            raise RuntimeError('Persistent material differs from assembled MID: ' + target
                               + ' ' + json.dumps(differences, sort_keys=True))
        if created and not u.EditorAssetLibrary.save_loaded_asset(instance, False):
            raise RuntimeError('Cannot save persistent material: ' + target)
        resolved[source] = instance
        visiting.remove(source)
        materials.append({'source_dynamic_material': source, 'material': _path(instance),
                          'parent': _path(parent), 'created': created,
                          'spec_sha256': digest, 'local_overrides': values})
        return instance

    for component in actor.get_components_by_class(u.SkeletalMeshComponent):
        for index in range(component.get_num_materials()):
            material = component.get_material(index)
            if isinstance(material, u.MaterialInstanceDynamic):
                pending.append((component, index, material, freeze(material)))
    bound = []
    try:
        for component, index, original, instance in pending:
            bound.append((component, index, original))
            component.set_material(index, instance)
            if component.get_material(index) != instance:
                raise RuntimeError('Persistent component material binding failed')
    except Exception:
        for component, index, original in reversed(bound):
            component.set_material(index, original)
        raise
    return {'version': VERSION, 'actor': _path(actor), 'asset_root': asset_root,
            'bindings': [{'component': _path(c), 'material_index': i,
                          'source_dynamic_material': _path(old), 'material': _path(new)}
                         for c, i, old, new in pending],
            'materials': materials, 'source_materials_modified': False,
            'map_saved': False, 'reload_verified': False}
