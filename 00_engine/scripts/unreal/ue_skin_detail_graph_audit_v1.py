"""Read-only RL_HQSkin graph/roughness audit. Inject Unreal; never open editor.

Local UE 5.8 MaterialEditingLibrary.cpp:1148 and :1262 directly read expressions;
their legacy header comments mentioning an active material editor are stale.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

RUN = Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/skin_detail_optimization_20261012_v1')
PROJECT = Path('D:/UE/projects/datatry_02')


def path(obj):
    return obj.get_path_name() if obj else None


def file_pin(asset):
    package = asset.get_path_name().split('.')[0]
    if not package.startswith('/Game/'):
        return None
    filename = PROJECT/'Content'/(package[6:]+'.uasset')
    return {'path': str(filename), 'sha256': hashlib.sha256(filename.read_bytes()).hexdigest()}


def value(v):
    if v is None or isinstance(v, (str, float, int, bool)):
        return v
    if hasattr(v, 'get_path_name'):
        return path(v)
    return str(v)


def properties(obj, names):
    result = {}
    for name in names:
        try:
            result[name] = value(obj.get_editor_property(name))
        except Exception:
            pass
    return result


def run(u, filename='roughness_graph_audit_v1.json'):
    if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
        raise ValueError('Wrong UE project')
    output = RUN/filename
    if output.parent != RUN or output.suffix != '.json' or output.exists():
        raise ValueError('Need a fresh owned JSON filename')
    lib = u.MaterialEditingLibrary
    material = u.load_asset('/Game/CC_Shaders/SkinShader/RL_HQSkin')
    before = file_pin(material)
    dirty_before = sorted(p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    graphs = {}

    def graph(owner):
        owner_path = path(owner)
        if owner_path in graphs:
            return
        if len(graphs) >= 128:
            raise RuntimeError('Unexpected material function graph count')
        is_material = isinstance(owner, u.Material)
        expressions = list(lib.get_material_expressions(owner) if is_material else lib.get_material_function_expressions(owner))
        result = {'path': owner_path, 'file': file_pin(owner), 'nodes': [], 'outputs': {}}
        graphs[owner_path] = result
        if is_material:
            for name in ['MP_ROUGHNESS', 'MP_SPECULAR', 'MP_NORMAL', 'MP_BASE_COLOR', 'MP_SUBSURFACE_COLOR', 'MP_MATERIAL_ATTRIBUTES']:
                prop = getattr(u.MaterialProperty, name, None)
                if prop is not None:
                    try:
                        node = lib.get_material_property_input_node(owner, prop)
                        result['outputs'][name] = {'node': path(node), 'output_name': lib.get_material_property_input_node_output_name(owner, prop)}
                    except Exception as exc:
                        result['outputs'][name] = {'error': str(exc)}
        for expr in expressions:
            node = {'path': path(expr), 'class': expr.get_class().get_name(), 'properties': properties(expr, (
                'parameter_name', 'default_value', 'desc', 'input_name', 'output_name', 'input_type',
                'preview_value', 'use_preview_value_as_default', 'const_a', 'const_b', 'const_alpha',
                'constant', 'min_default', 'max_default', 'r', 'g', 'b', 'a', 'texture', 'material_function',
                'sampler_type', 'sampler_source', 'sort_priority', 'group')), 'inputs': []}
            input_names = list(lib.get_material_expression_input_names(expr))
            links = list(lib.get_inputs_for_material_expression(owner, expr) if is_material else lib.get_inputs_for_material_function_expression(owner, expr))
            node['output_names'] = list(lib.get_material_expression_output_names(expr))
            for index, linked in enumerate(links):
                row = {'input_index': index, 'input_name': input_names[index] if index < len(input_names) else None,
                       'source_node': path(linked)}
                if linked is not None:
                    try:
                        row['source_output_name_first_matching_link'] = value(lib.get_input_node_output_name_for_material_expression(expr, linked))
                    except Exception as exc:
                        row['source_output_name_error'] = str(exc)
                node['inputs'].append(row)
            result['nodes'].append(node)
            function = node['properties'].get('material_function')
            if function:
                loaded = u.load_asset(function)
                if isinstance(loaded, u.MaterialFunction):
                    graph(loaded)
                else:
                    node['function_graph_unavailable'] = 'Not a concrete MaterialFunction'

    graph(material)
    # This closure is exact only within the parent graph. Function graph nodes
    # are separately recorded; do not interpret the whole function as executed.
    parent = graphs[path(material)]
    by_path = {n['path']: n for n in parent['nodes']}
    todo = [parent['outputs'].get('MP_ROUGHNESS', {}).get('node')]
    reachable = set()
    while todo:
        current = todo.pop()
        if current is None or current in reachable:
            continue
        reachable.add(current)
        todo.extend(row['source_node'] for row in by_path.get(current, {}).get('inputs', []))
    result = {'schema': 'skin_detail_roughness_graph_audit_v1', 'graphs': graphs,
              'roughness_parent_upstream_nodes': sorted(reachable),
              'scope': 'Read-only expression graph; static switches and scalar values must be evaluated separately per MIC. Duplicate input links may need output-index inspection.',
              'material_source': before}
    if file_pin(material) != before:
        raise RuntimeError('Parent material file changed')
    for entry in graphs.values():
        record = entry['file']
        if record and hashlib.sha256(Path(record['path']).read_bytes()).hexdigest() != record['sha256']:
            raise RuntimeError('Function material file changed')
    dirty_after = sorted(p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    if dirty_after != dirty_before:
        raise RuntimeError('Read-only graph audit changed dirty set')
    result['source_and_dirty_unchanged'] = True
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
    return {'success': True, 'path': str(output), 'graph_count': len(graphs),
            'node_count': sum(len(g['nodes']) for g in graphs.values()),
            'roughness_upstream_count': len(reachable)}
