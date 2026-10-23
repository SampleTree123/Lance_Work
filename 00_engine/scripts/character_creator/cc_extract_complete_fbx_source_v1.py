"""Read existing binary FBX meshes, Morph channels, materials and skeleton.

Source presence is distinct from meaningful position movement and UE import.
No CC/UE operations or exports. Reuses the project's binary FBX parser.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

import numpy as np

from cc_audit_headshot_fbx_v1 import read_nodes

POSITION_THRESHOLDS_CM = (0, 1e-8, 1e-4, 2e-4, 5e-4, 1e-3, 2e-3, 1e-2, .015)


def summarize_nodes(top):
    objects = {o['props'][0]: o for o in top['Objects']['children']}
    parents, children = defaultdict(list), defaultdict(list)
    for edge in top['Connections']['children']:
        values = edge['props']
        if values[0] == 'OO':
            parents[values[1]].append(values[2])
            children[values[2]].append(values[1])

    def name(obj):
        return obj['props'][1].split('\x00')[0]

    def kind(obj):
        return obj['props'][2] if len(obj['props']) > 2 else ''

    geometries = {oid: obj for oid, obj in objects.items()
                  if obj['name'] == 'Geometry' and kind(obj) == 'Mesh'}
    channels = defaultdict(list)
    for oid, obj in objects.items():
        if obj['name'] != 'Deformer' or kind(obj) != 'BlendShapeChannel':
            continue
        if len(parents[oid]) != 1 or len(parents[parents[oid][0]]) != 1:
            raise ValueError('Ambiguous Morph channel parent')
        geometry = parents[parents[oid][0]][0]
        if geometry not in geometries:
            raise ValueError('Morph channel not linked to a mesh')
        maxima, shapes = [], []
        for shape_id in children[oid]:
            shape = objects.get(shape_id)
            if not shape or shape['name'] != 'Geometry' or kind(shape) != 'Shape':
                continue
            raw = next(n['props'][0] for n in shape['children'] if n['name'] == 'Vertices')
            vertices = np.asarray(raw, dtype=float)
            if vertices.ndim != 1 or len(vertices) % 3 or not np.isfinite(vertices).all():
                raise ValueError('Invalid/nonfinite FBX shape delta')
            vertices = vertices.reshape(-1, 3)
            maxima.append(float(np.linalg.norm(vertices, axis=1).max()) if len(vertices) else 0)
            shapes.append(name(shape))
        channels[geometry].append({'name': name(obj), 'shapes': shapes,
                                   'max_position_delta_cm': max(maxima, default=0)})

    meshes = []
    for oid, obj in geometries.items():
        models = [p for p in parents[oid] if p in objects and objects[p]['name'] == 'Model']
        if len(models) != 1:
            raise ValueError('Mesh must have exactly one model parent')
        materials = [name(objects[c]) for c in children[models[0]] if c in objects and objects[c]['name'] == 'Material']
        rows = sorted(channels[oid], key=lambda row: row['name'])
        names = [row['name'] for row in rows]
        meshes.append({'source_name': name(obj), 'model_name': name(objects[models[0]]),
            'fbx_morph_names': names, 'morph_channel_count': len(rows),
            'expected_nonzero_morph_names': [row['name'] for row in rows if row['max_position_delta_cm'] > 1e-8],
            'expected_materials': materials, 'morph_position_deltas': rows,
            'position_delta_audit': [{'threshold_cm': threshold, 'channel_count': sum(row['max_position_delta_cm'] > threshold for row in rows)}
                                    for threshold in POSITION_THRESHOLDS_CM]})
    bones = []
    for oid, obj in objects.items():
        if obj['name'] == 'Model' and kind(obj) == 'LimbNode':
            p = [p for p in parents[oid] if p in objects and objects[p]['name'] == 'Model']
            bones.append({'name': name(obj), 'parent': name(objects[p[0]]) if p else None})
    return {'expected_meshes': meshes, 'bone_count': len(bones), 'bones': sorted(bones, key=lambda row: row['name']),
            'scope': 'Existing FBX source data only. Tiny nonzero deltas may be float noise. Listed thresholds are an audit sweep, not an asserted UE default or an acceptance exemption.'}


def extract(path):
    path = Path(path).resolve()
    version, nodes = read_nodes(path)
    result = summarize_nodes(nodes)
    result.update(schema_version=1, fbx_version=version,
                  source={'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = extract(args.input)
    with Path(args.output).open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
    print(json.dumps({'source': result['source'], 'bone_count': result['bone_count'], 'mesh_count': len(result['expected_meshes'])}))
